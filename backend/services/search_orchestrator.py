import logging
import time
import json
from .ai_parser import AIParser
from .fallback_parser import FallbackParser
from .category_filter import CategoryRelevanceFilter
from .relevance_scorer import RelevanceScorer

logger = logging.getLogger(__name__)

class SearchOrchestrator:
    def __init__(self):
        self.ai_parser = AIParser()
        self.fallback_parser = FallbackParser()
        
    def parse_query_intent(self, query, user_context_str=None):
        """First attempts Gemini AI parsing, falls back to rule-based parser if it fails"""
        intent = None
        try:
            logger.info("SearchOrchestrator: Attempting Gemini AI parsing...")
            intent = self.ai_parser.try_gemini(query, user_context_str)
            if intent:
                intent["gemini_used"] = True
                logger.info("SearchOrchestrator: Gemini AI parsing succeeded.")
        except Exception as e:
            logger.error(f"SearchOrchestrator: Gemini AI parsing failed with error: {e}", exc_info=True)
            
        if not intent:
            try:
                logger.info("SearchOrchestrator: Falling back to local parser...")
                intent = self.fallback_parser.fallback_parser(query)
                intent["gemini_used"] = False
                logger.info("SearchOrchestrator: Local fallback parsing succeeded.")
            except Exception as e:
                logger.error(f"SearchOrchestrator: Local fallback parsing crashed: {e}", exc_info=True)
                # Absolute last-resort default intent
                intent = {
                    "category": None,
                    "brand": None,
                    "budget_min": None,
                    "budget_max": None,
                    "confidence": 0.1,
                    "rewritten_query": query,
                    "gemini_used": False,
                    "search_explanation_bullets": [f"Showing products matching '{query}'"],
                    "refinements": []
                }
                
        if intent:
            if 'budget_max' in intent and 'max_price' not in intent:
                intent['max_price'] = intent['budget_max']
            if 'budget_min' in intent and 'min_price' not in intent:
                intent['min_price'] = intent['budget_min']
            if 'max_price' in intent and 'budget_max' not in intent:
                intent['budget_max'] = intent['max_price']
            if 'min_price' in intent and 'budget_min' not in intent:
                intent['budget_min'] = intent['min_price']
                
        return intent

    def apply_category_relevance_filtering(self, products, category, query_lower):
        """Filters out products that match category relevance exclusions"""
        before_count = len(products)
        filtered = [
            p for p in products
            if not CategoryRelevanceFilter.is_irrelevant(p, category, query_lower)
        ]
        removed_count = before_count - len(filtered)
        if removed_count > 0:
            logger.info(f"SearchOrchestrator: Filtered out {removed_count} products due to category relevance exclusions.")
        return filtered
