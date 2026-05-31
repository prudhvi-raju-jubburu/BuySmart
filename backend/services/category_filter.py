import re
import logging

logger = logging.getLogger(__name__)

CATEGORY_EXCLUSIONS = {
    "laptop": ["bag", "backpack", "sleeve", "cover", "case", "screen guard", "sticker", "decal", "toy", "learning toy", "stand", "holder", "accessories", "accessory"],
    "phone": ["cover", "case", "mobile cover", "tempered glass", "glass", "charger", "cable", "adapter", "screen guard", "protector", "holder", "stand", "accessories", "accessory"],
    "mobile": ["cover", "case", "mobile cover", "tempered glass", "glass", "charger", "cable", "adapter", "screen guard", "protector", "holder", "stand", "accessories", "accessory"],
    "shirt": ["combo pack", "combo", "accessories", "accessory", "cover", "case"],
    "shoes": ["accessories", "accessory", "care", "cleaner", "polish", "lace", "laces"]
}

class CategoryRelevanceFilter:
    @staticmethod
    def get_active_exclusions(category, query_lower):
        if not category:
            return set()
            
        cat_lower = category.lower().strip()
        exclusions = set()
        
        # Check map matching keys
        for map_cat, terms in CATEGORY_EXCLUSIONS.items():
            if map_cat == cat_lower or cat_lower in map_cat or map_cat in cat_lower:
                exclusions.update(terms)
                
        # Remove any terms that are explicitly requested in the query
        active_exclusions = set()
        for term in exclusions:
            if not re.search(r'\b' + re.escape(term) + r'\b', query_lower):
                active_exclusions.add(term)
                
        return active_exclusions

    @staticmethod
    def is_irrelevant(product, category, query_lower):
        if not category:
            return False
            
        active_exclusions = CategoryRelevanceFilter.get_active_exclusions(category, query_lower)
        if not active_exclusions:
            return False
            
        p_name = (product.get('name') or '').lower()
        p_cat = (product.get('category') or '').lower()
        p_desc = (product.get('description') or '').lower()
        
        for term in active_exclusions:
            pattern = r'\b' + re.escape(term) + r'\b'
            if (re.search(pattern, p_name) or 
                re.search(pattern, p_cat) or 
                re.search(pattern, p_desc)):
                logger.info(f"Category Relevance Filter: Excluded product '{product.get('name')}' due to forbidden term '{term}'")
                return True
                
        return False
