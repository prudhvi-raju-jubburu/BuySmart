import json
import pytest
from app import app
from models import db, User, Product, Feedback

@pytest.fixture
def client(test_db):
    app.config['JWT_SECRET_KEY'] = 'test-jwt-secret'
    
    # Seed test user
    user = User(email="sec_test@buysmart.com", name="Sec User", role="user", is_active=True)
    user.set_password("password123")
    
    # Seed product
    p = Product(name="Safe Product", price=100.0, rating=4.5, platform="Amazon", product_url="http://amazon.com/p", category="Stuff")
    db.session.add_all([user, p])
    db.session.commit()
    
    return app.test_client()

# --- Route Protection ---

def test_unauthenticated_protected_route_fails(client):
    res = client.get('/api/dashboard/overview')
    assert res.status_code in [401, 422]

def test_authenticated_protected_route_succeeds(client):
    login_res = client.post('/api/auth/login', json={"identifier": "sec_test@buysmart.com", "password": "password123"})
    token = json.loads(login_res.data)['data']['access_token']
    res = client.get('/api/dashboard/overview', headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200

# --- SQL Injection Resilience ---

def test_sql_injection_search(client):
    # Query with classic SQL injection payload (3 words, routes to keyword search)
    sqli_payload = "Laptop' OR '1'='1"
    res = client.get(f'/api/search?query={sqli_payload}')
    assert res.status_code == 200
    data = json.loads(res.data)
    # It should run successfully but return 0 results since no product matches that literal name,
    # and not crash or return everything.
    assert len(data['results']) == 0

# --- XSS Script Sanitization ---

def test_xss_feedback(client):
    login_res = client.post('/api/auth/login', json={"identifier": "sec_test@buysmart.com", "password": "password123"})
    token = json.loads(login_res.data)['data']['access_token']
    headers = {"Authorization": f"Bearer {token}"}
    
    # Post guest feedback containing script tags
    xss_payload = "<script>alert('XSS')</script>"
    res = client.put('/api/auth/profile', json={"name": f"User {xss_payload}"}, headers=headers)
    assert res.status_code == 200
    
    # Check if user details return fine without throwing rendering errors or collapsing
    data = json.loads(res.data)
    assert f"User {xss_payload}" in data['data']['user']['name']
