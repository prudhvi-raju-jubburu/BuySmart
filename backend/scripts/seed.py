import sys
import os

# Add backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend'))

from app import app
from models import db, User, Product, SearchEvent, ClickEvent, WishlistItem, PriceDropAlert, PurchaseEvent, UserPreference
from datetime import datetime, timedelta
import secrets

def seed_db():
    print("=" * 60)
    print("BuySmart Database Seeder")
    print("=" * 60)
    
    with app.app_context():
        # Ensure database tables exist
        db.create_all()
        print("[OK] Database tables initialized.")
        
        # Check/Create Admin User
        admin = User.query.filter_by(email="manju@gmail.com").first()
        if not admin:
            admin = User(
                email="manju@gmail.com",
                name="Manju",
                phone_number="9876543210",
                role="admin",
                is_admin=True,
                is_active=True
            )
            admin.set_password("password123")
            db.session.add(admin)
            print("[OK] Created admin user: manju@gmail.com (Password: password123)")
        else:
            # Ensure admin credentials are intact
            admin.role = 'admin'
            admin.is_admin = True
            admin.is_active = True
            print("[OK] Verified admin user manju@gmail.com already exists.")

        # Seed products if empty
        if Product.query.count() == 0:
            products_data = [
                # Mobiles
                ("Apple iPhone 15 Pro", 134900.0, 4.8, 850, "Amazon", "Mobiles", "Apple", "http://amazon.in/iphone15pro"),
                ("Apple iPhone 15", 79900.0, 4.7, 1200, "Flipkart", "Mobiles", "Apple", "http://flipkart.in/iphone15"),
                ("Samsung Galaxy S24 Ultra", 129999.0, 4.8, 640, "Amazon", "Mobiles", "Samsung", "http://amazon.in/s24ultra"),
                ("Samsung Galaxy S24", 74999.0, 4.6, 980, "Flipkart", "Mobiles", "Samsung", "http://flipkart.in/s24"),
                ("OnePlus 12", 64999.0, 4.5, 450, "Amazon", "Mobiles", "OnePlus", "http://amazon.in/oneplus12"),
                ("Redmi Note 13 Pro", 25999.0, 4.3, 1500, "Flipkart", "Mobiles", "Xiaomi", "http://flipkart.in/redminote13"),
                
                # Electronics
                ("MacBook Air M3", 114900.0, 4.8, 310, "Amazon", "Electronics", "Apple", "http://amazon.in/macbookairm3"),
                ("Dell Inspiron 15 Laptop", 43990.0, 4.1, 720, "Flipkart", "Electronics", "Dell", "http://flipkart.in/dellinspiron15"),
                ("HP Pavilion 15", 58990.0, 4.3, 540, "Amazon", "Electronics", "HP", "http://amazon.in/hppavilion15"),
                ("Lenovo IdeaPad Slim 3", 36990.0, 4.0, 890, "Flipkart", "Electronics", "Lenovo", "http://flipkart.in/ideapadslim3"),
                ("Sony WH-1000XM5 Headphones", 29990.0, 4.7, 1150, "Amazon", "Electronics", "Sony", "http://amazon.in/sonywh1000xm5"),
                ("Sony WH-1000XM4 Headphones", 19990.0, 4.6, 2400, "Flipkart", "Electronics", "Sony", "http://flipkart.in/sonywh1000xm4"),
                ("iPad Air M2", 59900.0, 4.7, 410, "Amazon", "Electronics", "Apple", "http://amazon.in/ipadairm2"),

                # Fashion / Clothing
                ("Nike Air Max Solo Sneakers", 8295.0, 4.5, 230, "Amazon", "Clothing", "Nike", "http://amazon.in/nikeairmaxsolo"),
                ("Nike Court Vision Low", 4995.0, 4.4, 450, "Myntra", "Clothing", "Nike", "http://myntra.com/nikecourtvision"),
                ("Adidas Ultraboost Light", 18999.0, 4.6, 120, "Amazon", "Clothing", "Adidas", "http://amazon.in/adidasultraboost"),
                ("Adidas Samba Shoes", 10999.0, 4.7, 340, "Myntra", "Clothing", "Adidas", "http://myntra.com/adidassamba"),
                ("Puma Classic Suede Sneakers", 6999.0, 4.3, 510, "Flipkart", "Clothing", "Puma", "http://flipkart.in/pumasuede"),
                ("Levi's 511 Slim Fit Jeans", 2599.0, 4.2, 1800, "Myntra", "Clothing", "Levis", "http://myntra.com/levis511"),
                ("Levi's 511 Slim Fit Jeans", 2299.0, 4.1, 1400, "Flipkart", "Clothing", "Levis", "http://flipkart.in/levis511"),
                
                # Low range / Meesho
                ("Men Slim Fit Solid Shirt", 399.0, 3.8, 12000, "Meesho", "Clothing", "General", "http://meesho.com/mensolidshirt"),
                ("Women Floral Print Saree", 499.0, 4.0, 25000, "Meesho", "Clothing", "General", "http://meesho.com/womensaree"),
                ("Wireless Bluetooth Earbuds", 599.0, 3.9, 8500, "Meesho", "Electronics", "General", "http://meesho.com/wirelessearbuds"),
                ("Smart Watch Fit Pro", 899.0, 3.7, 5400, "Meesho", "Electronics", "General", "http://meesho.com/smartwatchfitpro"),
            ]
            
            for name, price, rating, reviews, platform, category, brand, url in products_data:
                p = Product(
                    name=name,
                    description=f"Premium {brand} {category} item on {platform}. Rated {rating}/5 with {reviews} reviews. Buy Smart price comparison matching details.",
                    price=price,
                    rating=rating,
                    review_count=reviews,
                    platform=platform,
                    product_url=url,
                    image_url="https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&q=80&w=200",
                    category=category,
                    brand=brand
                )
                db.session.add(p)
            db.session.commit()
            print(f"[OK] Seeded {len(products_data)} products.")
        else:
            print("[OK] Products already exist in the database.")

        # Seed sample activities for manju@gmail.com
        db.session.flush()
        db_user = User.query.filter_by(email="manju@gmail.com").first()
        
        # User preference
        pref = UserPreference.query.filter_by(user_id=db_user.id).first()
        if not pref:
            pref = UserPreference(
                user_id=db_user.id,
                preferred_categories={"Clothing": 5, "Mobiles": 3, "Electronics": 1},
                preferred_brands={"Nike": 3, "Apple": 2},
                preferred_platforms={"Amazon": 4, "Myntra": 2},
                preferred_price_min=1000.0,
                preferred_price_max=100000.0
            )
            db.session.add(pref)
            print("[OK] Created default preferences for Manju.")
            
        # ClickEvents
        if ClickEvent.query.filter_by(user_id=db_user.id).count() == 0:
            prods = Product.query.limit(5).all()
            for p in prods:
                click = ClickEvent(
                    user_id=db_user.id,
                    product_id=p.id,
                    platform=p.platform,
                    source='search',
                    created_at=datetime.utcnow() - timedelta(days=secrets.SystemRandom().randint(1, 5))
                )
                db.session.add(click)
            print("[OK] Seeded sample click events.")

        # SearchEvents
        if db.session.query(SearchEvent).filter_by(user_id=db_user.id).count() == 0:
            queries = ["iphone 15", "nike shoes", "laptop", "wireless earbuds"]
            for q in queries:
                se = SearchEvent(
                    user_id=db_user.id,
                    query=q,
                    created_at=datetime.utcnow() - timedelta(days=secrets.SystemRandom().randint(1, 5))
                )
                db.session.add(se)
            print("[OK] Seeded sample search history.")

        # WishlistItems
        if WishlistItem.query.filter_by(user_id=db_user.id).count() == 0:
            w_prods = Product.query.filter_by(category="Clothing").limit(2).all()
            for p in w_prods:
                wi = WishlistItem(
                    user_id=db_user.id,
                    product_id=p.id,
                    created_at=datetime.utcnow() - timedelta(hours=secrets.SystemRandom().randint(1, 10))
                )
                db.session.add(wi)
            print("[OK] Seeded sample wishlist items.")

        db.session.commit()
        print("=" * 60)
        print("Database seeding completed successfully!")
        print("=" * 60)

if __name__ == '__main__':
    seed_db()
