from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from models import db, User, Product, UserPreference, RecommendationFeedback, AISearchEvent, PurchaseEvent, SearchEvent
from services.ai_search import AISearchService
from services.scraper import ScraperManager
from services.recommender import ProductRecommender
from datetime import datetime
from functools import wraps
import logging
import concurrent.futures
import time
import threading
import re
import json
from collections import defaultdict
from config import Config

logger = logging.getLogger(__name__)

def get_memory_usage():
    try:
        import os
        if os.path.exists('/proc/self/status'):
            with open('/proc/self/status', 'r') as f:
                for line in f:
                    if line.startswith('VmRSS:'):
                        return line.split()[1] + ' KB'
        import resource
        rusage_self = resource.getrusage(resource.RUSAGE_SELF)
        return f"{rusage_self.ru_maxrss} KB"
    except Exception:
        return "Unknown"

def diversify_by_platform(products, target_count=20):
    """
    Selects up to target_count products from the list, ensuring that no single platform 
    occupies more than 40% of the final results (i.e. max 8 out of 20) 
    unless other platforms are exhausted.
    """
    if not products:
        return []
        
    platform_groups = {}
    for p in products:
        plat = (p.get('platform') or 'Unknown').lower().strip()
        if plat not in platform_groups:
            platform_groups[plat] = []
        platform_groups[plat].append(p)
        
    cap_limit = int(target_count * 0.4)
    if cap_limit < 1:
        cap_limit = 1
        
    selected_products = []
    platform_counts = {plat: 0 for plat in platform_groups}
    
    while len(selected_products) < target_count:
        available_platforms = [
            plat for plat, items in platform_groups.items() 
            if items and platform_counts[plat] < cap_limit
        ]
        
        if not available_platforms:
            available_platforms = [
                plat for plat, items in platform_groups.items() if items
            ]
            
        if not available_platforms:
            break
            
        best_plat = max(
            available_platforms,
            key=lambda plat: platform_groups[plat][0].get('combined_score') or platform_groups[plat][0].get('score') or 0
        )
        
        item = platform_groups[best_plat].pop(0)
        selected_products.append(item)
        platform_counts[best_plat] += 1
        
    return selected_products

search_bp = Blueprint('search', __name__)
ai_search_service = AISearchService()
scraper_manager = ScraperManager()
recommender = ProductRecommender()
from services.search_orchestrator import SearchOrchestrator
search_orchestrator = SearchOrchestrator()

CATEGORY_MAP = {
    "shirt": ["shirt", "shirts", "tshirt", "t-shirt", "formal shirt", "casual shirt"],
    "watch": ["watch", "watches", "smartwatch"],
    "headphone": ["headphone", "earphone", "earbud", "earbuds"],
    "mobile_cover": ["cover", "case", "mobile cover"],
    "laptop": ["laptop", "laptops", "notebook", "notebooks", "macbook", "chromebook"],
    "shoes": ["shoe", "shoes", "sneaker", "sneakers", "running shoes", "sports shoes"]
}

def detect_category_from_query(query):
    if not query:
        return None
    query_lower = query.lower()
    for cat, synonyms in CATEGORY_MAP.items():
        for syn in synonyms:
            if syn in query_lower:
                return cat
    return None

def product_matches_category(product, category):
    if not category:
        return True
        
    cat_lower = category.lower().strip()
    
    # Normalize category to map key
    map_key = None
    if cat_lower in ["shirt", "shirts", "tshirt", "t-shirt", "clothing", "fashion"]:
        map_key = "shirt"
    elif cat_lower in ["watch", "watches", "smartwatch"]:
        map_key = "watch"
    elif cat_lower in ["headphone", "headphones", "earphone", "earphones", "earbud", "earbuds", "audio"]:
        map_key = "headphone"
    elif cat_lower in ["cover", "covers", "case", "cases", "mobile cover", "mobile_cover"]:
        map_key = "mobile_cover"
    elif cat_lower in ["laptop", "laptops", "notebook", "notebooks", "macbook", "chromebook"]:
        map_key = "laptop"
    elif cat_lower in ["shoes", "shoe", "sneaker", "sneakers", "running shoes", "sports shoes"]:
        map_key = "shoes"
        
    if not map_key:
        return True
        
    allowed_keywords = CATEGORY_MAP[map_key]
    
    p_name = (product.get('name') or '').lower()
    p_cat = (product.get('category') or '').lower()
    
    has_allowed = False
    for kw in allowed_keywords:
        if kw in p_name or kw in p_cat:
            has_allowed = True
            break
            
    if not has_allowed:
        return False
        
    # Exclude other mapped categories to keep it pure
    for other_key, other_kws in CATEGORY_MAP.items():
        if other_key == map_key:
            continue
        for kw in other_kws:
            if kw in p_name:
                return False
                
    return True


