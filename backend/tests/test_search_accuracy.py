import json
import pytest
from unittest.mock import patch, MagicMock
from app import app, db
from models import User, Product

@pytest.fixture
def client(test_db):
    app.config['JWT_SECRET_KEY'] = 'test-jwt-secret'
    
    # Seed user
    user = User(email="accuracy_test@buysmart.com", name="Accuracy User", role="user", is_active=True)
    user.set_password("password123")
    db.session.add(user)
    
    # Seed products
    products = [
        # Laptops & Laptop Accessories
        Product(name="ASUS Zenbook Premium Laptop", price=75000.0, rating=4.7, review_count=50, platform="Amazon", product_url="http://amazon.com/zenbook", category="Laptop", brand="ASUS"),
        Product(name="Dell Inspiron 15 Coding Laptop", price=52000.0, rating=4.3, review_count=120, platform="Flipkart", product_url="http://flipkart.com/inspiron", category="Laptop", brand="Dell"),
        Product(name="Lenovo Laptop Bag Backpack", price=1200.0, rating=4.1, review_count=300, platform="Amazon", product_url="http://amazon.com/bag", category="Laptop Accessories", brand="Lenovo"),
        Product(name="Sleek Laptop Sleeve Case 15.6", price=800.0, rating=4.2, review_count=90, platform="Flipkart", product_url="http://flipkart.com/sleeve", category="Laptop Accessories", brand="Generic"),
        Product(name="Tempered Glass Screen Guard for Laptop", price=300.0, rating=3.9, review_count=45, platform="Meesho", product_url="http://meesho.com/guard", category="Laptop Accessories", brand="Generic"),

        # Shirts & Clothing Accessories
        Product(name="Roadster Men Cotton Casual Shirt", price=1200.0, rating=4.2, review_count=80, platform="Myntra", product_url="http://myntra.com/shirt1", category="Fashion", brand="Roadster"),
        Product(name="Peter England Men Cotton Formal Shirt", price=1800.0, rating=4.5, review_count=150, platform="Myntra", product_url="http://myntra.com/shirt2", category="Fashion", brand="Peter England"),
        Product(name="Premium Silk Luxury Shirt", price=3500.0, rating=4.6, review_count=40, platform="Myntra", product_url="http://myntra.com/shirt3", category="Fashion", brand="Peter England"),
        Product(name="Men Leather Belt Clothing Accessory", price=600.0, rating=4.0, review_count=110, platform="Myntra", product_url="http://myntra.com/belt", category="Fashion Accessories", brand="Levis"),

        # Shoes & Shoe Accessories
        Product(name="Puma Nitro Running Shoes", price=2800.0, rating=4.4, review_count=95, platform="Amazon", product_url="http://amazon.com/shoes1", category="Shoes", brand="Puma"),
        Product(name="Adidas Ultra Boost Sport Shoes", price=5500.0, rating=4.7, review_count=210, platform="Flipkart", product_url="http://flipkart.com/shoes2", category="Shoes", brand="Adidas"),
        Product(name="Shoe Cleaner Polish Liquid", price=250.0, rating=4.2, review_count=70, platform="Amazon", product_url="http://amazon.com/polish", category="Shoe Accessories", brand="Puma")
    ]
    db.session.add_all(products)
    db.session.commit()
    
    return app.test_client()

def test_query_laptops_returns_laptops_only(client):
    # Standard Search Routing (detects laptop category and filters)
    res = client.get('/api/search?query=laptops')
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data['success'] is True
    assert len(data['results']) > 0
    
    for r in data['results']:
        name_lower = r['name'].lower()
        # Verify it is actually a laptop and not an accessory
        assert any(kw in name_lower for kw in ["laptop", "zenbook", "inspiron"])
        assert not any(kw in name_lower for kw in ["bag", "backpack", "sleeve", "cover", "guard", "accessory"])

def test_query_cotton_shirts_returns_shirts_only(client):
    # Conversational Search Routing
    res = client.post('/api/search', json={
        "query": "cotton shirts under 2000"
    })
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data['success'] is True
    assert len(data['products']) > 0
    
    for p in data['products']:
        name_lower = p['name'].lower()
        assert "shirt" in name_lower
        assert "cotton" in name_lower
        assert p['price'] <= 2000.0
        assert not any(kw in name_lower for kw in ["belt", "accessory", "polish"])

def test_query_running_shoes_returns_shoes_only(client):
    # Conversational Search Routing
    res = client.post('/api/search', json={
        "query": "running shoes under 3000"
    })
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data['success'] is True
    assert len(data['products']) > 0
    
    for p in data['products']:
        name_lower = p['name'].lower()
        assert "shoe" in name_lower or "shoes" in name_lower
        assert p['price'] <= 3000.0
        assert not any(kw in name_lower for kw in ["polish", "cleaner"])

@patch('services.ai_parser.requests.post')
def test_ai_failure_still_returns_relevant_products(mock_post, client):
    # Force Gemini to fail by returning error status code
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mock_post.return_value = mock_response
    
    res = client.post('/api/search', json={
        "query": "cotton shirts under 2000"
    })
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data['success'] is True
    assert len(data['products']) > 0
    
    for p in data['products']:
        name_lower = p['name'].lower()
        assert "shirt" in name_lower
        assert "cotton" in name_lower
        assert p['price'] <= 2000.0
