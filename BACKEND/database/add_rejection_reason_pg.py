"""
Add rejection_reason column to orders table in PostgreSQL
"""
import os
os.environ['DATABASE_URL'] = 'postgresql://postgres:Amf%402007@localhost/skillverse_pg'

from app import create_app
from models import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        # Check if column already exists
        result = db.session.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='orders' AND column_name='rejection_reason'
        """))
        
        if result.fetchone() is None:
            print("Adding rejection_reason column to orders table...")
            db.session.execute(text('ALTER TABLE orders ADD COLUMN rejection_reason TEXT'))
            db.session.commit()
            print("[OK] rejection_reason column added successfully!")
        else:
            print("[OK] rejection_reason column already exists")
            
    except Exception as e:
        print(f"[ERROR] Failed to add column: {e}")
        db.session.rollback()
