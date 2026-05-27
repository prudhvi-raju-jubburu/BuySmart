from flask import Blueprint, jsonify
from models import db
from services.ai_status import get_ai_status
import logging

logger = logging.getLogger(__name__)
health_bp = Blueprint('health', __name__)

@health_bp.route('/api/health', methods=['GET'])
def get_health():
    """Verify raw database connectivity and return system health statuses"""
    db_ok = False
    try:
        db.session.execute(db.text("SELECT 1"))
        db_ok = True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")

    ai_status = get_ai_status()
    
    status_str = "healthy" if db_ok else "unhealthy"
    status_code = 200 if db_ok else 500

    return jsonify({
        "status": status_str,
        "database": db_ok,
        "gemini": ai_status["gemini_available"],
        "openai": ai_status["openai_available"],
        "fallback_parser": ai_status["fallback_active"]
    }), status_code
