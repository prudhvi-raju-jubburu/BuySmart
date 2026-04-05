"""
Flask application for Product Recommendation and Price Comparison System
"""
from flask import Flask, request, jsonify, redirect
from flask_cors import CORS
from models import db, Product, ScrapingLog, User, SessionToken, WishlistItem, SearchEvent, ClickEvent, PurchaseEvent, PriceHistory, PriceDropAlert, RedirectToken, Feedback
from services.scraper import ScraperManager
from services.recommender import ProductRecommender
from config import Config
import schedule
import time
import threading
from datetime import datetime
import logging
import re
from functools import wraps
import json
from datetime import timedelta
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)
# Enable CORS for React frontend
CORS(app, resources={r"/api/*": {
    "origins": ["http://localhost:3000", "http://127.0.0.1:3000"],
    "allow_headers": ["Content-Type", "Authorization", "Access-Control-Allow-Credentials"],
    "supports_credentials": True
}})

db.init_app(app)
scraper_manager = ScraperManager()
recommender = ProductRecommender()

# Initialize database
with app.app_context():
    db.create_all()
    # Train recommender on startup
    recommender.train()
    # Bootstrap some fresh API data if DB is nearly empty
    try:
        existing_count = Product.query.count()
        if existing_count < 10:
            bootstrap_queries = ['laptop', 'phone', 'headphones']
            for q in bootstrap_queries:
                scraper_manager.scrape_platform('meesho', query=q, max_results=20)
                scraper_manager.scrape_platform('myntra', query=q, max_results=20)
            recommender.train()
    except Exception:
        pass

def _get_bearer_token():
    auth = request.headers.get('Authorization', '')
    if not auth:
        return None
    if auth.lower().startswith('bearer '):
        token = auth.split(' ', 1)[1].strip()
        logger.debug(f"Bearer token extracted: {token[:10]}...")
        return token
    logger.warning(f"Malformed Authorization header: {auth[:20]}...")
    return None

def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = _get_bearer_token()
        if not token:
            logger.warning(f"Auth required but no token found in {request.path}")
            return jsonify({'error': 'Missing Authorization: Bearer <token>'}), 401
        session = SessionToken.query.filter_by(token=token).first()
        if not session:
            logger.warning(f"Session not found for token in {request.path}")
            return jsonify({'error': 'Invalid token'}), 401
        if not session.is_active():
            logger.warning(f"Session expired for user={session.user_id} in {request.path}")
            return jsonify({'error': 'Expired token'}), 401
            
        request.user = session.user  # lightweight attach
        request.session = session
        return fn(*args, **kwargs)
    return wrapper

def require_admin(fn):
    @wraps(fn)
    @require_auth
    def wrapper(*args, **kwargs):
        if not getattr(request, 'user', None) or not request.user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        return fn(*args, **kwargs)
    return wrapper

def get_optional_user():
    """Return user if Authorization header contains a valid token; else None."""
    token = _get_bearer_token()
    if not token:
        logger.debug("Optional auth: no token found")
        return None
    session = SessionToken.query.filter_by(token=token).first()
    if not session or not session.is_active():
        logger.debug(f"Optional auth: session invalid for token {token[:10]}...")
        return None
    logger.debug(f"Optional auth: user={session.user.id} {session.user.email}")
    return session.user

def scheduled_scraping():
    """Scheduled scraping function"""
    with app.app_context():
        logger.info("Starting scheduled scraping...")
        # Scrape trending/popular products
        # You can customize this to scrape specific categories or trending searches
        trending_searches = ['laptop', 'smartphone', 'headphones', 'smartwatch']
        for search_term in trending_searches:
            scraper_manager.scrape_all_platforms(query=search_term, max_results_per_platform=10)
        logger.info("Scheduled scraping completed")

def check_price_drop_alerts():
    """Lightweight scheduled alert checker (simulated emails via logs)."""
    with app.app_context():
        alerts = (PriceDropAlert.query
                  .filter(PriceDropAlert.is_active.is_(True))
                  .filter(PriceDropAlert.triggered_at.is_(None))
                  .all())
        triggered = 0
        for alert in alerts:
            product = Product.query.get(alert.product_id)
            if not product:
                continue
            if product.platform != alert.platform:
                # For this mini-project, Product is per-platform; keep it strict.
                continue
            if product.price is None:
                continue
            if float(product.price) <= float(alert.target_price):
                alert.triggered_at = datetime.utcnow()
                alert.is_active = False
                triggered += 1
                logger.info(f"[PRICE DROP ALERT] user={alert.user_id} product={product.id} platform={alert.platform} price={product.price} target={alert.target_price} email={alert.email or '(simulated)'}")
        if triggered:
            db.session.commit()

def run_scheduler():
    """Run the scheduler in a separate thread"""
    schedule.every(Config.SCRAPING_INTERVAL_HOURS).hours.do(scheduled_scraping)
    schedule.every(10).minutes.do(check_price_drop_alerts)
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

# Start scheduler in background thread
scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
scheduler_thread.start()

@app.before_request
def log_request_info():
    """Log every incoming API request for debugging"""
    if request.path.startswith('/api'):
        method = request.method
        path = request.path
        user_agent = request.headers.get('User-Agent', 'Unknown')
        user = get_optional_user()
        user_id = user.id if user else 'guest'
        logger.info(f"API Request: {method} {path} | User: {user_id} | Agent: {user_agent[:50]}...")

