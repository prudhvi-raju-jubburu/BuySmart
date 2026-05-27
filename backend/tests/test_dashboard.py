import json
import pytest
from datetime import datetime, timedelta
from app import app
from models import db, User, Product, SearchEvent, ClickEvent, WishlistItem, PriceDropAlert, PurchaseEvent

@pytest.fixture
def client(test_db):
    app.config['JWT_SECRET_KEY'] = 'test-jwt-secret'
    
    # Create users
    user = User(email="test_dash@buysmart.com", name="Dash User", role="user", is_active=True)
    user.set_password("password123")
    other = User(email="other_dash@buysmart.com", name="Other User", role="user", is_active=True)
    other.set_password("password123")
    db.session.add_all([user, other])
    
    # Create product
    p = Product(name="Test Laptop Pro 15", price=25000.0, rating=4.5, platform="Amazon", product_url="https://amazon.in/p1", category="Electronics")
    db.session.add(p)
    db.session.commit()
    
    return app.test_client()

def get_token(client, email="test_dash@buysmart.com"):
    login_res = client.post('/api/auth/login', json={"identifier": email, "password": "password123"})
    return json.loads(login_res.data)['data']['access_token']

def test_dashboard_overview(client):
    token = get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    
    with app.app_context():
        user = User.query.filter_by(email="test_dash@buysmart.com").first()
        prod = Product.query.first()
        
        # Add various dashboard events
        db.session.add(SearchEvent(user_id=user.id, query='Laptop', results_count=5))
        db.session.add(ClickEvent(user_id=user.id, product_id=prod.id, platform='Amazon', source='recommendation'))
        db.session.add(WishlistItem(user_id=user.id, product_id=prod.id))
        db.session.add(PriceDropAlert(user_id=user.id, product_id=prod.id, platform='Amazon', target_price=20000.0))
        db.session.add(PurchaseEvent(user_id=user.id, product_id=prod.id, platform='Amazon'))
        db.session.commit()
        
    res = client.get('/api/dashboard/overview', headers=headers)
    assert res.status_code == 200
    data = json.loads(res.data)['data']
    assert data['total_searches'] >= 1
    assert data['product_views'] >= 1
    assert data['wishlist_items'] >= 1
    assert data['active_price_alerts'] >= 1
    assert data['total_purchases'] >= 1

def test_search_history_pagination_and_delete(client):
    token = get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    
    with app.app_context():
        user = User.query.filter_by(email="test_dash@buysmart.com").first()
        s1 = SearchEvent(user_id=user.id, query='Laptop A', created_at=datetime.utcnow() - timedelta(minutes=5))
        s2 = SearchEvent(user_id=user.id, query='Phone B', created_at=datetime.utcnow() - timedelta(minutes=4))
        s3 = SearchEvent(user_id=user.id, query='Tablet C', created_at=datetime.utcnow() - timedelta(minutes=3))
        db.session.add_all([s1, s2, s3])
        db.session.commit()
        s2_id = s2.id
        s3_id = s3.id
        
    # Get with pagination
    res = client.get('/api/dashboard/search-history?page=1&per_page=2', headers=headers)
    assert res.status_code == 200
    data = json.loads(res.data)['data']
    assert len(data['items']) == 2
    assert data['total'] == 3
    
    # Delete an item
    del_res = client.delete(f'/api/dashboard/search-history/{s3_id}', headers=headers)
    assert del_res.status_code == 200
    
    # Verify deletion
    res2 = client.get('/api/dashboard/search-history', headers=headers)
    data2 = json.loads(res2.data)['data']
    assert data2['total'] == 2
    assert s3_id not in [x['id'] for x in data2['items']]

    # Attempt to delete from other user (should fail)
    other_token = get_token(client, email="other_dash@buysmart.com")
    del_fail = client.delete(f'/api/dashboard/search-history/{s2_id}', headers={"Authorization": f"Bearer {other_token}"})
    assert del_fail.status_code == 404
