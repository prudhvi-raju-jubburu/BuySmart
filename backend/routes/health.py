import os
from flask import Blueprint, jsonify
from models import db
from services.ai_status import get_ai_status
from services.ai_search import AISearchService
import logging

logger = logging.getLogger(__name__)
ai_search_service = AISearchService()
health_bp = Blueprint('health', __name__)

@health_bp.route('/api/health', methods=['GET'])
def get_health():
    db_ok = False

    try:
        db.session.execute(db.text("SELECT 1"))
        db_ok = True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")

    try:
        ai_status = get_ai_status()
    except Exception as e:
        logger.exception(f"AI status failed: {e}")

        ai_status = {
            "gemini_available": False,
            "openai_available": False,
            "fallback_active": True
        }

    return jsonify({
        "status": "healthy" if db_ok else "unhealthy",
        "database": db_ok,
        "gemini": ai_status["gemini_available"],
        "openai": ai_status["openai_available"],
        "fallback_parser": ai_status["fallback_active"]
    })

@health_bp.route('/api/ai-health', methods=['GET'])
def get_ai_health():
    gemini_key = os.environ.get("GEMINI_API_KEY")
    gemini_configured = bool(gemini_key)
    
    gemini_working = False
    if gemini_configured:
        try:
            gemini_working = ai_search_service.test_connection()
        except Exception as e:
            logger.error(f"Gemini connection test failed: {e}")
            
    fallback_available = True
    status = "healthy" if (gemini_configured and gemini_working) else "unhealthy"
    
    return jsonify({
        "gemini_configured": gemini_configured,
        "gemini_working": gemini_working,
        "fallback_available": fallback_available,
        "status": status
    })