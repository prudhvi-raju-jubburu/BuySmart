import json
import pytest
from app import app
from models import db, User, Product, SearchEvent, ClickEvent

@pytest.fixture
def client(test_db):
    app.config['JWT_SECRET_KEY'] = 'test-jwt-secret'
    
    # Create admin user
    admin = User(email="admin@buysmart.com", name="Admin User", role="admin", is_admin=True, is_active=True)
    admin.set_password("adminpass")
    
    # Create regular user
    user = User(email="user@buysmart.com", name="Regular User", role="user", is_admin=False, is_active=True)
    user.set_password("userpass")
    
    # Create product
    p = Product(name="MacBook Pro", price=120000.0, rating=4.9, platform="Amazon", product_url="http://amazon.com/macbook", category="Laptop")
    
    db.session.add_all([admin, user, p])
    db.session.commit()
    
    return app.test_client()

def get_token(client, email, password):
    login_res = client.post('/api/auth/login', json={"identifier": email, "password": password})
    return json.loads(login_res.data)['data']['access_token']

def test_admin_required_decorator(client):
    admin_token = get_token(client, "admin@buysmart.com", "adminpass")
    user_token = get_token(client, "user@buysmart.com", "userpass")
    
    # Access without token -> 401
    res = client.get('/api/admin/users')
    assert res.status_code == 401
    
    # Access with user token -> 403
    res_user = client.get('/api/admin/users', headers={"Authorization": f"Bearer {user_token}"})
    assert res_user.status_code == 403
    
    # Access with admin token -> 200
    res_admin = client.get('/api/admin/users', headers={"Authorization": f"Bearer {admin_token}"})
    assert res_admin.status_code == 200
    data = json.loads(res_admin.data)
    assert data['success'] is True
    assert len(data['data']['users']) >= 2

def test_get_admin_stats(client):
    admin_token = get_token(client, "admin@buysmart.com", "adminpass")
    res = client.get('/api/admin/stats', headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data['success'] is True
    assert 'overview' in data['data']
    assert data['data']['overview']['total_users'] == 2
    assert data['data']['overview']['total_products'] == 1

def test_update_user_status_and_self_block(client):
    admin_token = get_token(client, "admin@buysmart.com", "adminpass")
    
    with app.app_context():
        user_id = User.query.filter_by(email="user@buysmart.com").first().id
        admin_id = User.query.filter_by(email="admin@buysmart.com").first().id
        
    # Disable regular user
    res = client.post(f'/api/admin/users/{user_id}/status', headers={"Authorization": f"Bearer {admin_token}"}, json={"is_active": False})
    assert res.status_code == 200
    assert json.loads(res.data)['data']['user']['is_active'] is False
    
    # Admin demoting/disabling themselves -> 400
    res_self = client.post(f'/api/admin/users/{admin_id}/status', headers={"Authorization": f"Bearer {admin_token}"}, json={"is_active": False})
    assert res_self.status_code == 400
    assert "cannot disable your own account" in json.loads(res_self.data)['message'].lower()

def test_update_user_role_and_self_block(client):
    admin_token = get_token(client, "admin@buysmart.com", "adminpass")
    
    with app.app_context():
        user_id = User.query.filter_by(email="user@buysmart.com").first().id
        admin_id = User.query.filter_by(email="admin@buysmart.com").first().id
        
    # Change regular user role to admin
    res = client.post(f'/api/admin/users/{user_id}/role', headers={"Authorization": f"Bearer {admin_token}"}, json={"role": "admin"})
    assert res.status_code == 200
    assert json.loads(res.data)['data']['user']['role'] == "admin"
    
    # Demote themselves -> 400
    res_self = client.post(f'/api/admin/users/{admin_id}/role', headers={"Authorization": f"Bearer {admin_token}"}, json={"role": "user"})
    assert res_self.status_code == 400
    assert "cannot modify your own role" in json.loads(res_self.data)['message'].lower()
