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
import re
import json
from collections import defaultdict
from config import Config

logger = logging.getLogger(__name__)
search_bp = Blueprint('search', __name__)
ai_search_service = AISearchService()
scraper_manager = ScraperManager()
recommender = ProductRecommender()

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

def handle_ai_search_pipeline(query, filters, user):
    """Runs the AI search intent extraction, hybrid ranking, and diversity logic"""
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
                
    # Extract Structured Intent (with built-in cache checks)
    intent = ai_search_service.extract_intent(query, user_context_str)
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
    
    platforms_to_search = ['amazon', 'flipkart', 'meesho', 'myntra']
    if platform:
        platforms_to_search = [platform.lower()]
    platform_status = {p: "success" for p in platforms_to_search}
    
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
    
    # Platform scraper fallback if local products < 10
    if len(products_list) < 10:
        def fetch_platform(plat):
            return scraper_manager.scrape_platform_realtime(plat, rewritten_q, 15)
                
        scraped_results = []
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(platforms_to_search)) as executor:
                futures = {executor.submit(fetch_platform, p): p for p in platforms_to_search}
                try:
                    for fut in concurrent.futures.as_completed(futures, timeout=Config.REALTIME_PLATFORM_TIMEOUT_SEC):
                        plat = futures[fut]
                        try:
                            scraped = fut.result()
                            scraped_results.extend(scraped or [])
                        except concurrent.futures.TimeoutError:
                            logger.error(f"Scraper timeout on {plat}")
                            platform_status[plat] = "timeout"
                        except Exception as exc:
                            logger.error(f"Scraper failure on {plat}: {exc}", exc_info=True)
                            platform_status[plat] = "failed"
                except concurrent.futures.TimeoutError:
                    logger.warning("AI search platform scraping reached overall timeout.")
                    for fut, plat in futures.items():
                        if not fut.done():
                            platform_status[plat] = "timeout"
                            fut.cancel()
        except Exception as e:
            logger.error(f"Error in ThreadPoolExecutor: {e}", exc_info=True)
                
        seen_urls = {p.get('product_url', '').lower() for p in products_list}
        for sp in scraped_results:
            url = sp.get('product_url', '').lower()
            if url and url not in seen_urls:
                seen_urls.add(url)
                products_list.append(sp)
                
    # Content relevance ranking
    recommender_filters = {
        'min_price': budget_min,
        'max_price': budget_max,
        'min_rating': rating,
        'category': category,
        'purpose': intent.get('purpose'),
        'confidence': confidence,
        'user_id': user.id if user else None,
        'user_pref': user_pref
    }
    ranked_products = recommender.rank_products_realtime(rewritten_q, products_list, recommender_filters)
    
    # Exclude purchased products
    final_products = []
    for p in ranked_products:
        p_url = p.get('product_url', '').lower()
        if p_url in purchased_urls:
            continue
        final_products.append(p)
        
    final_results = final_products[:20]
    
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

