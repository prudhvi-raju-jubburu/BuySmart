import os
import re
import hashlib
import json
import requests
import logging
from datetime import datetime, timedelta
from models import db, Product, UserPreference, SearchEvent, ClickEvent, WishlistItem, AISearchCache, PurchaseEvent
from config import Config
from .ai_status import mark_provider_quota_failed, is_provider_on_cooldown
from .ai_parser import AIParser
from .fallback_parser import FallbackParser, parse_budget_to_number

logger = logging.getLogger(__name__)

class AISearchService:
    """AI Search Service connecting LLM intent extraction with product rankings"""
    
    def __init__(self):
        self._ai_parser = AIParser()
        self._fallback_parser = FallbackParser()
        self.gemini_key = self._ai_parser.gemini_key
        self.openai_key = self._ai_parser.openai_key
        self.gemini_model = self._ai_parser.gemini_model
        
    def test_connection(self):
        return self._ai_parser.test_connection()
        
    def try_gemini(self, query, user_context_str=None):
        return self._ai_parser.try_gemini(query, user_context_str)
        
    def try_openai(self, query, user_context_str=None):
        return self._ai_parser.try_openai(query, user_context_str)
        
    def fallback_parser(self, query):
        return self._fallback_parser.fallback_parser(query)

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
        query = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', query)[:500]
        query_hash = hashlib.sha256(query.lower().strip().encode('utf-8')).hexdigest()
        
        try:
            cached = db.session.query(AISearchCache).filter_by(query_hash=query_hash).first()
            if cached and cached.expires_at > datetime.utcnow():
                logger.info("AI Search: Intent cache hit")
                intent = cached.intent_json
                if intent:
                    intent.setdefault("gemini_used", False)
                return intent
        except Exception as ex:
            logger.warning(f"Cache lookup failed: {ex}")
                   
        intent = None
        
        if self.gemini_key:
            intent = self.try_gemini(query, user_context_str)
            if intent:
                intent["gemini_used"] = True
            
        if not intent and self.openai_key:
            intent = self.try_openai(query, user_context_str)
            if intent:
                intent["gemini_used"] = False
            
        if not intent:
            logger.info("LLM APIs unavailable or on cooldown. Falling back to local parser.")
            intent = self.fallback_parser(query)
            intent["gemini_used"] = False
            
        try:
            intent['budget_min'] = parse_budget_to_number(intent.get('budget_min'))
            intent['budget_max'] = parse_budget_to_number(intent.get('budget_max'))
            
            if intent.get('confidence') is None:
                intent['confidence'] = 0.5
            intent['confidence'] = float(intent['confidence'])
            
            if not intent.get('search_explanation_bullets'):
                intent['search_explanation_bullets'] = [f"✓ Results matching '{query}'"]
            if not intent.get('refinements'):
                intent['refinements'] = [f"Best {query}", f"{query} under 10k", f"new {query}"]
        except Exception as e:
            logger.warning(f"Error sanitizing intent keys: {e}")
            
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
