from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from models import db, User, Product, SearchEvent, ClickEvent, WishlistItem, PurchaseEvent, ScrapingLog, Feedback, AnalyticsCounter, AISearchEvent
from datetime import datetime, timedelta
from services.ai_status import get_ai_status
from functools import wraps
import logging

logger = logging.getLogger(__name__)
admin_bp = Blueprint('admin', __name__)

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            user = User.query.get(user_id)
            if not user or (user.role != 'admin' and not user.is_admin):
                return jsonify({"success": False, "message": "Admin access required"}), 403
            if not user.is_active:
                return jsonify({"success": False, "message": "Account disabled. Please contact support."}), 403
            return fn(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Admin required check failed: {e}")
            return jsonify({"success": False, "message": "Invalid or expired token"}), 401
    return wrapper

@admin_bp.route('/users', methods=['GET'])
@admin_required
def get_users():
    """Fetch list of all users along with their individual activity statistics"""
    try:
        users = User.query.order_by(User.created_at.desc()).all()
        user_list = []
        for u in users:
            searches = db.session.query(SearchEvent).filter_by(user_id=u.id).count()
            clicks = ClickEvent.query.filter_by(user_id=u.id).count()
            wishlist = WishlistItem.query.filter_by(user_id=u.id).count()
            purchases = PurchaseEvent.query.filter_by(user_id=u.id).count()
            
            u_dict = u.to_dict()
            u_dict['stats'] = {
                'searches': searches,
                'clicks': clicks,
                'wishlist': wishlist,
                'purchases': purchases
            }
            user_list.append(u_dict)
            
        return jsonify({
            "success": True,
            "data": {
                "users": user_list
            }
        }), 200
    except Exception as e:
        logger.error(f"Error fetching users: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@admin_bp.route('/users/<int:user_id>/status', methods=['POST'])
@admin_required
def update_user_status(user_id):
    """Enable or disable user account (soft-delete) with self-disabling check"""
    try:
        current_user_id = get_jwt_identity()
        if str(user_id) == str(current_user_id):
            return jsonify({"success": False, "message": "You cannot disable your own account."}), 400
            
        user = User.query.get(user_id)
        if not user:
            return jsonify({"success": False, "message": "User not found."}), 404
            
        data = request.get_json() or {}
        is_active = data.get('is_active')
        if is_active is None:
            is_active = not user.is_active
            
        user.is_active = bool(is_active)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"User account has been {'enabled' if user.is_active else 'disabled'}.",
            "data": {
                "user": user.to_dict()
            }
        }), 200
    except Exception as e:
        logger.error(f"Error updating user status: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@admin_bp.route('/users/<int:user_id>/role', methods=['POST'])
@admin_required
def update_user_role(user_id):
    """Change user role (user/admin) with self-demotion check"""
    try:
        current_user_id = get_jwt_identity()
        if str(user_id) == str(current_user_id):
            return jsonify({"success": False, "message": "You cannot modify your own role."}), 400
            
        user = User.query.get(user_id)
        if not user:
            return jsonify({"success": False, "message": "User not found."}), 404
            
        data = request.get_json() or {}
        role = data.get('role')
        if role not in ['user', 'admin']:
            return jsonify({"success": False, "message": "Invalid role specified."}), 400
            
        user.role = role
        user.is_admin = (role == 'admin')
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"User role has been updated to {role}.",
            "data": {
                "user": user.to_dict()
            }
        }), 200
    except Exception as e:
        logger.error(f"Error updating user role: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@admin_bp.route('/stats', methods=['GET'])
@admin_required
def get_stats():
    """Fetch comprehensive system and performance statistics for dashboard"""
    try:
        # Overview totals
        total_users = User.query.count()
        total_products = Product.query.count()
        total_searches = db.session.query(SearchEvent).count()
        total_clicks = ClickEvent.query.count()
        total_wishlist = WishlistItem.query.count()
        total_purchases = PurchaseEvent.query.count()
        
        # Recommendation CTR
        served_counter = AnalyticsCounter.query.filter_by(key='recommendations_served').first()
        recommendations_served = served_counter.value if served_counter else 0
        
        clicked_counter = AnalyticsCounter.query.filter_by(key='recommendations_clicked').first()
        recommendation_clicks = clicked_counter.value if clicked_counter else 0
        if recommendation_clicks == 0:
            recommendation_clicks = ClickEvent.query.filter_by(source='recommendation').count()
            
        liked_counter = AnalyticsCounter.query.filter_by(key='recommendations_liked').first()
        recommendations_liked = liked_counter.value if liked_counter else 0
        
        hidden_counter = AnalyticsCounter.query.filter_by(key='recommendations_hidden').first()
        recommendations_hidden = hidden_counter.value if hidden_counter else 0
        
        recommendation_ctr = (recommendation_clicks / recommendations_served * 100) if recommendations_served > 0 else 0.0
        like_rate = (recommendations_liked / recommendations_served * 100) if recommendations_served > 0 else 0.0
        hide_rate = (recommendations_hidden / recommendations_served * 100) if recommendations_served > 0 else 0.0

        # User Growth Analytics
        now = datetime.utcnow()
        today_start = datetime(now.year, now.month, now.day)
        week_start = now - timedelta(days=7)
        month_start = now - timedelta(days=30)
        
        users_today = User.query.filter(User.created_at >= today_start).count()
        users_week = User.query.filter(User.created_at >= week_start).count()
        users_month = User.query.filter(User.created_at >= month_start).count()
        
        # Most Active Users (Top 10)
        users = User.query.all()
        user_activity_list = []
        for u in users:
            u_searches = db.session.query(SearchEvent).filter_by(user_id=u.id).count()
            u_clicks = ClickEvent.query.filter_by(user_id=u.id).count()
            if u_searches > 0 or u_clicks > 0:
                user_activity_list.append({
                    "id": u.id,
                    "name": u.name,
                    "email": u.email,
                    "searches": u_searches,
                    "clicks": u_clicks,
                    "total": u_searches + u_clicks
                })
        # Sort desc by total activity
        most_active_users = sorted(user_activity_list, key=lambda x: x["total"], reverse=True)[:10]

        # Platform Performance Analytics
        # Get count, avg rating, avg price per platform
        platform_performance = []
        platforms = ['amazon', 'flipkart', 'myntra', 'meesho']
        for plat in platforms:
            prod_count = Product.query.filter(db.func.lower(Product.platform) == plat).count()
            avg_rating_query = db.session.query(db.func.avg(Product.rating)).filter(db.func.lower(Product.platform) == plat).scalar()
            avg_price_query = db.session.query(db.func.avg(Product.price)).filter(db.func.lower(Product.platform) == plat).scalar()
            
            platform_performance.append({
                "platform": plat.capitalize(),
                "products": prod_count,
                "avg_rating": round(avg_rating_query, 2) if avg_rating_query else 0.0,
                "avg_price": round(avg_price_query, 2) if avg_price_query else 0.0
            })

        # Search Intelligence Dashboard
        # Top 10 Searches
        top_searches_query = db.session.query(
            SearchEvent.query,
            db.func.count(SearchEvent.id).label('count')
        ).group_by(SearchEvent.query).order_by(db.text('count DESC')).limit(10).all()
        top_searches = [{"query": row[0], "count": row[1]} for row in top_searches_query]

        # Failed Searches (results_count == 0)
        failed_searches_query = db.session.query(
            SearchEvent.query,
            db.func.count(SearchEvent.id).label('count')
        ).filter(SearchEvent.results_count == 0).group_by(SearchEvent.query).order_by(db.text('count DESC')).limit(10).all()
        failed_searches = [{"query": row[0], "count": row[1]} for row in failed_searches_query]

        # Searches Today and Week
        searches_today = db.session.query(SearchEvent).filter(SearchEvent.created_at >= today_start).count()
        searches_week = db.session.query(SearchEvent).filter(SearchEvent.created_at >= week_start).count()

        # Category Popularity (Group by category)
        category_query = db.session.query(
            Product.category,
            db.func.count(Product.id).label('count')
        ).filter(Product.category != None, Product.category != '').group_by(Product.category).order_by(db.text('count DESC')).limit(10).all()
        category_popularity = [{"category": row[0], "count": row[1]} for row in category_query]

        # Search Trends (Last 7 Days)
        search_trends = []
        for i in range(6, -1, -1):
            day_date = today_start - timedelta(days=i)
            next_day_date = day_date + timedelta(days=1)
            day_searches = db.session.query(SearchEvent).filter(SearchEvent.created_at >= day_date, SearchEvent.created_at < next_day_date).count()
            search_trends.append({
                "day": day_date.strftime("%b %d"),
                "searches": day_searches
            })

        # Scraping Monitor
        recent_logs = ScrapingLog.query.order_by(ScrapingLog.started_at.desc()).limit(10).all()
        scraping_monitor = [log.to_dict() for log in recent_logs]

        # Feedback Center
        recent_feedback = Feedback.query.order_by(Feedback.created_at.desc()).limit(10).all()
        feedback_list = [f.to_dict() for f in recent_feedback]

        # AI Search stats
        total_ai_searches = db.session.query(AISearchEvent).count()
        success_ai_searches = db.session.query(AISearchEvent).filter_by(is_success=True).count()
        ai_search_success_rate = round((success_ai_searches / total_ai_searches * 100), 2) if total_ai_searches > 0 else 0.0
        
        helpful_count = db.session.query(AISearchEvent).filter_by(feedback='helpful').count()
        not_helpful_count = db.session.query(AISearchEvent).filter_by(feedback='not_helpful').count()
        
        # Vendor-neutral extraction of top categories/brands from AI JSON intents
        recent_ai_events = db.session.query(AISearchEvent).order_by(AISearchEvent.created_at.desc()).limit(500).all()
        ai_categories = {}
        ai_brands = {}
        for ev in recent_ai_events:
            intent = ev.extracted_intent or {}
            cat = intent.get('category')
            brand = intent.get('brand')
            if cat:
                ai_categories[cat] = ai_categories.get(cat, 0) + 1
            if brand:
                ai_brands[brand] = ai_brands.get(brand, 0) + 1
        
        top_ai_categories = sorted([{"category": k, "count": v} for k, v in ai_categories.items()], key=lambda x: x["count"], reverse=True)[:5]
        top_ai_brands = sorted([{"brand": k, "count": v} for k, v in ai_brands.items()], key=lambda x: x["count"], reverse=True)[:5]

        return jsonify({
            "success": True,
            "data": {
                "overview": {
                    "total_users": total_users,
                    "total_products": total_products,
                    "total_searches": total_searches,
                    "total_clicks": total_clicks,
                    "wishlist_count": total_wishlist,
                    "purchase_count": total_purchases,
                    "recommendations_served": recommendations_served,
                    "recommendation_clicks": recommendation_clicks,
                    "recommendation_ctr": round(recommendation_ctr, 2),
                    "recommendations_liked": recommendations_liked,
                    "recommendations_hidden": recommendations_hidden,
                    "like_rate": round(like_rate, 2),
                    "hide_rate": round(hide_rate, 2),
                    "total_ai_searches": total_ai_searches,
                    "ai_search_success_rate": ai_search_success_rate,
                    "ai_helpful_count": helpful_count,
                    "ai_not_helpful_count": not_helpful_count,
                    "top_ai_categories": top_ai_categories,
                    "top_ai_brands": top_ai_brands,
                    "ai_status": get_ai_status()
                },
                "user_growth": {
                    "today": users_today,
                    "week": users_week,
                    "month": users_month
                },
                "most_active_users": most_active_users,
                "platform_performance": platform_performance,
                "search_intelligence": {
                    "top_searches": top_searches,
                    "failed_searches": failed_searches,
                    "searches_today": searches_today,
                    "searches_week": searches_week,
                    "category_popularity": category_popularity,
                    "search_trends": search_trends
                },
                "scraping_monitor": scraping_monitor,
                "feedback_center": feedback_list
            }
        }), 200
    except Exception as e:
        logger.error(f"Error fetching admin stats: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@admin_bp.route('/ai-status', methods=['GET'])
@admin_required
def get_admin_ai_status():
    """Fetch current AI provider and cooldown status for admin view"""
    try:
        status = get_ai_status()
        return jsonify({
            "success": True,
            "data": status
        }), 200
    except Exception as e:
        logger.error(f"Error fetching admin AI status: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500