def handle_keyword_search_pipeline(query, filters, user):
    """Runs the standard keyword search, parallel platform scrapers, and interleaving"""
    query_lower = query.lower()
    electronics_set = {'laptop', 'phone', 'mobile', 'macbook', 'ipad', 'tablet', 'desktop', 'monitor', 'gpu', 'cpu', 'camera', 'tv'}
    fashion_set = {'shirt', 'tshirt', 'pant', 'jeans', 'shoe', 'sneaker', 'dress', 'saree', 'kurti', 'jacket', 'hoodie', 'sweater', 'bag', 'backpack'}
    
    has_electronics = any(e in query_lower for e in electronics_set)
    has_fashion = any(f in query_lower for f in fashion_set)
    
    requested_input = filters.get('platforms')
    if not requested_input:
        if has_electronics and not has_fashion:
            platforms_to_search = ['amazon', 'flipkart']
        elif has_fashion and not has_electronics:
            platforms_to_search = ['myntra', 'meesho', 'flipkart']
        else:
            platforms_to_search = ['amazon', 'flipkart', 'meesho', 'myntra']
    else:
        platforms_to_search = [p.strip().lower() for p in requested_input if isinstance(p, str)]
        if not platforms_to_search:
            platforms_to_search = ['amazon', 'flipkart', 'meesho', 'myntra']
            
    all_products = []
    platform_status = {p: "success" for p in platforms_to_search}
    
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
    
    # Run scrapers as fallback/supplement if local products < 10
    if len(all_products) < 10:
        def fetch_platform(platform_name):
            return scraper_manager.scrape_platform_realtime(platform_name, query, 20)
                
        scraped_results = []
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, len(platforms_to_search))) as executor:
                futures = {executor.submit(fetch_platform, p): p for p in platforms_to_search}
                try:
                    for future in concurrent.futures.as_completed(futures, timeout=Config.REALTIME_PLATFORM_TIMEOUT_SEC):
                        platform = futures[future]
                        try:
                            products = future.result()
                            scraped_results.extend(products or [])
                        except concurrent.futures.TimeoutError:
                            logger.error(f"Scraper timeout on {platform}")
                            platform_status[platform] = "timeout"
                        except Exception as e:
                            logger.error(f"Platform {platform} failure: {e}", exc_info=True)
                            platform_status[platform] = "failed"
                except concurrent.futures.TimeoutError:
                    logger.warning("Keyword search platform scraping reached overall timeout.")
                    for future, platform in futures.items():
                        if not future.done():
                            platform_status[platform] = "timeout"
                            future.cancel()
        except Exception as e:
            logger.error(f"Error in ThreadPoolExecutor: {e}", exc_info=True)
            
        seen_urls = {p.get('product_url', '').lower() for p in all_products}
        for sp in scraped_results:
            url = sp.get('product_url', '').lower()
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_products.append(sp)
                
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
        
    ranked_products = recommender.rank_products_realtime(query, filtered_products, filters)
    
    for idx, p in enumerate(ranked_products):
        if 'id' not in p or not p.get('id'):
            p['id'] = hash(p.get('product_url', f'product_{idx}')) % 1000000
            
    final_results = ranked_products[:20]
    
    # Store standard search history
    if user:
        try:
            last_event = db.session.query(SearchEvent).filter(SearchEvent.user_id == user.id).order_by(SearchEvent.created_at.desc()).first()
            if not last_event or last_event.query != query or (datetime.utcnow() - last_event.created_at).total_seconds() >= 10:
                event = SearchEvent(
                    user_id=user.id,
                    query=str(query)[:300],
                    filters_json=json.dumps(normalized_filters),
                    results_count=len(final_results)
                )
                db.session.add(event)
                db.session.commit()
        except Exception as se:
            logger.error(f"Failed to save standard history: {se}")
            db.session.rollback()
            
    # Interleave
    platform_groups = {}
    for p in ranked_products:
        plat = p.get('platform', 'Unknown')
        if plat not in platform_groups:
            platform_groups[plat] = []
        platform_groups[plat].append(p)
        
    interleaved_results = []
    while len(interleaved_results) < 20 and any(platform_groups.values()):
        sorted_platforms = sorted(platform_groups.keys(), key=lambda k: platform_groups[k][0].get('combined_score', 0) if platform_groups[k] else 0, reverse=True)
        for plat in sorted_platforms:
            if platform_groups[plat]:
                interleaved_results.append(platform_groups[plat].pop(0))
            if len(interleaved_results) >= 20:
                break
                
    return {
        "success": True,
        "is_ai": False,
        "products": interleaved_results,
        "results": interleaved_results,
        "alternative_products": [],
        "suggested_queries": [],
        "platform_status": platform_status
    }

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
        else:
            query = request.args.get('query', '').strip()
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
            res_payload = handle_ai_search_pipeline(query, filters, user)
        else:
            logger.info(f"Unified Search: Routing keyword query '{query}' to standard Search pipeline...")
            res_payload = handle_keyword_search_pipeline(query, filters, user)
            
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
        res_payload = handle_ai_search_pipeline(query, filters, user)
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
