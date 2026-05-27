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

def deserialize_val(val, col_type):
    """Convert JSON string back to python types, specifically handling datetime"""
    if val is None:
        return None
    # If the column type is DateTime, parse string to datetime
    if "datetime" in str(col_type).lower():
        try:
            return datetime.fromisoformat(val)
        except Exception:
            return val
    return val

def import_db(input_file):
    print("=" * 60)
    print("BuySmart Database Restore Utility")
    print("=" * 60)
    
    if not os.path.exists(input_file):
        print(f"[ERROR] Backup file not found: {input_file}")
        sys.exit(1)
        
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("[ERROR] DATABASE_URL environment variable is not set!")
        sys.exit(1)
        
    with open(input_file, 'r', encoding='utf-8') as f:
        backup_data = json.load(f)
        
    print("Recreating database tables for a clean import...")
    
    with app.app_context():
        try:
            # 1. Drop all tables and recreate them to ensure no primary key or foreign key conflicts
            db.drop_all()
            db.create_all()
            print("[OK] Database tables reset successfully.")
            
            # 2. Define import order (Parent tables first, then children with FKs)
            import_order = [
                ("products", Product),
                ("users", User),
                ("wishlist", WishlistItem),
                ("search_events", SearchEvent),
                ("click_events", ClickEvent),
                ("purchase_events", PurchaseEvent),
                ("scraping_logs", ScrapingLog),
                ("analytics_counters", AnalyticsCounter),
                ("ai_search_events", AISearchEvent),
                ("ai_search_cache", AISearchCache),
                ("price_alerts", PriceDropAlert),
                ("user_preferences", UserPreference),
                ("recommendation_feedback", RecommendationFeedback)
            ]
            
            for key, model in import_order:
                rows = backup_data.get(key, [])
                print(f"Importing {len(rows)} records into '{key}'...")
                
                for r_data in rows:
                    instance = model()
                    for col in model.__table__.columns:
                        if col.name in r_data:
                            val = deserialize_val(r_data[col.name], col.type)
                            setattr(instance, col.name, val)
                    db.session.add(instance)
                
                db.session.commit()
                print(f"  -> Imported '{key}' successfully.")
            
            # 3. Reset PostgreSQL sequences so auto-increment works on future inserts
            print("Resetting PostgreSQL primary key auto-increment sequences...")
            for key, model in import_order:
                table_name = model.__tablename__
                try:
                    # Query max ID in table
                    max_id_res = db.session.execute(db.text(f"SELECT MAX(id) FROM {table_name}")).fetchone()
                    max_id = max_id_res[0] if max_id_res and max_id_res[0] else 1
                    
                    # Update sequence
                    db.session.execute(db.text(
                        f"SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), :max_id)"
                    ), {"max_id": max_id})
                    db.session.commit()
                except Exception as seq_err:
                    # Ignore sequence resets for tables that don't use auto-increment ids
                    db.session.rollback()
            
            print("=" * 60)
            print("[SUCCESS] Database restore completed successfully!")
            print("=" * 60)
            
        except Exception as e:
            print(f"[ERROR] Restore failed: {e}")
            db.session.rollback()
            sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("[ERROR] Please specify the backup file to import!")
        print("Usage: python import_database.py <path_to_backup.json>")
        sys.exit(1)
        
    in_path = sys.argv[1]
    import_db(in_path)