search_status_store = {}
search_status_lock = threading.Lock()

def update_search_status(search_id, updates):
    if not search_id:
        return
    with search_status_lock:
        if search_id not in search_status_store:
            search_status_store[search_id] = {
                "status": "searching",
                "platforms": {},
                "stage": "initializing",
                "updated_at": time.time()
            }
        if "platforms" in updates:
            if "platforms" not in search_status_store[search_id]:
                search_status_store[search_id]["platforms"] = {}
            search_status_store[search_id]["platforms"].update(updates["platforms"])
        for k, v in updates.items():
            if k != "platforms":
                search_status_store[search_id][k] = v
        search_status_store[search_id]["updated_at"] = time.time()

def clean_stale_search_statuses():
    now = time.time()
    with search_status_lock:
        to_delete = [sid for sid, status in search_status_store.items() if now - status.get("updated_at", 0) > 600]
        for sid in to_delete:
            del search_status_store[sid]

# In-memory rate limiting dictionary (User ID or IP -> list of request timestamps)
ai_rate_limit_store = defaultdict(list)

def check_ai_rate_limit(key):
    now = time.time()
    # clean up older timestamps (> 60 seconds)
    ai_rate_limit_store[key] = [t for t in ai_rate_limit_store[key] if now - t < 60]
    if len(ai_rate_limit_store[key]) >= 15:  # 15 requests per minute for unified search
        return False
    ai_rate_limit_store[key].append(now)
    return True

def get_optional_user():
    """Retrieve optional user from JWT token"""
    try:
        verify_jwt_in_request(optional=True)
        user_id = get_jwt_identity()
        if user_id:
            return db.session.query(User).get(user_id)
    except Exception:
        pass
    return None

