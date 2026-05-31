import os
import requests
import json
import logging
from config import Config
from .ai_status import mark_provider_quota_failed, is_provider_on_cooldown

logger = logging.getLogger(__name__)

class AIParser:
    def __init__(self):
        self.gemini_key = Config.GEMINI_API_KEY
        self.openai_key = os.environ.get("OPENAI_API_KEY")
        self.gemini_model = Config.GEMINI_MODEL

    def test_connection(self):
        """Perform a real Gemini test request to verify if the API is working"""
        if not self.gemini_key:
            return False
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent?key={self.gemini_key}"
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": "respond with 'ok'"
                            }
                        ]
                    }
                ]
            }
            res = requests.post(url, json=payload, timeout=5)
            if res.status_code == 200:
                data = res.json()
                if "candidates" in data and len(data["candidates"]) > 0:
                    return True
            return False
        except Exception as e:
            logger.warning(f"Gemini connection test failed: {e}")
            return False

    def try_gemini(self, query, user_context_str=None):
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
            "- material: Material requested, e.g. 'cotton', 'silk', 'polyester', or null\n"
            "- gender: Target gender/demographic, e.g. 'men', 'women', 'boys', 'girls', 'kids', 'unisex', or null\n"
            "- color: Specific color requested, e.g. 'black', 'red', 'white', or null\n"
            "- specifications: List of technical specifications requested, e.g. ['16gb ram', '512gb ssd'], or empty list\n"
            "- confidence: Float value from 0.0 to 1.0 representing how confident you are in this mapping. E.g. set <= 0.60 for generic or vague queries\n"
            "- rewritten_query: String keyword expansions containing space-separated terms to query e-commerce search engines\n"
            "- search_explanation_bullets: List of checkmarked human-readable explanation strings, e.g. ['✓ Laptops suitable for coding', '✓ Budget under ₹60,000']\n"
            "- refinements: List of 3 queries user can refine search with, e.g. ['Gaming laptops under 60k', 'Macbook for coding']\n\n"
            "Format the output strictly as a JSON object. Do not include markdown code ticks."
        )
        user_prompt = f"User Context (resolve pronouns like 'one' or 'it' using this if needed): {user_context_str or 'None'}\n\nSearch Query: \"{query}\"\n\nJSON output:"

        try:
            logger.info("=== GEMINI REQUEST START ===")
            logger.info(f"Query: {query}")
            
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent?key={self.gemini_key}"
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
            logger.info("=== GEMINI RESPONSE ===")
            logger.info(res.text)
            logger.info(f"Gemini Status Code: {res.status_code}")

            if res.status_code == 200:
                data = res.json()
                if "candidates" in data and len(data["candidates"]) > 0:
                    text_res = data["candidates"][0]["content"]["parts"][0]["text"]
                    intent_data = json.loads(text_res)
                    
                    logger.info(f"Category: {intent_data.get('category')}")
                    logger.info(f"Purpose: {intent_data.get('purpose')}")
                    logger.info(f"Budget: {intent_data.get('budget_max')}")
                    logger.info(f"Keywords: {intent_data.get('rewritten_query')}")
                    logger.info(f"Confidence: {intent_data.get('confidence')}")
                    
                    return intent_data
                else:
                    logger.error("Gemini API failed")
            elif res.status_code == 429 or "RESOURCE_EXHAUSTED" in res.text or "quota" in res.text.lower():
                logger.error("Gemini API failed")
                mark_provider_quota_failed("gemini")
            else:
                logger.error("Gemini API failed")
                if res.status_code >= 400:
                    mark_provider_quota_failed("gemini")
        except Exception as e:
            logger.error("Gemini API failed")
            logger.exception("Gemini API execution failed")
            err_str = str(e).lower()
            if "429" in err_str or "quota" in err_str or "exhausted" in err_str or "limit" in err_str:
                mark_provider_quota_failed("gemini")
        return None

    def try_openai(self, query, user_context_str=None):
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
            "- material: Material requested, e.g. 'cotton', 'silk', 'polyester', or null\n"
            "- gender: Target gender/demographic, e.g. 'men', 'women', 'boys', 'girls', 'kids', 'unisex', or null\n"
            "- color: Specific color requested, e.g. 'black', 'red', 'white', or null\n"
            "- specifications: List of technical specifications requested, e.g. ['16gb ram', '512gb ssd'], or empty list\n"
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
