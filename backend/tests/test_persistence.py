import pytest
from app import app
from models import db, User, Product, WishlistItem, PriceDropAlert, AISearchEvent, RecommendationFeedback
from app import run_migrations

def test_user_persistence(test_db):
    """Test user survives app context restarts"""
    with app.app_context():
        user = User(email="persist_user@buysmart.com", name="Persist User", role="user")
        user.set_password("Password123!")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    # Verify user still exists after context recreation
    with app.app_context():
        db_user = User.query.get(user_id)
        assert db_user is not None
        assert db_user.email == "persist_user@buysmart.com"
        assert db_user.name == "Persist User"

def test_wishlist_persistence(test_db):
    """Test wishlist items survive restarts"""
    with app.app_context():
        user = User(email="persist_wish@buysmart.com", name="Wish User")
        user.set_password("Password123!")
        p = Product(name="Persist Prod A", price=100.0, platform="Amazon", product_url="http://amazon.com/pa")
        db.session.add_all([user, p])
        db.session.commit()
        user_id = user.id
        product_id = p.id
        
        w = WishlistItem(user_id=user_id, product_id=product_id)
        db.session.add(w)
        db.session.commit()

    # Verify wishlist item survives
    with app.app_context():
        wish_items = WishlistItem.query.filter_by(user_id=user_id).all()
        assert len(wish_items) == 1
        assert wish_items[0].product_id == product_id

def test_price_alert_persistence(test_db):
    """Test price drop alerts survive restarts"""
    with app.app_context():
        user = User(email="persist_alert@buysmart.com", name="Alert User")
        user.set_password("Password123!")
        p = Product(name="Persist Prod B", price=200.0, platform="Flipkart", product_url="http://flipkart.com/pb")
        db.session.add_all([user, p])
        db.session.commit()
        user_id = user.id
        product_id = p.id
        
        alert = PriceDropAlert(user_id=user_id, product_id=product_id, platform="Flipkart", target_price=150.0)
        db.session.add(alert)
        db.session.commit()

    # Verify price alert survives
    with app.app_context():
        alerts = PriceDropAlert.query.filter_by(user_id=user_id).all()
        assert len(alerts) == 1
        assert alerts[0].product_id == product_id
        assert alerts[0].target_price == 150.0

def test_ai_search_persistence(test_db):
    """Test AI search events survive restarts"""
    with app.app_context():
        user = User(email="persist_ai@buysmart.com", name="AI User")
        user.set_password("Password123!")
        db.session.add(user)
        db.session.commit()
        user_id = user.id
        
        event = AISearchEvent(
            user_id=user_id, 
            query="blue shoes", 
            extracted_intent={"category": "Shoes", "budget_max": 5000.0}
        )
        db.session.add(event)
        db.session.commit()

    # Verify AI search event survives
    with app.app_context():
        events = db.session.query(AISearchEvent).filter_by(user_id=user_id).all()
        assert len(events) == 1
        assert events[0].query == "blue shoes"
        assert events[0].extracted_intent.get("budget_max") == 5000.0

def test_recommendation_feedback_persistence(test_db):
    """Test recommendation feedback survives restarts"""
    with app.app_context():
        user = User(email="persist_rec@buysmart.com", name="Rec User")
        user.set_password("Password123!")
        p = Product(name="Persist Prod C", price=300.0, platform="Amazon", product_url="http://amazon.com/pc")
        db.session.add_all([user, p])
        db.session.commit()
        user_id = user.id
        product_id = p.id
        
        feed = RecommendationFeedback(user_id=user_id, product_id=product_id, feedback_type="like")
        db.session.add(feed)
        db.session.commit()

    # Verify feedback survives
    with app.app_context():
        feedbacks = RecommendationFeedback.query.filter_by(user_id=user_id).all()
        assert len(feedbacks) == 1
        assert feedbacks[0].feedback_type == "like"
        assert feedbacks[0].product_id == product_id

def test_migration_no_data_loss(test_db):
    """Test running migrations does not alter or delete existing data"""
    with app.app_context():
        user = User(email="persist_mig@buysmart.com", name="Mig User")
        user.set_password("Password123!")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    # Run migration logic
    run_migrations()

    # Verify data is still intact
    with app.app_context():
        db_user = User.query.filter_by(email="persist_mig@buysmart.com").first()
        assert db_user is not None
        assert db_user.id == user_id
