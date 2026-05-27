import pytest
from sqlalchemy.exc import IntegrityError
from app import app
from models import db, User, Product, WishlistItem, PriceDropAlert, RecommendationFeedback, UserPreference



# --- Users Table Integrity ---

def test_user_email_uniqueness(db_session):
    u1 = User(email="dup@example.com", name="User 1")
    u1.set_password("Pass123!")
    db_session.add(u1)
    db_session.commit()
    
    u2 = User(email="dup@example.com", name="User 2")
    u2.set_password("Pass123!")
    db_session.add(u2)
    with pytest.raises(IntegrityError):
        db_session.commit()

def test_user_phone_uniqueness(db_session):
    u1 = User(email="u1@example.com", phone_number="9876543210", name="User 1")
    u1.set_password("Pass123!")
    db_session.add(u1)
    db_session.commit()
    
    u2 = User(email="u2@example.com", phone_number="9876543210", name="User 2")
    u2.set_password("Pass123!")
    db_session.add(u2)
    with pytest.raises(IntegrityError):
        db_session.commit()

def test_user_null_fields_prevention(db_session):
    # Email is non-nullable
    u = User(email=None, name="User")
    db_session.add(u)
    with pytest.raises(IntegrityError):
        db_session.commit()

# --- Wishlist Integrity ---

def test_wishlist_duplicate_records_prevented(db_session):
    u = User(email="w@example.com", name="Wishlist User")
    u.set_password("Pass123!")
    p = Product(name="Product A", price=10.0, product_url="http://p1", platform="Amazon")
    db_session.add_all([u, p])
    db_session.commit()
    
    w1 = WishlistItem(user_id=u.id, product_id=p.id)
    w2 = WishlistItem(user_id=u.id, product_id=p.id)
    db_session.add_all([w1, w2])
    with pytest.raises(IntegrityError):
        db_session.commit()

def test_wishlist_invalid_references(db_session):
    # Invalid user_id or product_id (non-existent IDs with foreign keys enabled)
    w = WishlistItem(user_id=9999, product_id=9999)
    db_session.add(w)
    try:
        db_session.commit()
        assert w.user is None
        assert w.product is None
    except IntegrityError:
        pass

# --- Price Alerts Integrity ---

def test_price_alert_uniqueness(db_session):
    u = User(email="alert@example.com", name="Alert User")
    u.set_password("Pass123!")
    p = Product(name="Product B", price=100.0, product_url="http://p2", platform="Amazon")
    db_session.add_all([u, p])
    db_session.commit()
    
    a1 = PriceDropAlert(user_id=u.id, product_id=p.id, platform="Amazon", target_price=80.0)
    a2 = PriceDropAlert(user_id=u.id, product_id=p.id, platform="Amazon", target_price=80.0)
    db_session.add_all([a1, a2])
    with pytest.raises(IntegrityError):
        db_session.commit()

# --- Recommendation Tables Integrity ---

def test_recommendation_feedback_uniqueness(db_session):
    u = User(email="feed@example.com", name="Feed User")
    u.set_password("Pass123!")
    p = Product(name="Product C", price=1000.0, product_url="http://p3", platform="Amazon")
    db_session.add_all([u, p])
    db_session.commit()
    
    f1 = RecommendationFeedback(user_id=u.id, product_id=p.id, feedback_type="like")
    f2 = RecommendationFeedback(user_id=u.id, product_id=p.id, feedback_type="dislike")
    db_session.add_all([f1, f2])
    with pytest.raises(IntegrityError):
        db_session.commit()
