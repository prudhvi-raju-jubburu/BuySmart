import os
import pytest
from unittest.mock import patch
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
os.environ["SKIP_DB_CHECK"] = "1"
os.environ["TESTING"] = "1"

import socket
from urllib.parse import urlparse

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
fallback_to_sqlite = False

if not TEST_DATABASE_URL:
    fallback_to_sqlite = True
else:
    try:
        parsed = urlparse(TEST_DATABASE_URL)
        host = parsed.hostname
        port = parsed.port or 5432
        
        # Test connection with a 2-second timeout
        with socket.create_connection((host, port), timeout=2.0) as conn:
            pass
    except Exception as e:
        print(f"\n[Warning] PostgreSQL database is unreachable: {e}")
        print("Falling back to SQLite in-memory database for testing.\n")
        fallback_to_sqlite = True

if fallback_to_sqlite:
    TEST_DATABASE_URL = "sqlite:///:memory:"

# Override DATABASE_URL in the environment BEFORE importing the app
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from app import app
from models import db

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Configure application URI and ensure test database connection is healthy"""
    app.config['TESTING'] = True
    app.config['JWT_SECRET_KEY'] = 'test-jwt-secret'
    
    with app.app_context():
        try:
            db.session.execute(db.text("SELECT 1"))
        except Exception as e:
            raise RuntimeError(
                f"Failed to connect to test PostgreSQL database {TEST_DATABASE_URL}: {e}"
            )
    yield

@pytest.fixture(scope="function")
def test_db():
    """Create tables and schema clean-up before and after each test function"""
    with app.app_context():
        db.create_all()
        yield db
        db.session.rollback()
        db.session.remove()
        db.drop_all()

@pytest.fixture(scope="function")
def client(test_db):
    """Client fixture utilizing the test database"""
    return app.test_client()

@pytest.fixture(scope="function")
def db_session(test_db):
    """Database session fixture utilizing the test database"""
    return test_db.session

@pytest.fixture(autouse=True)
def mock_scraper_realtime():
    """Autouse fixture to mock real-time scraping and fallback to database queries in tests."""
    with patch('routes.search.scraper_manager.scrape_platform_realtime') as mock:
        def side_effect(platform, query, limit=20):
            from app import app
            from models import Product
            with app.app_context():
                # Search local database for items matching the query to simulate scrapers returning database items.
                q_term = f"%{query}%"
                prods = Product.query.filter(
                    (Product.name.ilike(q_term)) | (Product.category.ilike(q_term))
                ).all()
                return [p.to_dict() for p in prods]
        mock.side_effect = side_effect
        yield mock
