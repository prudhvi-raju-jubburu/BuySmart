"""
Flask application for Product Recommendation and Price Comparison System
"""
import os
from flask import Flask, request, jsonify, redirect
from flask_cors import CORS
from models import db, Product, ScrapingLog, User, SessionToken, WishlistItem, SearchEvent, ClickEvent, PurchaseEvent, PriceHistory, PriceDropAlert, RedirectToken, Feedback, TokenBlocklist, AnalyticsCounter, UserPreference, RecommendationFeedback, AISearchEvent, AISearchCache
from services.scraper import ScraperManager
from services.recommender import ProductRecommender
from config import Config
Config.validate_environment()
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, get_jwt, verify_jwt_in_request
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.dashboard import dashboard_bp
from routes.recommendations import recommendations_bp
from routes.search import search_bp
from routes.health import health_bp
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
# Enable CORS for React frontend (allow all origins for public API accessibility)
CORS(app, resources={r"/*": {"origins": "*"}})



@app.route("/")
def home():
    return jsonify({
        "status": "success",
        "message": "BuySmart Backend is Running 🚀"
    })


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "BuySmart Backend"
    })


db.init_app(app)
scraper_manager = ScraperManager()
recommender = ProductRecommender()

# JWT Configuration & Initialization
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY') or app.config.get('SECRET_KEY') or 'jwt-dev-secret-key-change-in-production'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=15)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)
jwt = JWTManager(app)

@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    jti = jwt_payload["jti"]
    token = TokenBlocklist.query.filter_by(jti=jti).first()
    return token is not None

# Register Blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(admin_bp, url_prefix='/api/admin')
app.register_blueprint(dashboard_bp)
app.register_blueprint(recommendations_bp)
app.register_blueprint(search_bp)
app.register_blueprint(health_bp)

# Run database migrations and initialization
def run_migrations():
    """Ensure database has all updated tables and columns"""
    import os
    if os.environ.get('SKIP_DB_CHECK') == '1':
        logger.info("Skipping database check and migrations (SKIP_DB_CHECK is set)")
        return
        
    with app.app_context():
        try:
            # 1. Create missing tables
            db.create_all()
            logger.info("Database tables initialized successfully")

            # 2. Migrate existing tables for new columns
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            if 'users' in inspector.get_table_names():
                columns = [c['name'] for c in inspector.get_columns('users')]
                
                # Check/Add role
                if 'role' not in columns:
                    logger.info("Database migration: adding 'role' column to users table")
                    db.session.execute(db.text("ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'user'"))
                    db.session.commit()
                    
                # Check/Add created_at
                if 'created_at' not in columns:
                    logger.info("Database migration: adding 'created_at' column to users table")
                    db.session.execute(db.text("ALTER TABLE users ADD COLUMN created_at TIMESTAMP WITHOUT TIME ZONE"))
                    db.session.commit()
                    
                # Check/Add last_login
                if 'last_login' not in columns:
                    logger.info("Database migration: adding 'last_login' column to users table")
                    db.session.execute(db.text("ALTER TABLE users ADD COLUMN last_login TIMESTAMP WITHOUT TIME ZONE"))
                    db.session.commit()
                    
                # Check/Add is_active
                if 'is_active' not in columns:
                    logger.info("Database migration: adding 'is_active' column to users table")
                    db.session.execute(db.text("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT TRUE"))
                    db.session.commit()

                # Check/Add phone_number
                if 'phone_number' not in columns:
                    logger.info("Database migration: adding 'phone_number' column to users table")
                    db.session.execute(db.text("ALTER TABLE users ADD COLUMN phone_number VARCHAR(20)"))
                    db.session.commit()

            # 3. Database validation & health check
            db.session.execute(db.text("SELECT 1"))
            logger.info("Connected to database")
            
            db.session.execute(db.text("SELECT COUNT(*) FROM users"))
            db.session.execute(
                db.text("INSERT INTO token_blocklist (jti, created_at) VALUES (:jti, :created_at)"),
                {"jti": "healthcheck-startup-jti", "created_at": datetime.utcnow()}
            )
            db.session.execute(
                db.text("DELETE FROM token_blocklist WHERE jti = :jti"),
                {"jti": "healthcheck-startup-jti"}
            )
            db.session.commit()
            
            # Clear AISearchCache to prevent stale query mappings across server restarts
            try:
                db.session.query(AISearchCache).delete()
                db.session.commit()
                logger.info("Stale AI Search cache cleared successfully")
            except Exception as cache_err:
                logger.warning(f"Could not clear search cache table: {cache_err}")
                db.session.rollback()

            logger.info("Database Health Check Passed")

        except Exception as e:
            logger.critical(f"Database startup validation or migration failed: {e}")
            db.session.rollback()
            raise RuntimeError(f"Database verification failed: {e}")

