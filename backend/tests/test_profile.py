import json
import pytest
from app import app
from models import db, User



def register_and_get_token(client, email="test@example.com", phone="9876543210"):
    client.post('/api/auth/register', json={
        "name": "Test User", "email": email, "phone_number": phone, "password": "Test@1234"
    })
    login_res = client.post('/api/auth/login', json={
        "identifier": email, "password": "Test@1234"
    })
    return json.loads(login_res.data)['data']['access_token']

def test_get_profile(client):
    token = register_and_get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get('/api/auth/me', headers=headers)
    data = json.loads(res.data)
    assert res.status_code == 200
    assert data['success'] is True
    assert data['data']['user']['email'] == 'test@example.com'

def test_update_profile_name(client):
    token = register_and_get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    res = client.put('/api/auth/profile', json={"name": "New Name"}, headers=headers)
    data = json.loads(res.data)
    assert res.status_code == 200
    assert data['success'] is True
    assert data['data']['user']['name'] == 'New Name'

def test_update_profile_phone(client):
    token = register_and_get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    res = client.put('/api/auth/profile', json={"phone_number": "8888888888"}, headers=headers)
    data = json.loads(res.data)
    assert res.status_code == 200
    assert data['success'] is True
    assert data['data']['user']['phone_number'] == '8888888888'

def test_update_profile_duplicate_phone_rejected(client):
    # Register another user with phone 8888888888
    client.post('/api/auth/register', json={
        "name": "Other User", "email": "other@example.com", "phone_number": "8888888888", "password": "Other@1234"
    })
    token = register_and_get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    res = client.put('/api/auth/profile', json={"phone_number": "8888888888"}, headers=headers)
    data = json.loads(res.data)
    assert res.status_code == 409
    assert data['success'] is False

def test_update_profile_name_too_short(client):
    token = register_and_get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    res = client.put('/api/auth/profile', json={"name": "AB"}, headers=headers)
    assert res.status_code == 400

def test_unauthenticated_profile_update(client):
    res = client.put('/api/auth/profile', json={"name": "NoToken"})
    assert res.status_code in [401, 422]

# --- Change Password Tests ---

def test_change_password_success(client):
    token = register_and_get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    res = client.post('/api/auth/change-password', json={
        "current_password": "Test@1234",
        "new_password": "NewPass@5678"
    }, headers=headers)
    data = json.loads(res.data)
    assert res.status_code == 200
    assert data['success'] is True

def test_change_password_wrong_current_password(client):
    token = register_and_get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    res = client.post('/api/auth/change-password', json={
        "current_password": "WrongPassword1!",
        "new_password": "NewPass@5678"
    }, headers=headers)
    assert res.status_code == 401

def test_change_password_same_password_rejected(client):
    token = register_and_get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    res = client.post('/api/auth/change-password', json={
        "current_password": "Test@1234",
        "new_password": "Test@1234"
    }, headers=headers)
    assert res.status_code == 400

def test_change_password_weak_new_password_rejected(client):
    token = register_and_get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    res = client.post('/api/auth/change-password', json={
        "current_password": "Test@1234",
        "new_password": "weak"
    }, headers=headers)
    assert res.status_code == 400

def test_login_after_password_change(client):
    token = register_and_get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    client.post('/api/auth/change-password', json={
        "current_password": "Test@1234",
        "new_password": "NewPass@5678"
    }, headers=headers)
    
    # Try logging in with old password
    login_old = client.post('/api/auth/login', json={"identifier": "test@example.com", "password": "Test@1234"})
    assert login_old.status_code == 401
    
    # Try logging in with new password
    login_new = client.post('/api/auth/login', json={"identifier": "test@example.com", "password": "NewPass@5678"})
    assert login_new.status_code == 200
