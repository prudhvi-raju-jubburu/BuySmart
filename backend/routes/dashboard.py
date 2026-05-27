from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from models import db, User, Product, SearchEvent, ClickEvent, WishlistItem, PurchaseEvent, PriceDropAlert
from datetime import datetime, timedelta
from functools import wraps
import logging

logger = logging.getLogger(__name__)
dashboard_bp = Blueprint('dashboard', __name__)

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

def get_category_for_query(query_str):
    """Dynamically map a search query to a category by checking actual products in DB"""
    if not query_str or not query_str.strip():
        return None
    try:
        result = db.session.query(Product.category, db.func.count(Product.category)) \
            .filter(Product.name.like(f"%{query_str.strip()}%")) \
            .filter(Product.category.isnot(None)) \
            .filter(Product.category != '') \
            .group_by(Product.category) \
            .order_by(db.func.count(Product.category).desc()) \
            .first()
        if result:
            return result[0]
    except Exception as e:
        logger.warning(f"Error mapping query to category: {e}")
    return None

# ==========================================
# 1. Profile Section APIs
# ==========================================

@dashboard_bp.route('/api/profile', methods=['GET'])
@require_auth
def get_profile():
    """Get the authenticated user's profile details"""
    user = request.user
    return jsonify({
        "success": True,
        "message": "Profile fetched successfully",
        "data": {
            "user": user.to_dict()
        }
    }), 200

@dashboard_bp.route('/api/profile', methods=['PUT'])
@require_auth
def update_profile():
    """Update the authenticated user's profile name and/or password"""
    user = request.user
    data = request.get_json() or {}
    
    name = data.get('name')
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    
    if name is not None:
        name_val = name.strip()
        if not name_val:
            return jsonify({"success": False, "message": "Name cannot be empty"}), 400
        user.name = name_val

    if new_password:
        if not current_password:
            return jsonify({"success": False, "message": "Current password is required to set a new password"}), 400
        if not user.check_password(current_password):
            return jsonify({"success": False, "message": "Incorrect current password"}), 401
        if len(new_password) < 6:
            return jsonify({"success": False, "message": "New password must be at least 6 characters"}), 400
        
        user.set_password(new_password)

    db.session.commit()
    return jsonify({
        "success": True,
        "message": "Profile updated successfully",
        "data": {
            "user": user.to_dict()
        }
    }), 200

# ==========================================
# 2. Overview Statistics APIs
# ==========================================

@dashboard_bp.route('/api/dashboard/overview', methods=['GET'])
@require_auth
def get_overview():
    """Get KPI summary statistics for the dashboard"""
    user_id = request.user.id
    
    # 1. Total Searches
    total_searches = db.session.query(SearchEvent).filter_by(user_id=user_id).count()
    
    # 2. Product Views
    product_views = ClickEvent.query.filter_by(user_id=user_id).count()
    
    # 3. Wishlist Items
    wishlist_items = WishlistItem.query.filter_by(user_id=user_id).count()
    
    # 4. Active Price Alerts
    active_alerts = PriceDropAlert.query.filter_by(user_id=user_id, is_active=True).count()
    
    # 5. Recommendation Clicks
    recommendation_clicks = ClickEvent.query.filter_by(user_id=user_id, source='recommendation').count()
    
    # 6. Purchases
    purchases = PurchaseEvent.query.filter_by(user_id=user_id).count()
    
    # 7. CTR
    recommendation_ctr = round(recommendation_clicks / product_views, 4) if product_views > 0 else 0.0

    return jsonify({
        "success": True,
        "message": "Overview statistics fetched successfully",
        "data": {
            "total_searches": total_searches,
            "product_views": product_views,
            "wishlist_items": wishlist_items,
            "active_price_alerts": active_alerts,
            "recommendation_clicks": recommendation_clicks,
            "total_purchases": purchases,
            "recommendation_ctr": recommendation_ctr
        }
    }), 200

# ==========================================
# 3. Search History Panel APIs
# ==========================================

