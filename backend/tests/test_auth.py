import json
import pytest
from app import app
from models import db, User, TokenBlocklist



def register(client, name="Test User", email="test@example.com", phone="9876543210", password="Test@1234"):
    return client.post('/api/auth/register', json={
        "name": name, "email": email, "phone_number": phone, "password": password
    })

def login(client, identifier="test@example.com", password="Test@1234"):
    return client.post('/api/auth/login', json={
        "identifier": identifier, "password": password
    })

# --- Registration Tests ---

def test_valid_registration(client):
    res = register(client)
    data = json.loads(res.data)
    assert res.status_code == 201
    assert data['success'] is True
    assert 'access_token' in data['data']
    assert 'refresh_token' in data['data']
    assert data['data']['user']['email'] == 'test@example.com'
    assert data['data']['user']['phone_number'] == '9876543210'

def test_duplicate_email_rejected(client):
    register(client)
    res = register(client, phone="9000000001")
    data = json.loads(res.data)
    assert res.status_code == 409
    assert data['success'] is False
    assert 'email' in data['message'].lower()

def test_duplicate_phone_rejected(client):
    register(client)
    res = register(client, email="other@example.com")
    data = json.loads(res.data)
    assert res.status_code == 409
    assert data['success'] is False
    assert 'phone' in data['message'].lower()

def test_weak_password_no_uppercase(client):
    res = register(client, password="test@1234")
    assert res.status_code == 400
    assert json.loads(res.data)['success'] is False

def test_weak_password_no_special_char(client):
    res = register(client, password="Test12345")
    assert res.status_code == 400
    assert json.loads(res.data)['success'] is False

def test_weak_password_too_short(client):
    res = register(client, password="T@1")
    assert res.status_code == 400
    assert json.loads(res.data)['success'] is False

def test_invalid_email_rejected(client):
    res = register(client, email="notanemail")
    assert res.status_code == 400
    assert json.loads(res.data)['success'] is False

def test_invalid_phone_rejected(client):
    res = register(client, phone="12345")
    assert res.status_code == 400
    assert json.loads(res.data)['success'] is False

def test_registration_email_only(client):
    res = register(client, phone="")
    data = json.loads(res.data)
    assert res.status_code == 201
    assert data['data']['user']['email'] == 'test@example.com'
    assert data['data']['user']['phone_number'] is None

def test_registration_phone_only(client):
    res = register(client, email="")
    data = json.loads(res.data)
    assert res.status_code == 201
    assert data['data']['user']['email'] is None
    assert data['data']['user']['phone_number'] == '9876543210'

def test_registration_neither_rejected(client):
    res = register(client, email="", phone="")
    assert res.status_code == 400
    assert json.loads(res.data)['success'] is False

# --- Login Tests ---

def test_login_with_email(client):
    register(client)
    res = login(client, identifier="test@example.com")
    data = json.loads(res.data)
    assert res.status_code == 200
    assert data['success'] is True
    assert 'access_token' in data['data']

def test_login_with_phone(client):
    register(client)
    res = login(client, identifier="9876543210")
    data = json.loads(res.data)
    assert res.status_code == 200
    assert data['success'] is True
    assert 'access_token' in data['data']

def test_wrong_password_rejected(client):
    register(client)
    res = login(client, password="WrongPassword123!")
    assert res.status_code == 401
    assert json.loads(res.data)['success'] is False

def test_blocked_account_rejected(client):
    register(client)
    # Block account in DB
    with app.app_context():
        user = User.query.filter_by(email="test@example.com").first()
        user.is_active = False
        db.session.commit()
    
    res = login(client)
    assert res.status_code == 403
    assert json.loads(res.data)['success'] is False
    assert "disabled" in json.loads(res.data)['message'].lower()

# --- Logout Tests ---

def test_logout(client):
    register(client)
    login_res = login(client)
    access_token = json.loads(login_res.data)['data']['access_token']
    refresh_token = json.loads(login_res.data)['data']['refresh_token']
    
    headers = {"Authorization": f"Bearer {access_token}"}
    logout_res = client.post('/api/auth/logout', json={"refresh_token": refresh_token}, headers=headers)
    assert logout_res.status_code == 200
    assert json.loads(logout_res.data)['success'] is True
