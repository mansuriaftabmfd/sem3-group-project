"""
Add rejection_reason column to orders table
"""
from app import create_app
from models import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        # Check if column already exists
        inspector = db.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('orders')]
        
        if 'rejection_reason' not in columns:
            print("Adding rejection_reason column to orders table...")
            
            # Add column based on database type
            if 'postgresql' in str(db.engine.url):
                db.session.execute(text('ALTER TABLE orders ADD COLUMN rejection_reason TEXT'))
            else:
                db.session.execute(text('ALTER TABLE orders ADD COLUMN rejection_reason TEXT'))
            
            db.session.commit()
            print("[OK] rejection_reason column added successfully!")
        else:
            print("[OK] rejection_reason column already exists")
            
    except Exception as e:
        print(f"[ERROR] Failed to add column: {e}")
        db.session.rollback()
