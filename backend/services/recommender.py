import numpy as np
import threading
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from models import Product, db, UserPreference, RecommendationFeedback, PurchaseEvent, SearchEvent, ClickEvent, WishlistItem, AnalyticsCounter
from config import Config
from .scraper import ScraperManager
import logging
import re
import json
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProductRecommender:
    """Hybrid recommendation system combining ML and rule-based approaches"""
    
    RECOGNIZED_BRANDS = {
        "apple", "samsung", "oneplus", "xiaomi", "realme", "oppo", "vivo", "google",
        "asus", "lenovo", "hp", "dell", "acer", "msi", "lg", "sony", "boat", "jbl",
        "nike", "adidas", "puma", "reebok", "under armour", "asics", "skechers",
        "woodland", "bata", "crocs", "levis", "zara", "h&m", "roadster", "hrx"
    }
    CATEGORY_SYNONYMS = {
        "laptop": ["laptop", "notebook", "ultrabook", "macbook", "chromebook", "computer", "laptops"],
        "mobile": ["mobile", "phone", "smartphone", "iphone", "mobiles", "phones"],
        "shoes": ["shoe", "shoes", "sneaker", "sneakers", "running shoes", "sports shoes", "footwear", "sandal", "sandals", "slippers"],
        "fashion": ["clothing", "fashion", "apparel", "shirt", "tshirt", "t-shirt", "pant", "jeans", "dress", "saree", "kurti", "jacket", "hoodie", "sweater", "wear", "garment", "garments"],
        "electronics": ["electronics", "gadget", "gadgets", "headphone", "headphones", "earbud", "earbuds", "watch", "smartwatch", "tv", "television", "monitor", "speaker", "audio"],
        "tablet": ["tablet", "tablets", "ipad", "ipads", "tab", "tabs"],
        "camera": ["camera", "cameras", "dslr", "lens", "lenses", "gopro", "action cam"],
        "watch": ["watch", "watches", "smartwatch", "smartwatches", "timepiece"],
        "audio": ["headphone", "headphones", "earbud", "earbuds", "earphone", "earphones", "speaker", "speakers", "soundbar", "audio", "mic", "microphone"],
        "television": ["tv", "tvs", "television", "televisions", "smart tv", "led tv"],
        "monitor": ["monitor", "monitors", "display", "displays", "screen", "screens"],
        "printer": ["printer", "printers", "scanner", "scanners", "copier", "inkjet", "laserjet"]
    }

    CATEGORY_GROUPS = {
        "fashion": [
            "fashion",
            "clothing",
            "shirt",
            "tshirt",
            "jeans",
            "dress",
            "apparel"
        ],
        "electronics": [
            "audio",
            "earbuds",
            "headphones",
            "speaker",
            "watch",
            "smartwatch"
        ],
        "laptop": [
            "laptop",
            "notebook",
            "computer"
        ],
        "phone": [
            "phone",
            "mobile",
            "smartphone"
        ],
        "shoes": [
            "shoe",
            "footwear",
            "sneaker"
        ]
    }

    PURPOSE_MAP = {
        "gaming": ["gaming", "gamer", "play", "graphics", "gpu"],
        "coding": ["coding", "program", "developer", "software", "vscode", "python", "java", "c++"],
        "machine_learning": ["machine learning", "ml", "ai", "data science", "neural", "deep learning", "nlp"],
        "office": ["office", "work", "business", "excel", "document", "productivity", "meeting", "zoom"],
        "student": ["student", "college", "school", "study", "studies", "education", "learning"],
        "video_editing": ["video editing", "premier", "editor", "rendering", "da vinci", "after effects"],
        "graphic_design": ["graphic design", "photoshop", "illustrator", "designing", "canva", "creator"],
        "business": ["business", "professional", "enterprise", "corporate", "travel", "thin", "lightweight"]
    }

    IRRELEVANT_TERMS = {
        "toy", "toys", "cover", "covers", "case", "cases", "skin", "skins",
        "sticker", "stickers", "book", "books", "guide", "guides", "manual", "manuals",
        "accessory", "accessories", "sleeve", "sleeves", "protector", "protectors",
        "charger", "adapter", "keyboard", "mouse", "mousepad", "bag", "backpack",
        "stand", "holder", "screen guard", "replacement", "repair", "parts", "spare",
        "refurbished", "dummy", "sample", "miniature"
    }

    STOP_WORDS = {
        "for", "under", "best", "cheap", "rs", "rupees", "with", "near", "around",
        "need", "looking", "suggest", "recommend", "show", "find", "buy", "please",
        "get", "search", "results", "matching", "product", "products", "item", "items",
        "about", "rs.", "inr", "below", "above", "and", "or", "in", "of", "a", "an", "the", "to"
    }

    MIN_ACCEPTABLE_SCORE = 0.35
    
    def __init__(self):
        self._local = threading.local()
        self.vectorizer = TfidfVectorizer(
            max_features=Config.TFIDF_MAX_FEATURES,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=1,
            max_df=0.95
        )
        self.scraper_manager = ScraperManager()
        self.product_vectors = None
        self.product_ids = None
        self.is_trained = False

    def get_last_removed_count(self):
        return getattr(self._local, 'removed_count', 0)

    
    def prepare_text_features(self, products):
        """Prepare text features for TF-IDF vectorization"""
        texts = []
        for product in products:
            # Combine name, description, category, brand, and platform
            text_parts = []
            if product.name:
                text_parts.append(product.name)
            if product.description:
                text_parts.append(product.description)
            if product.category:
                text_parts.append(product.category)
            if product.brand:
                text_parts.append(product.brand)
            if product.platform:
                text_parts.append(product.platform)
            texts.append(' '.join(text_parts))
        return texts
    
    def train(self):
        """Train the TF-IDF vectorizer on all products"""
        try:
            products = Product.query.filter(
                Product.name.isnot(None),
                Product.description.isnot(None)
            ).all()
            
            if len(products) < 2:
                logger.warning("Not enough products to train the model")
                self.is_trained = False
                return
            
            texts = self.prepare_text_features(products)
            self.product_vectors = self.vectorizer.fit_transform(texts)
            self.product_ids = [p.id for p in products]
            self.is_trained = True
            logger.info(f"Trained TF-IDF model on {len(products)} products")
        except Exception as e:
            logger.error(f"Error training model: {str(e)}")
            self.is_trained = False
    
    def find_similar_products(self, query, top_n=None):
        """Find products similar to the search query using TF-IDF and cosine similarity"""
        if not self.is_trained:
            self.train()
        
        if not self.is_trained:
            # Fallback to simple text search
            return self._fallback_search(query, top_n)
        
        try:
            # Vectorize the query
            query_vector = self.vectorizer.transform([query])
            
            # Calculate cosine similarity
            similarities = cosine_similarity(query_vector, self.product_vectors).flatten()
            
            # Filter by threshold
            threshold = Config.SIMILARITY_THRESHOLD
            similar_indices = np.where(similarities >= threshold)[0]
            
            # Get products with their similarity scores
            results = []
            for idx in similar_indices:
                product_id = self.product_ids[idx]
                product = Product.query.get(product_id)
                if product:
                    results.append({
                        'product': product,
                        'similarity_score': float(similarities[idx])
                    })
            
            # Sort by similarity score
            results.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            # Limit results
            if top_n:
                results = results[:top_n]
            
            return results
            
        except Exception as e:
            logger.error(f"Error finding similar products: {str(e)}")
            return self._fallback_search(query, top_n)
    
    def _fallback_search(self, query, top_n=None):
        """Fallback search when ML model is not available"""
        query_lower = query.lower()
        products = Product.query.filter(
            db.or_(
                Product.name.ilike(f'%{query}%'),
                Product.description.ilike(f'%{query}%'),
                Product.category.ilike(f'%{query}%')
            )
        ).all()
        
        results = [{'product': p, 'similarity_score': 0.5} for p in products]
        if top_n:
            results = results[:top_n]
        return results
    
    def calculate_recommendation_score(self, product, min_price=None, max_price=None):
        """Calculate recommendation score using rule-based approach"""
        score = 0.0
        
        # Safely convert min_price and max_price to floats
        if min_price is not None:
            try:
                min_price = float(min_price)
            except (ValueError, TypeError):
                min_price = None
        if max_price is not None:
            try:
                max_price = float(max_price)
            except (ValueError, TypeError):
                max_price = None
        
        # Normalize price score (lower price = higher score)
        if product.price and min_price is not None and max_price is not None:
            if max_price > min_price:
                price_score = 1.0 - ((product.price - min_price) / (max_price - min_price))
            else:
                price_score = 1.0
        else:
            # If no price range, use inverse of price (normalized)
            all_prices = [p.price for p in Product.query.filter(Product.price.isnot(None)).all() if p.price]
            if all_prices and product.price:
                max_price_all = max(all_prices)
                min_price_all = min(all_prices)
                if max_price_all > min_price_all:
                    price_score = 1.0 - ((product.price - min_price_all) / (max_price_all - min_price_all))
                else:
                    price_score = 1.0
            else:
                price_score = 0.5
        
        score += Config.PRICE_WEIGHT * price_score
        
        # Rating score (normalized to 0-1)
        if product.rating:
            rating_score = product.rating / 5.0
        else:
            rating_score = 0.0
        score += Config.RATING_WEIGHT * rating_score
        
        # Platform trust score
        platform_trust = self.scraper_manager.get_platform_trust_score(product.platform)
        score += Config.PLATFORM_TRUST_WEIGHT * platform_trust
        
        # Review count score (normalized)
        if product.review_count:
            all_review_counts = [p.review_count for p in Product.query.filter(Product.review_count.isnot(None)).all() if p.review_count]
            if all_review_counts:
                max_reviews = max(all_review_counts)
                if max_reviews > 0:
                    review_score = min(1.0, product.review_count / max_reviews)
                else:
                    review_score = 0.0
            else:
                review_score = 0.5
        else:
            review_score = 0.0
        score += Config.REVIEW_COUNT_WEIGHT * review_score
        
        return score
    def classify_search_intent_type(self, query_lower):
        """Classify if the query intent is for a PRIMARY_PRODUCT, ACCESSORY, BOOK, or TOY"""
        accessory_keywords = {
            "cover", "covers", "case", "cases", "skin", "skins", "sticker", "stickers",
            "accessory", "accessories", "sleeve", "sleeves", "protector", "protectors",
            "charger", "adapter", "keyboard", "mouse", "mousepad", "bag", "backpack",
            "stand", "holder", "screen guard", "replacement", "repair", "parts", "spare"
        }
        book_keywords = {"book", "books", "guide", "guides", "manual", "manuals", "textbook", "textbooks"}
        toy_keywords = {"toy", "toys"}
        
        words = set(re.findall(r'\b\w+\b', query_lower))
        if any(w in book_keywords for w in words):
            return "BOOK"
        if any(w in toy_keywords for w in words):
            return "TOY"
        if any(w in accessory_keywords for w in words):
            return "ACCESSORY"
        return "PRIMARY_PRODUCT"

    def is_accessory_product(self, p_name, p_cat, p_desc):
        p_text = f"{p_name} {p_desc} {p_cat}".lower()
        accessory_keywords = {
            "cover", "covers", "case", "cases", "skin", "skins", "sticker", "stickers",
            "accessory", "accessories", "sleeve", "sleeves", "protector", "protectors",
            "charger", "adapter", "keyboard", "mouse", "mousepad", "bag", "backpack",
            "stand", "holder", "screen guard", "replacement", "repair", "parts", "spare"
        }
        return any(re.search(r'\b' + re.escape(w) + r'\b', p_text) for w in accessory_keywords)

    def is_book_product(self, p_name, p_cat, p_desc):
        p_text = f"{p_name} {p_desc} {p_cat}".lower()
        book_keywords = {"book", "books", "guide", "guides", "manual", "manuals", "textbook", "textbooks"}
        return any(re.search(r'\b' + re.escape(w) + r'\b', p_text) for w in book_keywords)

    def is_toy_product(self, p_name, p_cat, p_desc):
        p_text = f"{p_name} {p_desc} {p_cat}".lower()
        toy_keywords = {"toy", "toys"}
        return any(re.search(r'\b' + re.escape(w) + r'\b', p_text) for w in toy_keywords)
    
    def rank_products_realtime(self, query, products_list, filters=None):
        """Rank products in real-time combining category, budget, exclusion filters and score boosting"""
        if not products_list:
            return []
            
        intent_category = filters.get('category') if filters else None
        intent_confidence = float(filters.get('confidence')) if filters and filters.get('confidence') is not None else 1.0
        
        # Pass 1: Strict filtering (threshold = 0.35)
        ranked = self._filter_and_score(query, products_list, filters, strict=True, threshold=0.35)
        
        # Pass 2: Fallback filtering if strict returned too few results (threshold = 0.20)
        if len(ranked) < 5:
            logger.info(f"Strict filtering returned only {len(ranked)} results. Running relaxed pass...")
            ranked = self._filter_and_score(query, products_list, filters, strict=False, threshold=0.20)
            
        # Apply brand and category diversity decay selection
        diversified = self._apply_diversity_and_limit(ranked, limit=20)
        
        # Log search query quality metrics in JSON format
        count_before = len(products_list)
        count_after = len(diversified)
        avg_score = float(np.mean([item['score'] for item in diversified])) if diversified else 0.0
        
        log_payload = {
            "query": query,
            "intent": intent_category or self.classify_search_intent_type(query.lower()),
            "confidence": intent_confidence,
            "before": count_before,
            "after": count_after,
            "avg_score": round(avg_score, 4)
        }
        logger.info(f"Search Quality Metrics: {json.dumps(log_payload)}")
        
        # Log Top 10 Ranked Products
        logger.info("=== Top 10 Ranked Products ===")
        for idx, item in enumerate(diversified[:10]):
            logger.info(json.dumps({
                "name": item.get("name"),
                "platform": item.get("platform"),
                "similarity": item.get("similarity_score"),
                "recommendation": item.get("recommendation_score"),
                "final_score": item.get("score")
            }))

        # Return top 20
        return diversified[:20]

    def _filter_and_score(self, query, products_list, filters=None, strict=True, threshold=0.35):
        self._local.removed_count = 0
        min_price = None
        max_price = None
        intent_category = None
        intent_purpose = None
        intent_confidence = 1.0
        user_pref = None
        user_id = None
        
        if filters:
            min_price = filters.get('min_price') if filters.get('min_price') is not None else filters.get('minPrice')
            max_price = filters.get('max_price') if filters.get('max_price') is not None else filters.get('maxPrice')
            intent_category = filters.get('category')
            intent_purpose = filters.get('purpose')
            intent_confidence = float(filters.get('confidence')) if filters.get('confidence') is not None else 1.0
            user_pref = filters.get('user_pref')
            user_id = filters.get('user_id')
            
        query_lower = query.lower()
        
        # Auto Category Detection in Standard Search
        if not intent_category:
            intent_type = self.classify_search_intent_type(query_lower)
            if intent_type == "PRIMARY_PRODUCT":
                for cat_key, synonyms in self.CATEGORY_SYNONYMS.items():
                    if cat_key in query_lower or any(re.search(r'\b' + re.escape(syn) + r'\b', query_lower) for syn in synonyms):
                        intent_category = cat_key
                        break
        
        # Brand detection
        requested_brand = None
        if filters and filters.get('brand'):
            requested_brand = filters.get('brand').strip().lower()
        else:
            for b in self.RECOGNIZED_BRANDS:
                if re.search(r'\b' + re.escape(b) + r'\b', query_lower):
                    requested_brand = b
                    break
                    
        detected_purpose = self.detect_purpose(query_lower, intent_purpose)
        
        # Pre-calculate min/max prices and review counts for normalization
        prices_in_batch = []
        review_counts_in_batch = []
        for p in products_list:
            price_val = self._get_val(p, 'price')
            if price_val is not None:
                try:
                    price_float = float(price_val)
                    if price_float > 0:
                        prices_in_batch.append(price_float)
                except (ValueError, TypeError):
                    pass
            rc_val = self._get_val(p, 'review_count')
            if rc_val is not None:
                try:
                    review_counts_in_batch.append(int(rc_val))
                except (ValueError, TypeError):
                    pass
                    
        max_reviews = max(review_counts_in_batch) if review_counts_in_batch else 1
        min_price_in_batch = min(prices_in_batch) if prices_in_batch else 0
        max_price_in_batch = max(prices_in_batch) if prices_in_batch else 0
        
        query_words = set(re.findall(r'\b\w+\b', query_lower))
        stemmed_query_words = [w.rstrip('s') if len(w) > 3 else w for w in query_words]
        
        # Filter out stop words and numbers for text matching
        meaningful_query_words = {w for w in stemmed_query_words if w not in self.STOP_WORDS and not w.isdigit()}
        if not meaningful_query_words:
            meaningful_query_words = set(stemmed_query_words)
            
        query_intent = {
            "query_lower": query_lower,
            "query_words": query_words,
            "stemmed_query_words": stemmed_query_words,
            "intent_category": intent_category,
            "detected_purpose": detected_purpose,
            "requested_brand": requested_brand,
            "min_price_in_batch": min_price_in_batch,
            "max_price_in_batch": max_price_in_batch
        }
        
        filtered_products = []
        intent_type = self.classify_search_intent_type(query_lower)
        
        for p in products_list:
            p_name = self._get_val(p, 'name') or ''
            p_cat = self._get_val(p, 'category') or ''
            p_desc = self._get_val(p, 'description') or ''
            p_price = self._get_val(p, 'price')
            p_brand = self._get_val(p, 'brand') or ''
            
            # Phase 2: Invalid Price check
            if p_price is None:
                continue
            try:
                price_val = float(p_price)
                if price_val <= 0:
                    continue
            except (ValueError, TypeError):
                continue
                
            # Budget enforcement (always hard constraint)
            if min_price is not None and str(min_price).strip() != "":
                try:
                    if price_val < float(min_price):
                        continue
                except (ValueError, TypeError):
                    pass
            if max_price is not None and str(max_price).strip() != "":
                try:
                    if price_val > float(max_price):
                        continue
                except (ValueError, TypeError):
                    pass
                
            # Search Intent Type filtering
            is_acc = self.is_accessory_product(p_name, p_cat, p_desc)
            is_bk = self.is_book_product(p_name, p_cat, p_desc)
            is_ty = self.is_toy_product(p_name, p_cat, p_desc)
            
            if intent_type == "PRIMARY_PRODUCT":
                if is_acc or is_bk or is_ty:
                    continue
            elif intent_type == "ACCESSORY":
                if not is_acc:
                    continue
            elif intent_type == "BOOK":
                if not is_bk:
                    continue
            elif intent_type == "TOY":
                if not is_ty:
                    continue
                    
            # Phase 1: Strict Category validation (always enforced if intent_category is present)
            if intent_category:
                if not self.validate_product_category(p_cat, p_name, intent_category, query_lower):
                    continue
                    
            # Phase 1.5: Strict Brand validation (always enforced if requested_brand is present)
            if requested_brand:
                p_brand_lower = p_brand.lower().strip() if p_brand else ""
                if p_brand_lower:
                    if p_brand_lower != requested_brand.lower():
                        continue
                else:
                    # If product has no brand, check if title contains another recognized brand
                    has_other_brand = False
                    for b in self.RECOGNIZED_BRANDS:
                        if b.lower() != requested_brand.lower() and re.search(r'\b' + re.escape(b) + r'\b', p_name.lower()):
                            has_other_brand = True
                            break
                    if has_other_brand:
                        continue
                    
            # Base similarity (text matching)
            sim_score = self._get_val(p, 'similarity_score')
            if sim_score is None:
                matches = 0
                for w in meaningful_query_words:
                    if w in p_name.lower() or w in p_desc.lower() or w in p_cat.lower():
                        matches += 1
                base_similarity = min(1.0, matches / max(1, len(meaningful_query_words)))
            else:
                base_similarity = sim_score
                
            # Category query boost
            if intent_category and (intent_category.lower() in p_cat.lower() or intent_category.lower() in p_name.lower()):
                base_similarity = min(1.0, base_similarity + 0.20)
                
            # Similarity relevance gate
            is_ai = filters.get('is_ai', False) if filters else False
            sim_threshold = 0.40 if is_ai else 0.30
            if base_similarity < sim_threshold:
                self._local.removed_count += 1
                continue
                
            # Scoring
            final_score, breakdown = self.calculate_final_product_score(
                p, base_similarity, query_intent, max_reviews, user_pref, strict=strict
            )
            
            # Result Quality Threshold
            if final_score < threshold:
                continue
                
            # Explanation reason text
            reason_str = self._generate_reason_text(
                p, intent_category, detected_purpose, user_pref, max_price, breakdown, max_reviews
            )
            
            item_payload = {}
            if isinstance(p, dict):
                item_payload.update(p)
            else:
                item_payload.update(p.to_dict())
                
            item_payload.update({
                'similarity_score': round(base_similarity, 4),
                'recommendation_score': round(breakdown['quality_score'], 4),
                'combined_score': round(final_score, 4),
                'score': round(final_score, 4),
                'preference_score': round(breakdown['preference_score'], 4),
                'match_percentage': int(final_score * 100),
                'reason': reason_str,
                'brand': p_brand,
                'category': p_cat
            })
            
            # Structured Debug Logging
            logger.info({
                "product": p_name[:50],
                "relevance": round(breakdown['relevance_score'], 2),
                "quality": round(breakdown['quality_score'], 2),
                "preference": round(breakdown['preference_score'], 2),
                "popularity": round(breakdown['popularity_score'], 2),
                "spec": round(breakdown['spec_score'], 2),
                "freshness": round(breakdown['freshness_score'], 2),
                "final": round(final_score, 2),
                "match_percentage": int(final_score * 100)
            })
            
            filtered_products.append(item_payload)
            
        if not filtered_products and products_list:
            logger.info("Strict/relaxed ranking filtered out all products. Using fallback best-effort selection.")
            for p in products_list[:10]:
                try:
                    item_payload = dict(p) if isinstance(p, dict) else p.to_dict()
                except Exception:
                    item_payload = {
                        'name': self._get_val(p, 'name', 'Product'),
                        'description': self._get_val(p, 'description', ''),
                        'price': self._get_val(p, 'price', 0.0),
                        'original_price': self._get_val(p, 'original_price', 0.0),
                        'rating': self._get_val(p, 'rating', 4.0),
                        'review_count': self._get_val(p, 'review_count', 10),
                        'platform': self._get_val(p, 'platform', 'Unknown'),
                        'product_url': self._get_val(p, 'product_url', ''),
                        'image_url': self._get_val(p, 'image_url', ''),
                        'category': self._get_val(p, 'category', 'General'),
                        'availability': self._get_val(p, 'availability', 'In Stock')
                    }
                item_payload.setdefault('score', 0.5)
                item_payload.setdefault('combined_score', 0.5)
                item_payload.setdefault('recommendation_score', 0.5)
                item_payload.setdefault('match_percentage', 50)
                item_payload.setdefault('reason', 'Best effort match')
                item_payload.setdefault('brand', self._get_val(p, 'brand', ''))
                item_payload.setdefault('category', self._get_val(p, 'category', 'General'))
                filtered_products.append(item_payload)
            
        deduped = self._deduplicate_products(filtered_products)
        deduped.sort(key=lambda x: x['score'], reverse=True)
        return deduped

    def _get_val(self, p, key, default=None):
        if isinstance(p, dict):
            return p.get(key, default)
        return getattr(p, key, default)

    def validate_product_category(self, product_category, product_title, intent_category, query_lower=None):
        if not intent_category:
            return True
            
        p_cat = (product_category or "").strip().lower()
        p_title = (product_title or "").strip().lower()
        intent_cat = intent_category.strip().lower()
        query_lower = (query_lower or "").strip().lower()

        # Category Group checks
        def get_category_group(cat_str, title_str=""):
            for group, keywords in self.CATEGORY_GROUPS.items():
                if group == cat_str or any(re.search(r'\b' + re.escape(kw) + r'\b', cat_str) for kw in keywords):
                    return group
            if title_str:
                for group, keywords in self.CATEGORY_GROUPS.items():
                    if any(re.search(r'\b' + re.escape(kw) + r'\b', title_str) for kw in keywords):
                        return group
            return None

        intent_group = get_category_group(intent_cat)
        p_group = get_category_group(p_cat, p_title)

        if intent_group and p_group and intent_group != p_group:
            logger.info(f"Category Group mismatch check failed: intent group '{intent_group}' != product group '{p_group}' for product '{product_title}'")
            return False
        
        # Calculate active exclusions (irrelevant terms that are NOT present in query)
        requested_terms = set()
        for term in self.IRRELEVANT_TERMS:
            if re.search(r'\b' + re.escape(term) + r'\b', query_lower):
                requested_terms.add(term)
                if term.endswith('s'):
                    requested_terms.add(term[:-1])
                else:
                    requested_terms.add(term + 's')
        active_exclusions = self.IRRELEVANT_TERMS - requested_terms
        
        target_key = None
        if intent_cat in self.CATEGORY_SYNONYMS:
            target_key = intent_cat
        else:
            for key, synonyms in self.CATEGORY_SYNONYMS.items():
                if intent_cat in synonyms or any(syn in intent_cat for syn in synonyms):
                    target_key = key
                    break
                
        if not target_key:
            if intent_cat in p_cat or intent_cat in p_title:
                # Ensure it doesn't contain active exclusion terms
                for term in active_exclusions:
                    pattern = r'\b' + re.escape(term) + r'\b'
                    if re.search(pattern, p_cat) or re.search(pattern, p_title):
                        return False
                return True
            return False
            
        # 1. Strong Match
        if any(syn in p_cat for syn in self.CATEGORY_SYNONYMS[target_key]):
            # Verify p_cat does not contain active exclusion terms
            for term in active_exclusions:
                pattern = r'\b' + re.escape(term) + r'\b'
                if re.search(pattern, p_cat):
                    return False
            return True
            
        # 2. Weak Match
        is_generic = any(gen in p_cat for gen in ["electronics", "gadget", "gadgets", "fashion", "apparel", "other", "general", "shopping", "product", "items", "utility", "all", ""])
        if is_generic or not p_cat:
            has_synonym = any(syn in p_title for syn in self.CATEGORY_SYNONYMS[target_key])
            
            # Laptop specific weak match expansions (e.g. processor/brand/specs)
            if not has_synonym and target_key == "laptop":
                laptop_specs = {
                    "intel", "amd", "ryzen", "core 3", "core 5", "core 7", "celeron", "pentium", 
                    "processor", "ram", "ssd", "display", "aspire", "inspiron", "pavilion", 
                    "vivobook", "thinkpad", "ideapad", "modern", "v15", "probook", "elitebook",
                    "primebook", "book"
                }
                has_synonym = any(re.search(r'\b' + re.escape(w) + r'\b', p_title) for w in laptop_specs)
                
            # Mobile specific weak match expansions
            if not has_synonym and target_key == "mobile":
                mobile_specs = {
                    "snapdragon", "mediatek", "dimensity", "bionic", "ram", "rom", "5g", "4g",
                    "redmi", "realme", "samsung", "oneplus", "iphone", "xiaomi", "motorola"
                }
                has_synonym = any(re.search(r'\b' + re.escape(w) + r'\b', p_title) for w in mobile_specs)

            if has_synonym:
                # Verify p_title does not contain active exclusion terms
                for term in active_exclusions:
                    pattern = r'\b' + re.escape(term) + r'\b'
                    if re.search(pattern, p_title):
                        return False
                return True
                
        return False

    def is_product_irrelevant(self, p_name, p_cat, p_desc, query_lower, strict=True):
        p_name = (p_name or "").lower()
        p_cat = (p_cat or "").lower()
        p_desc = (p_desc or "").lower()
        
        # Always enforce full exclusion dictionary to prevent accessories from leaking in relaxed pass
        terms_to_check = self.IRRELEVANT_TERMS
            
        requested_terms = set()
        for term in terms_to_check:
            if re.search(r'\b' + re.escape(term) + r'\b', query_lower):
                requested_terms.add(term)
                if term.endswith('s'):
                    requested_terms.add(term[:-1])
                else:
                    requested_terms.add(term + 's')
                    
        active_exclusions = terms_to_check - requested_terms
        
        for term in active_exclusions:
            pattern = r'\b' + re.escape(term) + r'\b'
            if (re.search(pattern, p_name) or 
                re.search(pattern, p_cat) or 
                re.search(pattern, p_desc)):
                return True
                
        return False

    def detect_purpose(self, query_lower, intent_purpose=None):
        if intent_purpose:
            p_clean = intent_purpose.lower().replace(" ", "_")
            if p_clean in self.PURPOSE_MAP:
                return p_clean
                
        for purpose, keywords in self.PURPOSE_MAP.items():
            for kw in keywords:
                if re.search(r'\b' + re.escape(kw) + r'\b', query_lower):
                    return purpose
        return None

    def calculate_spec_match_score(self, p_text, purpose, p_price=None, p_brand=None):
        if not purpose:
            return 0.0
            
        spec_score = 0.0
        has_ram_16 = bool(re.search(r'\b(16\s*gb|16gb|32\s*gb|32gb|64\s*gb|64gb)\b', p_text, re.I))
        has_ssd = bool(re.search(r'\b(ssd|nvme|solid\s+state)\b', p_text, re.I))
        has_cpu_strong = bool(re.search(r'\b(i5|i7|i9|ryzen\s*5|ryzen\s*7|ryzen\s*9|m1|m2|m3)\b', p_text, re.I))
        has_gpu_dedicated = bool(re.search(r'\b(rtx|gtx|nvidia|geforce|gpu|graphics|radeon|dedicated)\b', p_text, re.I))
        
        if purpose == "gaming":
            if has_gpu_dedicated: spec_score += 0.5
            if has_ram_16: spec_score += 0.3
            if has_cpu_strong: spec_score += 0.2
        elif purpose == "coding":
            if has_ram_16: spec_score += 0.4
            if has_ssd: spec_score += 0.3
            if has_cpu_strong: spec_score += 0.3
        elif purpose == "machine_learning":
            if has_gpu_dedicated: spec_score += 0.4
            if has_ram_16: spec_score += 0.3
            if has_cpu_strong: spec_score += 0.2
            if has_ssd: spec_score += 0.1
        elif purpose in ["office", "business"]:
            if has_ssd: spec_score += 0.5
            if has_cpu_strong: spec_score += 0.3
            if p_brand and p_brand.lower() in ["apple", "dell", "hp", "lenovo"]: spec_score += 0.2
        elif purpose == "student":
            if p_price and p_price < 40000: spec_score += 0.5
            if has_cpu_strong or has_ssd: spec_score += 0.5
        elif purpose in ["video_editing", "graphic_design"]:
            if has_ram_16: spec_score += 0.4
            if has_gpu_dedicated: spec_score += 0.3
            if has_cpu_strong: spec_score += 0.3
        else:
            if has_ram_16: spec_score += 0.4
            if has_ssd: spec_score += 0.3
            if has_cpu_strong: spec_score += 0.3
            
        return min(1.0, spec_score)

    def calculate_quality_score(self, product, max_reviews=1):
        rating_val = self._get_val(product, 'rating')
        rating = float(rating_val) if rating_val else 0.0
        rating_score = min(1.0, rating / 5.0)
        
        review_count_val = self._get_val(product, 'review_count')
        review_count = float(review_count_val) if review_count_val else 0.0
        review_score = min(1.0, review_count / max_reviews) if max_reviews > 0 else 0.0
        
        platform = (self._get_val(product, 'platform') or "").lower().strip()
        platform_scores = {
            "amazon": 0.95,
            "flipkart": 0.90,
            "myntra": 0.92,
            "meesho": 0.75
        }
        platform_trust = platform_scores.get(platform, 0.80)
        
        brand = (self._get_val(product, 'brand') or "").lower().strip()
        brand_score = 1.0 if brand in self.RECOGNIZED_BRANDS else 0.0
        
        image_url = self._get_val(product, 'image_url') or self._get_val(product, 'image')
        category = self._get_val(product, 'category')
        price = self._get_val(product, 'price')
        
        completeness_fields = [
            bool(image_url),
            bool(rating > 0),
            bool(review_count > 0),
            bool(category),
            bool(price is not None and price > 0)
        ]
        completeness_score = sum(completeness_fields) / len(completeness_fields)
        
        quality_score = (
            0.35 * rating_score +
            0.20 * review_score +
            0.20 * platform_trust +
            0.15 * brand_score +
            0.10 * completeness_score
        )
        return min(1.0, max(0.0, quality_score))

    def calculate_freshness_score(self, created_at):
        if not created_at:
            return 0.5
        try:
            if isinstance(created_at, str):
                # Clean and parse string timestamp
                dt_str = created_at.split(".")[0].replace("Z", "")
                dt = datetime.fromisoformat(dt_str)
            elif isinstance(created_at, datetime):
                dt = created_at
            else:
                return 0.5
                
            if dt.tzinfo is not None:
                dt = dt.replace(tzinfo=None)
            now = datetime.utcnow()
            days_old = (now - dt).days
            if days_old <= 30:
                return 1.0
            elif days_old >= 180:
                return 0.0
            else:
                return 1.0 - (days_old - 30) / 150.0
        except Exception:
            return 0.5

    def calculate_final_product_score(self, product, relevance_score, query_intent=None, max_reviews=1, user_pref=None, strict=True):
        p_name = self._get_val(product, 'name') or ''
        p_cat = self._get_val(product, 'category') or ''
        p_desc = self._get_val(product, 'description') or ''
        p_brand = (self._get_val(product, 'brand') or '').lower().strip()
        p_price = self._get_val(product, 'price')
        p_text = f"{p_name} {p_desc} {p_cat}".lower()
        
        brand_multiplier = 1.0
        requested_brand = query_intent.get('requested_brand') if query_intent else None
        if requested_brand:
            if p_brand:
                if p_brand == requested_brand:
                    brand_multiplier = 1.0
                else:
                    brand_multiplier = 0.4 if strict else 0.7
            else:
                has_other_brand = False
                for b in self.RECOGNIZED_BRANDS:
                    if b != requested_brand and re.search(r'\b' + re.escape(b) + r'\b', p_name.lower()):
                        has_other_brand = True
                        break
                if has_other_brand:
                    brand_multiplier = 0.4 if strict else 0.7
                else:
                    brand_multiplier = 0.7
                    
        relevance = relevance_score * brand_multiplier
        quality = self.calculate_quality_score(product, max_reviews)
        
        preference = 0.0
        if user_pref:
            cat_affinity = user_pref.preferred_categories.get(p_cat, 0) if p_cat else 0
            brand_affinity = user_pref.preferred_brands.get(p_brand, 0) if p_brand else 0
            p_platform = self._get_val(product, 'platform')
            plat_affinity = user_pref.preferred_platforms.get(p_platform, 0) if p_platform else 0
            
            max_cat = max(user_pref.preferred_categories.values()) if user_pref.preferred_categories else 1
            max_brand = max(user_pref.preferred_brands.values()) if user_pref.preferred_brands else 1
            max_plat = max(user_pref.preferred_platforms.values()) if user_pref.preferred_platforms else 1
            
            cat_score = cat_affinity / max_cat if max_cat > 0 else 0.0
            brand_score = brand_affinity / max_brand if max_brand > 0 else 0.0
            plat_score = plat_affinity / max_plat if max_plat > 0 else 0.0
            
            price_score = 0.0
            if p_price is not None:
                try:
                    price_val = float(p_price)
                    if user_pref.preferred_price_min <= price_val <= user_pref.preferred_price_max:
                        price_score = 1.0
                    elif (user_pref.preferred_price_min * 0.5) <= price_val <= (user_pref.preferred_price_max * 1.5):
                        price_score = 0.5
                except (ValueError, TypeError):
                    pass
            preference = 0.4 * cat_score + 0.3 * brand_score + 0.2 * price_score + 0.1 * plat_score
            
        review_count = float(self._get_val(product, 'review_count') or 0.0)
        popularity = (review_count / max_reviews) if max_reviews > 0 else 0.0
        
        detected_purpose = query_intent.get('detected_purpose') if query_intent else None
        spec = self.calculate_spec_match_score(p_text, detected_purpose, p_price, p_brand)
        
        created_at = self._get_val(product, 'created_at')
        freshness = self.calculate_freshness_score(created_at)
        
        final_score = (
            0.75 * relevance +
            0.0833 * quality +
            0.0625 * preference +
            0.0417 * popularity +
            0.0417 * spec +
            0.0208 * freshness
        )
        
        breakdown = {
            'relevance_score': relevance,
            'quality_score': quality,
            'preference_score': preference,
            'popularity_score': popularity,
            'spec_score': spec,
            'freshness_score': freshness
        }
        return min(1.0, max(0.0, final_score)), breakdown

    def _apply_diversity_and_limit(self, scored_items, limit=20):
        diverse_list = []
        remaining = list(scored_items)
        
        brand_multipliers = {}
        cat_multipliers = {}
        
        while remaining and len(diverse_list) < limit:
            for item in remaining:
                brand = (item.get('brand') or '').lower().strip()
                cat = (item.get('category') or '').lower().strip()
                
                mult_brand = brand_multipliers.get(brand, 1.0)
                mult_cat = cat_multipliers.get(cat, 1.0)
                
                item['current_score'] = item['score'] * mult_brand * mult_cat
                
            remaining.sort(key=lambda x: x['current_score'], reverse=True)
            best_item = remaining.pop(0)
            diverse_list.append(best_item)
            
            best_brand = (best_item.get('brand') or '').lower().strip()
            best_cat = (best_item.get('category') or '').lower().strip()
            
            if best_brand:
                brand_multipliers[best_brand] = brand_multipliers.get(best_brand, 1.0) * 0.90
            if best_cat:
                cat_multipliers[best_cat] = cat_multipliers.get(best_cat, 1.0) * 0.95
                
        return diverse_list

    def _deduplicate_products(self, products):
        seen_keys = set()
        deduped = []
        for item in products:
            item_url = (item.get('product_url') or '').strip().lower()
            item_name = (item.get('name') or '').strip().lower()
            item_price = item.get('price')
            
            cleaned_name = re.sub(r'[^a-z0-9]', '', item_name)[:30]
            
            url_key = item_url
            name_price_key = f"{cleaned_name}_{item_price}" if item_price is not None else None
            
            is_dup = False
            if url_key and url_key in seen_keys:
                is_dup = True
            elif name_price_key and name_price_key in seen_keys:
                is_dup = True
                
            if not is_dup:
                if url_key:
                    seen_keys.add(url_key)
                if name_price_key:
                    seen_keys.add(name_price_key)
                deduped.append(item)
        return deduped

    def _generate_reason_text(self, p, intent_category, detected_purpose, user_pref, max_price, breakdown, max_reviews):
        reasons = []
        p_brand = self._get_val(p, 'brand')
        p_cat = self._get_val(p, 'category') or intent_category or 'products'
        
        spec_score = breakdown['spec_score']
        if spec_score > 0 and detected_purpose:
            purpose_label = detected_purpose.replace("_", " ")
            reasons.append(f"Optimized for {purpose_label}")
            
        if user_pref and p_brand:
            pref_brands = [b.lower() for b in user_pref.preferred_brands.keys()]
            if p_brand.lower() in pref_brands:
                reasons.append(f"Matches your preferred {p_brand} brand")
                
        p_price = self._get_val(p, 'price')
        
        # Safely convert prices to floats
        max_price_val = None
        if max_price is not None:
            try:
                max_price_val = float(max_price)
            except (ValueError, TypeError):
                pass
                
        p_price_val = None
        if p_price is not None:
            try:
                p_price_val = float(p_price)
            except (ValueError, TypeError):
                pass

        if max_price_val is not None and p_price_val is not None and p_price_val <= max_price_val:
            def format_currency_inr(val):
                if val is None:
                    return ""
                try:
                    return f"₹{float(val):,.0f}"
                except Exception:
                    return f"₹{val}"
            reasons.append(f"Fits within your {format_currency_inr(max_price_val)} budget")
            
        rating = float(self._get_val(p, 'rating') or 0)
        review_count = float(self._get_val(p, 'review_count') or 0)
        if rating >= 4.0 and review_count > 100:
            reasons.append("Highly rated among users")
            
        if reasons:
            return " & ".join(reasons[:2])
            
        if max_price_val is not None:
            def format_currency_inr(val):
                if val is None:
                    return ""
                try:
                    return f"₹{float(val):,.0f}"
                except Exception:
                    return f"₹{val}"
            return f"Fits within your {format_currency_inr(max_price_val)} budget"
        if detected_purpose:
            return f"Matches your {detected_purpose.replace('_', ' ')} requirements"
        return f"Top match for {p_cat.lower()}"

    def rank_products(self, products_with_similarity, min_price=None, max_price=None, query=None, filters=None):
        """Rank products by combining similarity and recommendation scores using the unified engine"""
        ranked_products = []
        
        query_intent = {}
        if query:
            query_lower = query.lower()
            query_words = set(re.findall(r'\b\w+\b', query_lower))
            stemmed_query_words = [w.rstrip('s') if len(w) > 3 else w for w in query_words]
            detected_purpose = self.detect_purpose(query_lower)
            requested_brand = None
            for b in self.RECOGNIZED_BRANDS:
                if re.search(r'\b' + re.escape(b) + r'\b', query_lower):
                    requested_brand = b
                    break
            query_intent = {
                "query_lower": query_lower,
                "query_words": query_words,
                "stemmed_query_words": stemmed_query_words,
                "intent_category": None,
                "detected_purpose": detected_purpose,
                "requested_brand": requested_brand,
                "min_price_in_batch": min_price or 0,
                "max_price_in_batch": max_price or 0
            }
            
        user_pref = filters.get('user_pref') if filters else None
        
        review_counts = []
        for item in products_with_similarity:
            p = item['product']
            rc = self._get_val(p, 'review_count')
            if rc:
                review_counts.append(int(rc))
        max_reviews = max(review_counts) if review_counts else 1
        
        for item in products_with_similarity:
            product = item['product']
            similarity_score = item['similarity_score']
            
            final_score, breakdown = self.calculate_final_product_score(
                product, similarity_score, query_intent, max_reviews, user_pref, strict=False
            )
            
            if hasattr(product, 'recommendation_score'):
                product.recommendation_score = final_score
                
            # Create a dict representation including database product fields + score fields
            p_dict = {}
            if hasattr(product, 'to_dict'):
                p_dict.update(product.to_dict())
            else:
                p_dict.update(product)
                
            p_dict.update({
                'product': product,
                'similarity_score': similarity_score,
                'recommendation_score': breakdown['quality_score'],
                'combined_score': final_score,
                'score': final_score,
                'match_percentage': int(final_score * 100),
                'brand': self._get_val(product, 'brand'),
                'category': self._get_val(product, 'category')
            })
            ranked_products.append(p_dict)
            
        diversified = self._apply_diversity_and_limit(ranked_products, limit=len(ranked_products))
        diversified.sort(key=lambda x: x['combined_score'], reverse=True)
        return diversified
    
    def recommend(self, query, filters=None, top_n=None):
        """Main recommendation method"""
        if top_n is None:
            top_n = Config.MAX_RECOMMENDATIONS
        
        # Find similar products
        similar_products = self.find_similar_products(query, top_n * 2)  # Get more for filtering
        
        # Apply filters
        if filters:
            filtered = []
            min_price = filters.get('min_price')
            max_price = filters.get('max_price')
            platforms = filters.get('platforms')
            min_rating = filters.get('min_rating')
            
            for item in similar_products:
                product = item['product']
                
                if min_price and product.price and product.price < min_price:
                    continue
                if max_price and product.price and product.price > max_price:
                    continue
                if platforms and product.platform not in platforms:
                    continue
                if min_rating and (not product.rating or product.rating < min_rating):
                    continue
                
                filtered.append(item)
            
            similar_products = filtered
        
        # Calculate price range for scoring
        prices = [item['product'].price for item in similar_products if item['product'].price]
        min_price = min(prices) if prices else None
        max_price = max(prices) if prices else None
        
        # Rank products
        ranked = self.rank_products(similar_products, min_price, max_price)
        
        # Limit results
        return ranked[:top_n]
    
    def get_category_for_query(self, query_str):
        """Helper to map a search query to a category in DB"""
        if not query_str or not query_str.strip():
            return None
        try:
            result = db.session.query(Product.category, db.func.count(Product.category)) \
                .filter(Product.name.like(f"%{query_str.strip()}%")) \
                .filter(Product.category.isnot(None)) \
                .filter(Product.category != '') \
                .group_by(Product.category) \
                .order_by(db.func.count(Product.category).desc()) \
                .first()
            if result:
                return result[0]
        except Exception as e:
            logger.warning(f"Error mapping query to category in recommender: {e}")
        return None

    def update_user_preferences(self, user_id):
        """Analyze user history to construct and save user preference profile"""
        try:
            categories = {}
            brands = {}
            platforms = {}
            prices = []
            
            # 1. Clicks (weight = 1)
            clicks = ClickEvent.query.filter_by(user_id=user_id).all()
            for c in clicks:
                if c.product:
                    p = c.product
                    cat = p.category
                    if cat:
                        categories[cat] = categories.get(cat, 0) + 1
                    brand = p.brand
                    if brand:
                        brands[brand] = brands.get(brand, 0) + 1
                    plat = p.platform
                    if plat:
                        platforms[plat] = platforms.get(plat, 0) + 1
                    if p.price:
                        prices.append(p.price)
            
            # 2. Searches (weight = 2)
            searches = db.session.query(SearchEvent).filter_by(user_id=user_id).all()
            for s in searches:
                cat = self.get_category_for_query(s.query)
                if cat:
                    categories[cat] = categories.get(cat, 0) + 2
            
            # 3. Wishlist additions (weight = 3)
            wishlist = WishlistItem.query.filter_by(user_id=user_id).all()
            for w in wishlist:
                if w.product:
                    p = w.product
                    cat = p.category
                    if cat:
                        categories[cat] = categories.get(cat, 0) + 3
                    brand = p.brand
                    if brand:
                        brands[brand] = brands.get(brand, 0) + 3
                    plat = p.platform
                    if plat:
                        platforms[plat] = platforms.get(plat, 0) + 3
                    if p.price:
                        prices.append(p.price)
                        
            # 4. Purchases (weight = 5)
            purchases = PurchaseEvent.query.filter_by(user_id=user_id).all()
            for pu in purchases:
                if pu.product:
                    p = pu.product
                    cat = p.category
                    if cat:
                        categories[cat] = categories.get(cat, 0) + 5
                    brand = p.brand
                    if brand:
                        brands[brand] = brands.get(brand, 0) + 5
                    plat = p.platform
                    if plat:
                        platforms[plat] = platforms.get(plat, 0) + 5
                    if p.price:
                        prices.append(p.price)
            
            # Budget calculation using 25th & 75th percentiles with a 20% buffer
            preferred_price_min = 0.0
            preferred_price_max = 1000000.0
            
            if prices:
                if len(prices) == 1:
                    preferred_price_min = float(prices[0] * 0.5)
                    preferred_price_max = float(prices[0] * 1.5)
                else:
                    p25 = np.percentile(prices, 25)
                    p75 = np.percentile(prices, 75)
                    preferred_price_min = float(p25 * 0.8)
                    preferred_price_max = float(p75 * 1.2)
                    
                    if preferred_price_min < 1.0:
                        preferred_price_min = 0.0
                    if preferred_price_max <= preferred_price_min:
                        preferred_price_max = float(np.max(prices) * 1.5)
            
            pref = UserPreference.query.filter_by(user_id=user_id).first()
            if not pref:
                pref = UserPreference(user_id=user_id)
                db.session.add(pref)
                
            pref.preferred_categories = categories
            pref.preferred_brands = brands
            pref.preferred_platforms = platforms
            pref.preferred_price_min = preferred_price_min
            pref.preferred_price_max = preferred_price_max
            pref.last_updated = datetime.utcnow()
            
            db.session.commit()
            logger.info(f"Updated preferences for user {user_id}")
            return pref
        except Exception as e:
            logger.error(f"Error updating preferences: {str(e)}")
            db.session.rollback()
            return None

    def _get_max_popularity(self):
        """Get max interaction count across all products for normalization"""
        try:
            all_prods = Product.query.with_entities(Product.id).all()
            max_interactions = 0
            for pid, in all_prods:
                clicks = ClickEvent.query.filter_by(product_id=pid).count()
                wishlists = WishlistItem.query.filter_by(product_id=pid).count()
                purchases = PurchaseEvent.query.filter_by(product_id=pid).count()
                val = clicks + 3 * wishlists + 5 * purchases
                if val > max_interactions:
                    max_interactions = val
            return max_interactions
        except Exception:
            return 1

    def calculate_hybrid_score(self, product, user_pref, user_vector, max_popularity):
        """Calculate hybrid personalized score and breakdown values using the unified final scoring engine"""
        content_score = 0.0
        if self.is_trained and user_vector is not None and product.id in self.product_ids:
            idx = self.product_ids.index(product.id)
            prod_vector = self.product_vectors[idx]
            content_score = float(cosine_similarity(user_vector, prod_vector)[0][0])
            
        final_score, breakdown = self.calculate_final_product_score(
            product, relevance_score=content_score, query_intent=None, max_reviews=max_popularity or 1, user_pref=user_pref, strict=False
        )
        
        return final_score, {
            'content_score': round(breakdown['relevance_score'], 2),
            'preference_score': round(breakdown['preference_score'], 2),
            'popularity_score': round(breakdown['popularity_score'], 2),
            'quality_score': round(breakdown['quality_score'], 2),
            'final_score': round(final_score, 2)
        }

    def generate_explanation(self, product, user_pref, user_id, is_exploration=False):
        """Generate human-readable personalization explanations based on user history"""
        if is_exploration:
            return f"Trending product in {product.category or 'Other'} to discover"
            
        # Check wishlist
        wish = WishlistItem.query.filter_by(user_id=user_id, product_id=product.id).first()
        if wish:
            return "Similar to items in your wishlist"
            
        # Check clicks
        clicks = ClickEvent.query.filter_by(user_id=user_id, product_id=product.id).first()
        if clicks:
            return "Based on products you recently viewed"
            
        # Preferred brand
        if user_pref and product.brand and product.brand in user_pref.preferred_brands:
            brand_weight = user_pref.preferred_brands[product.brand]
            if brand_weight > 2:
                return f"Matches your brand preference for {product.brand}"
                
        # Preferred category
        if user_pref and product.category and product.category in user_pref.preferred_categories:
            return f"Recommended because you frequently browse {product.category}"
            
        # Price range
        if user_pref and product.price and user_pref.preferred_price_min <= product.price <= user_pref.preferred_price_max:
            if product.rating and product.rating >= 4.0:
                return f"Matches your budget with a solid {product.rating}★ rating"
                
        return "Popular pick matching your general interests"

    def get_personalized_recommendations(self, user_id, limit=20):
        """Core personalized recommendation method serving three distinct rails"""
        if not self.is_trained:
            self.train()
            
        # Update user profile
        user_pref = UserPreference.query.filter_by(user_id=user_id).first()
        if not user_pref:
            user_pref = self.update_user_preferences(user_id)
            
        # Exclusions: Purchased items + Disliked/Hidden items
        purchased_ids = [p.product_id for p in PurchaseEvent.query.filter_by(user_id=user_id).all()]
        feedback_records = RecommendationFeedback.query.filter_by(user_id=user_id).all()
        
        disliked_ids = [f.product_id for f in feedback_records if f.feedback_type in ['dislike', 'not_interested']]
        saved_ids = [f.product_id for f in feedback_records if f.feedback_type == 'save_for_later']
        
        exclude_ids = set(purchased_ids + disliked_ids)
        
        # Build user weighted vector
        user_vector = None
        if self.is_trained:
            clicks = ClickEvent.query.filter_by(user_id=user_id).all()
            wish = WishlistItem.query.filter_by(user_id=user_id).all()
            purchases = PurchaseEvent.query.filter_by(user_id=user_id).all()
            
            if clicks or wish or purchases:
                user_vector = np.zeros((1, self.product_vectors.shape[1]))
                total_weight = 0.0
                for c in clicks:
                    if c.product_id in self.product_ids:
                        idx = self.product_ids.index(c.product_id)
                        user_vector += self.product_vectors[idx].toarray() * 1.0
                        total_weight += 1.0
                for w in wish:
                    if w.product_id in self.product_ids:
                        idx = self.product_ids.index(w.product_id)
                        user_vector += self.product_vectors[idx].toarray() * 3.0
                        total_weight += 3.0
                for p in purchases:
                    if p.product_id in self.product_ids:
                        idx = self.product_ids.index(p.product_id)
                        user_vector += self.product_vectors[idx].toarray() * 5.0
                        total_weight += 5.0
                if total_weight > 0:
                    user_vector = user_vector / total_weight
                    norm = np.linalg.norm(user_vector)
                    if norm > 0:
                        user_vector = user_vector / norm
                        
        max_popularity = self._get_max_popularity()
        
        # Candidate products
        candidates_query = Product.query
        if exclude_ids:
            candidates_query = candidates_query.filter(Product.id.not_in(exclude_ids))
        candidates = candidates_query.all()
        
        scored_candidates = []
        for p in candidates:
            score, breakdown = self.calculate_hybrid_score(p, user_pref, user_vector, max_popularity)
            # Boost saved items
            if p.id in saved_ids:
                score += 0.15
                breakdown['final_score'] = round(score, 2)
            scored_candidates.append({
                'product': p,
                'score': score,
                'breakdown': breakdown
            })
            
        scored_candidates.sort(key=lambda x: x['score'], reverse=True)
        
        # 1. Recommended For You (Balanced + Diversity + 10% Exploration)
        diverse_list = []
        category_counts = {}
        decay = 0.8
        
        remaining = list(scored_candidates)
        while remaining and len(diverse_list) < 8:
            for item in remaining:
                cat = item['product'].category or 'Other'
                count = category_counts.get(cat, 0)
                item['current_score'] = item['score'] * (decay ** count)
                
            remaining.sort(key=lambda x: x['current_score'], reverse=True)
            top_item = remaining.pop(0)
            diverse_list.append(top_item)
            
            cat = top_item['product'].category or 'Other'
            category_counts[cat] = category_counts.get(cat, 0) + 1
            
        # Inject 10% Exploration items (Popular items in non-user categories)
        user_categories = set(user_pref.preferred_categories.keys()) if user_pref and user_pref.preferred_categories else set()
        
        exploration_items = []
        if len(diverse_list) >= 8:
            other_candidates_query = Product.query
            if user_categories:
                other_candidates_query = other_candidates_query.filter(Product.category.not_in(user_categories))
            if exclude_ids:
                other_candidates_query = other_candidates_query.filter(Product.id.not_in(exclude_ids))
            # Exclude already in diverse list
            already_recommended = [x['product'].id for x in diverse_list]
            if already_recommended:
                other_candidates_query = other_candidates_query.filter(Product.id.not_in(already_recommended))
                
            other_candidates = other_candidates_query.all()
            other_scored = []
            for p in other_candidates:
                clicks = ClickEvent.query.filter_by(product_id=p.id).count()
                wishlists = WishlistItem.query.filter_by(product_id=p.id).count()
                purchases = PurchaseEvent.query.filter_by(product_id=p.id).count()
                pop = clicks + 3 * wishlists + 5 * purchases
                other_scored.append((p, pop))
                
            other_scored.sort(key=lambda x: x[1], reverse=True)
            exploration_items = [item[0] for item in other_scored[:2]]
            
        # Place exploration items in the list
        recommended_for_you_rail = []
        for i, item in enumerate(diverse_list):
            recommended_for_you_rail.append({
                'product': item['product'].to_dict(),
                'reason': self.generate_explanation(item['product'], user_pref, user_id),
                'breakdown': item['breakdown'],
                'is_exploration': False
            })
            
        # Inject exploration at position 9 and 18
        if len(exploration_items) >= 1 and len(recommended_for_you_rail) >= 10:
            p_explore = exploration_items[0]
            _, breakdown = self.calculate_hybrid_score(p_explore, user_pref, user_vector, max_popularity)
            recommended_for_you_rail.insert(9, {
                'product': p_explore.to_dict(),
                'reason': self.generate_explanation(p_explore, user_pref, user_id, is_exploration=True),
                'breakdown': breakdown,
                'is_exploration': True
            })
            
        if len(exploration_items) >= 2 and len(recommended_for_you_rail) >= 19:
            p_explore = exploration_items[1]
            _, breakdown = self.calculate_hybrid_score(p_explore, user_pref, user_vector, max_popularity)
            recommended_for_you_rail.insert(18, {
                'product': p_explore.to_dict(),
                'reason': self.generate_explanation(p_explore, user_pref, user_id, is_exploration=True),
                'breakdown': breakdown,
                'is_exploration': True
            })
            
        # 2. Trending In Your Interests Rail
        trending_in_your_interests_rail = []
        interest_categories = list(user_categories) if user_categories else []
        
        trending_query = Product.query
        if interest_categories:
            trending_query = trending_query.filter(Product.category.in_(interest_categories))
        if exclude_ids:
            trending_query = trending_query.filter(Product.id.not_in(exclude_ids))
            
        trending_candidates = trending_query.all()
        trending_scored = []
        for p in trending_candidates:
            # Score primarily on global popularity and value
            clicks = ClickEvent.query.filter_by(product_id=p.id).count()
            wishlists = WishlistItem.query.filter_by(product_id=p.id).count()
            purchases = PurchaseEvent.query.filter_by(product_id=p.id).count()
            pop = clicks + 3 * wishlists + 5 * purchases
            pop_score = float(np.log1p(pop) / np.log1p(max_popularity)) if max_popularity > 0 else 0.0
            
            rank_score = self.calculate_recommendation_score(p)
            score = 0.6 * pop_score + 0.4 * rank_score
            trending_scored.append((p, score, pop_score, rank_score))
            
        trending_scored.sort(key=lambda x: x[1], reverse=True)
        for p, s, pop_s, rank_s in trending_scored[:6]:
            trending_in_your_interests_rail.append({
                'product': p.to_dict(),
                'reason': f"Popular among users interested in {p.category or 'Other'}",
                'breakdown': {
                    'content_score': 0.0,
                    'preference_score': 1.0,
                    'popularity_score': round(pop_s, 2),
                    'quality_score': round(rank_s, 2),
                    'final_score': round(s, 2)
                }
            })
            
        # 3. Recently Similar Products Rail (similar to last 3 viewed items)
        recently_similar_rail = []
        recent_views = ClickEvent.query.filter_by(user_id=user_id).order_by(ClickEvent.created_at.desc()).limit(3).all()
        recent_viewed_product_ids = [c.product_id for c in recent_views if c.product]
        
        if recent_viewed_product_ids and self.is_trained:
            similar_candidates_with_scores = []
            
            for pid in recent_viewed_product_ids:
                if pid in self.product_ids:
                    idx = self.product_ids.index(pid)
                    vec = self.product_vectors[idx]
                    similarities = cosine_similarity(vec, self.product_vectors).flatten()
                    
                    # Sort candidates
                    for other_idx, sim in enumerate(similarities):
                        other_pid = self.product_ids[other_idx]
                        if other_pid == pid or other_pid in exclude_ids:
                            continue
                        # If already added, keep the maximum similarity score
                        existing = next((x for x in similar_candidates_with_scores if x[0].id == other_pid), None)
                        if existing:
                            if sim > existing[1]:
                                similar_candidates_with_scores.remove(existing)
                                product_obj = Product.query.get(other_pid)
                                if product_obj:
                                    similar_candidates_with_scores.append((product_obj, sim, pid))
                        else:
                            product_obj = Product.query.get(other_pid)
                            if product_obj:
                                similar_candidates_with_scores.append((product_obj, sim, pid))
                                
            similar_candidates_with_scores.sort(key=lambda x: x[1], reverse=True)
            for p, sim, source_pid in similar_candidates_with_scores[:6]:
                source_product = Product.query.get(source_pid)
                source_name = source_product.name[:30] + "..." if source_product else "items you viewed"
                
                # Compute sub-scores for breakdown
                _, breakdown = self.calculate_hybrid_score(p, user_pref, user_vector, max_popularity)
                
                recently_similar_rail.append({
                    'product': p.to_dict(),
                    'reason': f"Similar to '{source_name}' you recently viewed",
                    'breakdown': breakdown
                })
                
        # Track served analytics
        try:
            total_served = len(recommended_for_you_rail) + len(trending_in_your_interests_rail) + len(recently_similar_rail)
            if total_served > 0:
                counter = AnalyticsCounter.query.filter_by(key='recommendations_served').first()
                if not counter:
                    counter = AnalyticsCounter(key='recommendations_served', value=0)
                    db.session.add(counter)
                counter.value += total_served
                db.session.commit()
        except Exception as ex:
            logger.warning(f"Error updating recommendations_served counter: {ex}")
            db.session.rollback()
            
        return {
            'recommended_for_you': recommended_for_you_rail,
            'trending_in_your_interests': trending_in_your_interests_rail,
            'recently_similar': recently_similar_rail
        }

    def get_cold_start_recommendations(self, limit=20):
        """Serve non-personalized onboarding rails for cold-start (guests/new users)"""
        # Rails to compile:
        # 1. Popular Electronics
        # 2. Popular Fashion
        # 3. Popular Mobiles
        # 4. Best Rated Products
        # 5. Most Wishlisted Products
        
        # Track impressions
        try:
            counter = AnalyticsCounter.query.filter_by(key='recommendations_served').first()
            if not counter:
                counter = AnalyticsCounter(key='recommendations_served', value=0)
                db.session.add(counter)
            counter.value += (limit * 5)
            db.session.commit()
        except Exception:
            db.session.rollback()

        max_popularity = self._get_max_popularity()
        
        def compile_rail(query_filter, reason_template):
            candidates = query_filter.all()
            scored = []
            for p in candidates:
                clicks = ClickEvent.query.filter_by(product_id=p.id).count()
                wishlists = WishlistItem.query.filter_by(product_id=p.id).count()
                purchases = PurchaseEvent.query.filter_by(product_id=p.id).count()
                pop = clicks + 3 * wishlists + 5 * purchases
                pop_score = float(np.log1p(pop) / np.log1p(max_popularity)) if max_popularity > 0 else 0.0
                rank_score = self.calculate_recommendation_score(p)
                score = 0.5 * pop_score + 0.5 * rank_score
                scored.append((p, score, pop_score, rank_score))
            scored.sort(key=lambda x: x[1], reverse=True)
            return [{
                'product': item[0].to_dict(),
                'reason': reason_template.format(cat=item[0].category),
                'breakdown': {
                    'content_score': 0.0,
                    'preference_score': 0.0,
                    'popularity_score': round(item[2], 2),
                    'quality_score': round(item[3], 2),
                    'final_score': round(item[1], 2)
                }
            } for item in scored[:limit]]

        # 1. Electronics
        elec_rail = compile_rail(
            Product.query.filter(Product.category.ilike('%electronic%')),
            "Top pick in {cat}"
        )
        # 2. Fashion
        fashion_rail = compile_rail(
            Product.query.filter(Product.category.ilike('%fashion%') | Product.category.ilike('%clothing%') | Product.category.ilike('%shirt%')),
            "Popular in fashion"
        )
        # 3. Mobiles
        mobiles_rail = compile_rail(
            Product.query.filter(Product.category.ilike('%mobile%') | Product.category.ilike('%phone%')),
            "Best choice in smart devices"
        )
        # 4. Best Rated
        best_rated_rail = compile_rail(
            Product.query.filter(Product.rating >= 4.5),
            "Highly rated ({rating}★) across platforms"
        )
        # For best rated, overwrite reason with actual rating
        for item in best_rated_rail:
            item['reason'] = f"Highly rated ({item['product']['rating']}★) on {item['product']['platform']}"
            
        # 5. Most Wishlisted
        wishlist_counts = db.session.query(WishlistItem.product_id, db.func.count(WishlistItem.id)) \
            .group_by(WishlistItem.product_id) \
            .order_by(db.func.count(WishlistItem.id).desc()) \
            .limit(limit) \
            .all()
            
        most_wishlisted_products = []
        for pid, count in wishlist_counts:
            p = Product.query.get(pid)
            if p:
                rank_score = self.calculate_recommendation_score(p)
                most_wishlisted_products.append({
                    'product': p.to_dict(),
                    'reason': f"Faved by {count} other shoppers",
                    'breakdown': {
                        'content_score': 0.0,
                        'preference_score': 0.0,
                        'popularity_score': 1.0,
                        'quality_score': round(rank_score, 2),
                        'final_score': round(rank_score, 2)
                    }
                })
        # Fill most wishlisted with general popular items if empty
        if not most_wishlisted_products:
            most_wishlisted_products = compile_rail(Product.query, "Popular pick for new shoppers")[:limit]

        return {
            'popular_electronics': elec_rail,
            'popular_fashion': fashion_rail,
            'popular_mobiles': mobiles_rail,
            'best_rated': best_rated_rail,
            'most_wishlisted': most_wishlisted_products
        }

    def update_recommendation_scores(self):
        """Update recommendation scores for all products"""
        products = Product.query.all()
        prices = [p.price for p in products if p.price]
        min_price = min(prices) if prices else None
        max_price = max(prices) if prices else None
        
        for product in products:
            score = self.calculate_recommendation_score(product, min_price, max_price)
            product.recommendation_score = score
        
        db.session.commit()
        logger.info(f"Updated recommendation scores for {len(products)} products")




