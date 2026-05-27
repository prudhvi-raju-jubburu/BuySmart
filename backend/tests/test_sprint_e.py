import json
import pytest
from unittest.mock import patch, MagicMock
from app import app, db
from models import User, Product
from services.ai_search import AISearchService
from services.ai_status import mark_provider_quota_failed, is_provider_on_cooldown, get_ai_status
from services.recommender import ProductRecommender

@pytest.fixture
def seed_products(test_db):
    """Seed sample products from different category groups for verification"""
    # Group: fashion
    p1 = Product(name="Casual Denim Shirt", price=1200.0, rating=4.2, review_count=50, platform="Myntra", product_url="http://myntra.com/p1", category="Fashion", brand="Roadster")
    p2 = Product(name="Cotton Formal Shirt", price=2500.0, rating=4.5, review_count=60, platform="Myntra", product_url="http://myntra.com/p2", category="Fashion", brand="Levis")
    
    # Group: electronics
    p3 = Product(name="Portronics TWS Earbuds", price=1999.0, rating=4.0, review_count=100, platform="Amazon", product_url="http://amazon.com/p3", category="Audio", brand="Portronics")
    p4 = Product(name="Sony Bluetooth Headphones", price=5500.0, rating=4.6, review_count=120, platform="Amazon", product_url="http://amazon.com/p4", category="Audio", brand="Sony")
    p5 = Product(name="Apple Watch Smartwatch", price=29999.0, rating=4.8, review_count=90, platform="Flipkart", product_url="http://flipkart.com/p5", category="Watch", brand="Apple")
    
    # Group: laptop
    p6 = Product(name="Lenovo ThinkPad Coding Laptop", price=65000.0, rating=4.7, review_count=200, platform="Amazon", product_url="http://amazon.com/p6", category="Laptop", brand="Lenovo")
    p7 = Product(name="Asus ROG Gaming Laptop", price=95000.0, rating=4.6, review_count=80, platform="Flipkart", product_url="http://flipkart.com/p7", category="Laptop", brand="Asus")
    
    # Group: phone
    p8 = Product(name="Samsung Galaxy Phone", price=18000.0, rating=4.3, review_count=150, platform="Flipkart", product_url="http://flipkart.com/p8", category="Mobile", brand="Samsung")
    
    # Group: shoes
    p9 = Product(name="Nike Air Zoom Running Shoes", price=7500.0, rating=4.7, review_count=220, platform="Amazon", product_url="http://amazon.com/p9", category="Shoes", brand="Nike")
    
    db.session.add_all([p1, p2, p3, p4, p5, p6, p7, p8, p9])
    db.session.commit()

# --- Test 1: Local Parser Intent Extraction ---
def test_fallback_parser_intent_extraction():
    svc = AISearchService()
    
    # Check "shirts under 6000"
    intent = svc.fallback_parser("shirts under 6000")
    assert intent["category"] == "Fashion"
    assert intent["budget_max"] == 6000.0
    
    # Check "best laptop for coding"
    intent = svc.fallback_parser("best laptop for coding")
    assert intent["category"] == "Laptop"
    assert intent["purpose"] == "coding"
    
    # Check "best laptop for AI"
    intent = svc.fallback_parser("best laptop for AI")
    assert intent["category"] == "Laptop"
    assert intent["purpose"] == "machine_learning"

    # Check "cheap gaming laptop"
    intent = svc.fallback_parser("cheap gaming laptop")
    assert intent["category"] == "Laptop"
    assert intent["purpose"] == "gaming"

    # Check "good camera phone"
    intent = svc.fallback_parser("good camera phone")
    assert intent["category"] == "Phone"
    assert "camera" in intent["features"]

    # Check "student laptop"
    intent = svc.fallback_parser("student laptop")
    assert intent["category"] == "Laptop"
    assert intent["purpose"] == "student"

    # Check "running shoes"
    intent = svc.fallback_parser("running shoes")
    assert intent["category"] == "Shoes"
    assert "running" in intent["features"]

    # Check "office laptop"
    intent = svc.fallback_parser("office laptop")
    assert intent["category"] == "Laptop"
    assert intent["purpose"] == "office"

    # Check "bluetooth headphones"
    intent = svc.fallback_parser("bluetooth headphones")
    assert intent["category"] == "Audio"
    assert "bluetooth" in intent["features"]


# --- Test 2: Category Group Isolation & Recommender Mismatches ---
def test_category_group_isolation(seed_products):
    with app.app_context():
        recommender = ProductRecommender()
        
        # Query: shirts under 6000 (Group: fashion)
        filters = {"category": "Fashion", "max_price": 6000.0}
        all_prods = Product.query.all()
        
        ranked = recommender.rank_products_realtime("shirts under 6000", all_prods, filters)
        
        # Should only return Fashion products
        for item in ranked:
            assert item["category"] == "Fashion"
            # Must NOT return earbuds/headphones/watches
            assert item["category"] not in ["Audio", "Watch", "Laptop", "Mobile", "Shoes"]

        # Query: gaming laptop under 80000 (Group: laptop)
        filters_laptop = {"category": "Laptop", "max_price": 80000.0}
        ranked_laptop = recommender.rank_products_realtime("gaming laptop under 80000", all_prods, filters_laptop)
        for item in ranked_laptop:
            assert item["category"] == "Laptop"
            assert item["category"] not in ["Mobile", "Tablet", "Audio", "Watch", "Fashion", "Shoes"]

        # Query: bluetooth headphones (Group: electronics / audio)
        filters_audio = {"category": "Audio"}
        ranked_audio = recommender.rank_products_realtime("bluetooth headphones", all_prods, filters_audio)
        for item in ranked_audio:
            assert item["category"] == "Audio"
            assert item["category"] not in ["Fashion", "Shoes", "Laptop", "Mobile"]


# --- Test 3: Quota Cooldown Mechanism ---
@patch('services.ai_search.requests.post')
def test_quota_cooldown_mechanism(mock_post):
    # Simulate Gemini failing with a 429 status code
    mock_res = MagicMock()
    mock_res.status_code = 429
    mock_res.text = "RESOURCE_EXHAUSTED"
    mock_post.return_value = mock_res
    
    svc = AISearchService()
    svc.gemini_key = "test_gemini_key"
    
    # Trigger first call, which fails and triggers cooldown
    intent = svc.try_gemini("laptop")
    assert intent is None
    assert is_provider_on_cooldown("gemini") is True
    
    # Subsequent calls should return None immediately without posting to Gemini API
    mock_post.reset_mock()
    intent = svc.try_gemini("laptop")
    assert intent is None
    mock_post.assert_not_called()
    
    # Clean up cooldown for remaining tests
    from services.ai_status import _cooldown_expirations
    _cooldown_expirations["gemini"] = None


# --- Test 4: Health Status Endpoint ---
def test_health_status_endpoint(client):
    res = client.get('/api/health')
    assert res.status_code == 200
    data = json.loads(res.data)
    assert "status" in data
    assert "database" in data
    assert "gemini" in data
    assert "openai" in data
    assert "fallback_parser" in data


# --- Test 5: End-to-end Search with Empty Keys ---
def test_search_with_empty_keys(client, seed_products):
    with patch.dict('os.environ', {'GEMINI_API_KEY': '', 'OPENAI_API_KEY': ''}):
        # Call AI Search unified path which forces fallback parser
        res = client.post('/api/search', json={
            "query": "shirts under 6000",
            "filters": {}
        })
        assert res.status_code == 200
        data = json.loads(res.data)
        assert data["success"] is True
        assert len(data["products"]) > 0
        for p in data["products"]:
            assert p["category"] == "Fashion"
