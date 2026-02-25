"""
Create PostgreSQL Tables for SkillVerse
"""
import os
os.environ['DATABASE_URL'] = 'postgresql://postgres:Amf%402007@localhost/skillverse_pg'

from app import create_app
from models import db

app = create_app('development')

with app.app_context():
    print("Creating all tables in PostgreSQL...")
    db.create_all()
    print("[OK] All tables created successfully!")
    
    # Show created tables
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    print(f"\nCreated {len(tables)} tables:")
    for table in tables:
        print(f"  - {table}")
