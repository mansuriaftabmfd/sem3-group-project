"""
Database Initialization and Seeding Script

This script:
1. Creates database tables
2. Creates default admin user
3. Seeds initial categories and sample data

Author: SkillVerse Team
Purpose: Initialize database with default data
"""

from models import db, User, Category, Service
from werkzeug.security import generate_password_hash


def create_default_admin(app):
    """
    Create default admin user if not exists
    
    Args:
        app: Flask application instance
    """
    with app.app_context():
        # Check if admin already exists
        admin = User.query.filter_by(email=app.config['ADMIN_EMAIL']).first()
        
        if not admin:
            # Create admin user
            admin = User(
                username='admin',
                email=app.config['ADMIN_EMAIL'],
                user_type='admin',
                full_name='System Administrator',
                is_active=True,
                is_verified=True
            )
            admin.set_password(app.config['ADMIN_PASSWORD'])
            
            db.session.add(admin)
            db.session.commit()
            
            print(f"[OK] Admin user created: {app.config['ADMIN_EMAIL']}")
        else:
            print(f"[OK] Admin user already exists: {app.config['ADMIN_EMAIL']}")


def seed_categories():
    """
    Seed initial categories
    
    Creates default service categories with icons and colors
    """
    # Default categories matching the original design
    categories_data = [
        {
            'name': 'Web Development',
            'description': 'Website and web application development services',
            'icon': 'bi-code-slash',
            'color': 'bg-primary'
        },
        {
            'name': 'Graphic Design',
            'description': 'Logo, branding, and graphic design services',
            'icon': 'bi-palette',
            'color': 'bg-danger'
        },
        {
            'name': 'Content Writing',
            'description': 'SEO content, blog posts, and copywriting',
            'icon': 'bi-pen',
            'color': 'bg-warning'
        },
        {
            'name': 'Video Editing',
            'description': 'Professional video editing and production',
            'icon': 'bi-camera-video',
            'color': 'bg-info'
        },
        {
            'name': 'Tutoring',
            'description': 'Online tutoring and educational services',
            'icon': 'bi-book',
            'color': 'bg-success'
        },
        {
            'name': 'Music & Audio',
            'description': 'Music production, mixing, and audio services',
            'icon': 'bi-music-note-beamed',
            'color': 'bg-secondary'
        },
        {
            'name': 'Photography',
            'description': 'Professional photography services',
            'icon': 'bi-camera',
            'color': 'bg-dark'
        },
        {
            'name': 'Marketing',
            'description': 'Digital marketing and social media services',
            'icon': 'bi-graph-up-arrow',
            'color': 'bg-primary'
        }
    ]
    
    for cat_data in categories_data:
        # Check if category already exists
        existing = Category.query.filter_by(name=cat_data['name']).first()
        
        if not existing:
            category = Category(**cat_data)
            db.session.add(category)
    
    try:
        db.session.commit()
        print(f"[OK] Seeded {len(categories_data)} categories")
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Error seeding categories: {str(e)}")


def seed_sample_data():
    """
    Seed sample services and users for testing
    
    This function creates sample data for demonstration
    """
    # Create sample provider users
    sample_providers = [
        {
            'username': 'alex_dev',
            'email': 'alex@example.com',
            'password': 'password123',
            'user_type': 'provider',
            'full_name': 'Alex Chen',
            'bio': 'Full-stack web developer with 5+ years experience'
        },
        {
            'username': 'sarah_design',
            'email': 'sarah@example.com',
            'password': 'password123',
            'user_type': 'provider',
            'full_name': 'Sarah Miller',
            'bio': 'Creative graphic designer specializing in brand identity'
        },
        {
            'username': 'james_writer',
            'email': 'james@example.com',
            'password': 'password123',
            'user_type': 'provider',
            'full_name': 'James Wilson',
            'bio': 'SEO content writer and copywriter'
        }
    ]
    
    created_users = []
    for user_data in sample_providers:
        # Check if user exists
        existing = User.query.filter_by(email=user_data['email']).first()
        if not existing:
            user = User(
                username=user_data['username'],
                email=user_data['email'],
                user_type=user_data['user_type'],
                full_name=user_data['full_name'],
                bio=user_data['bio'],
                is_verified=True
            )
            user.set_password(user_data['password'])
            db.session.add(user)
            created_users.append(user)
    
    db.session.commit()
    
    # Create sample services
    if created_users:
        web_dev_category = Category.query.filter_by(name='Web Development').first()
        design_category = Category.query.filter_by(name='Graphic Design').first()
        writing_category = Category.query.filter_by(name='Content Writing').first()
        
        sample_services = [
            {
                'user_id': created_users[0].id,
                'category_id': web_dev_category.id if web_dev_category else 1,
                'title': 'Professional Website Development',
                'description': 'I will create a modern, responsive website using React and Node.js',
                'price': 150.00,
                'delivery_time': '5 days',
                'tags': 'React, Node.js, JavaScript, HTML, CSS'
            },
            {
                'user_id': created_users[1].id,
                'category_id': design_category.id if design_category else 2,
                'title': 'Logo Design & Brand Identity',
                'description': 'Professional logo design with complete brand identity package',
                'price': 80.00,
                'delivery_time': '3 days',
                'tags': 'Logo, Branding, Illustrator, Figma'
            },
            {
                'user_id': created_users[2].id,
                'category_id': writing_category.id if writing_category else 3,
                'title': 'SEO Content Writing Services',
                'description': 'High-quality SEO-optimized content for your website or blog',
                'price': 50.00,
                'delivery_time': '2 days',
                'tags': 'SEO, Content Writing, Copywriting, Blog'
            }
        ]
        
        for service_data in sample_services:
            service = Service(**service_data)
            db.session.add(service)
        
        db.session.commit()
        db.session.commit()
        print(f"[OK] Seeded {len(sample_services)} sample services")


if __name__ == '__main__':
    """
    Run this script directly to initialize database
    """
    from app import create_app
    
    app = create_app()
    
    with app.app_context():
        # Create all tables
        db.create_all()
        print("[OK] Database tables created")
        
        # Create admin
        create_default_admin(app)
        
        # Seed categories
        seed_categories()
        
        # Seed sample data
        seed_sample_data()
        
        print("\n[OK] Database initialization complete!")
        print(f"Admin login: {app.config['ADMIN_EMAIL']} / {app.config['ADMIN_PASSWORD']}")
