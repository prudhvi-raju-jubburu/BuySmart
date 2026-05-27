import json
import pytest
from unittest.mock import patch, MagicMock
from app import app, db
from models import User, Product, AISearchEvent, SearchEvent
from services.recommender import ProductRecommender

@pytest.fixture
def seed_data(test_db):
    # Seed various products: laptops, accessories, toys, etc.
    p1 = Product(name="ASUS Vivobook 16 Laptop", price=55000.0, rating=4.5, review_count=100, platform="Amazon", product_url="http://amazon.com/asus", category="Laptop", brand="ASUS")
    p2 = Product(name="Lenovo IdeaPad Laptop 8GB", price=45000.0, rating=4.0, review_count=80, platform="Flipkart", product_url="http://flipkart.com/lenovo", category="Laptop", brand="Lenovo")
    p3 = Product(name="Laptop cover sticker decal", price=150.0, rating=4.3, review_count=120, platform="Meesho", product_url="http://meesho.com/sticker", category="Laptop Accessories", brand="Generic")
    p4 = Product(name="Laptop educational learning toy", price=450.0, rating=3.8, review_count=50, platform="Amazon", product_url="http://amazon.com/toy", category="Toy", brand="KidsPlay")
    p5 = Product(name="Python Programming Book", price=800.0, rating=4.6, review_count=60, platform="Flipkart", product_url="http://flipkart.com/book", category="Books", brand="O'Reilly")
    p6 = Product(name="Mast & Harbour Unisex Laptop Sleeve", price=821.0, rating=4.0, review_count=380, platform="Myntra", product_url="http://myntra.com/sleeve", category="Laptop Accessories", brand="Mast & Harbour")
    p7 = Product(name="ASUS ROG Strix Gaming Laptop 16GB RAM 1TB SSD RTX 4060 GPU", price=85000.0, rating=4.7, review_count=90, platform="Amazon", product_url="http://amazon.com/rog", category="Laptop", brand="ASUS")
    
    # Duplicate products (different URL but identical name + price to test deduplication)
    p9 = Product(name="ASUS Vivobook 16 Laptop", price=55000.0, rating=4.5, review_count=100, platform="Flipkart", product_url="http://flipkart.com/asus_dup", category="Laptop", brand="ASUS")
    
    db.session.add_all([p1, p2, p3, p4, p5, p6, p7, p9])
    db.session.commit()

# --- Test Category Filtering ---
def test_category_relevance_filtering(seed_data):
    recommender = ProductRecommender()
    all_products = [p.to_dict() for p in Product.query.all()]
    
    # Search for Laptop
    filters = {'category': 'Laptop'}
    ranked = recommender.rank_products_realtime("laptop", all_products, filters)
    
    # Verify no covers, stickers, toys, or books
    names = [p['name'].lower() for p in ranked]
    categories = [p['category'].lower() for p in ranked]
    
    assert any("asus" in n for n in names)
    assert any("lenovo" in n for n in names)
    
    import re
    for n in names:
        assert "sticker" not in n
        assert "toy" not in n
        assert not re.search(r'\bbooks?\b', n)
        assert "sleeve" not in n
        
    for c in categories:
        assert "toy" not in c
        assert "book" not in c
        assert "accessories" not in c

# --- Test Budget Enforcement ---
def test_budget_enforcement(seed_data):
    recommender = ProductRecommender()
    all_products = [p.to_dict() for p in Product.query.all()]
    
    # Under 50000 filter
    filters = {'max_price': 50000.0, 'category': 'Laptop'}
    ranked = recommender.rank_products_realtime("laptop under 50000", all_products, filters)
    
    for p in ranked:
        assert p['price'] <= 50000.0
        assert p['price'] > 0

# --- Test Quality Ranking ---
def test_quality_ranking_order(seed_data):
    recommender = ProductRecommender()
    # Compare ASUS Vivobook (4.5 rating) vs Lenovo IdeaPad (4.0 rating)
    # relevance is equal since both are laptops. Higher quality (rating) should rank above.
    p1 = Product.query.filter_by(name="ASUS Vivobook 16 Laptop").first().to_dict()
    p2 = Product.query.filter_by(name="Lenovo IdeaPad Laptop 8GB").first().to_dict()
    
    filters = {'category': 'Laptop'}
    ranked = recommender.rank_products_realtime("laptop", [p1, p2], filters)
    
    assert ranked[0]['name'] == "ASUS Vivobook 16 Laptop"

# --- Test Specification Boosting ---
def test_specification_boosting(seed_data):
    recommender = ProductRecommender()
    all_products = [p.to_dict() for p in Product.query.all()]
    
    # Query with coding and ml purpose
    filters = {'category': 'Laptop', 'purpose': 'coding'}
    ranked = recommender.rank_products_realtime("laptop for coding and machine learning", all_products, filters)
    
    # ASUS ROG Strix (16GB RAM, SSD, GPU) should rank higher than Lenovo IdeaPad (8GB, no specs mentioned)
    assert ranked[0]['name'] == "ASUS ROG Strix Gaming Laptop 16GB RAM 1TB SSD RTX 4060 GPU"

# --- Test Deduplication ---
def test_duplicate_removal(seed_data):
    recommender = ProductRecommender()
    all_products = [p.to_dict() for p in Product.query.all()]
    
    filters = {'category': 'Laptop'}
    ranked = recommender.rank_products_realtime("laptop", all_products, filters)
    
    # Verify no duplicate URLs or identical name + price combinations
    urls = [p['product_url'] for p in ranked]
    assert len(urls) == len(set(urls))
    
    names_and_prices = [(p['name'], p['price']) for p in ranked]
    assert len(names_and_prices) == len(set(names_and_prices))