def require_auth(fn):
    """Decorator to verify JWT and attach user to request.user"""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            user = db.session.query(User).get(user_id)
            if not user:
                return jsonify({"success": False, "message": "User not found"}), 401
            if not user.is_active:
                return jsonify({"success": False, "message": "Account disabled. Please contact support."}), 403
            request.user = user
            return fn(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Auth required check failed: {e}")
            return jsonify({"success": False, "message": "Invalid or expired token"}), 401
    return wrapper

def is_conversational_query(query):
    """Classify if search query is conversational/natural language vs simple keywords"""
    query_clean = query.strip().lower()
    words = query_clean.split()
    
    # 1. More than 3 words is usually conversational
    if len(words) > 3:
        return True
        
    # 2. Key conversational trigger words
    conversational_triggers = {
        'need', 'looking', 'suggest', 'comfortable', 'under', 'cheap', 'best', 
        'around', 'for', 'with', 'buy', 'show', 'find', 'recommend', 'good', 
        'battery', 'camera', 'budget', 'premium', 'software', 'coding', 'gaming',
        'about', 'below', 'above', 'want', 'laptop', 'phone', 'shoe', 'shoes'
    }
    
    # If the query contains any conversational modifier words, classify as conversational
    conversational_modifiers = {
        'need', 'looking', 'suggest', 'comfortable', 'under', 'cheap', 'best', 
        'around', 'for', 'with', 'buy', 'show', 'find', 'recommend', 'good', 
        'battery', 'camera', 'budget', 'premium', 'software', 'coding', 'gaming',
        'about', 'below', 'above', 'want'
    }
    if any(w in conversational_modifiers for w in words):
        return True
        
    return False

def handle_ai_search_pipeline(query, filters, user, search_id=None):
    """Runs the AI search intent extraction, hybrid ranking, and diversity logic"""
    start_total_time = time.time()
    try:
        user_context_str = None
        purchased_urls = set()
        user_pref = None
        if user:
            user_context_str = ai_search_service.compile_user_context(user.id)
            user_pref = db.session.query(UserPreference).filter_by(user_id=user.id).first()
            # Compile purchases to exclude them from search results
            purchased_events = db.session.query(PurchaseEvent).filter_by(user_id=user.id).all()
            for pe in purchased_events:
                if pe.product:
                    purchased_urls.add(pe.product.product_url.lower())
                    
        # Extract Structured Intent using SearchOrchestrator
        intent = search_orchestrator.parse_query_intent(query, user_context_str)
        confidence = intent.get('confidence', 0.5)
        rewritten_q = intent.get('rewritten_query') or query
        
        # Search local database first
        local_products = []
        category = intent.get('category')
        brand = intent.get('brand')
        budget_min = intent.get('budget_min')
        budget_max = intent.get('budget_max')
        platform = intent.get('platform')
        rating = intent.get('rating')
        
        platforms_to_search = ['amazon', 'flipkart', 'myntra', 'meesho']
        if platform and platform.lower() in ['amazon', 'flipkart', 'myntra', 'meesho']:
            platforms_to_search = [platform.lower()]
        platform_status = {p: "success" for p in platforms_to_search}
        
        if search_id:
            clean_stale_search_statuses()
            update_search_status(search_id, {
                "status": "searching",
                "platforms": {p: "pending" for p in platforms_to_search},
                "stage": "initializing"
            })
            
        db_query = db.session.query(Product).filter(Product.price.isnot(None), Product.price > 0)
        if category:
            cat_lower = category.lower().strip()
            synonyms = [cat_lower]
            for key, syns in recommender.CATEGORY_SYNONYMS.items():
                if key == cat_lower or cat_lower in syns or any(syn in cat_lower for syn in syns):
                    synonyms = list(set([key] + syns))
                    break
            conditions = []
            for syn in synonyms:
                conditions.append(Product.category.ilike(f"%{syn}%"))
                conditions.append(Product.name.ilike(f"%{syn}%"))
            db_query = db_query.filter(db.or_(*conditions))
        if brand:
            db_query = db_query.filter(Product.brand.ilike(f"%{brand}%") | Product.name.ilike(f"%{brand}%"))
        if budget_min is not None:
            db_query = db_query.filter(Product.price >= budget_min)
        if budget_max is not None:
            db_query = db_query.filter(Product.price <= budget_max)
        if platform:
            db_query = db_query.filter(Product.platform.ilike(f"%{platform}%"))
        if rating is not None:
            db_query = db_query.filter(Product.rating >= rating)
            
        local_products = db_query.limit(50).all()
        
        # Fallback/supplemental DB search
        if confidence < 0.60 or len(local_products) < 10:
            words = rewritten_q.split()
            keyword_filters = []
            for w in words:
                if len(w) > 2:
                    keyword_filters.append(Product.name.ilike(f"%{w}%") | Product.description.ilike(f"%{w}%"))
            
            if keyword_filters:
                supplemental_query = db.session.query(Product).filter(Product.price.isnot(None), Product.price > 0)
                combined_or = keyword_filters[0]
                for f in keyword_filters[1:]:
                    combined_or = combined_or | f
                supplemental_query = supplemental_query.filter(combined_or)
                
                existing_ids = {p.id for p in local_products}
                if existing_ids:
                    supplemental_query = supplemental_query.filter(Product.id.not_in(existing_ids))
                    
                supplemental_results = supplemental_query.limit(30).all()
                local_products = list(local_products) + list(supplemental_results)
                
        products_list = [p.to_dict() for p in local_products]
        
        # Apply category validation to cache products list before checking scraper threshold
        detected_category = category or detect_category_from_query(query)
        logger.info(f"AI Search Category Filtering: Detected category '{detected_category}'")
        if detected_category:
            from services.category_filter import CategoryRelevanceFilter
            products_list = [p for p in products_list if product_matches_category(p, detected_category)]
            products_list = [p for p in products_list if not CategoryRelevanceFilter.is_irrelevant(p, detected_category, query.lower())]
        
        # Platform scraper fallback if local products < 10
        if len(products_list) < 10:
            if search_id:
                update_search_status(search_id, {
                    "stage": "scraping"
                })
            scraped_results = []
            for plat in platforms_to_search:
                if search_id:
                    update_search_status(search_id, {
                        "platforms": {plat: "searching"}
                    })
                start_time = time.time()
                mem_before = get_memory_usage()
                logger.info(f"[Scraper Start] Platform: {plat}, Memory: {mem_before}")
                try:
                    scraped = scraper_manager.scrape_platform_realtime(plat, rewritten_q, 15)
                    scraped_results.extend(scraped or [])
                    platform_status[plat] = "success"
                    if search_id:
                        update_search_status(search_id, {
                            "platforms": {plat: "complete"}
                        })
                    duration = time.time() - start_time
                    mem_after = get_memory_usage()
                    logger.info(f"[Scraper End] Platform: {plat}, Status: success, Duration: {duration:.2f}s, Count: {len(scraped or [])}, Memory: {mem_after}")
                except Exception as exc:
                    duration = time.time() - start_time
                    mem_after = get_memory_usage()
                    logger.error(f"[Scraper End] Platform: {plat}, Status: failed, Duration: {duration:.2f}s, Memory: {mem_after}, Error: {exc}", exc_info=True)
                    platform_status[plat] = "failed"
                    if search_id:
                        update_search_status(search_id, {
                            "platforms": {plat: "failed"}
                        })
                    
            seen_urls = {p.get('product_url', '').lower() for p in products_list}
            for sp in scraped_results:
                url = sp.get('product_url', '').lower()
                if url and url not in seen_urls:
                    if detected_category:
                        from services.category_filter import CategoryRelevanceFilter
                        if not product_matches_category(sp, detected_category):
                            continue
                        if CategoryRelevanceFilter.is_irrelevant(sp, detected_category, query.lower()):
                            continue
                    seen_urls.add(url)
                    products_list.append(sp)
        else:
            if search_id:
                update_search_status(search_id, {
                    "platforms": {p: "cached" for p in platforms_to_search}
                })
                    
        # Content relevance ranking
        if search_id:
            update_search_status(search_id, {
                "stage": "ranking"
            })

        recommender_filters = {
            'min_price': budget_min,
            'max_price': budget_max,
            'min_rating': rating,
            'category': category,
            'purpose': intent.get('purpose'),
            'confidence': confidence,
            'user_id': user.id if user else None,
            'user_pref': user_pref,
            'is_ai': True
        }
        ranked_products = recommender.rank_products_realtime(rewritten_q, products_list, recommender_filters)
        removed_irrelevant = recommender.get_last_removed_count()
        
        # Exclude purchased products
        final_products = []
        for p in ranked_products:
            p_url = p.get('product_url', '').lower()
            if p_url in purchased_urls:
                continue
            final_products.append(p)
            
        final_results = diversify_by_platform(final_products, 20)
        
        # Diagnostics Logging
        amazon_products = [p for p in products_list if (p.get('platform') or '').lower() == 'amazon']
        flipkart_products = [p for p in products_list if (p.get('platform') or '').lower() == 'flipkart']
        myntra_products = [p for p in products_list if (p.get('platform') or '').lower() == 'myntra']
        meesho_products = [p for p in products_list if (p.get('platform') or '').lower() == 'meesho']
        
        logger.info(f"Amazon products before ranking: {len(amazon_products)}")
        logger.info(f"Flipkart products before ranking: {len(flipkart_products)}")
        logger.info(f"Myntra products before ranking: {len(myntra_products)}")
        logger.info(f"Meesho products before ranking: {len(meesho_products)}")
        logger.info(f"Total Products Before Ranking: {len(products_list)}")
        logger.info(f"Total Products After Ranking: {len(final_results)}")
        
        # Log structured Search Quality Metrics
        logger.info(json.dumps({
            "query": query,
            "gemini_used": intent.get("gemini_used", False),
            "category": category,
            "confidence": confidence,
            "removed_irrelevant": removed_irrelevant,
            "amazon_count": len(amazon_products),
            "flipkart_count": len(flipkart_products),
            "myntra_count": len(myntra_products),
            "meesho_count": len(meesho_products),
            "total_scraped": len(products_list),
            "ranked_results": len(final_results)
        }))
        
        explanation_bullets = intent.get('search_explanation_bullets', [])
        explanation_str = " | ".join(explanation_bullets) if explanation_bullets else f"Showing products matching '{query}'"
        
        new_event = AISearchEvent(
            user_id=user.id if user else None,
            query=query,
            rewritten_query=rewritten_q,
            confidence_score=confidence,
            extracted_intent=intent,
            search_explanation=explanation_str,
            results_count=len(final_results),
            is_success=True,
            created_at=datetime.utcnow()
        )
        db.session.add(new_event)
        db.session.commit()
        
        if search_id:
            update_search_status(search_id, {
                "status": "complete",
                "stage": "complete"
            })
            
        # Logging backend execution details for audit
        duration_total = time.time() - start_total_time
        mem_final = get_memory_usage()
        logger.info(f"=== SEARCH COMPLETED (AI) ===\n"
                    f"Query: {query}\n"
                    f"Products Found: {len(final_results)}\n"
                    f"Platform Status: {platform_status}\n"
                    f"Execution Time: {duration_total:.2f}s\n"
                    f"Memory Usage: {mem_final}\n"
                    f"=============================")
        
        return {
            "success": True,
            "is_ai": True,
            "event_id": new_event.id,
            "intent": intent,
            "confidence": confidence,
            "search_explanation": explanation_str,
            "products": final_results,
            "results": final_results,
            "alternative_products": [],
            "suggested_queries": intent.get('refinements', []),
            "platform_status": platform_status
        }
    except Exception as e:
        if search_id:
            update_search_status(search_id, {
                "status": "failed",
                "stage": "failed"
            })
        logger.error(f"Error in handle_ai_search_pipeline: {e}", exc_info=True)
        raise e

def handle_keyword_search_pipeline(query, filters, user, search_id=None):
    """Runs the standard keyword search, parallel platform scrapers, and interleaving"""
    start_total_time = time.time()
    try:
        query_lower = query.lower()
        electronics_set = {'laptop', 'phone', 'mobile', 'macbook', 'ipad', 'tablet', 'desktop', 'monitor', 'gpu', 'cpu', 'camera', 'tv'}
        fashion_set = {'shirt', 'tshirt', 'pant', 'jeans', 'shoe', 'sneaker', 'dress', 'saree', 'kurti', 'jacket', 'hoodie', 'sweater', 'bag', 'backpack'}
        
        has_electronics = any(e in query_lower for e in electronics_set)
        has_fashion = any(f in query_lower for f in fashion_set)
        
        requested_input = filters.get('platforms')
        if not requested_input:
            platforms_to_search = ['amazon', 'flipkart', 'myntra', 'meesho']
        else:
            platforms_to_search = [p.strip().lower() for p in requested_input if isinstance(p, str) and p.strip().lower() in ['amazon', 'flipkart', 'myntra', 'meesho']]
            if not platforms_to_search:
                platforms_to_search = ['amazon', 'flipkart', 'myntra', 'meesho']
                
        all_products = []
        platform_status = {p: "success" for p in platforms_to_search}
        
        if search_id:
            clean_stale_search_statuses()
            update_search_status(search_id, {
                "status": "searching",
                "platforms": {p: "pending" for p in platforms_to_search},
                "stage": "initializing"
            })
            
        # Search local database first
        local_products = []
        words = query_lower.split()
        meaningful_words = [w for w in words if w not in recommender.STOP_WORDS and len(w) > 2]
        if not meaningful_words:
            meaningful_words = [w for w in words if len(w) > 2]
            
        if meaningful_words:
            db_query = db.session.query(Product).filter(Product.price.isnot(None), Product.price > 0)
            
            # Check if the query indicates a category intent
            intent_cat = None
            for key, synonyms in recommender.CATEGORY_SYNONYMS.items():
                if key in query_lower or any(re.search(r'\b' + re.escape(syn) + r'\b', query_lower) for syn in synonyms):
                    intent_cat = key
                    break
                    
            if intent_cat:
                cat_syns = list(set([intent_cat] + recommender.CATEGORY_SYNONYMS[intent_cat]))
                conditions = []
                for syn in cat_syns:
                    conditions.append(Product.category.ilike(f"%{syn}%"))
                    conditions.append(Product.name.ilike(f"%{syn}%"))
                db_query = db_query.filter(db.or_(*conditions))
            else:
                conditions = []
                for w in meaningful_words:
                    conditions.append(Product.name.ilike(f"%{w}%") | Product.description.ilike(f"%{w}%") | Product.category.ilike(f"%{w}%"))
                db_query = db_query.filter(db.or_(*conditions))
                
            local_products = db_query.limit(50).all()
            
        all_products = [p.to_dict() for p in local_products]
        
        # Apply category validation to cache products list before checking scraper threshold
        detected_category = detect_category_from_query(query)
        logger.info(f"Keyword Search Category Filtering: Detected category '{detected_category}'")
        if detected_category:
            from services.category_filter import CategoryRelevanceFilter
            all_products = [p for p in all_products if product_matches_category(p, detected_category)]
            all_products = [p for p in all_products if not CategoryRelevanceFilter.is_irrelevant(p, detected_category, query.lower())]
            
        # Run scrapers as fallback/supplement if local products < 10
        if len(all_products) < 10:
            if search_id:
                update_search_status(search_id, {
                    "stage": "scraping"
                })
            scraped_results = []
            for platform in platforms_to_search:
                if search_id:
                    update_search_status(search_id, {
                        "platforms": {platform: "searching"}
                    })
                start_time = time.time()
                mem_before = get_memory_usage()
                logger.info(f"[Scraper Start] Platform: {platform}, Memory: {mem_before}")
                try:
                    products = scraper_manager.scrape_platform_realtime(platform, query, 15)
                    scraped_results.extend(products or [])
                    platform_status[platform] = "success"
                    if search_id:
                        update_search_status(search_id, {
                            "platforms": {platform: "complete"}
                        })
                    duration = time.time() - start_time
                    mem_after = get_memory_usage()
                    logger.info(f"[Scraper End] Platform: {platform}, Status: success, Duration: {duration:.2f}s, Count: {len(products or [])}, Memory: {mem_after}")
                except Exception as e:
                    duration = time.time() - start_time
                    mem_after = get_memory_usage()
                    logger.error(f"[Scraper End] Platform: {platform}, Status: failed, Duration: {duration:.2f}s, Memory: {mem_after}, Error: {e}", exc_info=True)
                    platform_status[platform] = "failed"
                    if search_id:
                        update_search_status(search_id, {
                            "platforms": {platform: "failed"}
                        })
                
            seen_urls = {p.get('product_url', '').lower() for p in all_products}
            for sp in scraped_results:
                url = sp.get('product_url', '').lower()
                if url and url not in seen_urls:
                    if detected_category:
                        from services.category_filter import CategoryRelevanceFilter
                        if not product_matches_category(sp, detected_category):
                            continue
                        if CategoryRelevanceFilter.is_irrelevant(sp, detected_category, query.lower()):
                            continue
                    seen_urls.add(url)
                    all_products.append(sp)
        else:
            if search_id:
                update_search_status(search_id, {
                    "platforms": {p: "cached" for p in platforms_to_search}
                })
                    
        # Deduplicate
        deduped = []
        seen_urls = set()
        seen_names = set()
        for p in all_products:
            url = p.get('product_url')
            name_key = re.sub(r'[^a-zA-Z0-9]', '', p.get('name', '').lower())[:30]
            if not url or url in seen_urls or name_key in seen_names:
                continue
            seen_urls.add(url)
            if len(name_key) > 5:
                seen_names.add(name_key)
            deduped.append(p)
        all_products = deduped
        
        normalized_filters = {
            'min_price': filters.get('min_price') if filters.get('min_price') is not None else filters.get('minPrice'),
            'max_price': filters.get('max_price') if filters.get('max_price') is not None else filters.get('maxPrice'),
            'min_rating': filters.get('min_rating') if filters.get('min_rating') is not None else filters.get('minRating'),
            'platforms': filters.get('platforms') if filters.get('platforms') is not None else filters.get('platforms')
        }
        
        filtered_products = []
        requested_normalized = [p.lower() for p in platforms_to_search]
        for p in all_products:
            p_platform = (p.get('platform') or '').lower()
            if requested_normalized and p_platform not in requested_normalized:
                continue
                
            min_rating = normalized_filters.get('min_rating')
            if min_rating is not None and min_rating != '':
                try:
                    p_rating = float(p.get('rating') or 0)
                    if p_rating > 0 and p_rating < float(min_rating):
                        continue
                except (ValueError, TypeError):
                    pass
                    
            p_price = p.get('price')
            if p_price is not None:
                try:
                    p_price_float = float(p_price)
                    min_price = normalized_filters.get('min_price')
                    if min_price is not None and min_price != '':
                        if p_price_float < float(min_price):
                            continue
                    max_price = normalized_filters.get('max_price')
                    if max_price is not None and max_price != '':
                        if p_price_float > float(max_price):
                            continue
                except (ValueError, TypeError):
                    pass
            filtered_products.append(p)

        if search_id:
            update_search_status(search_id, {
                "stage": "ranking"
            })
            
        if not isinstance(filters, dict):
            filters = {}
        else:
            filters = dict(filters)
        filters['is_ai'] = False
        
        ranked_products = recommender.rank_products_realtime(query, filtered_products, filters)
        removed_irrelevant = recommender.get_last_removed_count()
        
        for idx, p in enumerate(ranked_products):
            if 'id' not in p or not p.get('id'):
                p['id'] = hash(p.get('product_url', f'product_{idx}')) % 1000000
                
        interleaved_results = diversify_by_platform(ranked_products, 20)
        
        # Diagnostics Logging
        amazon_products = [p for p in filtered_products if (p.get('platform') or '').lower() == 'amazon']
        flipkart_products = [p for p in filtered_products if (p.get('platform') or '').lower() == 'flipkart']
        myntra_products = [p for p in filtered_products if (p.get('platform') or '').lower() == 'myntra']
        meesho_products = [p for p in filtered_products if (p.get('platform') or '').lower() == 'meesho']
        
        logger.info(f"Amazon products before ranking: {len(amazon_products)}")
        logger.info(f"Flipkart products before ranking: {len(flipkart_products)}")
        logger.info(f"Myntra products before ranking: {len(myntra_products)}")
        logger.info(f"Meesho products before ranking: {len(meesho_products)}")
        logger.info(f"Total Products Before Ranking: {len(filtered_products)}")
        logger.info(f"Total Products After Ranking: {len(interleaved_results)}")
        
        # Log structured Search Quality Metrics
        logger.info(json.dumps({
            "query": query,
            "gemini_used": False,
            "category": detected_category,
            "confidence": 1.0,
            "removed_irrelevant": removed_irrelevant,
            "amazon_count": len(amazon_products),
            "flipkart_count": len(flipkart_products),
            "myntra_count": len(myntra_products),
            "meesho_count": len(meesho_products),
            "total_scraped": len(filtered_products),
            "ranked_results": len(interleaved_results)
        }))
        
        # Store standard search history
        if user:
            try:
                last_event = db.session.query(SearchEvent).filter(SearchEvent.user_id == user.id).order_by(SearchEvent.created_at.desc()).first()
                if not last_event or last_event.query != query or (datetime.utcnow() - last_event.created_at).total_seconds() >= 10:
                    event = SearchEvent(
                        user_id=user.id,
                        query=str(query)[:300],
                        filters_json=json.dumps(normalized_filters),
                        results_count=len(interleaved_results)
                    )
                    db.session.add(event)
                    db.session.commit()
            except Exception as se:
                logger.error(f"Failed to save standard history: {se}")
                db.session.rollback()
                
        if search_id:
            update_search_status(search_id, {
                "status": "complete",
                "stage": "complete"
            })
            
        # Logging backend execution details for audit
        duration_total = time.time() - start_total_time
        mem_final = get_memory_usage()
        logger.info(f"=== SEARCH COMPLETED (KEYWORD) ===\n"
                    f"Query: {query}\n"
                    f"Products Found: {len(interleaved_results)}\n"
                    f"Platform Status: {platform_status}\n"
                    f"Execution Time: {duration_total:.2f}s\n"
                    f"Memory Usage: {mem_final}\n"
                    f"=============================")
                    
        return {
            "success": True,
            "is_ai": False,
            "products": interleaved_results,
            "results": interleaved_results,
            "alternative_products": [],
            "suggested_queries": [],
            "platform_status": platform_status
        }
    except Exception as e:
        if search_id:
            update_search_status(search_id, {
                "status": "failed",
                "stage": "failed"
            })
        logger.error(f"Error in handle_keyword_search_pipeline: {e}", exc_info=True)
        raise e

@search_bp.route('/api/search/status', methods=['GET'])
def get_search_status():
    """Returns the current real-time scraper progress status for a search_id"""
    search_id = request.args.get('search_id')
    if not search_id:
        return jsonify({"success": False, "message": "search_id is required"}), 400
        
    with search_status_lock:
        status = search_status_store.get(search_id)
        
    if not status:
        return jsonify({
            "success": True,
            "status": "pending",
            "platforms": {},
            "stage": "initializing"
        }), 200
        
    return jsonify({
        "success": True,
        "status": status.get("status"),
        "platforms": status.get("platforms"),
        "stage": status.get("stage")
    }), 200

@search_bp.route('/api/search', methods=['GET', 'POST'])
def search_unified():
    """Unified Search Router dynamically redirecting conversational query vs keyword query"""
    try:
        ip_addr = request.remote_addr or 'unknown'
        user = get_optional_user()
        rate_limit_key = f"user_{user.id}" if user else f"ip_{ip_addr}"
        
        if not check_ai_rate_limit(rate_limit_key):
            return jsonify({
                "success": False,
                "message": "Too many requests. Please slow down."
            }), 429
            
        # Parse inputs
        if request.method == 'POST':
            data = request.get_json() or {}
            query = data.get('query', '').strip()
            filters = data.get('filters', {})
            search_id = data.get('search_id')
        else:
            query = request.args.get('query', '').strip()
            search_id = request.args.get('search_id')
            filters = {
                'min_price': request.args.get('min_price', type=float),
                'max_price': request.args.get('max_price', type=float),
                'platforms': request.args.getlist('platform'),
                'min_rating': request.args.get('min_rating', type=float)
            }
            
        if not query:
            return jsonify({"success": False, "message": "Query parameter is required."}), 400
            
        if len(query) > 500:
            return jsonify({"success": False, "message": "Query is too long."}), 400
            
        # Router Condition
        if is_conversational_query(query):
            logger.info(f"Unified Search: Routing conversational query '{query}' to AI Search pipeline...")
            res_payload = handle_ai_search_pipeline(query, filters, user, search_id)
        else:
            logger.info(f"Unified Search: Routing keyword query '{query}' to standard Search pipeline...")
            res_payload = handle_keyword_search_pipeline(query, filters, user, search_id)
            
        return jsonify(res_payload), 200
        
    except Exception as e:
        logger.error(f"Error in unified search router: {e}", exc_info=True)
        return jsonify({"success": False, "message": "An error occurred during search execution."}), 500

@search_bp.route('/api/search/ai', methods=['POST'])
def search_ai():
    """AI Search Endpoint direct access fallback for compatibility with existing tests"""
    try:
        user = get_optional_user()
        data = request.get_json() or {}
        query = data.get('query', '').strip()
        filters = data.get('filters', {})
        search_id = data.get('search_id')
        res_payload = handle_ai_search_pipeline(query, filters, user, search_id)
        return jsonify(res_payload), 200
    except Exception as e:
        logger.error(f"Error in legacy search_ai endpoint: {e}")
        return jsonify({"success": False, "message": "Error running AI search."}), 500

@search_bp.route('/api/search/ai/<int:event_id>/feedback', methods=['POST'])
def submit_ai_feedback(event_id):
    """Submit user feedback ('helpful' / 'not_helpful') for an AI search event"""
    try:
        data = request.get_json() or {}
        feedback_type = data.get('feedback', '').strip().lower()
        
        if feedback_type not in ['helpful', 'not_helpful']:
            return jsonify({"success": False, "message": "Feedback type must be 'helpful' or 'not_helpful'."}), 400
            
        event = db.session.query(AISearchEvent).get(event_id)
        if not event:
            return jsonify({"success": False, "message": "AI Search Event not found."}), 404
            
        event.feedback = feedback_type
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Feedback submitted successfully.",
            "data": event.to_dict()
        }), 200
    except Exception as e:
        logger.error(f"Error submitting AI search feedback: {e}")
        return jsonify({"success": False, "message": "Internal server error."}), 500

