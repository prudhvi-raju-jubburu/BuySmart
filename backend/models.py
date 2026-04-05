from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import secrets
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class Product(db.Model):
    """Product model for storing scraped product information"""
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(500), nullable=False, index=True)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False, index=True)
    original_price = db.Column(db.Float)
    rating = db.Column(db.Float, index=True)
    review_count = db.Column(db.Integer, default=0, index=True)
    platform = db.Column(db.String(100), nullable=False, index=True)
    product_url = db.Column(db.String(1000), unique=True, nullable=False)
    image_url = db.Column(db.String(1000))
    category = db.Column(db.String(200), index=True)
    brand = db.Column(db.String(200))
    availability = db.Column(db.String(50), default='In Stock')
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Computed score for ranking
    recommendation_score = db.Column(db.Float, default=0.0, index=True)
    
    def to_dict(self):
        """Convert product to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': self.price,
            'original_price': self.original_price,
            'rating': self.rating,
            'review_count': self.review_count,
            'platform': self.platform,
            'product_url': self.product_url,
            'image_url': self.image_url,
            'category': self.category,
            'brand': self.brand,
            'availability': self.availability,
            'recommendation_score': self.recommendation_score,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<Product {self.name[:50]} - {self.platform}>'

class ScrapingLog(db.Model):
    """Log model for tracking scraping operations"""
    __tablename__ = 'scraping_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(50), nullable=False)  # success, failed, partial
    products_scraped = db.Column(db.Integer, default=0)
    errors = db.Column(db.Text)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    duration_seconds = db.Column(db.Float)
    
    def to_dict(self):
        return {
            'id': self.id,
            'platform': self.platform,
            'status': self.status,
            'products_scraped': self.products_scraped,
            'errors': self.errors,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'duration_seconds': self.duration_seconds
        }


class User(db.Model):
    """User model for login/profile management"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(320), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    last_login_at = db.Column(db.DateTime)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'is_admin': self.is_admin,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None
        }


class SessionToken(db.Model):
    """Simple token-based auth (student-friendly)."""
    __tablename__ = 'session_tokens'

    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    expires_at = db.Column(db.DateTime, nullable=True, index=True)
    revoked_at = db.Column(db.DateTime, nullable=True, index=True)

    user = db.relationship('User', backref=db.backref('sessions', lazy=True))

    @staticmethod
    def generate_token() -> str:
        # 32 bytes -> 64 hex chars
        return secrets.token_hex(32)

    def is_active(self, now=None) -> bool:
        now = now or datetime.utcnow()
        if self.revoked_at is not None:
            return False
        if self.expires_at is not None and now >= self.expires_at:
            return False
        return True


class SearchEvent(db.Model):
    """Stores search history and powers trending searches/products."""
    __tablename__ = 'search_events'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    query = db.Column(db.String(300), nullable=False, index=True)
    filters_json = db.Column(db.Text)  # store raw filters as JSON string (student-friendly)
    results_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship('User', backref=db.backref('search_events', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'query': self.query,
            'filters_json': self.filters_json,
            'results_count': self.results_count,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class WishlistItem(db.Model):
    """Wishlist per user."""
    __tablename__ = 'wishlist_items'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship('User', backref=db.backref('wishlist_items', lazy=True))
    product = db.relationship('Product')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'product_id', name='uq_wishlist_user_product'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'product_id': self.product_id, 
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'product': self.product.to_dict() if self.product else None
        }


class ClickEvent(db.Model):
    """Click analytics for platform redirections and recommendation effectiveness."""
    __tablename__ = 'click_events'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)
    platform = db.Column(db.String(100), nullable=False, index=True)  # Amazon/Flipkart/etc
    source = db.Column(db.String(50), default='search', index=True)   # search/recommendation/trending/wishlist
    search_query = db.Column(db.String(300), index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship('User', backref=db.backref('click_events', lazy=True))
    product = db.relationship('Product')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'product_id': self.product_id,
            'platform': self.platform,
            'source': self.source,
            'search_query': self.search_query,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class PurchaseEvent(db.Model):
    """Simulated purchase tracking (manual confirmation)."""
    __tablename__ = 'purchase_events'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)
    platform = db.Column(db.String(100), nullable=False, index=True)
    status = db.Column(db.String(30), default='purchased', index=True)  # purchased/cancelled/delivered/etc
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)

    user = db.relationship('User', backref=db.backref('purchase_events', lazy=True))
    product = db.relationship('Product')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'product_id': self.product_id,
            'platform': self.platform,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'product': self.product.to_dict() if self.product else None
        }


class PriceHistory(db.Model):
    """Stores price changes over time (near real-time comparison demo)."""
    __tablename__ = 'price_history'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)
    platform = db.Column(db.String(100), nullable=False, index=True)
    price = db.Column(db.Float, nullable=False, index=True)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    product = db.relationship('Product')

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'platform': self.platform,
            'price': self.price,
            'recorded_at': self.recorded_at.isoformat() if self.recorded_at else None
        }


class PriceDropAlert(db.Model):
    """User sets a target price; system triggers when product price drops below it."""
    __tablename__ = 'price_drop_alerts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)
    platform = db.Column(db.String(100), nullable=False, index=True)
    target_price = db.Column(db.Float, nullable=False, index=True)
    email = db.Column(db.String(320))  # optional; can be blank -> simulated
    is_active = db.Column(db.Boolean, default=True, index=True)
    triggered_at = db.Column(db.DateTime, nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship('User', backref=db.backref('price_alerts', lazy=True))
    product = db.relationship('Product')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'product_id', 'platform', 'target_price', name='uq_alert_user_product_platform_target'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'product_id': self.product_id,
            'platform': self.platform,
            'target_price': self.target_price,
            'email': self.email,
            'is_active': self.is_active,
            'triggered_at': self.triggered_at.isoformat() if self.triggered_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'product': self.product.to_dict() if self.product else None
        }


class RedirectToken(db.Model):
    """Short-lived token to securely redirect users to seller sites while logging clicks."""
    __tablename__ = 'redirect_tokens'

    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)
    platform = db.Column(db.String(100), nullable=False, index=True)
    source = db.Column(db.String(50), default='search', index=True)
    search_query = db.Column(db.String(300), index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    used_at = db.Column(db.DateTime, nullable=True, index=True)

    user = db.relationship('User')
    product = db.relationship('Product')

    @staticmethod
    def generate_token() -> str:
        return secrets.token_hex(32)

    def is_valid(self, now=None) -> bool:
        now = now or datetime.utcnow()
        if self.used_at is not None:
            return False
        if self.expires_at and now >= self.expires_at:
            return False
        return True


class Feedback(db.Model):
    """User feedback for the website"""
    __tablename__ = 'feedbacks'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    name = db.Column(db.String(120), nullable=True) # For guest feedback
    rating = db.Column(db.Integer, nullable=False, index=True) # 1-5 stars
    description = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    user = db.relationship('User', backref=db.backref('feedbacks', lazy=True))
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name or (self.user.name if self.user else "Anonymous"),
            'rating': self.rating,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