@app.route('/api')
def api_info():
    """API information endpoint"""
    return jsonify({
        'status': 'online',
        'message': 'Product Recommendation and Price Comparison System API',
        'version': '1.0.0',
        'endpoints': {
            'search': '/api/search',
            'products': '/api/products',
            'scrape': '/api/scrape',
            'stats': '/api/stats',
            'scraping-logs': '/api/scraping-logs',
            'auth-register': '/api/auth/register',
            'auth-login': '/api/auth/login',
            'auth-me': '/api/auth/me',
            'auth-logout': '/api/auth/logout'
        }
    })

@app.route('/api/auth/register', methods=['POST'])
def auth_register():
    """Register a new user"""
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    name = (data.get('name') or '').strip()
    password = data.get('password') or ''

    if not email or not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
        return jsonify({'error': 'Valid email is required'}), 400
    if not name:
        return jsonify({'error': 'Name is required'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    existing = User.query.filter_by(email=email).first()
    if existing:
        return jsonify({'error': 'Email already registered'}), 409

    user = User(email=email, name=name, is_admin=bool(data.get('is_admin', False)))
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return jsonify({'status': 'success', 'user': user.to_dict()}), 201

@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    """Login and get a bearer token"""
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid email or password'}), 401

    token = SessionToken.generate_token()
    session = SessionToken(token=token, user_id=user.id)
    user.last_login_at = datetime.utcnow()
    db.session.add(session)
    db.session.commit()

    return jsonify({'status': 'success', 'token': token, 'user': user.to_dict()})

@app.route('/api/auth/me', methods=['GET'])
@require_auth
def auth_me():
    """Get current user profile"""
    return jsonify({'user': request.user.to_dict()})

@app.route('/api/auth/logout', methods=['POST'])
@require_auth
def auth_logout():
    """Revoke current token"""
    request.session.revoked_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'status': 'success'})

@app.route('/api/redirect/create', methods=['POST'])
def create_redirect():
    """Create a short-lived redirect token (secure redirection + click analytics)."""
    data = request.get_json() or {}
    product_id = data.get('product_id')
    product_data = data.get('product_data')  # for real-time products
    source = (data.get('source') or 'search').strip()
    search_query = (data.get('search_query') or '').strip()[:300] or None

    if not product_id and not (product_data and product_data.get('product_url')):
        return jsonify({'error': 'product_id (or product_data.product_url) is required'}), 400

    # For real-time products: create/find by URL
    product = None
    if product_data and product_data.get('product_url'):
        product = Product.query.filter_by(product_url=product_data['product_url']).first()
        if not product:
            product = Product(
                name=product_data.get('name', 'Unknown'),
                description=product_data.get('description'),
                price=float(product_data.get('price') or 0),
                original_price=product_data.get('original_price'),
                rating=product_data.get('rating'),
                review_count=int(product_data.get('review_count') or 0),
                platform=product_data.get('platform', 'Unknown'),
                product_url=product_data['product_url'],
                image_url=product_data.get('image_url'),
                category=product_data.get('category'),
                brand=product_data.get('brand'),
                availability=product_data.get('availability', 'In Stock')
            )
            db.session.add(product)
            db.session.commit()
    else:
        product = Product.query.get_or_404(int(product_id))

    user = get_optional_user()

    token = RedirectToken.generate_token()
    rt = RedirectToken(
        token=token,
        user_id=user.id if user else None,
        product_id=product.id,
        platform=product.platform,
        source=source,
        search_query=search_query,
        expires_at=datetime.utcnow() + timedelta(minutes=10)
    )
    db.session.add(rt)
    db.session.commit()

    # Frontend calls this URL to redirect the browser
    return jsonify({'status': 'success', 'redirect_url': f'/api/redirect/{token}'}), 201

@app.route('/api/redirect/<string:token>', methods=['GET'])
def do_redirect(token):
    """Redirect user to seller URL while logging click analytics."""
    rt = RedirectToken.query.filter_by(token=token).first()
    if not rt or not rt.is_valid():
        return jsonify({'error': 'Invalid or expired redirect token'}), 400

    product = Product.query.get(rt.product_id)
    if not product or not product.product_url:
        return jsonify({'error': 'Product not found'}), 404

    # Mark as used and log click
    rt.used_at = datetime.utcnow()
    db.session.add(ClickEvent(
        user_id=rt.user_id,
        product_id=rt.product_id,
        platform=rt.platform,
        source=rt.source,
        search_query=rt.search_query
    ))
    db.session.commit()

    # Simple safety: allow only http/https
    parsed = urlparse(product.product_url)
    if parsed.scheme not in ('http', 'https'):
        return jsonify({'error': 'Unsafe redirect URL'}), 400

    return redirect(product.product_url, code=302)

