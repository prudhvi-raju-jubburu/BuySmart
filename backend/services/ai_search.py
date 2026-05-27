import os
import re
import json
import hashlib
import logging
import requests
from datetime import datetime, timedelta
from models import db, Product, UserPreference, SearchEvent, ClickEvent, WishlistItem, AISearchCache, PurchaseEvent
from config import Config
from .ai_status import mark_provider_quota_failed, is_provider_on_cooldown

logger = logging.getLogger(__name__)

def parse_budget_to_number(val):
    """Sanitize budget string extractions (e.g., '50k', '₹60,000', 'fifty thousand') to float"""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val) if val >= 0 else None
    if not isinstance(val, str):
        return None
        
    val_clean = val.strip().lower()
    if not val_clean:
        return None
        
    number_words = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
        "hundred": 100, "thousand": 1000, "lakh": 100000, "crore": 10000000
    }
    
    # Match digit followed by unit abbreviation
    match_k = re.search(r'([\d\.]+)\s*(k|thousand|lakh)', val_clean)
    if match_k:
        try:
            num = float(match_k.group(1))
            unit = match_k.group(2)
            if unit == 'k' or unit == 'thousand':
                return num * 1000.0
            elif unit == 'lakh':
                return num * 100000.0
        except ValueError:
            pass

    # Strip currency signs, commas, and extra text
    digits_only = re.sub(r'[^\d\.]', '', val_clean)
    if digits_only:
        try:
            parsed = float(digits_only)
            return parsed if parsed >= 0 else None
        except ValueError:
            pass

    # Check for text numbers
    words = re.findall(r'[a-z]+', val_clean)
    if words:
        total = 0
        current = 0
        for w in words:
            if w in number_words:
                val_mapping = number_words[w]
                if val_mapping == 100:
                    current *= 100
                elif val_mapping >= 1000:
                    current *= val_mapping
                    total += current
                    current = 0
                else:
                    current += val_mapping
        total += current
        if total > 0:
            return float(total)
            
    return None