@dashboard_bp.route('/api/dashboard/search-history', methods=['GET'])
@require_auth
def get_search_history():
    """Get the authenticated user's search history with pagination & filters"""
    user_id = request.user.id
    
    # Query parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    query_filter = request.args.get('query', '').strip()
    
    # Build query
    history_query = db.session.query(SearchEvent).filter(SearchEvent.user_id == user_id)
    if query_filter:
        history_query = history_query.filter(SearchEvent.query.like(f"%{query_filter}%"))
        
    history_query = history_query.order_by(SearchEvent.created_at.desc())
    
    # Paginate
    pagination = history_query.paginate(page=page, per_page=per_page, error_out=False)
    items = [item.to_dict() for item in pagination.items]
    
    # Statistics
    # Most frequent search terms (Top 5)
    frequent_terms_raw = db.session.query(SearchEvent.query, db.func.count(SearchEvent.query)) \
        .filter(SearchEvent.user_id == user_id) \
        .group_by(SearchEvent.query) \
        .order_by(db.func.count(SearchEvent.query).desc()) \
        .limit(5) \
        .all()
    
    frequent_terms = [{"term": row[0], "count": row[1]} for row in frequent_terms_raw]
    
    # Search Category Frequency (computed from search events themselves)
    all_events = db.session.query(SearchEvent.query).filter(SearchEvent.user_id == user_id).all()
    category_counts = {}
    for event in all_events:
        cat = get_category_for_query(event.query)
        if cat:
            category_counts[cat] = category_counts.get(cat, 0) + 1
            
    sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
    most_searched_category = sorted_categories[0][0] if sorted_categories else None
    
    return jsonify({
        "success": True,
        "message": "Search history fetched successfully",
        "data": {
            "items": items,
            "total": pagination.total,
            "page": page,
            "pages": pagination.pages,
            "has_next": pagination.has_next,
            "has_prev": pagination.has_prev,
            "most_searched_category": most_searched_category,
            "frequent_search_terms": frequent_terms
        }
    }), 200

@dashboard_bp.route('/api/dashboard/search-history/<int:event_id>', methods=['DELETE'])
@require_auth
def delete_search_history_entry(event_id):
    """Delete (or hide) a single search history entry"""
    user_id = request.user.id
    event = db.session.query(SearchEvent).filter_by(id=event_id, user_id=user_id).first()
    
    if not event:
        return jsonify({"success": False, "message": "Search history entry not found or unauthorized"}), 404
        
    db.session.delete(event)
    db.session.commit()
    
    return jsonify({
        "success": True,
        "message": "Search history entry deleted successfully"
    }), 200

# ==========================================
# 4. Recently Viewed Products APIs
# ==========================================

@dashboard_bp.route('/api/dashboard/recently-viewed', methods=['GET'])
@require_auth
def get_recently_viewed():
    """Get the authenticated user's recently viewed products (unique, top 20, via ClickEvent)"""
    user_id = request.user.id
    
    # Query click events ordered by latest, grouping by product_id
    # We fetch latest click events, filter unique product_ids in memory, and fetch products.
    clicks = ClickEvent.query.filter_by(user_id=user_id).order_by(ClickEvent.created_at.desc()).all()
    
    unique_product_ids = []
    product_views_map = {} # Maps product_id to latest view time
    
    for c in clicks:
        if c.product_id not in product_views_map:
            product_views_map[c.product_id] = c.created_at
            unique_product_ids.append(c.product_id)
            
        if len(unique_product_ids) >= 20:
            break
            
    # Fetch the product details
    if not unique_product_ids:
        return jsonify({
            "success": True,
            "message": "No recently viewed products found",
            "data": []
        }), 200
        
    products = Product.query.filter(Product.id.in_(unique_product_ids)).all()
    # Sort them back in the order of their latest click
    products_sorted = sorted(products, key=lambda p: product_views_map[p.id], reverse=True)
    
    data = []
    for p in products_sorted:
        p_dict = p.to_dict()
        p_dict['viewed_at'] = product_views_map[p.id].isoformat()
        data.append(p_dict)
        
    return jsonify({
        "success": True,
        "message": "Recently viewed products fetched successfully",
        "data": data
    }), 200

# ==========================================
# 5. Wishlist Management APIs
# ==========================================