@app.route('/api/search', methods=['GET', 'POST'])
def search_products():
    """Real-time search: Fetch products directly from APIs/scrapers (no DB dependency)"""
    try:
        if request.method == 'POST':
            data = request.get_json()
            query = data.get('query', '')
            filters = data.get('filters', {})
            top_n = data.get('top_n', 50)
            fast_mode = bool(data.get('fast_mode', True))
            include_live_scraping = bool(data.get('include_live_scraping', False))
        else:
            query = request.args.get('query', '')
            filters = {
                'min_price': request.args.get('min_price', type=float),
                'max_price': request.args.get('max_price', type=float),
                'platforms': request.args.getlist('platform'),
                'min_rating': request.args.get('min_rating', type=float)
            }
            top_n = request.args.get('top_n', 50, type=int)
            fast_mode = True
            include_live_scraping = False
        
        if not query:
            return jsonify({'error': 'Query parameter is required'}), 400
        
        logger.info(f"Real-time search for '{query}' across all platforms...")
        
        # CLASSIFY INTENT: Identify category focus
        query_lower = query.lower()
        electronics_set = {'laptop', 'phone', 'mobile', 'macbook', 'ipad', 'tablet', 'desktop', 'monitor', 'gpu', 'cpu', 'camera', 'tv'}
        fashion_set = {'shirt', 'tshirt', 'pant', 'jeans', 'shoe', 'sneaker', 'dress', 'saree', 'kurti', 'jacket', 'hoodie', 'sweater', 'bag', 'backpack'}
        
        has_electronics = any(e in query_lower for e in electronics_set)
        has_fashion = any(f in query_lower for f in fashion_set)
        
        # REAL-TIME: Fetch from platforms simultaneously (no DB)
        requested_input = filters.get('platforms')
        
        if not requested_input:
            # DYNAMIC ROUTING: If user hasn't specified platforms, route based on intent
            if has_electronics and not has_fashion:
                platforms_to_search = ['amazon', 'flipkart']
                logger.info(f"Intent classified: ELECTRONICS. Routing to: {platforms_to_search}")
            elif has_fashion and not has_electronics:
                platforms_to_search = ['myntra', 'meesho', 'flipkart']
                logger.info(f"Intent classified: FASHION. Routing to: {platforms_to_search}")
            else:
                platforms_to_search = ['amazon', 'flipkart', 'meesho', 'myntra']
        else:
            # Honor user's explicit platform choices
            platforms_to_search = [p.strip().lower() for p in requested_input if isinstance(p, str)]
            if not platforms_to_search:
                platforms_to_search = ['amazon', 'flipkart', 'meesho', 'myntra']

        all_products = []
        
        # Fetch from each platform in parallel (using threads for better performance)
        import concurrent.futures
        def fetch_platform(platform_name):
            try:
                max_per_platform = max(15, top_n // len(platforms_to_search))
                products = scraper_manager.scrape_platform_realtime(platform_name, query, max_per_platform)
                return products or []
            except Exception as e:
                logger.error(f"Error fetching from {platform_name}: {e}")
                return []
        
        # Use ThreadPoolExecutor for concurrent calls with timeouts (faster UI)
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, len(platforms_to_search))) as executor:
            futures = {executor.submit(fetch_platform, p): p for p in platforms_to_search}
            try:
                for future in concurrent.futures.as_completed(futures, timeout=Config.REALTIME_OVERALL_TIMEOUT_SEC):
                    platform = futures[future]
                    try:
                        products = future.result(timeout=Config.REALTIME_PLATFORM_TIMEOUT_SEC)
                        all_products.extend(products or [])
                        logger.info(f"Fetched {len(products or [])} products from {platform}")
                    except Exception as e:
                        logger.error(f"Platform {platform} failed/timeout: {e}")
            except Exception:
                # overall timeout reached; proceed with what we have
                pass

        # De-duplicate by URL and near-identical names
        deduped = []
        seen_urls = set()
        seen_names = set()
        for p in all_products:
            url = p.get('product_url')
            name_key = re.sub(r'[^a-zA-Z0-9]', '', p.get('name', '').lower())[:30] # First 30 chars
            if not url or url in seen_urls or name_key in seen_names:
                continue
            seen_urls.add(url)
            if len(name_key) > 5:
                seen_names.add(name_key)
            deduped.append(p)
        all_products = deduped
        
        # Normalize filters to handle both camelCase (frontend) and snake_case (backend convention)
        normalized_filters = {
            'min_price': filters.get('min_price') if filters.get('min_price') is not None else filters.get('minPrice'),
            'max_price': filters.get('max_price') if filters.get('max_price') is not None else filters.get('maxPrice'),
            'min_rating': filters.get('min_rating') if filters.get('min_rating') is not None else filters.get('minRating'),
            'platforms': filters.get('platforms') if filters.get('platforms') is not None else filters.get('platforms')
        }
        
        # Apply filters
        # Note: We filter BEFORE ranking to speed up the recommender
        filtered_products = []
        # Normalize requested platforms for case-insensitive matching
        requested_normalized = [p.lower() for p in (platforms_to_search or [])]
        
        # Smart Relevance has been removed. We now trust the e-commerce platforms' native search engines 
        # to return relevant products for generic queries (like 'mobiles' or 'laptops'), as product 
        # titles for electronics often omit the category name (e.g. 'Apple iPhone 15' doesn't say 'mobile').
        # The recommender engine will handle accessory penalties.
        for p in all_products:
            # Check if product is in the user's selected platforms (case-insensitive)
            p_platform = (p.get('platform') or '').lower()
            if requested_normalized and p_platform not in requested_normalized:
                continue
                
            # Rating filter
            min_rating = normalized_filters.get('min_rating')
            if min_rating is not None and min_rating != '':
                try:
                    p_rating = float(p.get('rating') or 0)
                    # Only exclude if we have a valid scrape (>0) and it's lower than requested.
                    # Or treat 0.0 as unrated and let it pass to give the user options.
                    if p_rating > 0 and p_rating < float(min_rating):
                        continue
                except (ValueError, TypeError):
                    pass
                
            # Price filter (with slight cushion for real-time volatility)
            p_price = p.get('price')
            if p_price is not None:
                try:
                    p_price_float = float(p_price)
                    
                    min_price = normalized_filters.get('min_price')
                    if min_price is not None and min_price != '':
                        if p_price_float < float(min_price):
                            continue
                            
                    max_price = normalized_filters.get('max_price')
                    if max_price is not None and max_price != '':
                        if p_price_float > float(max_price):
                            continue
                except (ValueError, TypeError):
                    pass
            
            filtered_products.append(p)
        
        # Use recommender to rank products
        ranked_products = recommender.rank_products_realtime(query, filtered_products, filters)
        
        # Ensure all products have IDs (for frontend compatibility)
        for idx, p in enumerate(ranked_products):
            if 'id' not in p or not p.get('id'):
                p['id'] = hash(p.get('product_url', f'product_{idx}')) % 1000000
        
        # Return top 20 relevant products
        final_results = ranked_products[:20]

        # Store search history (for logged-in users and guests via frontend)
        user = get_optional_user()
        if user:
            try:
                # Deduplicate: Avoid spamming identical searches
                last_event = (db.session.query(SearchEvent)
                             .filter(SearchEvent.user_id == user.id)
                             .order_by(SearchEvent.created_at.desc())
                             .first())
                
                if last_event and last_event.query == query:
                    time_diff = (datetime.utcnow() - last_event.created_at).total_seconds()
                    if time_diff < 10: # Reduced to 10s for better responsiveness
                        logger.info(f"Skipping spam search history for user={user.id}")
                        user = None # Treat as if we already handled it

                if user:
                    # Save with normalized filters for consistency
                    event = SearchEvent(
                        user_id=user.id,
                        query=str(query)[:300],
                        filters_json=json.dumps(normalized_filters),
                        results_count=len(final_results)
                    )
                    db.session.add(event)
                    db.session.commit()
                    logger.info(f"Saved server search history for user={user.id} query='{query}' results={len(final_results)}")
            except Exception as se:
                logger.error(f"Failed to save history for user={user.id}: {se}")
                db.session.rollback()
        else:
            logger.info(f"Search for '{query}' - local history handled by frontend")
        
        # Implement cross-platform diversity (interleaving / round-robin)
        # We group ranked products by platform and pick them in order.
        # This prevents one platform from monopolizing the top 10 results simply
        # due to having marginally higher ratings or scraper advantages.
        max_results = 10
        platform_groups = {}
        
        # Keep results ordered by their individual combined scores within their platform group
        for p in ranked_products:
            plat = p.get('platform', 'Unknown')
            if plat not in platform_groups:
                platform_groups[plat] = []
            platform_groups[plat].append(p)
            
        final_results = []
        
        # Round robin extraction
        while len(final_results) < max_results and any(platform_groups.values()):
            # We want to pull from the 'strongest' platforms first if possible, 
            # so we iterate through platforms sorted by the highest top score they provide
            sorted_platforms = sorted(platform_groups.keys(), key=lambda k: platform_groups[k][0].get('combined_score', 0) if platform_groups[k] else 0, reverse=True)
            
            for plat in sorted_platforms:
                if platform_groups[plat]:
                    final_results.append(platform_groups[plat].pop(0))
                if len(final_results) >= max_results:
                    break
        
        active_platforms = list(set(p.get('platform', 'Unknown') for p in final_results))
        
        logger.info(f"Returning top {len(final_results)} interleaved products from {len(active_platforms)} platforms: {active_platforms}")

        return jsonify({
            'query': query,
            'count': len(final_results),
            'results': final_results,
            'sources': list(set(p.get('platform') for p in final_results)),
            'message': None if len(active_platforms) > 0 else "No products found on any platform."
        })
        
    except Exception as e:
        logger.error(f"Error in search: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/history/search', methods=['GET'])
@require_auth
def get_search_history():
    """Get current user's search history"""
    limit = request.args.get('limit', 50, type=int)
    
    logger.info(f"Fetching search history for user={request.user.id} {request.user.email} (limit={limit})")
    
    events = (db.session.query(SearchEvent)
              .filter(SearchEvent.user_id == request.user.id)
              .order_by(SearchEvent.created_at.desc())
              .limit(min(limit, 200))
              .all())
              
    logger.info(f"Found {len(events)} search events for user={request.user.id}")
    
    return jsonify({
        'status': 'success',
        'count': len(events),
        'items': [e.to_dict() for e in events]
    })

@app.route('/api/history/search', methods=['DELETE'])
@require_auth
def clear_search_history():
    """Clear current user's search history"""
    db.session.query(SearchEvent).filter(SearchEvent.user_id == request.user.id).delete()
    db.session.commit()
    return jsonify({'status': 'success'})

@app.route('/api/wishlist', methods=['GET'])
@require_auth
def wishlist_list():
    items = (WishlistItem.query
             .filter(WishlistItem.user_id == request.user.id)
             .order_by(WishlistItem.created_at.desc())
             .all())
    return jsonify({'count': len(items), 'items': [i.to_dict() for i in items]})

@app.route('/api/wishlist', methods=['POST'])
@require_auth
def wishlist_add():
    """Add product to wishlist - works with real-time products (stores product data)"""
    data = request.get_json() or {}
    product_id = data.get('product_id')
    product_data = data.get('product_data')  # Full product data for real-time products
    
    if not product_id:
        return jsonify({'error': 'product_id is required'}), 400
    
    # For real-time products, check by product_url instead of DB ID
    if product_data and product_data.get('product_url'):
        # Check if product exists in DB by URL, if not create it
        product = Product.query.filter_by(product_url=product_data['product_url']).first()
        if not product:
            # Create product in DB for wishlist tracking
            product = Product(
                name=product_data.get('name', 'Unknown'),
                description=product_data.get('description'),
                price=product_data.get('price', 0),
                original_price=product_data.get('original_price'),
                rating=product_data.get('rating'),
                review_count=product_data.get('review_count', 0),
                platform=product_data.get('platform', 'Unknown'),
                product_url=product_data['product_url'],
                image_url=product_data.get('image_url'),
                category=product_data.get('category'),
                brand=product_data.get('brand'),
                availability=product_data.get('availability', 'In Stock')
            )
            db.session.add(product)
            db.session.commit()
    else:
        # Try to find by ID (for DB products)
        product = Product.query.get(int(product_id))
        if not product:
            return jsonify({'error': 'Product not found'}), 404

    existing = WishlistItem.query.filter_by(user_id=request.user.id, product_id=product.id).first()
    if existing:
        return jsonify({'status': 'success', 'item': existing.to_dict()})

    item = WishlistItem(user_id=request.user.id, product_id=product.id)
    db.session.add(item)
    db.session.commit()
    return jsonify({'status': 'success', 'item': item.to_dict()}), 201

@app.route('/api/wishlist/<int:product_id>', methods=['DELETE'])
@require_auth
def wishlist_remove(product_id):
    item = WishlistItem.query.filter_by(user_id=request.user.id, product_id=product_id).first()
    if not item:
        return jsonify({'status': 'success'})
    db.session.delete(item)
    db.session.commit()
    return jsonify({'status': 'success'})

@app.route('/api/click', methods=['POST'])
def track_click():
    """Track clicks (user optional)."""
    data = request.get_json() or {}
    product_id = data.get('product_id')
    platform = (data.get('platform') or '').strip()
    source = (data.get('source') or 'search').strip()
    search_query = (data.get('search_query') or '').strip()[:300] or None

    if not product_id or not platform:
        return jsonify({'error': 'product_id and platform are required'}), 400
    product = Product.query.get_or_404(int(product_id))

    user = get_optional_user()
    evt = ClickEvent(
        user_id=user.id if user else None,
        product_id=product.id,
        platform=platform,
        source=source,
        search_query=search_query
    )
    db.session.add(evt)
    db.session.commit()
    return jsonify({'status': 'success'}), 201

@app.route('/api/purchases', methods=['GET'])
@require_auth
def purchases_list():
    limit = request.args.get('limit', 100, type=int)
    items = (PurchaseEvent.query
             .filter(PurchaseEvent.user_id == request.user.id)
             .order_by(PurchaseEvent.created_at.desc())
             .limit(min(limit, 200))
             .all())
    return jsonify({'count': len(items), 'items': [p.to_dict() for p in items]})

@app.route('/api/purchases/confirm', methods=['POST'])
@require_auth
def purchases_confirm():
    """User manually confirms purchase - works with real-time products"""
    data = request.get_json() or {}
    product_id = data.get('product_id')
    product_data = data.get('product_data')  # Full product data for real-time products
    platform = (data.get('platform') or '').strip()
    status = (data.get('status') or 'purchased').strip()
    
    if not product_id:
        return jsonify({'error': 'product_id is required'}), 400
    
    # For real-time products, check by product_url or create product
    if product_data and product_data.get('product_url'):
        product = Product.query.filter_by(product_url=product_data['product_url']).first()
        if not product:
            # Create product in DB for purchase tracking
            product = Product(
                name=product_data.get('name', 'Unknown'),
                description=product_data.get('description'),
                price=product_data.get('price', 0),
                original_price=product_data.get('original_price'),
                rating=product_data.get('rating'),
                review_count=product_data.get('review_count', 0),
                platform=platform or product_data.get('platform', 'Unknown'),
                product_url=product_data['product_url'],
                image_url=product_data.get('image_url'),
                category=product_data.get('category'),
                brand=product_data.get('brand'),
                availability=product_data.get('availability', 'In Stock')
            )
            db.session.add(product)
            db.session.commit()
    else:
        product = Product.query.get(int(product_id))
        if not product:
            return jsonify({'error': 'Product not found'}), 404
        platform = platform or product.platform
    purchase = PurchaseEvent(
        user_id=request.user.id,
        product_id=product.id,
        platform=platform,
        status=status
    )
    db.session.add(purchase)
    db.session.commit()
    return jsonify({'status': 'success', 'purchase': purchase.to_dict()}), 201

@app.route('/api/purchases/<int:purchase_id>', methods=['PATCH'])
@require_auth
def purchases_update_status(purchase_id):
    data = request.get_json() or {}
    status = (data.get('status') or '').strip()
    if not status:
        return jsonify({'error': 'status is required'}), 400

    purchase = PurchaseEvent.query.get_or_404(purchase_id)
    if purchase.user_id != request.user.id and not request.user.is_admin:
        return jsonify({'error': 'Not allowed'}), 403
    purchase.status = status[:30]
    db.session.commit()
    return jsonify({'status': 'success', 'purchase': purchase.to_dict()})

@app.route('/api/products', methods=['GET'])
def get_products():
    """Get all products with optional filtering"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        platform = request.args.get('platform')
        min_price = request.args.get('min_price', type=float)
        max_price = request.args.get('max_price', type=float)
        min_rating = request.args.get('min_rating', type=float)
        sort_by = request.args.get('sort_by', 'recommendation_score')  # price, rating, recommendation_score
        
        query = Product.query
        
        # Apply filters
        if platform:
            query = query.filter(Product.platform == platform)
        if min_price:
            query = query.filter(Product.price >= min_price)
        if max_price:
            query = query.filter(Product.price <= max_price)
        if min_rating:
            query = query.filter(Product.rating >= min_rating)
        
        # Apply sorting
        if sort_by == 'price':
            query = query.order_by(Product.price.asc())
        elif sort_by == 'rating':
            query = query.order_by(Product.rating.desc())
        else:
            query = query.order_by(Product.recommendation_score.desc())
        
        # Paginate
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'page': page,
            'per_page': per_page,
            'total': pagination.total,
            'pages': pagination.pages,
            'products': [p.to_dict() for p in pagination.items]
        })
        
    except Exception as e:
        logger.error(f"Error getting products: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    """Get a specific product by ID"""
    try:
        product = Product.query.get_or_404(product_id)
        return jsonify(product.to_dict())
    except Exception as e:
        logger.error(f"Error getting product: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/products/<int:product_id>/price-history', methods=['GET'])
def product_price_history(product_id):
    product = Product.query.get_or_404(product_id)
    limit = request.args.get('limit', 50, type=int)
    rows = (PriceHistory.query
            .filter(PriceHistory.product_id == product.id)
            .order_by(PriceHistory.recorded_at.desc())
            .limit(min(limit, 200))
            .all())
    return jsonify({'product_id': product.id, 'count': len(rows), 'items': [r.to_dict() for r in rows]})

@app.route('/api/alerts/price-drop', methods=['GET'])
@require_auth
def alerts_list():
    alerts = (PriceDropAlert.query
              .filter(PriceDropAlert.user_id == request.user.id)
              .order_by(PriceDropAlert.created_at.desc())
              .all())
    return jsonify({'count': len(alerts), 'items': [a.to_dict() for a in alerts]})

@app.route('/api/alerts/price-drop', methods=['POST'])
@require_auth
def alerts_create():
    data = request.get_json() or {}
    product_id = data.get('product_id')
    target_price = data.get('target_price')
    email = (data.get('email') or '').strip() or None

    if not product_id or target_price is None:
        return jsonify({'error': 'product_id and target_price are required'}), 400

    product = Product.query.get_or_404(int(product_id))
    alert = PriceDropAlert(
        user_id=request.user.id,
        product_id=product.id,
        platform=product.platform,
        target_price=float(target_price),
        email=email,
        is_active=True
    )
    db.session.add(alert)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        # Idempotent-ish behavior for the same alert
        existing = (PriceDropAlert.query
                    .filter_by(user_id=request.user.id, product_id=product.id, platform=product.platform, target_price=float(target_price))
                    .first())
        if existing:
            return jsonify({'status': 'success', 'alert': existing.to_dict()})
        raise

    return jsonify({'status': 'success', 'alert': alert.to_dict()}), 201

@app.route('/api/scrape', methods=['POST'])
def trigger_scraping():
    """Manually trigger scraping for a platform"""
    try:
        data = request.get_json() or {}
        platform = data.get('platform', 'all')
        query = data.get('query')
        max_results = data.get('max_results', 20)
        
        if platform == 'all':
            products = scraper_manager.scrape_all_platforms(query, max_results)
        else:
            products = scraper_manager.scrape_platform(platform, query, max_results)
        
        # Retrain recommender with new data
        recommender.train()
        
        return jsonify({
            'status': 'success',
            'products_scraped': len(products),
            'message': f'Scraped {len(products)} products'
        })
        
    except Exception as e:
        logger.error(f"Error in scraping: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/scraping-logs', methods=['GET'])
def get_scraping_logs():
    """Get scraping logs"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        platform = request.args.get('platform')
        
        query = ScrapingLog.query
        if platform:
            query = query.filter(ScrapingLog.platform == platform)
        
        query = query.order_by(ScrapingLog.started_at.desc())
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'page': page,
            'per_page': per_page,
            'total': pagination.total,
            'pages': pagination.pages,
            'logs': [log.to_dict() for log in pagination.items]
        })
        
    except Exception as e:
        logger.error(f"Error getting scraping logs: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get system statistics"""
    try:
        total_products = Product.query.count()
        platforms = db.session.query(Product.platform, db.func.count(Product.id)).group_by(Product.platform).all()
        avg_price = db.session.query(db.func.avg(Product.price)).scalar() or 0
        avg_rating = db.session.query(db.func.avg(Product.rating)).scalar() or 0
        
        return jsonify({
            'total_products': total_products,
            'platforms': {p[0]: p[1] for p in platforms},
            'average_price': float(avg_price),
            'average_rating': float(avg_rating),
            'last_updated': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/trending/products', methods=['GET'])
def trending_products():
    """Trending products based on click activity."""
    days = request.args.get('days', 7, type=int)
    limit = request.args.get('limit', 20, type=int)
    since = datetime.utcnow() - timedelta(days=max(1, min(days, 30)))

    rows = (db.session.query(ClickEvent.product_id, db.func.count(ClickEvent.id).label('clicks'))
            .filter(ClickEvent.created_at >= since)
            .group_by(ClickEvent.product_id)
            .order_by(db.text('clicks DESC'))
            .limit(min(limit, 50))
            .all())

    product_ids = [r[0] for r in rows]
    products = Product.query.filter(Product.id.in_(product_ids)).all() if product_ids else []
    by_id = {p.id: p for p in products}

    items = []
    for pid, clicks in rows:
        p = by_id.get(pid)
        if not p:
            continue
        d = p.to_dict()
        d['clicks'] = int(clicks)
        items.append(d)

    return jsonify({'since': since.isoformat(), 'count': len(items), 'items': items})

@app.route('/api/trending/searches', methods=['GET'])
def trending_searches():
    """Trending searches based on system activity."""
    days = request.args.get('days', 7, type=int)
    limit = request.args.get('limit', 20, type=int)
    since = datetime.utcnow() - timedelta(days=max(1, min(days, 30)))

    rows = (db.session.query(SearchEvent.query, db.func.count(SearchEvent.id).label('count'))
            .filter(SearchEvent.created_at >= since)
            .group_by(SearchEvent.query)
            .order_by(db.text('count DESC'))
            .limit(min(limit, 50))
            .all())

    items = [{'query': q, 'count': int(c)} for q, c in rows]
    return jsonify({'since': since.isoformat(), 'count': len(items), 'items': items})

@app.route('/api/analytics/overview', methods=['GET'])
def analytics_overview():
    """Public analytics overview (student-friendly, no admin required)."""
    days = request.args.get('days', 30, type=int)
    since = datetime.utcnow() - timedelta(days=max(1, min(days, 90)))

    total_users = User.query.count()
    total_products = Product.query.count()
    
    # Platform counts (ensuring all 4 show up)
    all_platforms = ['Amazon', 'Flipkart', 'Meesho', 'Myntra']
    db_platform_counts = dict(db.session.query(Product.platform, db.func.count(Product.id))
                              .group_by(Product.platform)
                              .all())
    
    platform_counts = {p: int(db_platform_counts.get(p, 0)) for p in all_platforms}
    
    # Category counts (top 8)
    category_counts = (db.session.query(Product.category, db.func.count(Product.id))
                      .filter(Product.category.isnot(None))
                      .group_by(Product.category)
                      .order_by(db.func.count(Product.id).desc())
                      .limit(8)
                      .all())
    
    # Price stats per platform
    price_stats = {}
    for platform in platform_counts:
        prices = db.session.query(Product.price).filter(
            Product.platform == platform,
            Product.price.isnot(None)
        ).all()
        if prices:
            price_list = [p[0] for p in prices]
            price_stats[platform] = {
                'mean': float(sum(price_list) / len(price_list)),
                'median': float(sorted(price_list)[len(price_list) // 2]),
                'min': float(min(price_list)),
                'max': float(max(price_list))
            }

    clicks_by_platform = (db.session.query(ClickEvent.platform, db.func.count(ClickEvent.id))
                          .filter(ClickEvent.created_at >= since)
                          .group_by(ClickEvent.platform)
                          .all())

    clicks_by_source = (db.session.query(ClickEvent.source, db.func.count(ClickEvent.id))
                        .filter(ClickEvent.created_at >= since)
                        .group_by(ClickEvent.source)
                        .all())

    purchases_by_platform = (db.session.query(PurchaseEvent.platform, db.func.count(PurchaseEvent.id))
                             .filter(PurchaseEvent.created_at >= since)
                             .group_by(PurchaseEvent.platform)
                             .all())

    total_clicks = int(sum([c for _, c in clicks_by_platform]) if clicks_by_platform else 0)
    total_purchases = int(sum([c for _, c in purchases_by_platform]) if purchases_by_platform else 0)
    conversion_rate = (total_purchases / total_clicks) if total_clicks else 0.0
    
    # Recommendation effectiveness
    rec_clicks = int(dict(clicks_by_source).get('recommendation', 0))
    search_clicks = int(dict(clicks_by_source).get('search', 0))
    
    # Recent price drop alerts
    recent_alerts = PriceDropAlert.query.filter(
        PriceDropAlert.triggered_at.isnot(None),
        PriceDropAlert.triggered_at >= since
    ).count()
    
    # Last scraped per platform
    last_scraped = {}
    for platform in platform_counts:
        last_log = ScrapingLog.query.filter_by(platform=platform, status='success').order_by(ScrapingLog.completed_at.desc()).first()
        if last_log and last_log.completed_at:
            last_scraped[platform] = last_log.completed_at.isoformat()

    return jsonify({
        'since': since.isoformat(),
        'totals': {
            'users': total_users,
            'products': total_products,
            'clicks': total_clicks,
            'purchases': total_purchases,
            'conversion_rate': round(conversion_rate, 4)
        },
        'platform_counts': {p: int(c) for p, c in platform_counts.items()},
        'category_counts': {c: int(cnt) for c, cnt in category_counts},
        'price_stats': price_stats,
        'clicks_by_platform': {p: int(c) for p, c in clicks_by_platform},
        'clicks_by_source': {s: int(c) for s, c in clicks_by_source},
        'purchases_by_platform': {p: int(c) for p, c in purchases_by_platform},
        'recommendation_effectiveness': {
            'recommendation_clicks': rec_clicks,
            'search_clicks': search_clicks,
            'recommendation_ctr': round(rec_clicks / total_clicks, 4) if total_clicks > 0 else 0.0
        },
        'recent_alerts_triggered': recent_alerts,
        'last_scraped': last_scraped
    })

@app.route('/api/admin/analytics', methods=['GET'])
@require_admin
def admin_analytics():
    """Basic analytics dashboard data (mini-project level)."""
    days = request.args.get('days', 30, type=int)
    since = datetime.utcnow() - timedelta(days=max(1, min(days, 90)))

    total_users = User.query.count()
    total_products = Product.query.count()

    clicks_by_platform = (db.session.query(ClickEvent.platform, db.func.count(ClickEvent.id))
                          .filter(ClickEvent.created_at >= since)
                          .group_by(ClickEvent.platform)
                          .all())

    clicks_by_source = (db.session.query(ClickEvent.source, db.func.count(ClickEvent.id))
                        .filter(ClickEvent.created_at >= since)
                        .group_by(ClickEvent.source)
                        .all())

    purchases_by_platform = (db.session.query(PurchaseEvent.platform, db.func.count(PurchaseEvent.id))
                             .filter(PurchaseEvent.created_at >= since)
                             .group_by(PurchaseEvent.platform)
                             .all())

    total_clicks = int(sum([c for _, c in clicks_by_platform]) if clicks_by_platform else 0)
    total_purchases = int(sum([c for _, c in purchases_by_platform]) if purchases_by_platform else 0)
    conversion_rate = (total_purchases / total_clicks) if total_clicks else 0.0

    return jsonify({
        'since': since.isoformat(),
        'totals': {
            'users': total_users,
            'products': total_products,
            'clicks': total_clicks,
            'purchases': total_purchases,
            'conversion_rate': conversion_rate
        },
        'clicks_by_platform': {p: int(c) for p, c in clicks_by_platform},
        'clicks_by_source': {s: int(c) for s, c in clicks_by_source},
        'purchases_by_platform': {p: int(c) for p, c in purchases_by_platform},
        'recommendation_effectiveness': {
            'recommendation_clicks': int(dict(clicks_by_source).get('recommendation', 0)),
            'search_clicks': int(dict(clicks_by_source).get('search', 0))
        }
    })

@app.route('/api/recommendations', methods=['GET'])
def get_recommendations():
    """Fetch top 20 recommended products from the database"""
    try:
        limit = request.args.get('limit', 20, type=int)
        # Fetching products with rating 4.0+ and sorting by rating/review_count or existing recommendation_score
        products = Product.query.filter(Product.rating >= 4.0).order_by(Product.recommendation_score.desc()).limit(limit).all()
        
        # If no scored products, just get high rated ones
        if not products:
             products = Product.query.filter(Product.rating >= 4.0).order_by(Product.rating.desc(), Product.review_count.desc()).limit(limit).all()

        return jsonify({
            'status': 'success',
            'items': [p.to_dict() for p in products]
        })
    except Exception as e:
        logger.error(f"Error fetching recommendations: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/recommendations/update-scores', methods=['POST'])
def update_scores():
    """Update recommendation scores for all products"""
    try:
        recommender.update_recommendation_scores()
        return jsonify({'status': 'success', 'message': 'Recommendation scores updated'})
    except Exception as e:
        logger.error(f"Error updating scores: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/feedback', methods=['GET'])
def get_feedback():
    """Fetch top feedbacks with 4+ stars for display in footer"""
    try:
        limit = request.args.get('limit', 10, type=int)
        min_stars = request.args.get('min_stars', 4, type=int)
        feedbacks = Feedback.query.filter(Feedback.rating >= min_stars).order_by(Feedback.created_at.desc()).limit(limit).all()
        return jsonify({
            'status': 'success',
            'items': [f.to_dict() for f in feedbacks]
        })
    except Exception as e:
        logger.error(f"Error fetching feedback: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/feedback', methods=['POST'])
def add_feedback():
    """Users submit feedback about the website"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        rating = data.get('rating')
        description = data.get('description')
        name = data.get('name', 'Anonymous')
        
        if not rating or not description:
            return jsonify({'error': 'Rating and Description are required'}), 400
            
        user = get_optional_user()
        new_feedback = Feedback(
            user_id=user.id if user else None,
            name=name if not user else user.name,
            rating=int(rating),
            description=description[:500]
        )
        
        db.session.add(new_feedback)
        db.session.commit()
        
        return jsonify({
            'status': 'success', 
            'message': 'Thank you for your feedback!',
            'item': new_feedback.to_dict()
        })
    except Exception as e:
        logger.error(f"Error adding feedback: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)