@search_bp.route('/api/dashboard/ai-search-analytics', methods=['GET'])
@require_auth
def get_ai_search_analytics():
    """Fetch AI Search history and metrics for personal User Dashboard"""
    try:
        user_id = request.user.id
        
        # Retrieve recent search events
        events = db.session.query(AISearchEvent).filter_by(user_id=user_id).order_by(AISearchEvent.created_at.desc()).limit(50).all()
        events_list = [e.to_dict() for e in events]
        
        # Calculate summary statistics
        total_searches = len(events_list)
        helpful_count = sum(1 for e in events_list if e.get('feedback') == 'helpful')
        not_helpful_count = sum(1 for e in events_list if e.get('feedback') == 'not_helpful')
        
        # Calculate category distribution
        categories = {}
        for e in events_list:
            cat = e.get('extracted_intent', {}).get('category')
            if cat:
                categories[cat] = categories.get(cat, 0) + 1
                
        category_distribution = [{"category": k, "count": v} for k, v in categories.items()]
        
        return jsonify({
            "success": True,
            "data": {
                "events": events_list,
                "stats": {
                    "total_searches": total_searches,
                    "helpful_count": helpful_count,
                    "not_helpful_count": not_helpful_count,
                    "satisfaction_rate": round(helpful_count / max(1, helpful_count + not_helpful_count) * 100, 2)
                },
                "category_distribution": category_distribution
            }
        }), 200
    except Exception as e:
        logger.error(f"Error fetching personal AI search analytics: {e}")
        return jsonify({"success": False, "message": "Internal server error."}), 500
