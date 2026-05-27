import json
import pytest
from app import app
from models import db, User, Product, ClickEvent, WishlistItem, PurchaseEvent, UserPreference, RecommendationFeedback
from services.recommender import ProductRecommender

@pytest.fixture
def client(test_db):
    app.config['JWT_SECRET_KEY'] = 'test-jwt-secret'
    
    # Create users
    user = User(email="rec_test@buysmart.com", name="Rec User", role="user", is_active=True)
    user.set_password("password123")
    db.session.add(user)
    
    # Seed various items (good items and prohibited items)
    p1 = Product(name="Lenovo ThinkPad Coding Laptop", price=55000.0, category="Laptop", brand="Lenovo", platform="Amazon", product_url="http://amazon.com/l1")
    p2 = Product(name="Asus Rog Gaming Laptop", price=59000.0, category="Laptop", brand="Asus", platform="Amazon", product_url="http://amazon.com/l2")
    p3 = Product(name="Laptop Keyboard Cover Accessories", price=500.0, category="Accessories", brand="Skins", platform="Amazon", product_url="http://amazon.com/a1")
    p4 = Product(name="C++ Programming Book", price=800.0, category="Books", brand="O'Reilly", platform="Amazon", product_url="http://amazon.com/b1")
    p5 = Product(name="Photography iPhone Mobile", price=29000.0, category="Mobile", brand="Apple", platform="Flipkart", product_url="http://flipkart.com/m1")
    p6 = Product(name="iPhone Screen Cover protector", price=299.0, category="Covers", brand="Spigen", platform="Flipkart", product_url="http://flipkart.com/m2")
    p7 = Product(name="Puma Nitro Running Shoes", price=2800.0, category="Shoes", brand="Puma", platform="Amazon", product_url="http://amazon.com/s1")
    p8 = Product(name="Laptop Sticker Pack Decals", price=150.0, category="Stickers", brand="Decals", platform="Amazon", product_url="http://amazon.com/s2")
    
    db.session.add_all([p1, p2, p3, p4, p5, p6, p7, p8])
    db.session.commit()
    
    return app.test_client()

# --- Recommendation Quality Audit ---

def test_query_laptop_under_60000(client):
    # Search for laptop under 60000. Under current setup, AI search route or standard search routes is utilized.
    # Let's test using the search endpoint or recommender logic directly.
    # Since search endpoint queries database:
    res = client.get('/api/search?query=laptop&max_price=60000.0')
    assert res.status_code == 200
    data = json.loads(res.data)
    
    # Must respect budget
    for r in data['results']:
        assert r['price'] <= 60000.0
        # Must respect category (Laptop) and NOT contain Books, Skins, Accessories
        assert r['category'].lower() not in ["books", "skins", "stickers", "accessories", "covers"]
        name_lower = r['name'].lower()
        if "book" in name_lower and "chromebook" not in name_lower and "macbook" not in name_lower:
            assert False, f"Found book/non-laptop: {r['name']}"
        assert "cover" not in name_lower


def test_query_mobile_under_30000(client):
    res = client.get('/api/search?query=mobile&max_price=30000.0')
    assert res.status_code == 200
    data = json.loads(res.data)
    for r in data['results']:
        assert r['price'] <= 30000.0
        assert r['category'].lower() not in ["books", "skins", "stickers", "accessories", "covers"]

def test_query_running_shoes_below_3000(client):
    res = client.get('/api/search?query=running+shoes&max_price=3000.0')
    assert res.status_code == 200
    data = json.loads(res.data)
    for r in data['results']:
        assert r['price'] <= 3000.0
        assert "shoe" in r['category'].lower() or "shoe" in r['name'].lower()

# --- Recommender System Tests ---

def test_purchase_and_feedback_exclusions(client):
    # Log in test user
    login_res = client.post('/api/auth/login', json={"identifier": "rec_test@buysmart.com", "password": "password123"})
    token = json.loads(login_res.data)['data']['access_token']
    headers = {"Authorization": f"Bearer {token}"}
    
    # Add click event and dislike feedback
    with app.app_context():
        user = User.query.filter_by(email="rec_test@buysmart.com").first()
        p_lenovo = Product.query.filter_by(brand="Lenovo").first()
        p_asus = Product.query.filter_by(brand="Asus").first()
        
        # Click Lenovo, dislike Asus
        db.session.add(ClickEvent(user_id=user.id, product_id=p_lenovo.id, platform="Amazon", source="search"))
        db.session.add(RecommendationFeedback(user_id=user.id, product_id=p_asus.id, feedback_type="not_interested"))
        db.session.commit()
        
        # Train recommender
        rec = ProductRecommender()
        rec.train()
        rec.update_user_preferences(user.id)
        
    # Get recommendations
    res = client.get('/api/recommendations/personalized', headers=headers)
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data['success'] is True
    
    # Lenovo (clicked) or Asus (disliked/not_interested) check
    # Recommended lists should not contain Asus since it has 'not_interested' feedback
    recommended_ids = [item['product']['id'] for item in data['data']['recommended_for_you']]
    with app.app_context():
        p_asus_id = Product.query.filter_by(brand="Asus").first().id
        assert p_asus_id not in recommended_ids
