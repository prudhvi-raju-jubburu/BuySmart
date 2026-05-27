from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from models import db, User, Product, UserPreference, RecommendationFeedback, AnalyticsCounter
from services.recommender import ProductRecommender
from datetime import datetime
from functools import wraps
import logging

logger = logging.getLogger(__name__)
recommendations_bp = Blueprint('recommendations', __name__)
recommender = ProductRecommender()

def get_optional_user():
    """Retrieve optional user from JWT token"""
    try:
        verify_jwt_in_request(optional=True)
        user_id = get_jwt_identity()
        if user_id:
            return User.query.get(user_id)
    except Exception:
        pass
    return None

def require_auth(fn):
    """Decorator to verify JWT and attach user to request.user"""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            user = User.query.get(user_id)
            if not user:
                return jsonify({"success": False, "message": "User not found"}), 401
            if not user.is_active:
                return jsonify({"success": False, "message": "Account disabled. Please contact support."}), 403
            request.user = user
            return fn(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Auth required check failed: {e}")
            return jsonify({"success": False, "message": "Invalid or expired token"}), 401
    return wrapper

@recommendations_bp.route('/api/recommendations/personalized', methods=['GET'])
def get_personalized_recs():
    """Get personalized or guest recommendations"""
    try:
        user = get_optional_user()
        limit = request.args.get('limit', 20, type=int)
        
        if user:
            # Authenticated user hybrid recommendations
            recs = recommender.get_personalized_recommendations(user.id, limit=limit)
            return jsonify({
                "success": True,
                "data": recs,
                "is_guest": False
            }), 200
        else:
            # Guest cold-start recommendations
            cold_start = recommender.get_cold_start_recommendations(limit=limit)
            return jsonify({
                "success": True,
                "data": cold_start,
                "is_guest": True
            }), 200
            
    except Exception as e:
        logger.error(f"Error generating personalized recommendations: {str(e)}")
        return jsonify({"success": False, "message": "Internal server error"}), 500

@recommendations_bp.route('/api/recommendations/feedback', methods=['POST'])
@require_auth
def post_recommendation_feedback():
    """Submit user feedback for a recommended product (like, not_interested, save_for_later)"""
    try:
        user_id = request.user.id
        data = request.get_json() or {}
        
        product_id = data.get('product_id')
        feedback_type = data.get('feedback_type')
        
        if not product_id or not feedback_type:
            return jsonify({"success": False, "message": "product_id and feedback_type are required"}), 400
            
        if feedback_type not in ['like', 'not_interested', 'save_for_later']:
            return jsonify({"success": False, "message": "Invalid feedback_type"}), 400
            
        # Check if product exists
        product = Product.query.get(product_id)
        if not product:
            return jsonify({"success": False, "message": "Product not found"}), 404
            
        # Add or update feedback record
        feedback = RecommendationFeedback.query.filter_by(user_id=user_id, product_id=product_id).first()
        if not feedback:
            feedback = RecommendationFeedback(user_id=user_id, product_id=product_id)
            db.session.add(feedback)
            
        feedback.feedback_type = feedback_type
        feedback.created_at = datetime.utcnow()
        db.session.commit()
        
        # Recalculate preference profile
        recommender.update_user_preferences(user_id)
        
        # Analytics Counters
        try:
            if feedback_type == 'like':
                counter_key = 'recommendations_liked'
            elif feedback_type == 'not_interested':
                counter_key = 'recommendations_hidden'
            else:
                counter_key = 'recommendations_saved_for_later'
                
            counter = AnalyticsCounter.query.filter_by(key=counter_key).first()
            if not counter:
                counter = AnalyticsCounter(key=counter_key, value=0)
                db.session.add(counter)
            counter.value += 1
            db.session.commit()
        except Exception as ex:
            logger.warning(f"Error updating feedback analytics counter: {ex}")
            db.session.rollback()
            
        return jsonify({
            "success": True,
            "message": "Feedback registered successfully",
            "data": feedback.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Error saving recommendation feedback: {str(e)}")
        return jsonify({"success": False, "message": "Internal server error"}), 500