run_migrations()

def run_bootstrap():
    """Background task to bootstrap data if needed"""
    with app.app_context():
        try:
            # Train recommender safely
            try:
                recommender.train()
                logger.info("Initial recommender training completed")
            except Exception as e:
                logger.warning(f"Recommender training skipped: {e}")

            # Bootstrap data if needed
            existing_count = Product.query.count()
            if existing_count < 10:
                logger.info("Bootstrapping initial data in background...")
                bootstrap_queries = ['laptop', 'phone', 'headphones']
                for q in bootstrap_queries:
                    try:
                        scraper_manager.scrape_platform('meesho', query=q, max_results=10)
                        scraper_manager.scrape_platform('myntra', query=q, max_results=10)
                    except Exception as e:
                        logger.warning(f"Bootstrap failed for {q}: {e}")

                try:
                    recommender.train()
                    logger.info("Post-bootstrap recommender training completed")
                except:
                    pass
        except Exception as e:
            logger.error(f"Bootstrap error: {e}")

# Start bootstrap in background thread (disabled on startup for production stability)
# threading.Thread(target=run_bootstrap, daemon=True).start()



def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            # verify_jwt_in_request verifies both validity and blocklist automatically
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            user = User.query.get(user_id)
            if not user:
                logger.warning(f"User not found for token in {request.path}")
                return jsonify({'error': 'User not found'}), 401
            if not user.is_active:
                logger.warning(f"Disabled user {user.id} tried to access {request.path}")
                return jsonify({'error': 'Account disabled. Please contact support.'}), 403
            request.user = user
            request.session = None  # kept for legacy references, set to None as we use JWT
            return fn(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Auth required check failed in {request.path}: {e}")
            return jsonify({'error': 'Invalid or expired token'}), 401
    return wrapper

def require_admin(fn):
    @wraps(fn)
    @require_auth
    def wrapper(*args, **kwargs):
        user = getattr(request, 'user', None)
        if not user or (user.role != 'admin' and not user.is_admin):
            return jsonify({'error': 'Admin access required'}), 403
        return fn(*args, **kwargs)
    return wrapper

def get_optional_user():
    """Return user if Authorization header contains a valid token; else None."""
    try:
        verify_jwt_in_request(optional=True)
        user_id = get_jwt_identity()
        if user_id:
            return User.query.get(user_id)
    except Exception:
        pass
    return None

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

def start_scheduler():
    if not app.debug:
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        logger.info("Scheduler started")

start_scheduler()


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

# Legacy auth routes have been removed in favor of routes/auth.py blueprint

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
    
    if rt.source == 'recommendation':
        try:
            counter = AnalyticsCounter.query.filter_by(key='recommendations_clicked').first()
            if not counter:
                counter = AnalyticsCounter(key='recommendations_clicked', value=0)
                db.session.add(counter)
            counter.value += 1
        except Exception as ex:
            logger.warning(f"Error updating recommendations_clicked counter: {ex}")
            
    db.session.commit()

    # Simple safety: allow only http/https
    parsed = urlparse(product.product_url)
    if parsed.scheme not in ('http', 'https'):
        return jsonify({'error': 'Unsafe redirect URL'}), 400

    return redirect(product.product_url, code=302)


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
        # Track recommendations served
        try:
            counter = AnalyticsCounter.query.filter_by(key='recommendations_served').first()
            if not counter:
                counter = AnalyticsCounter(key='recommendations_served', value=0)
                db.session.add(counter)
            counter.value += 1
            db.session.commit()
        except Exception as ex:
            logger.warning(f"Error incrementing recommendation impression counter: {ex}")
            db.session.rollback()

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

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Route not found"}), 404


@app.errorhandler(500)
def internal_server_error(error):
    logger.error("Internal Server Error", exc_info=True)
    return jsonify({
        "success": False,
        "message": "Internal server error"
    }), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)



