import os
import sys
import json
from datetime import datetime

# Add parent directory to path to import models and config
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../backend'))

from app import app
from models import (
    db, User, Product, WishlistItem, SearchEvent, ClickEvent, 
    PurchaseEvent, ScrapingLog, AnalyticsCounter, AISearchEvent, 
    AISearchCache, PriceDropAlert, UserPreference, RecommendationFeedback
)

def serialize_model(model_class):
    """Serialize all records of a model class to a list of dicts"""
    records = model_class.query.all()
    serialized = []
    for r in records:
        data = {}
        for col in r.__table__.columns:
            val = getattr(r, col.name)
            if isinstance(val, datetime):
                val = val.isoformat()
            data[col.name] = val
        serialized.append(data)
    return serialized

def export_db(output_file):
    print("=" * 60)
    print("BuySmart Database Backup Utility")
    print("=" * 60)
    
    # Check DATABASE_URL in config first
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("[ERROR] DATABASE_URL environment variable is not set!")
        sys.exit(1)
        
    print(f"Connecting to database to backup all tables...")
    
    backup_data = {}
    with app.app_context():
        try:
            # List of tables to backup
            tables = {
                "users": User,
                "products": Product,
                "wishlist": WishlistItem,
                "search_events": SearchEvent,
                "click_events": ClickEvent,
                "purchase_events": PurchaseEvent,
                "scraping_logs": ScrapingLog,
                "analytics_counters": AnalyticsCounter,
                "ai_search_events": AISearchEvent,
                "ai_search_cache": AISearchCache,
                "price_alerts": PriceDropAlert,
                "user_preferences": UserPreference,
                "recommendation_feedback": RecommendationFeedback
            }
            
            for key, model in tables.items():
                print(f"Exporting table '{key}'...")
                backup_data[key] = serialize_model(model)
                print(f"  -> Exported {len(backup_data[key])} rows.")
                
            # Write to JSON
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
            print("=" * 60)
            print(f"[SUCCESS] Database backup saved to: {output_file}")
            print("=" * 60)
            
        except Exception as e:
            print(f"[ERROR] Backup failed: {e}")
            sys.exit(1)

if __name__ == "__main__":
    # Create defaults backup name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    default_filename = f"buysmart_backup_{timestamp}.json"
    
    out_path = sys.argv[1] if len(sys.argv) > 1 else default_filename
    export_db(out_path)