@dashboard_bp.route('/api/dashboard/wishlist', methods=['GET'])
@require_auth
def get_wishlist_details():
    """Get user wishlist with advanced sorting and detailed stats"""
    user_id = request.user.id
    sort_by = request.args.get('sort_by', 'date_added').strip().lower()
    
    # Query all items
    query = WishlistItem.query.filter_by(user_id=user_id)
    
    # Apply sorting
    if sort_by == 'price_asc':
        query = query.join(Product, WishlistItem.product_id == Product.id).order_by(Product.price.asc())
    elif sort_by == 'price_desc':
        query = query.join(Product, WishlistItem.product_id == Product.id).order_by(Product.price.desc())
    elif sort_by == 'rating':
        query = query.join(Product, WishlistItem.product_id == Product.id).order_by(Product.rating.desc())
    else: # date_added
        query = query.order_by(WishlistItem.created_at.desc())
        
    items = query.all()
    items_list = [item.to_dict() for item in items]
    
    # Statistics
    total_items = len(items)
    
    avg_rating = 0.0
    avg_price = 0.0
    highest_rated = None
    lowest_price_item = None
    
    if total_items > 0:
        ratings = [item.product.rating for item in items if item.product and item.product.rating is not None]
        prices = [item.product.price for item in items if item.product and item.product.price is not None]
        
        avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else 0.0
        avg_price = round(sum(prices) / len(prices), 2) if prices else 0.0
        
        # Highest Rated Product
        sorted_by_rating = sorted([item.product for item in items if item.product and item.product.rating is not None], key=lambda x: x.rating, reverse=True)
        highest_rated = sorted_by_rating[0].to_dict() if sorted_by_rating else None
        
        # Lowest Price Product
        sorted_by_price = sorted([item.product for item in items if item.product and item.product.price is not None], key=lambda x: x.price)
        lowest_price_item = sorted_by_price[0].to_dict() if sorted_by_price else None

    return jsonify({
        "success": True,
        "message": "Wishlist details fetched successfully",
        "data": {
            "items": items_list,
            "stats": {
                "total_items": total_items,
                "average_rating": avg_rating,
                "average_price": avg_price,
                "highest_rated_item": highest_rated,
                "lowest_price_item": lowest_price_item
            }
        }
    }), 200

# ==========================================
# 6. Price Alert Center APIs
# ==========================================

@dashboard_bp.route('/api/dashboard/price-alerts', methods=['GET'])
@require_auth
def get_price_alerts():
    """Get all user price alerts with summaries"""
    user_id = request.user.id
    alerts = PriceDropAlert.query.filter_by(user_id=user_id).order_by(PriceDropAlert.created_at.desc()).all()
    
    active_count = sum(1 for a in alerts if a.is_active)
    triggered_count = sum(1 for a in alerts if a.triggered_at is not None)
    
    return jsonify({
        "success": True,
        "message": "Price alerts fetched successfully",
        "data": {
            "alerts": [a.to_dict() for a in alerts],
            "active_count": active_count,
            "triggered_count": triggered_count
        }
    }), 200

@dashboard_bp.route('/api/dashboard/price-alerts/<int:alert_id>', methods=['PUT'])
@require_auth
def update_price_alert(alert_id):
    """Edit target price of a price alert"""
    user_id = request.user.id
    alert = PriceDropAlert.query.filter_by(id=alert_id, user_id=user_id).first()
    
    if not alert:
        return jsonify({"success": False, "message": "Price alert not found or unauthorized"}), 404
        
    data = request.get_json() or {}
    target_price = data.get('target_price')
    
    if target_price is None:
        return jsonify({"success": False, "message": "Target price is required"}), 400
        
    try:
        target_price = float(target_price)
        if target_price <= 0:
            return jsonify({"success": False, "message": "Target price must be greater than zero"}), 400
    except ValueError:
        return jsonify({"success": False, "message": "Invalid target price"}), 400
        
    alert.target_price = target_price
    # If the user edits the target price, we reactivate the alert and reset the triggered timestamp
    alert.is_active = True
    alert.triggered_at = None
    
    db.session.commit()
    return jsonify({
        "success": True,
        "message": "Price alert updated successfully",
        "data": alert.to_dict()
    }), 200

@dashboard_bp.route('/api/dashboard/price-alerts/<int:alert_id>', methods=['DELETE'])
@require_auth
def delete_price_alert(alert_id):
    """Delete a price alert"""
    user_id = request.user.id
    alert = PriceDropAlert.query.filter_by(id=alert_id, user_id=user_id).first()
    
    if not alert:
        return jsonify({"success": False, "message": "Price alert not found or unauthorized"}), 404
        
    db.session.delete(alert)
    db.session.commit()
    
    return jsonify({
        "success": True,
        "message": "Price alert deleted successfully"
    }), 200

