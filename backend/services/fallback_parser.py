import re
import logging

logger = logging.getLogger(__name__)

def parse_budget_to_number(val):
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

    digits_only = re.sub(r'[^\d\.]', '', val_clean)
    if digits_only:
        try:
            parsed = float(digits_only)
            return parsed if parsed >= 0 else None
        except ValueError:
            pass

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

def format_currency_inr(val):
    if not val:
        return ""
    try:
        return f"₹{val:,.0f}"
    except Exception:
        return f"₹{val}"

class FallbackParser:
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
        
        for cat, keywords in category_map.items():
            for kw in keywords:
                if re.search(r'\b' + re.escape(kw) + r'\b', query_lower):
                    category = cat
                    break
            if category:
                break
                
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

        platforms = ["amazon", "flipkart", "meesho", "myntra"]
        for p in platforms:
            if re.search(r'\b' + re.escape(p) + r'\b', query_lower):
                platform = p.capitalize()
                break

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

        gender = None
        gender_map = {
            "men": ["men", "mens", "male", "gentleman", "gentlemen"],
            "women": ["women", "womens", "female", "lady", "ladies"],
            "boys": ["boy", "boys"],
            "girls": ["girl", "girls"],
            "kids": ["kid", "kids", "child", "children"],
            "unisex": ["unisex"]
        }
        for gen, keywords in gender_map.items():
            for kw in keywords:
                if re.search(r'\b' + re.escape(kw) + r'\b', query_lower):
                    gender = gen
                    break
            if gender:
                break

        material = None
        materials = ["cotton", "silk", "polyester", "denim", "linen", "wool", "woollen", "leather", "nylon"]
        for mat in materials:
            if re.search(r'\b' + re.escape(mat) + r'\b', query_lower):
                material = mat
                break

        color = None
        colors = ["red", "blue", "green", "black", "white", "grey", "gray", "yellow", "pink", "purple", "orange", "brown", "gold", "silver"]
        for col in colors:
            if re.search(r'\b' + re.escape(col) + r'\b', query_lower):
                color = col
                break

        specifications = []
        spec_patterns = [
            r'\b\d+\s*(?:gb|tb)\b',
            r'\bi[3579]\b',
            r'\bryzen\s*[3579]\b',
            r'\brtx\s*\d{4}\b',
            r'\bssd\b',
            r'\bdedicated graphics\b'
        ]
        for pat in spec_patterns:
            matches = re.findall(pat, query_lower)
            if matches:
                specifications.extend(matches)

        bullets = []
        if category:
            bullets.append(f"✓ Looking for: {category}")
        if brand:
            bullets.append(f"✓ Brand: {brand}")
        if gender:
            bullets.append(f"✓ Gender: {gender.capitalize()}")
        if material:
            bullets.append(f"✓ Material: {material.capitalize()}")
        if color:
            bullets.append(f"✓ Color: {color.capitalize()}")
        if budget_max:
            if budget_min:
                bullets.append(f"✓ Budget: {format_currency_inr(budget_min)} – {format_currency_inr(budget_max)}")
            else:
                bullets.append(f"✓ Budget: Under {format_currency_inr(budget_max)}")
        if purpose:
            bullets.append(f"✓ Purpose: {purpose.replace('_', ' ').capitalize()}")
        if features:
            bullets.append(f"✓ Key Features: {', '.join(features)}")
        if specifications:
            bullets.append(f"✓ Specifications: {', '.join(specifications)}")
            
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
            "material": material,
            "gender": gender,
            "color": color,
            "specifications": specifications,
            "confidence": 0.5,
            "rewritten_query": query,
            "search_explanation_bullets": bullets,
            "refinements": refinements
        }
