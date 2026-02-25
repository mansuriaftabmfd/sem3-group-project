"""
Migration Script: Convert to Unified User Model
Changes user_type from 'client'/'provider' to just 'user'
Keeps 'admin' separate
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from BACKEND.models.models import db, User
from BACKEND.core.app import create_app

def migrate_to_unified_user():
    """
    Migrate existing users to unified model
    - All 'client' and 'provider' users become 'user'
    - 'admin' stays as 'admin'
    """
    app = create_app('development')
    
    with app.app_context():
        print("=" * 60)
        print("🔄 Migrating to Unified User Model")
        print("=" * 60)
        
        # Get all non-admin users
        clients = User.query.filter_by(user_type='client').all()
        providers = User.query.filter_by(user_type='provider').all()
        
        print(f"\n📊 Found:")
        print(f"   - {len(clients)} clients")
        print(f"   - {len(providers)} providers")
        
        # Convert all to 'user'
        count = 0
        for user in clients + providers:
            user.user_type = 'user'
            count += 1
        
        db.session.commit()
        
        print(f"\n✅ Successfully migrated {count} users to unified 'user' type")
        print(f"✅ Admin users remain unchanged")
        
        # Verify
        users = User.query.filter_by(user_type='user').count()
        admins = User.query.filter_by(user_type='admin').count()
        
        print(f"\n📈 Final Count:")
        print(f"   - Users: {users}")
        print(f"   - Admins: {admins}")
        print("\n" + "=" * 60)
        print("✅ Migration Complete!")
        print("=" * 60)

if __name__ == '__main__':
    migrate_to_unified_user()
