#!/usr/bin/env python3
"""
Database creation and migration script for AliExpress Scraper
"""

import sqlite3
import os
from app import app, db
from models import Product, PriceHistory, SearchKeyword, ScrapingLog

def create_database():
    """Create database with all tables"""
    print("Creating database...")
    
    with app.app_context():
        # Drop all tables first (in case of old schema)
        db.drop_all()
        print("Dropped existing tables (if any)")
        
        # Create all tables with new schema
        db.create_all()
        print("Created all tables with new schema")
        
        # Verify tables were created
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"Created tables: {tables}")
        
        # Check if Product table has new columns
        columns = [col['name'] for col in inspector.get_columns('products')]
        print(f"Product table columns: {columns}")
        
        # Verify new variant columns exist
        required_columns = ['sku_id', 'spu_id', 'variant_title']
        missing_columns = [col for col in required_columns if col not in columns]
        
        if missing_columns:
            print(f"ERROR: Missing columns: {missing_columns}")
            return False
        else:
            print("✅ All variant columns present")
            return True

def migrate_existing_database():
    """Migrate existing database to add variant columns"""
    db_path = 'aliexpress_scraper.db'
    
    if not os.path.exists(db_path):
        print(f"Database {db_path} does not exist. Creating new database.")
        return create_database()
    
    print(f"Migrating existing database: {db_path}")
    
    # Connect directly to SQLite to add columns
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if new columns already exist
        cursor.execute("PRAGMA table_info(products)")
        columns = [row[1] for row in cursor.fetchall()]
        
        new_columns = ['sku_id', 'spu_id', 'variant_title']
        missing_columns = [col for col in new_columns if col not in columns]
        
        if not missing_columns:
            print("✅ Database already has variant columns")
            return True
        
        print(f"Adding missing columns: {missing_columns}")
        
        # Add missing columns
        if 'sku_id' in missing_columns:
            cursor.execute("ALTER TABLE products ADD COLUMN sku_id VARCHAR(50)")
            print("Added sku_id column")
        
        if 'spu_id' in missing_columns:
            cursor.execute("ALTER TABLE products ADD COLUMN spu_id VARCHAR(50)")
            print("Added spu_id column")
        
        if 'variant_title' in missing_columns:
            cursor.execute("ALTER TABLE products ADD COLUMN variant_title VARCHAR(500)")
            print("Added variant_title column")
        
        # Create indexes for new columns
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_sku_id ON products(sku_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_spu_id ON products(spu_id)")
            print("Created indexes for new columns")
        except sqlite3.Error as e:
            print(f"Warning: Could not create indexes: {e}")
        
        conn.commit()
        print("✅ Database migration completed successfully")
        return True
        
    except sqlite3.Error as e:
        print(f"ERROR during migration: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("AliExpress Scraper Database Setup")
    print("=" * 40)
    
    try:
        success = migrate_existing_database()
        
        if success:
            print("\n✅ Database setup completed successfully!")
            print("You can now start the application with: python3 app.py")
        else:
            print("\n❌ Database setup failed!")
            print("Please check the error messages above.")
            
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("Please check your database setup.")