# ==========================================
# 7. User Activity Analytics APIs
# ==========================================

@dashboard_bp.route('/api/dashboard/activity-analytics', methods=['GET'])
@require_auth
def get_activity_analytics():
    """Get personal activity trends and timelines for Recharts and displays"""
    user_id = request.user.id
    now = datetime.utcnow()
    
    # 1. Searches this week and month
    one_week_ago = now - timedelta(days=7)
    one_month_ago = now - timedelta(days=30)
    
    searches_week = db.session.query(SearchEvent) \
        .filter(SearchEvent.user_id == user_id, SearchEvent.created_at >= one_week_ago) \
        .count()
        
    searches_month = db.session.query(SearchEvent) \
        .filter(SearchEvent.user_id == user_id, SearchEvent.created_at >= one_month_ago) \
        .count()
        
    # 2. Wishlist Growth (Timeline)
    wishlist_items = WishlistItem.query.filter_by(user_id=user_id).order_by(WishlistItem.created_at.asc()).all()
    wishlist_growth = []
    running_total = 0
    
    # Group by date
    growth_by_date = {}
    for item in wishlist_items:
        date_str = item.created_at.strftime('%Y-%m-%d')
        growth_by_date[date_str] = growth_by_date.get(date_str, 0) + 1
        
    # Build timeline for chart
    for d in sorted(growth_by_date.keys()):
        running_total += growth_by_date[d]
        wishlist_growth.append({"date": d, "count": running_total})
        
    # 3. Most viewed category
    most_viewed_cat_raw = db.session.query(Product.category, db.func.count(Product.category)) \
        .join(ClickEvent, ClickEvent.product_id == Product.id) \
        .filter(ClickEvent.user_id == user_id) \
        .filter(Product.category.isnot(None)) \
        .filter(Product.category != '') \
        .group_by(Product.category) \
        .order_by(db.func.count(Product.category).desc()) \
        .first()
        
    most_viewed_category = most_viewed_cat_raw[0] if most_viewed_cat_raw else "N/A"
    
    # 4. Most clicked platform
    most_clicked_plat_raw = db.session.query(ClickEvent.platform, db.func.count(ClickEvent.platform)) \
        .filter(ClickEvent.user_id == user_id) \
        .group_by(ClickEvent.platform) \
        .order_by(db.func.count(ClickEvent.platform).desc()) \
        .first()
        
    most_clicked_platform = most_clicked_plat_raw[0] if most_clicked_plat_raw else "N/A"
    
    # 5. Most active day of the week
    clicks = ClickEvent.query.filter_by(user_id=user_id).all()
    searches = db.session.query(SearchEvent).filter(SearchEvent.user_id == user_id).all()
    
    day_counts = {0:0, 1:0, 2:0, 3:0, 4:0, 5:0, 6:0} # Monday is 0, Sunday is 6
    for c in clicks:
        day_counts[c.created_at.weekday()] += 1
    for s in searches:
        day_counts[s.created_at.weekday()] += 1
        
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    most_active_day_index = max(day_counts, key=day_counts.get)
    most_active_day = day_names[most_active_day_index] if sum(day_counts.values()) > 0 else "N/A"
    
    # 6. Charts Data: Search trend (last 14 days)
    search_trend = []
    for i in range(13, -1, -1):
        day = now - timedelta(days=i)
        day_start = datetime(day.year, day.month, day.day)
        day_end = day_start + timedelta(days=1)
        
        count = db.session.query(SearchEvent) \
            .filter(SearchEvent.user_id == user_id) \
            .filter(SearchEvent.created_at >= day_start) \
            .filter(SearchEvent.created_at < day_end) \
            .count()
            
        search_trend.append({
            "date": day_start.strftime('%b %d'),
            "searches": count
        })
        
    # 7. Charts Data: Platform usage distribution
    platform_dist_raw = db.session.query(ClickEvent.platform, db.func.count(ClickEvent.platform)) \
        .filter(ClickEvent.user_id == user_id) \
        .group_by(ClickEvent.platform) \
        .all()
        
    platform_dist = [{"name": row[0], "value": row[1]} for row in platform_dist_raw]
    
    # 8. Charts Data: Category interest distribution
    category_dist_raw = db.session.query(Product.category, db.func.count(Product.category)) \
        .join(ClickEvent, ClickEvent.product_id == Product.id) \
        .filter(ClickEvent.user_id == user_id) \
        .filter(Product.category.isnot(None)) \
        .filter(Product.category != '') \
        .group_by(Product.category) \
        .limit(10) \
        .all()
        
    category_dist = [{"name": row[0], "value": row[1]} for row in category_dist_raw]
    
    # 9. Recent Activity Timeline
    timeline_events = []
    
    # Fetch recent ClickEvents
    recent_clicks = ClickEvent.query.filter_by(user_id=user_id).order_by(ClickEvent.created_at.desc()).limit(15).all()
    for c in recent_clicks:
        if c.product:
            timeline_events.append({
                "type": "view",
                "description": f"Viewed {c.product.name[:50]}...",
                "timestamp": c.created_at,
                "platform": c.platform,
                "product": c.product.to_dict()
            })
            
    # Fetch recent WishlistItems
    recent_wishlist = WishlistItem.query.filter_by(user_id=user_id).order_by(WishlistItem.created_at.desc()).limit(15).all()
    for w in recent_wishlist:
        if w.product:
            timeline_events.append({
                "type": "wishlist",
                "description": f"Added {w.product.name[:50]}... to wishlist",
                "timestamp": w.created_at,
                "platform": w.product.platform,
                "product": w.product.to_dict()
            })
            
    # Fetch recent PriceDropAlerts
    recent_alerts = PriceDropAlert.query.filter_by(user_id=user_id).order_by(PriceDropAlert.created_at.desc()).limit(15).all()
    for a in recent_alerts:
        if a.product:
            timeline_events.append({
                "type": "alert",
                "description": f"Created price alert for {a.product.name[:50]}... (Target: ₹{a.target_price:,.2f})",
                "timestamp": a.created_at,
                "platform": a.platform,
                "product": a.product.to_dict()
            })
            
    # Fetch recent PurchaseEvents
    recent_purchases = PurchaseEvent.query.filter_by(user_id=user_id).order_by(PurchaseEvent.created_at.desc()).limit(15).all()
    for p in recent_purchases:
        if p.product:
            timeline_events.append({
                "type": "purchase",
                "description": f"Purchased {p.product.name[:50]}... via {p.platform}",
                "timestamp": p.created_at,
                "platform": p.platform,
                "product": p.product.to_dict()
            })
            
    # Sort and slice timeline to 15 items
    timeline_events = sorted(timeline_events, key=lambda x: x["timestamp"], reverse=True)[:15]
    
    # Format dates
    for ev in timeline_events:
        ev["timestamp"] = ev["timestamp"].isoformat()

    return jsonify({
        "success": True,
        "message": "Activity analytics fetched successfully",
        "data": {
            "searches_week": searches_week,
            "searches_month": searches_month,
            "wishlist_growth": wishlist_growth,
            "most_viewed_category": most_viewed_category,
            "most_clicked_platform": most_clicked_platform,
            "most_active_day": most_active_day,
            "search_trend": search_trend,
            "platform_distribution": platform_dist,
            "category_distribution": category_dist,
            "timeline": timeline_events
        }
    }), 200

