import json
import pytest
from unittest.mock import patch, MagicMock
from app import app, db
from models import User, Product, AISearchEvent, SearchEvent, UserPreference
from services.ai_search import parse_budget_to_number, AISearchService

@pytest.fixture
def client(test_db):
    app.config['JWT_SECRET_KEY'] = 'test-jwt-secret'
    
    # Seed user
    user = User(email="test_search_user@example.com", name="Search User", role="user", is_active=True)
    user.set_password("password123")
    db.session.add(user)
    
    # Seed products
    p1 = Product(name="Lenovo ThinkPad Laptop", price=45000.0, rating=4.5, review_count=100, platform="Amazon", product_url="http://amazon.com/l1", category="Laptop", brand="Lenovo")
    p2 = Product(name="MacBook Air Laptop", price=85000.0, rating=4.8, review_count=200, platform="Flipkart", product_url="http://flipkart.com/l2", category="Laptop", brand="Apple")
    p3 = Product(name="iPhone 15 Mobile", price=79000.0, rating=4.7, review_count=300, platform="Amazon", product_url="http://amazon.com/p1", category="Mobile", brand="Apple")
    db.session.add_all([p1, p2, p3])
    db.session.commit()
    
    return app.test_client()

# --- Budget Parsing Utility Tests ---

def test_budget_parsing():
    assert parse_budget_to_number("50k") == 50000.0
    assert parse_budget_to_number("fifty thousand") == 50000.0
    assert parse_budget_to_number("₹60,000") == 60000.0
    assert parse_budget_to_number("under 20000") == 20000.0
    assert parse_budget_to_number("Any") is None

# --- Standard Search Tests ---

def test_standard_search_keyword(client):
    res = client.get('/api/search?query=Lenovo')
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data['success'] is True
    assert len(data['results']) == 1
    assert data['results'][0]['name'] == "Lenovo ThinkPad Laptop"

def test_standard_search_filters(client):
    # filter by max price
    res = client.post('/api/search', json={
        "query": "Laptop",
        "filters": {"max_price": 50000.0}
    })
    assert res.status_code == 200
    data = json.loads(res.data)
    assert len(data['results']) == 1
    assert data['results'][0]['name'] == "Lenovo ThinkPad Laptop"

# --- AI Search Tests ---

@patch('services.ai_search.requests.post')
def test_ai_search_intent_extraction(mock_post, client):
    # Mock Gemini API response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "candidates": [{
            "content": {
                "parts": [{
                    "text": json.dumps({
                        "category": "Laptop",
                        "subcategory": "Coding Laptop",
                        "brand": "Lenovo",
                        "budget_min": None,
                        "budget_max": 60000.0,
                        "platform": None,
                        "rating": 4.0,
                        "purpose": "Coding",
                        "features": [],
                        "confidence": 0.95,
                        "rewritten_query": "Lenovo coding laptop under 60000",
                        "search_explanation_bullets": ["✓ Coding laptop", "✓ Under ₹60k"],
                        "refinements": []
                    })
                }]
            }
        }]
    }
    mock_post.return_value = mock_response

    svc = AISearchService()
    svc.gemini_key = "dummy_key"
    
    intent = svc.extract_intent("Need a laptop for coding under 60000")
    assert intent["category"] == "Laptop"
    assert intent["budget_max"] == 60000.0
    assert intent["brand"] == "Lenovo"