class AISearchService:
    """AI Search Service connecting LLM intent extraction with product rankings"""
    
    def __init__(self):
        self.gemini_key = os.environ.get("GEMINI_API_KEY")
        self.openai_key = os.environ.get("OPENAI_API_KEY")

        logger.info(
            f"Gemini Key Loaded: {bool(self.gemini_key)}"
        )

        logger.info(
            f"OpenAI Key Loaded: {bool(self.openai_key)}"
        )
        
    def compile_user_context(self, user_id):
        """Compile a summary of user preferences and activities to guide conversational reference resolution"""
        if not user_id:
            return "No historical context available."
            
        try:
            context = []
            
            # User profile preferences
            pref = db.session.query(UserPreference).filter_by(user_id=user_id).first()
            if pref:
                top_cats = sorted(pref.preferred_categories.keys(), key=lambda x: pref.preferred_categories[x], reverse=True)[:2]
                top_brands = sorted(pref.preferred_brands.keys(), key=lambda x: pref.preferred_brands[x], reverse=True)[:2]
                if top_cats:
                    context.append(f"Preferred Categories: {', '.join(top_cats)}")
                if top_brands:
                    context.append(f"Preferred Brands: {', '.join(top_brands)}")
                    
            # Last 3 searches
            searches = db.session.query(SearchEvent) \
                .filter(SearchEvent.user_id == user_id) \
                .order_by(SearchEvent.created_at.desc()) \
                .limit(3).all()
            if searches:
                context.append(f"Recent Search History: {', '.join([s.query for s in searches])}")
                
            # Clicked category
            recent_clicks = db.session.query(Product.category) \
                .join(ClickEvent, ClickEvent.product_id == Product.id) \
                .filter(ClickEvent.user_id == user_id) \
                .order_by(ClickEvent.created_at.desc()) \
                .limit(3).all()
            if recent_clicks:
                context.append(f"Recently Viewed Categories: {', '.join(set([c[0] for c in recent_clicks if c[0]]))}")
                
            return " | ".join(context) if context else "No historical context available."
        except Exception as e:
            logger.warning(f"Error compiling user context: {e}")
            return "No historical context available."

    def extract_intent(self, query, user_context_str=None):
        """Extract structured intent using query caching and LLM prompt execution with fallback strategy"""
        # Validate query length and sanitize
        query = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', query)[:500]
        
        # Calculate SHA256 query hash
        query_hash = hashlib.sha256(query.lower().strip().encode('utf-8')).hexdigest()
        
        # 1. Check cache first (Cache Check)
        try:
            cached = db.session.query(AISearchCache).filter_by(query_hash=query_hash).first()
            if cached and cached.expires_at > datetime.utcnow():
                logger.info("AI Search: Intent cache hit")
                return cached.intent_json
        except Exception as ex:
            logger.warning(f"Cache lookup failed: {ex}")
                   
        intent = None
        
        # 2. Try Gemini
        if self.gemini_key:
            intent = self.try_gemini(query, user_context_str)
            
        # 3. Try OpenAI
        if not intent and self.openai_key:
            intent = self.try_openai(query, user_context_str)
            
        # 4. Fallback parser
        if not intent:
            logger.info("LLM APIs unavailable or on cooldown. Falling back to local parser.")
            intent = self.fallback_parser(query)
            
        # Post-process and sanitize budget limits
        try:
            intent['budget_min'] = parse_budget_to_number(intent.get('budget_min'))
            intent['budget_max'] = parse_budget_to_number(intent.get('budget_max'))
            
            # Ensure safety
            if intent.get('confidence') is None:
                intent['confidence'] = 0.5
            intent['confidence'] = float(intent['confidence'])
            
            if not intent.get('search_explanation_bullets'):
                intent['search_explanation_bullets'] = [f"✓ Results matching '{query}'"]
            if not intent.get('refinements'):
                intent['refinements'] = [f"Best {query}", f"{query} under 10k", f"new {query}"]
        except Exception as e:
            logger.warning(f"Error sanitizing intent keys: {e}")
            
        # 5. Store Cache for 24 hours
        try:
            db.session.query(AISearchCache).filter(AISearchCache.expires_at < datetime.utcnow()).delete()
            
            new_cache = AISearchCache(
                query_hash=query_hash,
                query=query,
                intent_json=intent,
                expires_at=datetime.utcnow() + timedelta(hours=24)
            )
            db.session.merge(new_cache)
            db.session.commit()
        except Exception as cache_ex:
            logger.warning(f"Failed to cache search intent: {cache_ex}")
            db.session.rollback()
            
        logger.info(f"AI Search: Extracted Intent for '{query}': {json.dumps(intent, indent=2)}")
        return intent

    def try_gemini(self, query, user_context_str=None):
        """Attempts to extract intent using Google Gemini 2.0 Flash. Enforces cooldown on failures."""
        if is_provider_on_cooldown("gemini"):
            logger.info("Gemini is on cooldown. Skipping API call.")
            return None

        system_prompt = (
            "You are a structured shopping assistant. Read a shopping search query and output JSON ONLY.\n"
            "Analyze the query and map it into the following attributes:\n"
            "- category: Singular noun, e.g. 'Laptop', 'Phone', 'Shoes', 'Watch'\n"
            "- subcategory: Specific subcategory, e.g. 'Gaming Laptop', 'Mechanical Keyboard'\n"
            "- brand: Specific brand requested, e.g. 'Samsung', 'Lenovo', 'Nike', 'Apple', or null\n"
            "- budget_min: Number (minimum budget limit, or null)\n"
            "- budget_max: Number (maximum budget limit, or null)\n"
            "- platform: Platform preference, e.g. 'Amazon', 'Flipkart', 'Meesho', 'Myntra', or null\n"
            "- rating: Float value representing minimum rating required (0.0 to 5.0, or null)\n"
            "- purpose: Main use case, MUST be one of ['gaming', 'coding', 'machine_learning', 'office', 'student', 'video_editing', 'graphic_design', 'business'] or null\n"
            "- features: List of string requested features, e.g. ['good camera', 'lightweight']\n"
            "- confidence: Float value from 0.0 to 1.0 representing how confident you are in this mapping. E.g. set <= 0.60 for generic or vague queries\n"
            "- rewritten_query: String keyword expansions containing space-separated terms to query e-commerce search engines\n"
            "- search_explanation_bullets: List of checkmarked human-readable explanation strings, e.g. ['✓ Laptops suitable for coding', '✓ Budget under ₹60,000']\n"
            "- refinements: List of 3 queries user can refine search with, e.g. ['Gaming laptops under 60k', 'Macbook for coding']\n\n"
            "Format the output strictly as a JSON object. Do not include markdown code ticks."
        )
        user_prompt = f"User Context (resolve pronouns like 'one' or 'it' using this if needed): {user_context_str or 'None'}\n\nSearch Query: \"{query}\"\n\nJSON output:"

        try:
            logger.info("Executing intent extraction via Google Gemini Flash...")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.gemini_key}"
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": f"{system_prompt}\n\n{user_prompt}"
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "responseMimeType": "application/json"
                }
            }
            res = requests.post(url, json=payload, timeout=12)
            logger.info(f"Gemini Status Code: {res.status_code}")

            if res.status_code == 200:
                data = res.json()
                if "candidates" in data and len(data["candidates"]) > 0:
                    text_res = data["candidates"][0]["content"]["parts"][0]["text"]
                    return json.loads(text_res)
                else:
                    logger.error(f"Gemini returned no candidates: {json.dumps(data)}")
            elif res.status_code == 429 or "RESOURCE_EXHAUSTED" in res.text or "quota" in res.text.lower():
                logger.warning("Gemini rate limit or quota exceeded. Triggering cooldown.")
                mark_provider_quota_failed("gemini")
            else:
                logger.error(f"Gemini API failed ({res.status_code}): {res.text}")
                if res.status_code >= 400:
                    mark_provider_quota_failed("gemini")
        except Exception as e:
            logger.exception("Gemini API execution failed")
            err_str = str(e).lower()
            if "429" in err_str or "quota" in err_str or "exhausted" in err_str or "limit" in err_str:
                mark_provider_quota_failed("gemini")
        return None

    def try_openai(self, query, user_context_str=None):
        """Attempts to extract intent using OpenAI GPT-4o-mini. Enforces cooldown on failures."""
        if is_provider_on_cooldown("openai"):
            logger.info("OpenAI is on cooldown. Skipping API call.")
            return None

        system_prompt = (
            "You are a structured shopping assistant. Read a shopping search query and output JSON ONLY.\n"
            "Analyze the query and map it into the following attributes:\n"
            "- category: Singular noun, e.g. 'Laptop', 'Phone', 'Shoes', 'Watch'\n"
            "- subcategory: Specific subcategory, e.g. 'Gaming Laptop', 'Mechanical Keyboard'\n"
            "- brand: Specific brand requested, e.g. 'Samsung', 'Lenovo', 'Nike', 'Apple', or null\n"
            "- budget_min: Number (minimum budget limit, or null)\n"
            "- budget_max: Number (maximum budget limit, or null)\n"
            "- platform: Platform preference, e.g. 'Amazon', 'Flipkart', 'Meesho', 'Myntra', or null\n"
            "- rating: Float value representing minimum rating required (0.0 to 5.0, or null)\n"
            "- purpose: Main use case, MUST be one of ['gaming', 'coding', 'machine_learning', 'office', 'student', 'video_editing', 'graphic_design', 'business'] or null\n"
            "- features: List of string requested features, e.g. ['good camera', 'lightweight']\n"
            "- confidence: Float value from 0.0 to 1.0 representing how confident you are in this mapping. E.g. set <= 0.60 for generic or vague queries\n"
            "- rewritten_query: String keyword expansions containing space-separated terms to query e-commerce search engines\n"
            "- search_explanation_bullets: List of checkmarked human-readable explanation strings, e.g. ['✓ Laptops suitable for coding', '✓ Budget under ₹60,000']\n"
            "- refinements: List of 3 queries user can refine search with, e.g. ['Gaming laptops under 60k', 'Macbook for coding']\n\n"
            "Format the output strictly as a JSON object."
        )
        user_prompt = f"User Context (resolve pronouns like 'one' or 'it' using this if needed): {user_context_str or 'None'}\n\nSearch Query: \"{query}\"\n\nJSON output:"

        try:
            logger.info("Executing intent extraction via OpenAI GPT-4o-mini...")
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.openai_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "response_format": {"type": "json_object"}
            }
            res = requests.post(url, headers=headers, json=payload, timeout=12)
            logger.info(f"OpenAI Status Code: {res.status_code}")

            if res.status_code == 200:
                data = res.json()
                text_res = data["choices"][0]["message"]["content"]
                return json.loads(text_res)
            elif res.status_code == 429 or "insufficient_quota" in res.text or "quota" in res.text.lower():
                logger.warning("OpenAI rate limit or quota exceeded. Triggering cooldown.")
                mark_provider_quota_failed("openai")
            else:
                logger.error(f"OpenAI API failed ({res.status_code}): {res.text}")
                if res.status_code >= 400:
                    mark_provider_quota_failed("openai")
        except Exception as e:
            logger.exception("OpenAI API execution failed")
            err_str = str(e).lower()
            if "429" in err_str or "quota" in err_str or "insufficient" in err_str or "limit" in err_str:
                mark_provider_quota_failed("openai")
        return None

    def fallback_parser(self, query):
        """Rule-based local search intelligence parser mapping categories, brands, purposes, budgets, features."""
        query_lower = query.lower()
        
        category = None
        brand = None
        budget_min = None
        budget_max = None
        platform = None
        rating = None
        purpose = None
        features = []
        
        # Category map
        category_map = {
            "Laptop": ["laptop", "notebook", "ultrabook", "macbook", "chromebook", "computer", "laptops", "computers", "pc"],
            "Phone": ["mobile", "phone", "smartphone", "iphone", "mobiles", "phones", "smartphones"],
            "Tablet": ["tablet", "tablets", "ipad", "ipads", "tab", "tabs"],
            "Shoes": ["shoe", "shoes", "sneaker", "sneakers", "running shoes", "sports shoes", "footwear", "sandal", "sandals", "slippers", "boot", "boots"],
            "Fashion": ["clothing", "fashion", "apparel", "shirt", "tshirt", "t-shirt", "pant", "jeans", "dress", "saree", "kurti", "jacket", "hoodie", "sweater", "wear", "garment", "garments", "shirts", "pants"],
            "Watch": ["watch", "watches", "smartwatch", "smartwatches", "timepiece"],
            "Audio": ["headphone", "headphones", "earbud", "earbuds", "earphone", "earphones", "speaker", "speakers", "soundbar", "audio", "mic", "microphone", "tws"],
            "Television": ["tv", "tvs", "television", "televisions", "smart tv", "led tv"],
            "Monitor": ["monitor", "monitors", "display", "displays", "screen", "screens"],
            "Camera": ["camera", "cameras", "dslr", "lens", "lenses", "gopro", "action cam"],
            "Printer": ["printer", "printers", "scanner", "scanners", "copier", "inkjet", "laserjet"],
            "Accessories": ["cover", "covers", "case", "cases", "charger", "adapter", "sleeve", "sleeves", "keyboard", "mouse", "mousepad", "bag", "backpack"]
        }
        
        # Word boundaries matching categories
        for cat, keywords in category_map.items():
            for kw in keywords:
                if re.search(r'\b' + re.escape(kw) + r'\b', query_lower):
                    category = cat
                    break
            if category:
                break
                
        # Brands: Apple, Samsung, Lenovo, Dell, HP, Asus, Acer, Nike, Adidas, Puma, Boat, JBL
        brands_map = {
            "Apple": ["apple", "macbook", "iphone", "ipad"],
            "Samsung": ["samsung", "galaxy"],
            "Lenovo": ["lenovo", "thinkpad"],
            "Dell": ["dell", "inspiron", "xps"],
            "HP": ["hp", "pavilion"],
            "Asus": ["asus", "rog", "zenbook"],
            "Acer": ["acer", "aspire", "nitro"],
            "Nike": ["nike"],
            "Adidas": ["adidas"],
            "Puma": ["puma"],
            "Boat": ["boat", "rockerz"],
            "JBL": ["jbl"]
        }
        for brand_name, keywords in brands_map.items():
            for kw in keywords:
                if re.search(r'\b' + re.escape(kw) + r'\b', query_lower):
                    brand = brand_name
                    break
            if brand:
                break

        # Platform: Amazon, Flipkart, Meesho, Myntra
        platforms = ["amazon", "flipkart", "meesho", "myntra"]
        for p in platforms:
            if re.search(r'\b' + re.escape(p) + r'\b', query_lower):
                platform = p.capitalize()
                break

        # Rating matching, e.g. "4 star", "4.5 rating", "rating above 4", "4 star and above"
        rating_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:\+)?\s*(?:star|rating)', query_lower)
        if rating_match:
            try:
                rating = float(rating_match.group(1))
            except ValueError:
                pass
        else:
            rating_match_alt = re.search(r'(?:rating|stars?)\s*(?:above|over|of)?\s*(\d+(?:\.\d+)?)', query_lower)
            if rating_match_alt:
                try:
                    rating = float(rating_match_alt.group(1))
                except ValueError:
                    pass

        # Purposes: Gaming, Coding, Machine Learning, Student, Office, Business, Graphic Design, Video Editing
        purpose_map = {
            "gaming": ["gaming", "gamer", "play", "games"],
            "coding": ["coding", "programming", "developer", "software", "vscode", "python", "java", "c++"],
            "machine_learning": ["machine learning", "ml", "ai", "data science", "deep learning", "neural"],
            "student": ["student", "college", "school", "study", "studies", "education"],
            "office": ["office", "work", "meeting", "excel"],
            "business": ["business", "professional", "enterprise", "corporate", "travel"],
            "graphic_design": ["graphic design", "design", "photoshop", "illustrator", "creator", "graphics"],
            "video_editing": ["video editing", "editor", "premiere", "rendering"]
        }
        for p_name, keywords in purpose_map.items():
            for kw in keywords:
                if re.search(r'\b' + re.escape(kw) + r'\b', query_lower):
                    purpose = p_name
                    break
            if purpose:
                break

        # Features: FEATURE_KEYWORDS map:
        feature_keywords = {
            "camera": ["camera", "photography", "selfie", "megapixels", "mp"],
            "battery": ["battery", "backup", "long lasting", "mah", "charger"],
            "lightweight": ["lightweight", "portable", "thin", "sleek"],
            "running": ["running", "jogging", "sports", "athletic"],
            "bluetooth": ["bluetooth", "wireless", "tws", "cordless"]
        }
        for feat, keywords in feature_keywords.items():
            for kw in keywords:
                if re.search(r'\b' + re.escape(kw) + r'\b', query_lower):
                    features.append(feat)
                    break

        # Budget extraction: e.g. "under 50000", "50k", "₹50,000", "30k to 50k"
        range_match = re.search(r'(\d+(?:\s*k)?)\s*(?:to|and|-)\s*(\d+(?:\s*k)?)', query_lower)
        if range_match:
            budget_min = parse_budget_to_number(range_match.group(1))
            budget_max = parse_budget_to_number(range_match.group(2))
        else:
            numbers = re.findall(r'\b(?:₹|rs\.?)?\s*(\d+(?:,\d+)*(?:\s*[kK])?)\b', query_lower)
            if numbers:
                for num_str in numbers:
                    parsed_num = parse_budget_to_number(num_str)
                    if parsed_num:
                        num_index = query_lower.find(num_str)
                        preceding_slice = query_lower[max(0, num_index-20):num_index].strip()
                        
                        is_max = any(w in preceding_slice for w in ["under", "below", "less", "max", "sub", "around", "within"])
                        is_min = any(w in preceding_slice for w in ["above", "over", "more", "min", "greater"])
                        
                        if is_min:
                            budget_min = parsed_num
                        elif is_max or not budget_min:
                            budget_max = parsed_num

        if budget_min is not None and budget_max is not None and budget_min > budget_max:
            budget_min, budget_max = budget_max, budget_min

        # Exclusions/Explanations
        bullets = []
        if category:
            bullets.append(f"✓ Looking for: {category}")
        if brand:
            bullets.append(f"✓ Brand: {brand}")
        if budget_max:
            if budget_min:
                bullets.append(f"✓ Budget: {format_currency_inr(budget_min)} – {format_currency_inr(budget_max)}")
            else:
                bullets.append(f"✓ Budget: Under {format_currency_inr(budget_max)}")
        if purpose:
            bullets.append(f"✓ Purpose: {purpose.replace('_', ' ').capitalize()}")
        if features:
            bullets.append(f"✓ Key Features: {', '.join(features)}")
            
        if not bullets:
            bullets.append(f"✓ Showing products matching '{query}'")

        refinements = []
        if category:
            refinements = [
                f"Best {category} reviews",
                f"Branded {category} options",
                f"Affordable {category} online"
            ]
        else:
            refinements = [
                f"Best {query} deals",
                f"Top rated {query}",
                f"Compare {query} prices"
            ]

        return {
            "category": category,
            "subcategory": None,
            "brand": brand,
            "budget_min": budget_min,
            "budget_max": budget_max,
            "platform": platform,
            "rating": rating,
            "purpose": purpose,
            "features": features,
            "confidence": 0.5,
            "rewritten_query": query,
            "search_explanation_bullets": bullets,
            "refinements": refinements
        }


def format_currency_inr(val):
    if not val:
        return ""
    try:
        return f"₹{val:,.0f}"
    except Exception:
        return f"₹{val}"