# ==========================================
# 8. User Preference Profile APIs
# ==========================================

@dashboard_bp.route('/api/dashboard/preferences', methods=['GET'])
@require_auth
def get_preferences():
    """Get automatically generated shopping preference insights"""
    user_id = request.user.id
    
    # 1. Preferred Categories (Top 2 from clicks & wishlist)
    cat_clicks = db.session.query(Product.category, db.func.count(Product.category)) \
        .join(ClickEvent, ClickEvent.product_id == Product.id) \
        .filter(ClickEvent.user_id == user_id) \
        .filter(Product.category.isnot(None)) \
        .filter(Product.category != '') \
        .group_by(Product.category) \
        .all()
        
    cat_wish = db.session.query(Product.category, db.func.count(Product.category)) \
        .join(WishlistItem, WishlistItem.product_id == Product.id) \
        .filter(WishlistItem.user_id == user_id) \
        .filter(Product.category.isnot(None)) \
        .filter(Product.category != '') \
        .group_by(Product.category) \
        .all()
        
    category_tally = {}
    for cat, count in cat_clicks + cat_wish:
        category_tally[cat] = category_tally.get(cat, 0) + count
        
    preferred_categories = sorted(category_tally.keys(), key=lambda x: category_tally[x], reverse=True)[:2]
    if not preferred_categories:
        preferred_categories = ["Electronics", "Fashion"] # Defaults
        
    # 2. Preferred Platforms (Top 2 from clicks & wishlist)
    plat_clicks = db.session.query(ClickEvent.platform, db.func.count(ClickEvent.platform)) \
        .filter(ClickEvent.user_id == user_id) \
        .group_by(ClickEvent.platform) \
        .all()
        
    plat_wish = db.session.query(Product.platform, db.func.count(Product.platform)) \
        .join(WishlistItem, WishlistItem.product_id == Product.id) \
        .filter(WishlistItem.user_id == user_id) \
        .group_by(Product.platform) \
        .all()
        
    platform_tally = {}
    for plat, count in plat_clicks + plat_wish:
        platform_tally[plat] = platform_tally.get(plat, 0) + count
        
    preferred_platforms = sorted(platform_tally.keys(), key=lambda x: platform_tally[x], reverse=True)[:2]
    if not preferred_platforms:
        preferred_platforms = ["Amazon", "Flipkart"] # Defaults
        
    # 3. Preferred Price Range (Bracket tally from clicks & wishlist)
    prices_clicks = db.session.query(Product.price) \
        .join(ClickEvent, ClickEvent.product_id == Product.id) \
        .filter(ClickEvent.user_id == user_id) \
        .filter(Product.price.isnot(None)) \
        .all()
        
    prices_wish = db.session.query(Product.price) \
        .join(WishlistItem, WishlistItem.product_id == Product.id) \
        .filter(WishlistItem.user_id == user_id) \
        .filter(Product.price.isnot(None)) \
        .all()
        
    all_prices = [p[0] for p in prices_clicks + prices_wish]
    
    # Calculate most frequent price bracket
    brackets = {
        "Under ₹1,000": 0,
        "₹1,000 - ₹5,000": 0,
        "₹5,000 - ₹10,000": 0,
        "₹10,000 - ₹30,000": 0,
        "₹30,000 - ₹50,000": 0,
        "Above ₹50,000": 0
    }
    
    for price in all_prices:
        if price < 1000:
            brackets["Under ₹1,000"] += 1
        elif price < 5000:
            brackets["₹1,000 - ₹5,000"] += 1
        elif price < 10000:
            brackets["₹5,000 - ₹10,000"] += 1
        elif price < 30000:
            brackets["₹10,000 - ₹30,000"] += 1
        elif price < 50000:
            brackets["₹30,000 - ₹50,000"] += 1
        else:
            brackets["Above ₹50,000"] += 1
            
    preferred_price_range = max(brackets, key=brackets.get) if all_prices else "₹10,000 - ₹30,000"
    
    # 4. Recommendation clicks, CTR, and top recommended category
    rec_clicks = ClickEvent.query.filter_by(user_id=user_id, source='recommendation').count()
    total_clicks = ClickEvent.query.filter_by(user_id=user_id).count()
    recommendation_ctr = round(rec_clicks / total_clicks, 4) if total_clicks > 0 else 0.0
    
    top_rec_cat_query = db.session.query(Product.category, db.func.count(Product.category)) \
        .join(ClickEvent, ClickEvent.product_id == Product.id) \
        .filter(ClickEvent.user_id == user_id, ClickEvent.source == 'recommendation') \
        .filter(Product.category.isnot(None)) \
        .filter(Product.category != '') \
        .group_by(Product.category) \
        .order_by(db.func.count(Product.category).desc()) \
        .first()
    top_recommended_category = top_rec_cat_query[0] if top_rec_cat_query else "N/A"

    return jsonify({
        "success": True,
        "message": "Preferences profile fetched successfully",
        "data": {
            "preferred_categories": preferred_categories,
            "preferred_platforms": preferred_platforms,
            "preferred_price_range": preferred_price_range,
            "recommendations_clicked": rec_clicks,
            "recommendation_ctr": recommendation_ctr,
            "top_recommended_category": top_recommended_category
        }
    }), 200
