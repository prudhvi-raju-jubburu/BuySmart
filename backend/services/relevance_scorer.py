import re
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class RelevanceScorer:
    @staticmethod
    def calculate_final_score(product, relevance_score, query_intent=None, max_reviews=1, user_pref=None, strict=True):
        p_name = product.get('name') or ''
        p_cat = product.get('category') or ''
        p_desc = product.get('description') or ''
        p_brand = (product.get('brand') or '').lower().strip()
        p_price = product.get('price')
        p_text = f"{p_name} {p_desc} {p_cat}".lower()
        
        brand_multiplier = 1.0
        requested_brand = (query_intent.get('brand') or query_intent.get('requested_brand')) if query_intent else None
        if requested_brand:
            requested_brand = str(requested_brand).lower().strip()
            if p_brand:
                if p_brand == requested_brand:
                    brand_multiplier = 1.0
                else:
                    brand_multiplier = 0.4 if strict else 0.7
            else:
                brand_multiplier = 0.7

        relevance = relevance_score * brand_multiplier
        
        # Calculate quality (rating, review count, platform trust, brand trust, completeness)
        rating_val = product.get('rating')
        rating = float(rating_val) if rating_val else 0.0
        rating_score = min(1.0, rating / 5.0)
        
        review_count_val = product.get('review_count')
        review_count = float(review_count_val) if review_count_val else 0.0
        review_score = min(1.0, review_count / max_reviews) if max_reviews > 0 else 0.0
        
        platform = (product.get('platform') or "").lower().strip()
        platform_scores = {
            "amazon": 0.95,
            "flipkart": 0.90,
            "myntra": 0.92,
            "meesho": 0.75
        }
        platform_trust = platform_scores.get(platform, 0.80)
        
        # Brand Match
        brand_match_score = 1.0 if p_brand and requested_brand and p_brand == requested_brand else 0.0
        
        quality_score = (
            0.35 * rating_score +
            0.20 * review_score +
            0.20 * platform_trust +
            0.15 * brand_match_score +
            0.10 * 0.9  # Completeness default
        )
        quality = min(1.0, max(0.0, quality_score))

        # Preference Match
        preference = 0.0
        if user_pref:
            cat_affinity = user_pref.preferred_categories.get(p_cat, 0) if p_cat else 0
            brand_affinity = user_pref.preferred_brands.get(p_brand, 0) if p_brand else 0
            plat_affinity = user_pref.preferred_platforms.get(platform, 0) if platform else 0
            
            max_cat = max(user_pref.preferred_categories.values()) if user_pref.preferred_categories else 1
            max_brand = max(user_pref.preferred_brands.values()) if user_pref.preferred_brands else 1
            max_plat = max(user_pref.preferred_platforms.values()) if user_pref.preferred_platforms else 1
            
            cat_score = cat_affinity / max_cat if max_cat > 0 else 0.0
            brand_score_pref = brand_affinity / max_brand if max_brand > 0 else 0.0
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
            preference = 0.4 * cat_score + 0.3 * brand_score_pref + 0.2 * price_score + 0.1 * plat_score

        # Popularity (normalized review count)
        popularity = review_score
        
        # Spec Match
        spec = 0.0
        detected_purpose = (query_intent.get('purpose') or query_intent.get('detected_purpose')) if query_intent else None
        if detected_purpose:
            has_ram_16 = bool(re.search(r'\b(16\s*gb|16gb|32\s*gb|32gb)\b', p_text, re.I))
            has_ssd = bool(re.search(r'\b(ssd|nvme)\b', p_text, re.I))
            has_cpu_strong = bool(re.search(r'\b(i5|i7|i9|ryzen|m1|m2|m3)\b', p_text, re.I))
            has_gpu_dedicated = bool(re.search(r'\b(rtx|gtx|nvidia|gpu)\b', p_text, re.I))
            
            if detected_purpose == "gaming":
                if has_gpu_dedicated: spec += 0.5
                if has_ram_16: spec += 0.3
                if has_cpu_strong: spec += 0.2
            elif detected_purpose == "coding":
                if has_ram_16: spec += 0.4
                if has_ssd: spec += 0.3
                if has_cpu_strong: spec += 0.3
            else:
                if has_ram_16: spec += 0.4
                if has_ssd: spec += 0.3
                if has_cpu_strong: spec += 0.3
            spec = min(1.0, spec)
            
        # Freshness
        freshness = 0.5
        
        # Calculate Final Relevance-First Score
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
