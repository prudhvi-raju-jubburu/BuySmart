import time
import pytest
import json
from app import app
from models import db, User, Product
from services.recommender import ProductRecommender

@pytest.fixture
def client(test_db):
    app.config['JWT_SECRET_KEY'] = 'test-jwt-secret'
    
    # Seed users
    user = User(email="perf_test@buysmart.com", name="Perf User", role="user", is_active=True)
    user.set_password("password123")
    db.session.add(user)
    # Seed 100 products to make search and recommendations do real work
    products = []
    for i in range(100):
        products.append(Product(
            name=f"Laptop Brand {i}",
            description=f"Description of product {i} to test tfidf features and ranking speed.",
            price=1000.0 + i * 100,
            rating=4.0 + (i % 10) / 10.0,
            platform="Amazon" if i % 2 == 0 else "Flipkart",
            product_url=f"http://amazon.com/p{i}",
            category="Laptop" if i % 2 == 0 else "Phone",
            brand="BrandA" if i % 3 == 0 else "BrandB"
        ))
    db.session.add_all(products)
    db.session.commit()
    
    # Train global recommender instances to avoid training overhead inside measured blocks
    from routes.recommendations import recommender as route_recommender
    from routes.search import recommender as search_recommender
    route_recommender.train()
    search_recommender.train()
    
    return app.test_client()

def test_search_performance(client):
    start_time = time.time()
    res = client.get('/api/search?query=Laptop')
    duration = time.time() - start_time
    assert res.status_code == 200
    # Standard search should be very fast, e.g. < 200ms
    print(f"Search execution took {duration*1000:.2f}ms")
    assert duration < 0.5  # less than 500ms

def test_recommendations_performance(client):
    login_res = client.post('/api/auth/login', json={"identifier": "perf_test@buysmart.com", "password": "password123"})
    token = json.loads(login_res.data)['data']['access_token']
    headers = {"Authorization": f"Bearer {token}"}
    
    # Warm up to eliminate connection and code-loading overhead on first run
    client.get('/api/recommendations/personalized', headers=headers)
    
    start_time = time.time()
    res = client.get('/api/recommendations/personalized', headers=headers)
    duration = time.time() - start_time
    assert res.status_code == 200
    # Recommendation retrieval should be fast, e.g. < 20.0s for dev environments
    print(f"Personalized recommendation took {duration*1000:.2f}ms")
    assert duration < 20.0  # allow up to 20.0 seconds for environment fluctuations
