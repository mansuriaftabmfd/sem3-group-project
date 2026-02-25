"""
Flask Routes (Controllers) for SkillVerse Application

This module contains all route handlers organized into blueprints.
Demonstrates MVC Pattern: Routes act as Controllers

Blueprints:
- main_bp: Main pages (home, about, etc.)
- auth_bp: Authentication (login, register, logout)
- service_bp: Service operations (create, view, edit, delete)
- user_bp: User profile and dashboard
- admin_bp: Admin panel
- api_bp: JSON API endpoints

Author: SkillVerse Team
Purpose: Handle HTTP requests and responses
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from datetime import datetime, timezone, timedelta
from flask_login import login_user, logout_user, login_required, current_user
from functools import wraps
from models import (db, User, Service, Category, Review, Order, Favorite, 
                   Notification, Message, ProjectShowcase, AvailabilitySlot, 
                   Booking, Testimonial, ContactMessage, Certificate, Transaction)
from managers import (service_manager, user_manager, search_engine, 
                     review_system, order_manager, category_manager, notification_manager, chat_manager, availability_manager)
from certificate_generator import generate_certificate, generate_cert_id

from werkzeug.utils import secure_filename
import os
from flask import current_app
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64
from sqlalchemy import func
import numpy as np
import textwrap

def save_uploaded_file(file_storage, folder='images'):
    """
    Save uploaded file to static folder
    """
    if not file_storage:
        return None

    # Local storage for all uploads
    filename = secure_filename(file_storage.filename)
    if not filename:
        return None
        
    # Generate unique filename
    import uuid
    name, ext = os.path.splitext(filename)
    unique_filename = f"{name}_{uuid.uuid4().hex[:8]}{ext}"
    
    # Ensure directory exists
    upload_path = os.path.join(current_app.static_folder, folder)
    os.makedirs(upload_path, exist_ok=True)
    
    # Save file
    file_storage.seek(0)
    file_storage.save(os.path.join(upload_path, unique_filename))
    return unique_filename


# Create blueprints
main_bp = Blueprint('main', __name__)
auth_bp = Blueprint('auth', __name__)
service_bp = Blueprint('service', __name__)
user_bp = Blueprint('user', __name__)
admin_bp = Blueprint('admin', __name__)
api_bp = Blueprint('api', __name__)
availability_bp = Blueprint('availability', __name__)


# ============================================================================
# DECORATORS
# ============================================================================

def admin_required(f):
    """
    Decorator to require admin privileges
    
    OOP Concept: DECORATOR PATTERN
    - Wraps route functions to add authentication check
    - Reusable across multiple routes
    
    Args:
        f: Function to wrap
        
    Returns:
        Wrapped function
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('You need admin privileges to access this page.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function


def provider_required(f):
    """
    Decorator to require non-admin user (unified user model)
    
    All users can sell services except admin.
    Admin users are NOT allowed - this is only for regular users.
    
    Args:
        f: Function to wrap
        
    Returns:
        Wrapped function
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'info')
            return redirect(url_for('auth.login'))
        if current_user.user_type == 'admin':
            flash('Admin accounts cannot sell or manage services.', 'warning')
            return redirect(url_for('admin.dashboard'))
        # Unified user model: all non-admin users can sell services
        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# MAIN ROUTES
# ============================================================================

@main_bp.route('/')
def index():
    """
    Landing page route
    
    Displays:
    - Hero section
    - Categories
    - Featured services
    - How it works
    - Testimonials
    - CTA
    
    Returns:
        Rendered template
    """
    # Get featured services using ServiceManager
    featured_services = service_manager.get_featured_services(limit=4)
    
    # Get all categories
    categories = category_manager.get_all_categories()
    
    # Get category stats
    category_stats = category_manager.get_category_stats()
    
    # =========================================================================
    # SATISFACTION RATE - Real-world weighted calculation
    # Combines 3 signals: Service Reviews + Testimonials + Order Completions
    # Each signal is weighted, and only signals with data contribute
    # =========================================================================
    
    satisfaction_components = []
    
    # Signal 1: Service Review Satisfaction (weight: 40%)
    # Reviews with 4-5 stars are considered "satisfied"
    total_reviews = Review.query.count()
    if total_reviews > 0:
        positive_reviews = Review.query.filter(Review.rating >= 4).count()
        review_satisfaction = (positive_reviews / total_reviews) * 100
        satisfaction_components.append({'score': review_satisfaction, 'weight': 40})
    
    # Signal 2: Testimonial Satisfaction (weight: 30%)
    # Testimonials with 4-5 stars are considered "satisfied"
    total_testimonials = Testimonial.query.filter_by(is_active=True).count()
    if total_testimonials > 0:
        positive_testimonials = Testimonial.query.filter(
            Testimonial.is_active == True,
            Testimonial.rating >= 4
        ).count()
        testimonial_satisfaction = (positive_testimonials / total_testimonials) * 100
        satisfaction_components.append({'score': testimonial_satisfaction, 'weight': 30})
    
    # Signal 3: Order Completion Rate (weight: 30%)
    # Completed orders vs total resolved orders (completed + cancelled)
    completed_orders = Order.query.filter_by(status='completed').count()
    cancelled_orders = Order.query.filter_by(status='cancelled').count()
    resolved_orders = completed_orders + cancelled_orders
    if resolved_orders > 0:
        completion_rate = (completed_orders / resolved_orders) * 100
        satisfaction_components.append({'score': completion_rate, 'weight': 30})
    
    # Calculate weighted average (only from signals that have data)
    if satisfaction_components:
        total_weight = sum(c['weight'] for c in satisfaction_components)
        weighted_sum = sum(c['score'] * c['weight'] for c in satisfaction_components)
        satisfaction_rate = round(weighted_sum / total_weight)
    else:
        satisfaction_rate = 0
    
    stats_data = {
        'total_users': User.query.count(),
        'total_services': Service.query.filter_by(is_active=True, is_approved=True).count(),
        'total_reviews': total_reviews,
        'satisfaction_rate': satisfaction_rate
    }
    
    return render_template('index.html',
                         featured_services=featured_services,
                         categories=categories,
                         category_stats=category_stats,
                         stats_data=stats_data,
                         testimonials=Testimonial.query.filter_by(is_active=True).order_by(Testimonial.created_at.desc()).all())


@main_bp.route('/testimonials/add', methods=['POST'])
@login_required
def add_testimonial():
    """Handle testimonial submission from modal"""
    content = request.form.get('content')
    rating = request.form.get('rating', type=int, default=5)
    role = request.form.get('role')
    
    if content:
        # Create new testimonial
        t = Testimonial(
            user_id=current_user.id,
            content=content,
            role=role,
            rating=rating,
            is_active=True
        )
        db.session.add(t)
        db.session.commit()
        flash('Thank you for your review!', 'success')
    else:
        flash('Review content cannot be empty.', 'error')
        
    return redirect(url_for('main.index', _anchor='testimonials'))



@main_bp.route('/about')
def about():
    """About page"""
    # Get stats for about page
    stats_data = {
        'total_users': User.query.count(),
        'total_services': Service.query.filter_by(is_active=True).count(),
        'total_reviews': Review.query.count()
    }
    return render_template('about.html', stats_data=stats_data)


@main_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    """Contact page"""
    if request.method == 'POST':
        name = request.form.get('firstName') + ' ' + request.form.get('lastName')
        email = request.form.get('email')
        phone = request.form.get('phone')
        subject = request.form.get('subject')
        message = request.form.get('message')
        
        if not name or not email or not subject or not message:
            flash('Please fill in all required fields.', 'danger')
        else:
            try:
                new_message = ContactMessage(
                    name=name,
                    email=email,
                    phone=phone,
                    subject=subject,
                    message=message
                )
                db.session.add(new_message)
                db.session.commit()
                flash('Your message has been sent successfully!', 'success')
                return redirect(url_for('main.contact'))
            except Exception as e:
                db.session.rollback()
                flash('An error occurred while sending your message. Please try again.', 'danger')
                print(f"Error sending message: {e}")
                
    return render_template('contact.html')


@main_bp.route('/terms')
def terms():
    """Terms of Service page"""
    return render_template('legal/terms.html')


@main_bp.route('/privacy')
def privacy():
    """Privacy Policy page"""
    return render_template('legal/privacy.html')


# ============================================================================
# CERTIFICATE VERIFICATION ROUTES (public — no login required)
# ============================================================================


@main_bp.route('/verify')
def verify_certificate_page():
    """Public certificate verification page"""
    return render_template('verify_certificate.html', cert_id=None)


@main_bp.route('/verify/<cert_id>')
def verify_certificate_prefilled(cert_id):
    """Verification page with cert ID pre-filled and auto-verified.
    Shareable links: /verify/CERT-A1B2C3
    """
    return render_template('verify_certificate.html', cert_id=cert_id)


@main_bp.route('/verify/api/<cert_id>')
def verify_certificate_api(cert_id):
    """JSON API called by the verify page's JS fetch().
    Returns certificate details if valid, or {'valid': False} if not found.
    """
    cert = Certificate.query.filter_by(cert_id=cert_id.upper().strip()).first()

    if not cert:
        return jsonify({'valid': False})

    student = User.query.get(cert.student_id)
    provider = User.query.get(cert.provider_id)

    student_name = (student.full_name or student.username) if student else 'Unknown'
    provider_name = (provider.full_name or provider.username) if provider else 'Unknown'

    return jsonify({
        'valid': True,
        'cert_id': cert.cert_id,
        'student_name': student_name,
        'skill_name': cert.skill_name,
        'provider_name': provider_name,
        'issued_at': cert.issued_at.strftime('%B %d, %Y'),
    })




# ============================================================================
# AUTHENTICATION ROUTES
# ============================================================================

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    User login route
    
    GET: Display login form
    POST: Process login credentials
    
    Returns:
        Rendered template or redirect
    """
    # Redirect if already logged in
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = request.form.get('remember', False)
        
        # Authenticate user using UserManager
        user = user_manager.authenticate(email, password)
        
        if user:
            # Check if account is active
            if not user.is_active:
                flash('YOU ARE DEACTIVATED BY ADMIN', 'danger')
                return redirect(url_for('auth.login'))
            
            # Log in user
            login_user(user, remember=remember)
            flash(f'Welcome, {user.full_name or user.username}!', 'success')
            
            # Redirect to next page or dashboard
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            
            # Redirect based on user type
            # All users (Admin, Provider, Client) go to Home Page after login
            return redirect(url_for('main.index'))
        else:
            flash('Invalid email or password. Please try again.', 'danger')
    
    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    User registration route
    
    GET: Display registration form
    POST: Create new user account
    
    Returns:
        Rendered template or redirect
    """
    # Redirect if already logged in
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        # Get form data
        data = {
            'username': request.form.get('username'),
            'email': request.form.get('email'),
            'password': request.form.get('password'),
            'user_type': request.form.get('user_type', 'client'),
            'full_name': request.form.get('full_name', '')
        }
        
        # Validate password confirmation
        password_confirm = request.form.get('password_confirm')
        if data['password'] != password_confirm:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register.html')
        
        # Create user using UserManager
        user, error = user_manager.create_user(data)
        
        if user:
            # Send welcome email
            from email_utils import send_welcome_email
            send_welcome_email(user)
            
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash(error, 'danger')
            return render_template('auth/register.html')
    
    return render_template('auth/register.html')



@auth_bp.route('/login/google')
def google_login():
    """Initiate Google OAuth login"""
    from flask import session
    from extensions import oauth
    
    # Save user_type and source in session for use after OAuth callback
    session['google_user_type'] = request.args.get('user_type', 'client')
    session['google_source'] = request.args.get('source', 'login')  # 'signup' or 'login'
    
    redirect_uri = url_for('auth.google_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route('/login/google/callback')
def google_callback():
    """Handle Google OAuth callback"""
    from flask import session
    from extensions import oauth
    from werkzeug.security import generate_password_hash
    import os
    from datetime import timedelta
    
    try:
        token = oauth.google.authorize_access_token()
        user_info = oauth.google.parse_id_token(token, nonce=None)
        
        # Retrieve user_type and source from session
        google_user_type = session.pop('google_user_type', 'client')
        google_source = session.pop('google_source', 'login')
        
        # Validate user_type
        if google_user_type not in ['client', 'provider']:
            google_user_type = 'client'
        
        # Check if user exists
        user = User.query.filter_by(email=user_info['email']).first()
        
        if user and not user.is_active:
            flash('YOU ARE DEACTIVATED BY ADMIN', 'danger')
            return redirect(url_for('auth.login'))
        
        if not user:
            # User does NOT exist
            if google_source == 'login':
                # Coming from Login page - don't create account, ask to sign up first
                flash('No account found with this Google email. Please sign up first.', 'warning')
                return redirect(url_for('auth.register'))
            
            # Coming from Sign Up page - create new user with selected user_type
            username = user_info['email'].split('@')[0]
            # Ensure unique username
            base_username = username
            counter = 1
            while User.query.filter_by(username=username).first():
                username = f"{base_username}{counter}"
                counter += 1
                
            user = User(
                username=username,
                email=user_info['email'],
                full_name=user_info.get('name', username),
                user_type=google_user_type,  # Use the selected user type from signup
                password_hash=generate_password_hash(os.urandom(24).hex()),
                is_active=True,
                is_verified=True  # Google verified
            )
            db.session.add(user)
            db.session.commit()
            
            # Send welcome email
            from email_utils import send_welcome_email
            send_welcome_email(user)
            
            role_label = 'service provider' if google_user_type == 'provider' else 'client'
            flash(f'Account created successfully via Google as a {role_label}!', 'success')
        else:
            # User exists - this is a login (regardless of whether source was signup or login)
            if google_source == 'signup':
                flash(f'An account already exists with this email. Logging you in.', 'info')
        
        # Refresh user from database to ensure proper session
        db.session.refresh(user)
        
        # Log in user
        login_user(user, remember=True)
        flash(f'Welcome, {user.full_name or user.username}!', 'success')
        return redirect(url_for('main.index'))
        
    except Exception as e:
        # Clean up session vars on error
        session.pop('google_user_type', None)
        session.pop('google_source', None)
        flash(f'Google login failed: {str(e)}', 'danger')
        return redirect(url_for('auth.login'))


@auth_bp.route('/logout')
@login_required
def logout():
    """
    User logout route
    
    Returns:
        Redirect to home page
    """
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('main.index'))


# ============================================================================
# SERVICE ROUTES
# ============================================================================

@service_bp.route('/browse')
def browse():
    """
    Browse all services with filters
    
    Query Parameters:
    - q: Search query
    - category: Category ID
    - min_price: Minimum price
    - max_price: Maximum price
    - sort: Sort option (price_asc, price_desc, rating, newest)
    
    Returns:
        Rendered template with services
    """
    # Get query parameters
    query = request.args.get('q', '')
    category_id = request.args.get('category', type=int)
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    sort_by = request.args.get('sort', 'rating')
    
    # Build filters dictionary
    filters = {}
    if category_id:
        filters['category_id'] = category_id
    if min_price:
        filters['min_price'] = min_price
    if max_price:
        filters['max_price'] = max_price
    
    # Search services
    if query or filters:
        services = service_manager.search_services(query, filters)
    else:
        # Get all services (only approved and active)
        services = Service.query.filter_by(is_active=True, is_approved=True).all()
    
    # Sort services
    if sort_by == 'price_asc':
        services.sort(key=lambda s: s.price)
    elif sort_by == 'price_desc':
        services.sort(key=lambda s: s.price, reverse=True)
    elif sort_by == 'rating':
        services.sort(key=lambda s: s.get_average_rating(), reverse=True)
    elif sort_by == 'newest':
        services.sort(key=lambda s: s.created_at, reverse=True)
    
    # Get categories for filter
    categories = category_manager.get_all_categories()
    
    return render_template('services.html',
                         services=services,
                         categories=categories,
                         query=query,
                         selected_category=category_id,
                         sort_by=sort_by)


@service_bp.route('/<int:service_id>')
def detail(service_id):
    """
    Service detail page
    
    Args:
        service_id: Service ID
        
    Returns:
        Rendered template with service details
    """
    service = Service.query.get_or_404(service_id)
    
    # Block unapproved services from public view (allow owner and admin)
    if not service.is_approved:
        if not current_user.is_authenticated:
            flash('This service is not available.', 'warning')
            return redirect(url_for('service.browse'))
        if service.user_id != current_user.id and not current_user.is_admin():
            flash('This service is not available.', 'warning')
            return redirect(url_for('service.browse'))
    
    # Increment view count
    service.increment_views()
    
    # Get reviews
    reviews = review_system.get_service_reviews(service_id, limit=10)
    
    # Get rating distribution
    rating_dist = review_system.calculate_rating_distribution(service_id)
    
    # Get related services (same category, approved only)
    related_services = Service.query.filter(
        Service.category_id == service.category_id,
        Service.id != service_id,
        Service.is_active == True,
        Service.is_approved == True
    ).limit(4).all()
    
    # Check if user has favorited this service
    is_favorited = False
    existing_order = None
    wallet_balance = 0  # Default wallet balance
    
    if current_user.is_authenticated:
        is_favorited = service.is_favorited_by(current_user)
        
        # Get wallet balance for order validation (Unit-9: OOP, Composition)
        from payment_system import WalletManager
        wallet_mgr = WalletManager()
        wallet_balance = wallet_mgr.get_balance(current_user.id)
        
        # Check if user has an ACTIVE order for this service (pending or in_progress)
        # This determines if Chat button should be shown instead of Order Now
        if current_user.id != service.user_id:
            existing_order = Order.query.filter_by(
                service_id=service_id,
                buyer_id=current_user.id
            ).filter(
                Order.status.in_(['pending', 'in_progress'])
            ).order_by(Order.created_at.desc()).first()
    
    return render_template('service_detail.html',
                         service=service,
                         reviews=reviews,
                         rating_dist=rating_dist,
                         related_services=related_services,
                         is_favorited=is_favorited,
                         existing_order=existing_order,
                         wallet_balance=wallet_balance)


@service_bp.route('/create', methods=['GET', 'POST'])
@login_required
@provider_required
def create():
    """
    Create new service (Providers and Admins only)
    
    Clients who signed up with 'Find Services' cannot create services.
    Only users who signed up with 'Offer Services' (providers) can sell skills.
    
    GET: Display service creation form
    POST: Create service
    
    Returns:
        Rendered template or redirect
    """
    if request.method == 'POST':
        
        # Get form data
        data = {
            'title': request.form.get('title'),
            'description': request.form.get('description'),
            'price': float(request.form.get('price', 0)),
            'delivery_time': request.form.get('delivery_time'),
            'category_id': int(request.form.get('category_id')),
            'category_id': int(request.form.get('category_id')),
            'tags': request.form.get('tags', '')
        }
        
        # Handle Image Upload
        # Handle Image Upload (Mandatory)
        if 'image' not in request.files or request.files['image'].filename == '':
            flash('Please upload a service image to continue.', 'danger')
            categories = category_manager.get_all_categories()
            return render_template('service_create.html', categories=categories)
            
        file = request.files['image']
        if file and file.filename != '':
            filename = save_uploaded_file(file)
            if filename:
                data['image_url'] = filename
        
        # Create service using ServiceManager
        service = service_manager.create_service(current_user.id, data)
        
        if service:
            if service.is_approved:
                flash('Service created successfully!', 'success')
            else:
                flash('Service submitted successfully! It will be visible after admin approval.', 'info')
            return redirect(url_for('service.detail', service_id=service.id))
        else:
            flash('Error creating service. Please try again.', 'danger')
    
    # Get categories for form
    categories = category_manager.get_all_categories()
    
    return render_template('service_create.html', categories=categories)


@service_bp.route('/<int:service_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(service_id):
    """
    Edit service (Owner or Admin only)
    
    Args:
        service_id: Service ID
        
    Returns:
        Rendered template or redirect
    """
    service = Service.query.get_or_404(service_id)
    
    # Check ownership
    if service.user_id != current_user.id and not current_user.is_admin():
        flash('You do not have permission to edit this service.', 'danger')
        return redirect(url_for('service.detail', service_id=service_id))
    
    if request.method == 'POST':
        # Update service
        service.title = request.form.get('title')
        service.description = request.form.get('description')
        service.price = float(request.form.get('price', 0))
        service.delivery_time = request.form.get('delivery_time')
        service.category_id = int(request.form.get('category_id'))
        service.tags = request.form.get('tags', '')
        
        # Handle Image Upload
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                filename = save_uploaded_file(file)
                if filename:
                    service.image_url = filename
        
        db.session.commit()
        
        # If the service was previously rejected and the owner edited it, re-submit for approval
        if not current_user.is_admin() and not service.is_approved:
            service.rejection_reason = None  # Clear rejection reason to mark as "pending" again
            db.session.commit()
            
            # Notify admins about re-submission
            admins = User.query.filter_by(user_type='admin').all()
            for admin in admins:
                notification_manager.create_notification(
                    user_id=admin.id,
                    title='Service Re-submitted for Review 🔄',
                    message=f'{current_user.username} updated and re-submitted "{service.title}" for review.',
                    link='/admin/services/pending'
                )
            flash('Service updated and re-submitted for review!', 'info')
        else:
            flash('Service updated successfully!', 'success')
        return redirect(url_for('service.detail', service_id=service_id))
    
    categories = category_manager.get_all_categories()
    return render_template('service_edit.html', service=service, categories=categories)


@service_bp.route('/<int:service_id>/delete', methods=['POST'])
@login_required
def delete(service_id):
    """
    Delete service (Owner or Admin only)
    
    For Admin: Permanently deletes the service from database (including related records)
    For Owner: Soft delete (sets is_active to False)
    
    Args:
        service_id: Service ID
        
    Returns:
        Redirect
    """
    service = Service.query.get_or_404(service_id)
    
    # Check ownership
    if service.user_id != current_user.id and not current_user.is_admin():
        flash('You do not have permission to delete this service.', 'danger')
        return redirect(url_for('service.detail', service_id=service_id))
    
    # Admin: Permanent delete from database
    if current_user.is_admin():
        service_title = service.title
        
        try:
            # Delete related orders and their messages first
            orders = Order.query.filter_by(service_id=service_id).all()
            for order in orders:
                # Delete messages associated with this order
                Message.query.filter_by(order_id=order.id).delete()
                db.session.delete(order)
            
            # Delete related reviews
            Review.query.filter_by(service_id=service_id).delete()
            
            # Delete related favorites
            Favorite.query.filter_by(service_id=service_id).delete()
            
            # Now delete the service
            db.session.delete(service)
            db.session.commit()
            
            flash(f'Service "{service_title}" and all related data permanently deleted.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error deleting service: {str(e)}', 'danger')
        
        return redirect(url_for('admin.services'))
    else:
        # Regular user: Soft delete (set is_active to False)
        service.is_active = False
        db.session.commit()
        flash('Service deleted successfully.', 'success')
        return redirect(url_for('user.dashboard'))


@service_bp.route('/<int:service_id>/review', methods=['POST'])
@login_required
def add_review(service_id):
    """
    Add review to service
    
    Args:
        service_id: Service ID
        
    Returns:
        Redirect
    """
    # Get the service to check ownership
    service = Service.query.get_or_404(service_id)
    
    # VALIDATION: Prevent service owner from reviewing their own service
    if service.user_id == current_user.id:
        flash('You cannot review your own service!', 'danger')
        return redirect(url_for('service.detail', service_id=service_id))
    
    # VALIDATION: Prevent admin from reviewing services
    if current_user.user_type == 'admin':
        flash('Admin accounts cannot submit reviews.', 'warning')
        return redirect(url_for('service.detail', service_id=service_id))
    
    rating = int(request.form.get('rating', 0))
    comment = request.form.get('comment', '')
    
    # Add review using ReviewSystem
    review, error = review_system.add_review(service_id, current_user.id, rating, comment)
    
    if review:
        flash('Review submitted successfully!', 'success')
    else:
        flash(error, 'danger')
    
    return redirect(url_for('service.detail', service_id=service_id))


@service_bp.route('/<int:service_id>/favorite', methods=['POST'])
@login_required
def toggle_favorite(service_id):
    """
    Toggle favorite status for service
    
    Args:
        service_id: Service ID
        
    Returns:
        JSON response
    """
    service = Service.query.get_or_404(service_id)
    
    # Check if already favorited
    favorite = Favorite.query.filter_by(
        user_id=current_user.id,
        service_id=service_id
    ).first()
    
    if favorite:
        # Remove from favorites
        db.session.delete(favorite)
        db.session.commit()
        return jsonify({'status': 'removed', 'message': 'Removed from favorites'})
    else:
        # Add to favorites
        favorite = Favorite(user_id=current_user.id, service_id=service_id)
        db.session.add(favorite)
        db.session.commit()
        return jsonify({'status': 'added', 'message': 'Added to favorites'})


@service_bp.route('/<int:service_id>/order', methods=['POST'])
@login_required
def place_order(service_id):
    """
    Place order for service
    
    WALLET VALIDATION (Unit-8: Exception Handling)
    - Checks if user has sufficient wallet balance before allowing order
    - Deducts amount from wallet upon successful order placement
    
    Args:
        service_id: Service ID
        
    Returns:
        Redirect
    """
    # Import payment system for wallet validation
    from payment_system import WalletManager, PaymentGateway, InsufficientBalanceException
    
    # Block admin from purchasing services
    if current_user.user_type == 'admin':
        flash('Admin accounts cannot purchase services.', 'warning')
        return redirect(url_for('service.detail', service_id=service_id))
    
    # Get service to check price
    service = Service.query.get_or_404(service_id)
    
    # Prevent user from buying their own service
    if service.user_id == current_user.id:
        flash('You cannot purchase your own service!', 'warning')
        return redirect(url_for('service.detail', service_id=service_id))
    
    requirements = request.form.get('requirements', '')
    budget_tier = request.form.get('budget_tier', 'Standard')
    
    # Calculate order price based on budget tier
    base_price = service.price
    if budget_tier == 'Basic':
        order_price = base_price * 0.8  # 20% discount for basic
    elif budget_tier == 'Premium':
        order_price = base_price * 1.5  # 50% extra for premium
    else:
        order_price = base_price  # Standard price
    
    # =====================================================================
    # WALLET BALANCE VALIDATION (Unit-8: Exception Handling, Unit-9: OOP)
    # =====================================================================
    gateway = PaymentGateway()
    wallet_mgr = WalletManager(payment_gateway=gateway)
    
    # Get current wallet balance
    current_balance = wallet_mgr.get_balance(current_user.id)
    
    # Check if user has sufficient balance
    if current_balance < order_price:
        # Insufficient balance - redirect to wallet page
        shortfall = order_price - current_balance
        flash(f'Insufficient wallet balance! You need ₹{int(order_price)} but have only ₹{int(current_balance)}. Please add ₹{int(shortfall)} to your wallet.', 'danger')
        return redirect(url_for('user.wallet'))
    
    # Create order using OrderManager
    order = order_manager.create_order(service_id, current_user.id, requirements, '', budget_tier, None)
    
    if order:
        # =====================================================================
        # DEDUCT AMOUNT FROM WALLET (Unit-6: File Handling, Unit-9: OOP)
        # =====================================================================
        buyer_payment_success = False
        seller_credit_success = False
        buyer_txn_id = None
        
        try:
            # Capture transaction result to get ID
            buyer_txn = wallet_mgr.deduct_money(
                user_id=current_user.id,
                amount=order.total_price,
                description=f'Service Purchase: {service.title} (Order #{order.id})',
                username=current_user.username
            )
            buyer_txn_id = buyer_txn.get('id')
            buyer_payment_success = True
            print(f"[DEBUG] Successfully deducted ₹{order.total_price} from buyer (user_id: {current_user.id}). Txn ID: {buyer_txn_id}")
            
        except InsufficientBalanceException:
            # This shouldn't happen as we checked above, but just in case
            flash('Payment failed due to insufficient balance.', 'danger')
            # Cancel the order
            order.status = 'cancelled'
            db.session.commit()
            return redirect(url_for('service.detail', service_id=service_id))
        except Exception as e:
            print(f"[ERROR] Buyer deduction failed: {str(e)}")
            flash(f'Payment processing error: {str(e)}', 'danger')
            order.status = 'cancelled'
            db.session.commit()
            return redirect(url_for('service.detail', service_id=service_id))
        
        # =====================================================================
        # CREDIT AMOUNT TO SELLER'S WALLET (Unit-6: File Handling, Unit-9: OOP)
        # =====================================================================
        # Platform fee: 10% (SkillVerse keeps 10%, seller gets 90%)
        platform_fee_percent = 0.10
        seller_amount = order.total_price * (1 - platform_fee_percent)
        
        # Get seller username for transaction record
        seller = User.query.get(order.seller_id)
        seller_username = seller.username if seller else f'User #{order.seller_id}'
        
        try:
            print(f"[DEBUG] Attempting to credit seller (user_id: {order.seller_id}) with ₹{seller_amount}")
            wallet_mgr.credit_seller(
                user_id=order.seller_id,
                amount=seller_amount,
                description=f'Payment Received: {service.title} (Order #{order.id}) - After 10% platform fee',
                username=seller_username,
                transaction_id=buyer_txn_id
            )
            seller_credit_success = True
            print(f"[DEBUG] Successfully credited ₹{seller_amount} to seller (user_id: {order.seller_id})")
            
            # =====================================================================
            # CREDIT PLATFORM FEE TO ADMIN'S WALLET
            # =====================================================================
            platform_fee_amount = order.total_price * platform_fee_percent
            admin_user = User.query.filter_by(user_type='admin').first()
            if admin_user:
                print(f"[DEBUG] Attempting to credit admin (user_id: {admin_user.id}) with ₹{platform_fee_amount}")
                wallet_mgr.credit_seller(
                    user_id=admin_user.id,
                    amount=platform_fee_amount,
                    description=f'Platform Fee Received: {service.title} (Order #{order.id})',
                    username=admin_user.username,
                    transaction_id=buyer_txn_id
                )
                print(f"[DEBUG] Successfully credited ₹{platform_fee_amount} to admin (user_id: {admin_user.id})")
            else:
                print(f"[WARNING] No admin user found to credit platform fee.")

        except Exception as e:
            # Log the error but don't cancel the order - the buyer already paid
            # Admin will need to manually credit the seller
            print(f"[ERROR] Failed to credit seller or admin: {str(e)}")
            # Note: In production, you'd want to queue this for retry or alert admin
        
        # Create notification for the provider
        notification_manager.create_notification(
            user_id=order.seller_id,
            title=f'New Order #{order.id} Received',
            message=f'You have a new order #{order.id} for "{order.service.title}" from {current_user.username}. Price: ₹{int(order.total_price)}',
            link=url_for('user.order_detail', order_id=order.id)
        )
        
        # Send emails to both customer and provider
        from email_utils import send_order_placed_emails
        send_order_placed_emails(order)
        
        flash(f'Order placed successfully! ₹{int(order.total_price)} deducted from your wallet.', 'success')
        return redirect(url_for('user.order_detail', order_id=order.id))
    else:
        flash('Error placing order. Please try again.', 'danger')
        return redirect(url_for('service.detail', service_id=service_id))


# ============================================================================
# USER ROUTES
# ============================================================================

@user_bp.route('/dashboard')
@login_required
def dashboard():
    """
    User dashboard
    
    Shows different content based on user type:
    - Provider: Services, orders, earnings
    - Client: Orders, favorites
    - Admin: Redirect to admin panel
    
    Returns:
        Rendered template
    """
    if current_user.is_admin():
        return redirect(url_for('admin.dashboard'))
    
    # Get combined stats for unified dashboard
    stats = user_manager.get_user_stats(current_user.id)
    
    # BUYER DATA
    buyer_orders = order_manager.get_user_orders(current_user.id, as_buyer=True)
    favorites = Favorite.query.filter_by(user_id=current_user.id).all()
    
    # SELLER DATA
    services = current_user.get_services()
    seller_orders = order_manager.get_user_orders(current_user.id, as_buyer=False)
    
    # Combined view - show client dashboard with additional seller stats
    if False:  # Unified model: always show client dashboard
        # Provider dashboard
        services = current_user.get_services()
        orders = order_manager.get_user_orders(current_user.id, as_buyer=False)
        
        # Get today's bookings
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).replace(tzinfo=None)
        today_end = today_start.replace(hour=23, minute=59, second=59)
        
        todays_bookings = Booking.query.join(AvailabilitySlot).filter(
            AvailabilitySlot.provider_id == current_user.id,
            AvailabilitySlot.start_time >= today_start,
            AvailabilitySlot.start_time <= today_end
        ).order_by(AvailabilitySlot.start_time).all()

        # Personal Analytics Graphs - Using Line Chart and Pie Chart (as per PDF)
        plt.style.use('default')

        # Graph 1: Earnings Trend - LINE CHART (plt.plot)
        earnings_data = db.session.query(
            func.date(Order.completed_at), func.sum(Order.total_price)
        ).filter(
            Order.seller_id == current_user.id,
            Order.status == 'completed',
            Order.completed_at != None
        ).group_by(func.date(Order.completed_at)).order_by(func.date(Order.completed_at)).all()

        dates_earn = []
        values_earn = []
        if earnings_data:
            dates_earn = [str(r[0])[-5:] for r in earnings_data]  # Show MM-DD format
            values_earn = [float(r[1]) for r in earnings_data]
        else:
            dates_earn = ['No Data']
            values_earn = [0]

        # LINE CHART - Simple as per PDF syntax: plt.plot(x, y)
        fig1 = plt.figure(figsize=(8, 4))
        plt.plot(dates_earn, values_earn, color='green', marker='o', linestyle='-', linewidth=2)
        plt.title('My Earnings Trend', fontsize=12, fontweight='bold')
        plt.xlabel('Date')
        plt.ylabel('Earnings (₹)')
        plt.grid(True)
        plt.xticks(rotation=45)
        plt.tight_layout()

        img1 = io.BytesIO()
        fig1.savefig(img1, format='png', dpi=100, bbox_inches='tight', facecolor='white')
        img1.seek(0)
        earnings_graph = base64.b64encode(img1.getvalue()).decode()
        plt.close(fig1)

        # Graph 2: Service Views Distribution - PIE CHART (plt.pie)
        my_services = Service.query.filter_by(user_id=current_user.id).all()
        top_services = sorted(my_services, key=lambda s: s.view_count, reverse=True)[:5]

        if top_services and sum(s.view_count for s in top_services) > 0:
            svc_names = [s.title[:15] + '...' if len(s.title) > 15 else s.title for s in top_services]
            svc_views = [s.view_count for s in top_services]
        else:
            svc_names = ['No Views Yet']
            svc_views = [1]

        # PIE CHART - Simple as per PDF syntax: plt.pie(sizes, labels=labels)
        fig2 = plt.figure(figsize=(8, 5))
        colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#C9CBCF', '#7CFC00', '#FF1493', '#00CED1']
        plt.pie(svc_views, labels=svc_names, autopct='%1.1f%%', colors=colors[:len(svc_views)], startangle=90)
        plt.title('Service Views Distribution', fontsize=12, fontweight='bold')
        plt.axis('equal')
        plt.tight_layout()

        img2 = io.BytesIO()
        fig2.savefig(img2, format='png', dpi=100, bbox_inches='tight', facecolor='white')
        img2.seek(0)
        services_graph = base64.b64encode(img2.getvalue()).decode()
        plt.close(fig2)

        return render_template('user/provider_dashboard.html',
                             services=services,
                             orders=orders,
                             stats=stats,
                             todays_bookings=todays_bookings,
                             earnings_graph=earnings_graph,
                             services_graph=services_graph)
    else:
        # Client dashboard
        orders = order_manager.get_user_orders(current_user.id, as_buyer=True)
        favorites = Favorite.query.filter_by(user_id=current_user.id).all()
        recommendations = service_manager.get_recommendations(current_user, limit=6)
        
        # Calculate session stats
        sessions_to_schedule = 0
        upcoming_sessions = 0
        
        for order in orders:
            # Check if order has a booking
            booking = Booking.query.filter_by(order_id=order.id).first()
            if not booking and order.status not in ['cancelled', 'completed']:
                sessions_to_schedule += 1
            elif booking and booking.slot.start_time > datetime.now(timezone.utc).replace(tzinfo=None):
                upcoming_sessions += 1
        
        # --- Client Analytics Graphs - Using Line Chart and Pie Chart (as per PDF) ---
        plt.style.use('default') 

        # Graph 1: Spending Trend - LINE CHART (plt.plot)
        spending_data = db.session.query(
            func.date(Order.created_at), func.sum(Order.total_price)
        ).filter(
            Order.buyer_id == current_user.id
        ).group_by(func.date(Order.created_at)).order_by(func.date(Order.created_at)).all()

        dates_spend = []
        values_spend = []
        if spending_data:
            dates_spend = [str(r[0])[-5:] for r in spending_data]  # Show MM-DD format
            values_spend = [float(r[1]) for r in spending_data]
        else:
            dates_spend = ['No Data']
            values_spend = [0]

        # LINE CHART - Simple as per PDF syntax: plt.plot(x, y)
        fig3 = plt.figure(figsize=(8, 4))
        plt.plot(dates_spend, values_spend, color='blue', marker='o', linestyle='-', linewidth=2)
        plt.title('My Spending Trend', fontsize=12, fontweight='bold')
        plt.xlabel('Date')
        plt.ylabel('Amount (₹)')
        plt.grid(True)
        plt.xticks(rotation=45)
        plt.tight_layout()

        img3 = io.BytesIO()
        fig3.savefig(img3, format='png', dpi=100, bbox_inches='tight', facecolor='white')
        img3.seek(0)
        spending_graph = base64.b64encode(img3.getvalue()).decode()
        plt.close(fig3)


        # Graph 2: Category Distribution - PIE CHART (plt.pie)
        cat_data = db.session.query(
            Category.name, func.count(Order.id)
        ).select_from(Order).join(Service).join(Category).filter(
            Order.buyer_id == current_user.id
        ).group_by(Category.name).all()

        if cat_data:
            labels = [r[0] for r in cat_data]
            sizes = [r[1] for r in cat_data]
        else:
            labels = ['No Orders']
            sizes = [1]

        # PIE CHART - Simple as per PDF syntax: plt.pie(sizes, labels=labels)
        fig4 = plt.figure(figsize=(8, 5))
        colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#C9CBCF', '#7CFC00', '#FF1493', '#00CED1']
        plt.pie(sizes, labels=labels, autopct='%1.1f%%', colors=colors[:len(sizes)], startangle=90)
        plt.title('Orders by Category', fontsize=12, fontweight='bold')
        plt.axis('equal')
        plt.tight_layout()
        
        img4 = io.BytesIO()
        fig4.savefig(img4, format='png', dpi=100, bbox_inches='tight', facecolor='white')
        img4.seek(0)
        distribution_graph = base64.b64encode(img4.getvalue()).decode()
        plt.close(fig4)
        
        return render_template('user/client_dashboard.html',
                             stats=stats,
                             orders=orders,
                             favorites=favorites,
                             recommendations=recommendations,
                             spending_graph=spending_graph,
                             distribution_graph=distribution_graph)


@user_bp.route('/dashboard/buyer')
@login_required
def buyer_dashboard():
    """Buyer-only dashboard showing purchase activities"""
    if current_user.is_admin():
        return redirect(url_for('admin.dashboard'))
    
    stats = user_manager.get_user_stats(current_user.id)
    orders = order_manager.get_user_orders(current_user.id, as_buyer=True)
    favorites = Favorite.query.filter_by(user_id=current_user.id).all()
    recommendations = service_manager.get_recommendations(current_user, limit=6)
    
    # Calculate session stats
    sessions_to_schedule = 0
    upcoming_sessions = 0
    
    for order in orders:
        booking = Booking.query.filter_by(order_id=order.id).first()
        if not booking and order.status not in ['cancelled', 'completed']:
            sessions_to_schedule += 1
        elif booking and booking.slot.start_time > datetime.now(timezone.utc).replace(tzinfo=None):
            upcoming_sessions += 1

    # Buyer Analytics Graphs
    plt.style.use('default')

    # Spending Trend
    spending_data = db.session.query(
        func.date(Order.created_at), func.sum(Order.total_price)
    ).filter(
        Order.buyer_id == current_user.id
    ).group_by(func.date(Order.created_at)).order_by(func.date(Order.created_at)).all()

    dates_spend = []
    values_spend = []
    if spending_data:
        dates_spend = [str(r[0])[-5:] for r in spending_data]
        values_spend = [float(r[1]) for r in spending_data]
    else:
        dates_spend = ['No Data']
        values_spend = [0]

    fig3 = plt.figure(figsize=(8, 4))
    plt.plot(dates_spend, values_spend, color='blue', marker='o', linestyle='-', linewidth=2)
    plt.title('My Spending Trend', fontsize=12, fontweight='bold')
    plt.xlabel('Date')
    plt.ylabel('Amount (₹)')
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()

    img3 = io.BytesIO()
    fig3.savefig(img3, format='png', dpi=100, bbox_inches='tight', facecolor='white')
    img3.seek(0)
    spending_graph = base64.b64encode(img3.getvalue()).decode()
    plt.close(fig3)

    # Category Distribution
    cat_data = db.session.query(
        Category.name, func.count(Order.id)
    ).select_from(Order).join(Service).join(Category).filter(
        Order.buyer_id == current_user.id
    ).group_by(Category.name).all()

    if cat_data:
        labels = [r[0] for r in cat_data]
        sizes = [r[1] for r in cat_data]
    else:
        labels = ['No Orders']
        sizes = [1]

    fig4 = plt.figure(figsize=(8, 5))
    colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#C9CBCF', '#7CFC00', '#FF1493', '#00CED1']
    plt.pie(sizes, labels=labels, autopct='%1.1f%%', colors=colors[:len(sizes)], startangle=90)
    plt.title('Orders by Category', fontsize=12, fontweight='bold')
    plt.axis('equal')
    plt.tight_layout()
    
    img4 = io.BytesIO()
    fig4.savefig(img4, format='png', dpi=100, bbox_inches='tight', facecolor='white')
    img4.seek(0)
    distribution_graph = base64.b64encode(img4.getvalue()).decode()
    plt.close(fig4)
    
    return render_template('user/client_dashboard.html',
                         stats=stats,
                         orders=orders,
                         favorites=favorites,
                         recommendations=recommendations,
                         spending_graph=spending_graph,
                         distribution_graph=distribution_graph)


@user_bp.route('/dashboard/seller')
@login_required
def seller_dashboard():
    """Seller-only dashboard showing service and earnings"""
    if current_user.is_admin():
        return redirect(url_for('admin.dashboard'))
    
    stats = user_manager.get_user_stats(current_user.id)
    services = current_user.get_services()
    orders = order_manager.get_user_orders(current_user.id, as_buyer=False)
    
    # Get today's bookings
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).replace(tzinfo=None)
    today_end = today_start.replace(hour=23, minute=59, second=59)
    
    todays_bookings = Booking.query.join(AvailabilitySlot).filter(
        AvailabilitySlot.provider_id == current_user.id,
        AvailabilitySlot.start_time >= today_start,
        AvailabilitySlot.start_time <= today_end
    ).order_by(AvailabilitySlot.start_time).all()

    # Seller Analytics Graphs
    plt.style.use('default')

    # Earnings Trend
    earnings_data = db.session.query(
        func.date(Order.completed_at), func.sum(Order.total_price)
    ).filter(
        Order.seller_id == current_user.id,
        Order.status == 'completed',
        Order.completed_at != None
    ).group_by(func.date(Order.completed_at)).order_by(func.date(Order.completed_at)).all()

    dates_earn = []
    values_earn = []
    if earnings_data:
        dates_earn = [str(r[0])[-5:] for r in earnings_data]
        values_earn = [float(r[1]) for r in earnings_data]
    else:
        dates_earn = ['No Data']
        values_earn = [0]

    fig1 = plt.figure(figsize=(8, 4))
    plt.plot(dates_earn, values_earn, color='green', marker='o', linestyle='-', linewidth=2)
    plt.title('My Earnings Trend', fontsize=12, fontweight='bold')
    plt.xlabel('Date')
    plt.ylabel('Earnings (₹)')
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()

    img1 = io.BytesIO()
    fig1.savefig(img1, format='png', dpi=100, bbox_inches='tight', facecolor='white')
    img1.seek(0)
    earnings_graph = base64.b64encode(img1.getvalue()).decode()
    plt.close(fig1)

    # Service Views Distribution
    my_services = Service.query.filter_by(user_id=current_user.id).all()
    top_services = sorted(my_services, key=lambda s: s.view_count, reverse=True)[:5]

    if top_services and sum(s.view_count for s in top_services) > 0:
        svc_names = [s.title[:15] + '...' if len(s.title) > 15 else s.title for s in top_services]
        svc_views = [s.view_count for s in top_services]
    else:
        svc_names = ['No Views Yet']
        svc_views = [1]

    fig2 = plt.figure(figsize=(8, 5))
    colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#C9CBCF', '#7CFC00', '#FF1493', '#00CED1']
    plt.pie(svc_views, labels=svc_names, autopct='%1.1f%%', colors=colors[:len(svc_views)], startangle=90)
    plt.title('Service Views Distribution', fontsize=12, fontweight='bold')
    plt.axis('equal')
    plt.tight_layout()

    img2 = io.BytesIO()
    fig2.savefig(img2, format='png', dpi=100, bbox_inches='tight', facecolor='white')
    img2.seek(0)
    services_graph = base64.b64encode(img2.getvalue()).decode()
    plt.close(fig2)

    return render_template('user/provider_dashboard.html',
                         services=services,
                         orders=orders,
                         stats=stats,
                         todays_bookings=todays_bookings,
                         earnings_graph=earnings_graph,
                         services_graph=services_graph)


@user_bp.route('/notifications/mark-read/<int:notification_id>', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Mark notification as read"""
    notification_manager.mark_as_read(notification_id)
    return jsonify({'status': 'success'})


@user_bp.route('/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    """Mark all notifications as read"""
    notification_manager.mark_all_read(current_user.id)
    return jsonify({'status': 'success'})


@user_bp.route('/notifications/delete/<int:notification_id>', methods=['POST'])
@login_required
def delete_notification(notification_id):
    """Delete a notification"""
    notification_manager.delete_notification(notification_id)
    return jsonify({'status': 'success'})


@user_bp.route('/notifications/clear-all', methods=['POST'])
@login_required
def clear_all_notifications():
    """Clear all notifications"""
    notification_manager.clear_all(current_user.id)
    return jsonify({'status': 'success'})


@user_bp.route('/notifications')
@login_required
def notifications():
    """View all notifications page"""
    # Get all notifications for the current user (not just recent 5)
    all_notifications = current_user.notifications.order_by(db.text('created_at desc')).all()
    
    # Mark all as read when viewing the page
    notification_manager.mark_all_read(current_user.id)
    
    return render_template('user/notifications.html', notifications=all_notifications)



@user_bp.route('/chats')
@login_required
def chats():
    """User chats page"""
    active_chats = chat_manager.get_active_chats(current_user.id)
    return render_template('user/chats.html', chats=active_chats)


@user_bp.route('/chats/delete/<int:order_id>', methods=['POST'])
@login_required
def delete_chat(order_id):
    """Hide a chat from the user's chat list"""
    chat_manager.hide_chat(order_id, current_user.id)
    return jsonify({'status': 'success'})


@user_bp.route('/order/<int:order_id>/chat/delete', methods=['POST'])
@login_required
def delete_order_chat(order_id):
    """Delete all messages in the order chat (Provider only)"""
    success, error = chat_manager.delete_chat(order_id, current_user.id)
    if success:
        flash('Chat history deleted successfully.', 'success')
    else:
        flash(f'Error: {error}', 'danger')
    return redirect(url_for('user.order_detail', order_id=order_id))



@user_bp.route('/chats/clear-all', methods=['POST'])
@login_required
def clear_all_chats():
    """Clear all chats from the user's chat list"""
    chat_manager.clear_all_chats(current_user.id)
    return jsonify({'status': 'success'})



@user_bp.route('/order/<int:order_id>')
@login_required
def order_detail(order_id):
    """Order detail with chat"""
    order = Order.query.get_or_404(order_id)
    
    # Check permission
    if current_user.id not in [order.buyer_id, order.seller_id] and not current_user.is_admin():
        flash('Unauthorized access', 'danger')
        return redirect(url_for('user.dashboard'))
        
    messages = chat_manager.get_messages(order_id, current_user.id)
    
    # Check for existing booking for this order
    booking = Booking.query.filter_by(order_id=order_id).first()
    
    return render_template('user/order_detail.html', order=order, messages=messages, booking=booking)

@user_bp.route('/order/<int:order_id>/action/<action>', methods=['POST'])
@login_required
def order_action(order_id, action):
    """Handle order actions (accept/complete)"""
    order = Order.query.get_or_404(order_id)
    
    if current_user.id != order.seller_id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('user.order_detail', order_id=order_id))
        
    if action == 'accept':
        # Validation: Check if booking is confirmed before accepting order
        # Provider must approve the slot in Availability Manager first
        booking = Booking.query.filter_by(order_id=order.id).first()
        if booking and booking.status != 'confirmed':
            flash('Cannot accept order yet. Please approve the booking request in "Manage Availability" first.', 'warning')
            return redirect(url_for('user.order_detail', order_id=order_id))

        if order_manager.accept_order(order_id):
            flash('Order accepted! You can now chat with the client.', 'success')
            notification_manager.create_notification(order.buyer_id, f"Order #{order.id} Accepted", f"Your order for {order.service.title} has been accepted.", url_for('user.order_detail', order_id=order.id))
            
            # Send acceptance emails
            from email_utils import send_order_accepted_emails
            send_order_accepted_emails(order)
            
    elif action == 'complete':
        if order_manager.complete_order(order_id):
            # ── 1. Update order status and basic notification ──────────────────
            flash('Order marked as complete!', 'success')
            notification_manager.create_notification(order.buyer_id, f"Order #{order.id} Completed", f"Your order for {order.service.title} is ready!", url_for('user.order_detail', order_id=order.id))
            
            # Send completion emails
            from email_utils import send_order_completed_emails
            send_order_completed_emails(order)

            # ── 2. Generate certificate ───────────────────────────────────────────
            try:
                print(f"[Certificate] Starting certificate generation for order {order.id}")
                student  = User.query.get(order.buyer_id)
                provider = User.query.get(order.seller_id)
                service  = order.service
                
                print(f"[Certificate] Student: {student.username}, Provider: {provider.username}, Service: {service.title}")

                cert_id  = generate_cert_id()
                print(f"[Certificate] Generated cert_id: {cert_id}")

                # Determine paths
                print(f"[Certificate] Calling generate_certificate function...")
                pdf_path = generate_certificate(
                    student_name    = student.full_name or student.username,
                    skill_name      = service.title,
                    provider_name   = provider.full_name or provider.username,
                    order_id        = order.id,
                    cert_id         = cert_id
                )
                print(f"[Certificate] PDF generated at: {pdf_path}")

                # ── 3. Save cert record to DB ─────────────────────────────────────
                cert = Certificate(
                    cert_id      = cert_id,
                    order_id     = order.id,
                    student_id   = order.buyer_id,
                    provider_id  = order.seller_id,
                    skill_name   = service.title,
                    pdf_filename = os.path.basename(pdf_path),
                )
                db.session.add(cert)
                
                # ── 4. Notify the buyer about the certificate ─────────────────────
                notification = Notification(
                    user_id = order.buyer_id,
                    title   = '🎓 Your Certificate is Ready!',
                    message = (f'Congratulations! You have completed "{service.title}". '
                               f'Your certificate ({cert_id}) is ready to download.'),
                    link    = url_for('user.download_certificate', cert_id=cert_id),
                )
                db.session.add(notification)
                db.session.commit()

                # ── 5. (Optional) send email with cert link ──────────────────────
                try:
                    _send_certificate_email(student, cert, pdf_path)
                except Exception as mail_err:
                    print(f"[Certificate] Email failed (non-fatal): {mail_err}")

                flash(f'Certificate {cert_id} has been issued successfully.', 'success')

            except Exception as e:
                import traceback
                print(f"[Certificate] Generation failed: {e}")
                print(f"[Certificate] Full traceback:")
                traceback.print_exc()
                flash(f'Order marked complete, but certificate generation failed: {str(e)}', 'warning')


    elif action == 'reject':
        # Only allow rejecting pending orders
        if order.status != 'pending':
            flash('Only pending orders can be rejected.', 'warning')
            return redirect(url_for('user.order_detail', order_id=order_id))

        # Get rejection reason from form
        reason = request.form.get('reason', '').strip()
        
        # Validate that reason is provided
        if not reason:
            flash('Rejection reason is required. Please provide a reason for rejecting this order.', 'danger')
            return redirect(url_for('user.order_detail', order_id=order_id))

        # Save rejection reason and update order status to cancelled
        order.rejection_reason = reason
        order.update_status('cancelled')
        db.session.commit()

        # Refund the buyer's wallet and reverse the seller's credit
        try:
            from payment_system import WalletManager, PaymentGateway
            gateway = PaymentGateway()
            wallet_mgr = WalletManager(payment_gateway=gateway)

            # 1. Refund full amount back to buyer
            wallet_mgr.add_money(
                user_id=order.buyer_id,
                amount=order.total_price,
                payment_method='refund',
                description=f'Refund for rejected Order #{order.id} - {order.service.title}'
            )

            # 2. Reverse the 90% that was credited to the seller at order placement
            platform_fee_percent = 0.10
            seller_amount = order.total_price * (1 - platform_fee_percent)
            seller = User.query.get(order.seller_id)
            seller_balance = float(seller.wallet_balance or 0.0) if seller else 0.0

            if seller and seller_balance >= seller_amount:
                wallet_mgr.deduct_money(
                    user_id=order.seller_id,
                    amount=seller_amount,
                    description=f'Reversal for rejected Order #{order.id} - {order.service.title}',
                    username=seller.username
                )
                print(f"[Order Reject] Reversed ₹{seller_amount:.0f} from seller (user_id: {order.seller_id})")
            else:
                # Seller has insufficient balance (e.g. already withdrawn) — log for admin
                print(f"[Order Reject] WARNING: Could not reverse ₹{seller_amount:.0f} from seller "
                      f"(user_id: {order.seller_id}). Current balance: ₹{seller_balance:.0f}. Manual review needed.")

            # 3. Reverse the 10% platform fee from admin wallet
            platform_fee_amount = order.total_price * platform_fee_percent
            admin_user = User.query.filter_by(user_type='admin').first()
            if admin_user:
                admin_balance = float(admin_user.wallet_balance or 0.0)
                if admin_balance >= platform_fee_amount:
                    wallet_mgr.deduct_money(
                        user_id=admin_user.id,
                        amount=platform_fee_amount,
                        description=f'Platform Fee Reversal for rejected Order #{order.id} - {order.service.title}',
                        username=admin_user.username
                    )
                    print(f"[Order Reject] Reversed ₹{platform_fee_amount:.0f} platform fee from admin")

        except Exception as e:
            print(f"[Order Reject] Wallet refund/reversal failed (non-fatal): {e}")

        # Notify the buyer with rejection reason
        reason = request.form.get('reason', '').strip()
        notification_manager.create_notification(
            order.buyer_id,
            f"Order #{order.id} Rejected",
            f"Unfortunately, your order for \"{order.service.title}\" was rejected by the provider. Reason: {reason}. Your payment has been refunded to your wallet.",
            url_for('user.orders')
        )
        
        # Send rejection email to the buyer
        from email_utils import send_order_rejected_email
        send_order_rejected_email(order, reason=reason)
        
        flash('Order rejected. The buyer has been notified and their payment refunded.', 'warning')
            
    return redirect(url_for('user.order_detail', order_id=order_id))


@user_bp.route('/certificate/<cert_id>/download')
@login_required
def download_certificate(cert_id):
    """
    Serves the certificate PDF.
    Only the student (buyer) or the provider or admin can download it.
    """
    from flask import send_file, abort
    
    cert = Certificate.query.filter_by(cert_id=cert_id).first_or_404()

    # Access control
    allowed = (
        current_user.id == cert.student_id or
        current_user.id == cert.provider_id or
        current_user.is_admin()
    )
    if not allowed:
        abort(403)

    # Use Flask's static folder directly - it's already configured correctly
    pdf_path = os.path.join(current_app.static_folder, 'certificates', cert.pdf_filename)
    
    # Debug logging
    print(f"\n{'='*60}")
    print(f"[CERTIFICATE DOWNLOAD]")
    print(f"{'='*60}")
    print(f"Cert ID: {cert_id}")
    print(f"Filename: {cert.pdf_filename}")
    print(f"Static folder: {current_app.static_folder}")
    print(f"Full path: {pdf_path}")
    print(f"File exists: {os.path.exists(pdf_path)}")
    
    if os.path.exists(current_app.static_folder):
        cert_dir = os.path.join(current_app.static_folder, 'certificates')
        print(f"Cert dir exists: {os.path.exists(cert_dir)}")
        if os.path.exists(cert_dir):
            files = os.listdir(cert_dir)
            print(f"Files in cert dir ({len(files)}): {files[:10]}")  # Show first 10
    print(f"{'='*60}\n")

    if not os.path.exists(pdf_path):
        print(f"[ERROR] Certificate file not found at: {pdf_path}")
        flash("Certificate file not found on server. Please contact support.", "danger")
        return redirect(url_for('user.my_certificates'))

    try:
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=f"SkillVerse_Certificate_{cert.cert_id}.pdf",
            mimetype='application/pdf'
        )
    except Exception as e:
        print(f"[ERROR] Failed to send file: {e}")
        import traceback
        traceback.print_exc()
        flash(f"Error downloading certificate: {str(e)}", "danger")
        return redirect(url_for('user.my_certificates'))


@user_bp.route('/api/certificate/order/<int:order_id>')
@login_required
def get_order_certificate(order_id):
    """Returns certificate info for an order as JSON (for frontend use)."""
    cert = Certificate.query.filter_by(order_id=order_id).first()
    if not cert:
        return jsonify({'exists': False})
    return jsonify({
        'exists'      : True,
        'cert_id'     : cert.cert_id,
        'issued_at'   : cert.issued_at.strftime('%B %d, %Y'),
        'download_url': url_for('user.download_certificate', cert_id=cert.cert_id),
    })


@user_bp.route('/my-certificates')
@login_required
def my_certificates():
    """Page listing all certificates earned by the current user."""
    certificates = Certificate.query.filter_by(student_id=current_user.id).order_by(Certificate.issued_at.desc()).all()
    return render_template('user/my_certificates.html', certificates=certificates)


@user_bp.route('/issued-certificates')
@login_required
def issued_certificates():
    """Page listing all certificates issued by the current provider or all for admin."""
    # All non-admin users can see certificates they issued
    if current_user.is_admin():
        # Admin sees everything
        certificates = Certificate.query.order_by(Certificate.issued_at.desc()).all()
    else:
        # User sees only what they issued (as seller)
        certificates = Certificate.query.filter_by(provider_id=current_user.id).order_by(Certificate.issued_at.desc()).all()
        
    return render_template('user/issued_certificates.html', certificates=certificates)


def _send_certificate_email(student, cert, pdf_path):
    """Send certificate download link to the student via email."""
    from email_utils import send_async_email, _get_default_sender
    from flask import current_app
    from threading import Thread

    download_url = url_for('user.download_certificate',
                           cert_id=cert.cert_id, _external=True)
    sender = _get_default_sender()

    html_content = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto">
            <h2 style="color:#1a1a4e">Congratulations, {student.full_name or student.username}! 🎉</h2>
            <p>You have successfully completed <strong>{cert.skill_name}</strong>.</p>
            <p>Your Certificate ID is: <strong>{cert.cert_id}</strong></p>
            <p style="margin:30px 0">
                <a href="{download_url}"
                   style="background:#B8860B;color:white;padding:14px 28px;
                          border-radius:6px;text-decoration:none;font-weight:bold">
                    Download Your Certificate
                </a>
            </p>
            <p style="color:#666;font-size:12px">
                This certificate was issued on {cert.issued_at.strftime('%B %d, %Y')} 
                by SkillVerse Platform.
            </p>
        </div>
        """
    
    app = current_app._get_current_object()
    Thread(
        target=send_async_email,
        args=(app, f'🎓 Your SkillVerse Certificate - {cert.skill_name}', student.email, html_content, sender)
    ).start()


@user_bp.route('/order/<int:order_id>/message', methods=['POST'])
@login_required
def send_message(order_id):
    """Send chat message"""
    content = request.form.get('content')
    if content:
        msg, error = chat_manager.send_message(order_id, current_user.id, content)
        if error:
            flash(error, 'danger')
        else:
            # Notify receiver
            order = Order.query.get(order_id)
            receiver_id = order.buyer_id if current_user.id == order.seller_id else order.seller_id
            notification_manager.create_notification(receiver_id, "New Message", f"New message from {current_user.username}", url_for('user.order_detail', order_id=order_id))
            
    return redirect(url_for('user.order_detail', order_id=order_id))


@user_bp.route('/profile/<username>')
def profile(username):
    """
    Public user profile
    
    Args:
        username: Username
        
    Returns:
        Rendered template
    """
    user = User.query.filter_by(username=username).first_or_404()
    
    # Get user's services (public profile shows only approved; owner sees all)
    if current_user.is_authenticated and (current_user.id == user.id or current_user.is_admin()):
        services = user.get_services()  # Owner/admin sees all active services
    else:
        services = Service.query.filter_by(user_id=user.id, is_active=True, is_approved=True).all()
    
    # Get user stats
    stats = user_manager.get_user_stats(user.id)

    # ── Satisfaction Rate Calculation ─────────────────────────────────────
    # Formula: 40% Testimonials + 20% Skill Reviews + 10% Skills Available + 30% Provider Reviews
    from models import Testimonial, Review, Service as Svc

    # Component 1 (40%): Average testimonial rating (scale 1-5 → 0-100)
    testimonials = Testimonial.query.filter_by(user_id=user.id, is_active=True).all()
    if testimonials:
        avg_testimonial = sum(t.rating for t in testimonials) / len(testimonials)
        testimonial_score = (avg_testimonial / 5.0) * 100
    else:
        testimonial_score = 0.0

    # Component 2 (20%): Average skill review rating across all provider services
    all_service_ids = [s.id for s in Svc.query.filter_by(user_id=user.id).all()]
    if all_service_ids:
        reviews_for_services = Review.query.filter(Review.service_id.in_(all_service_ids)).all()
        if reviews_for_services:
            avg_review = sum(r.rating for r in reviews_for_services) / len(reviews_for_services)
            review_score = (avg_review / 5.0) * 100
        else:
            review_score = 0.0
    else:
        review_score = 0.0

    # Component 3 (10%): Skills available — score based on active service count (max 10 services = 100%)
    active_service_count = Svc.query.filter_by(user_id=user.id, is_active=True).count()
    skills_available_score = min(active_service_count / 10.0, 1.0) * 100

    # Component 4 (30%): Provider's own average rating (from User.get_average_rating)
    provider_avg_rating = user.get_average_rating()  # Returns float 0-5
    provider_review_score = (provider_avg_rating / 5.0) * 100

    # Weighted satisfaction rate
    satisfaction_rate = (
        0.40 * testimonial_score +
        0.20 * review_score +
        0.10 * skills_available_score +
        0.30 * provider_review_score
    )
    satisfaction_rate = round(min(max(satisfaction_rate, 0), 100), 1)
    # ─────────────────────────────────────────────────────────────────────
    
    return render_template('user/profile.html',
                         user=user,
                         services=services,
                         stats=stats,
                         satisfaction_rate=satisfaction_rate)


@user_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """
    User settings page
    
    GET: Display settings form
    POST: Update user settings
    
    Returns:
        Rendered template or redirect
    """
    if request.method == 'POST':
        # Update profile
        current_user.full_name = request.form.get('full_name', '')
        current_user.bio = request.form.get('bio', '')
        current_user.bio = request.form.get('bio', '')
        current_user.phone = request.form.get('phone', '')
        
        # Handle Avatar Upload
        if 'avatar' in request.files:
            file = request.files['avatar']
            if file and file.filename != '':
                filename = save_uploaded_file(file, folder='avatars')
                # Update user avatar field (assuming model has avatar_url or similar)
                # Checking models.py next, but applying common pattern
                if filename:
                    current_user.avatar_url = filename
        
        # Update password if provided
        new_password = request.form.get('new_password')
        if new_password:
            current_password = request.form.get('current_password')
            if current_user.check_password(current_password):
                current_user.set_password(new_password)
                flash('Password updated successfully!', 'success')
            else:
                flash('Current password is incorrect.', 'danger')
                return render_template('user/settings.html')
        
        db.session.commit()
        flash('Settings updated successfully!', 'success')
        return redirect(url_for('user.settings'))
    
    return render_template('user/settings.html')


@user_bp.route('/portfolio/add', methods=['POST'])
@login_required
def add_portfolio():
    """Add a portfolio project"""
    title = request.form.get('title')
    description = request.form.get('description')
    link = request.form.get('link')
    
    image_url = None
    if 'image' in request.files:
        file = request.files['image']
        if file and file.filename != '':
            image_url = save_uploaded_file(file, folder='portfolio')
            
    if not title:
        flash('Project title is required', 'danger')
        return redirect(url_for('user.settings'))
    
    project = ProjectShowcase(
        user_id=current_user.id,
        title=title,
        description=description,
        image_url=image_url,
        link=link
    )
    
    db.session.add(project)
    db.session.commit()
    
    flash('Project added to your portfolio!', 'success')
    return redirect(url_for('user.settings'))


@user_bp.route('/portfolio/delete/<int:project_id>', methods=['POST'])
@login_required
def delete_portfolio(project_id):
    """Delete a portfolio project"""
    project = ProjectShowcase.query.get_or_404(project_id)
    
    if project.user_id != current_user.id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('user.settings'))
    
    db.session.delete(project)
    db.session.commit()
    
    flash('Project removed from portfolio', 'success')
    return redirect(url_for('user.settings'))






@user_bp.route('/orders')
@login_required
def orders():
    """
    User orders page
    
    Returns:
        Rendered template
    """
    # Get orders as buyer and seller
    orders_as_buyer = order_manager.get_user_orders(current_user.id, as_buyer=True)
    orders_as_seller = order_manager.get_user_orders(current_user.id, as_buyer=False)
    
    return render_template('user/orders.html',
                         orders_as_buyer=orders_as_buyer,
                         orders_as_seller=orders_as_seller)


# ============================================================================
# WALLET & PAYMENT ROUTES (Unit-8, 9: OOP, Unit-6: File Handling)
# ============================================================================

@user_bp.route('/wallet')
@login_required
def wallet():
    """
    User wallet page
    
    Displays:
    - Current wallet balance
    - Add money option
    - Transaction history
    
    Returns:
        Rendered template
    """
    # Import payment system classes
    from payment_system import WalletManager, PaymentGateway
    
    # Initialize wallet manager
    gateway = PaymentGateway()
    wallet_mgr = WalletManager(payment_gateway=gateway)
    
    # Get wallet balance for current user
    wallet_balance = wallet_mgr.get_balance(current_user.id)
    
    # Get recent transactions
    transactions = wallet_mgr.get_transaction_history(current_user.id)
    
    return render_template('user/wallet.html',
                         wallet_balance=wallet_balance,
                         transactions=transactions)


@user_bp.route('/wallet/add', methods=['POST'])
@login_required
def add_money():
    """
    Add money to wallet (API endpoint)
    
    Expects JSON data:
    - amount: Amount to add
    - method: Payment method
    
    Returns:
        JSON response with transaction result
    """
    from payment_system import WalletManager, PaymentGateway, CustomException
    
    try:
        data = request.get_json()
        amount = float(data.get('amount', 0))
        method = data.get('method', 'card')
        
        if amount <= 0:
            return jsonify({'success': False, 'error': 'Invalid amount'})
        
        gateway = PaymentGateway()
        wallet_mgr = WalletManager(payment_gateway=gateway)
        
        # Process payment and add to wallet
        result = wallet_mgr.add_money(
            user_id=current_user.id,
            amount=amount,
            payment_method=method,
            description='Wallet Recharge'
        )
        
        return jsonify({
            'success': result['status'] == 'success',
            'transaction': result
        })
        
    except CustomException as e:
        return jsonify({'success': False, 'error': str(e)})
    except Exception as e:
        return jsonify({'success': False, 'error': 'Payment failed. Please try again.'})


@user_bp.route('/wallet/deduct', methods=['POST'])
@login_required
def deduct_money():
    """
    Deduct money from wallet (for purchases)
    
    Expects JSON data:
    - amount: Amount to deduct
    - description: Transaction description
    
    Returns:
        JSON response with transaction result
    """
    from payment_system import WalletManager, PaymentGateway, InsufficientBalanceException, CustomException
    
    try:
        data = request.get_json()
        amount = float(data.get('amount', 0))
        description = data.get('description', 'Service Purchase')
        
        if amount <= 0:
            return jsonify({'success': False, 'error': 'Invalid amount'})
        
        gateway = PaymentGateway()
        wallet_mgr = WalletManager(payment_gateway=gateway)
        
        # Check balance and deduct
        result = wallet_mgr.deduct_money(
            user_id=current_user.id,
            amount=amount,
            description=description
        )
        
        return jsonify({
            'success': True,
            'transaction': result,
            'new_balance': result.get('new_balance', 0)
        })
        
    except InsufficientBalanceException as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'insufficient_balance': True,
            'required': e.required,
            'available': e.available
        })
    except CustomException as e:
        return jsonify({'success': False, 'error': str(e)})
    except Exception as e:
        return jsonify({'success': False, 'error': 'Transaction failed. Please try again.'})


@user_bp.route('/wallet/balance')
@login_required
def get_balance():
    """
    Get current wallet balance (API endpoint)
    
    Returns:
        JSON response with balance
    """
    from payment_system import WalletManager
    
    wallet_mgr = WalletManager()
    balance = wallet_mgr.get_balance(current_user.id)
    
    return jsonify({
        'success': True,
        'balance': balance
    })


@user_bp.route('/transactions')
@login_required
def transactions():
    """
    Transaction history page
    
    Displays:
    - All user transactions
    - Filter options
    - Export functionality
    
    Returns:
        Rendered template
    """
    from payment_system import PaymentGateway
    
    gateway = PaymentGateway()
    user_transactions = gateway.get_user_transactions(current_user.id)
    
    return render_template('user/transactions.html',
                         transactions=user_transactions)


@user_bp.route('/transactions/export')
@login_required
def export_transactions():
    """
    Export transactions as CSV
    
    Returns:
        CSV file download
    """
    from payment_system import PaymentGateway, TransactionFilter
    from flask import Response
    
    gateway = PaymentGateway()
    transactions = gateway.get_user_transactions(current_user.id)
    
    # Generate CSV content
    csv_content = TransactionFilter.export_to_csv(
        transactions,
        filename=f'transactions_{current_user.id}.csv'
    )
    
    # Return as downloadable file
    return Response(
        csv_content,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename=transactions_{current_user.id}.csv'}
    )


@user_bp.route('/invoice/<txn_id>')
@login_required
def get_invoice(txn_id):
    """
    Get invoice for a transaction
    
    Args:
        txn_id: Transaction ID
        
    Returns:
        HTML invoice or JSON error
    """
    from payment_system import PaymentGateway, InvoiceGenerator, TransactionNotFoundException
    
    try:
        gateway = PaymentGateway()
        transaction = gateway.get_transaction(txn_id)
        
        # Verify transaction belongs to current user
        if str(transaction.get('user_id')) != str(current_user.id):
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        
        # Generate invoice HTML
        invoice_gen = InvoiceGenerator()
        invoice_html = invoice_gen.generate_invoice_html(transaction)
        
        return invoice_html
        
    except TransactionNotFoundException:
        return jsonify({'success': False, 'error': 'Transaction not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# ADMIN ROUTES
# ============================================================================

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """
    Admin dashboard
    
    Shows:
    - Total users, services, orders
    - Recent activity
    - Statistics
    
    Returns:
        Rendered template
    """
    # Get statistics
    total_users = User.query.count()
    total_services = Service.query.filter_by(is_active=True, is_approved=True).count()
    pending_services_count = service_manager.get_pending_count()
    total_orders = Order.query.count()
    total_reviews = Review.query.count()
    
    # Get recent users
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
    
    # Get recent services
    recent_services = Service.query.order_by(Service.created_at.desc()).limit(10).all()
    
    # Get recent orders
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()

    # --- Generate Graphs (Optimized for Admin Dashboard) ---
    # REPLACED Revenue Graph with User Growth Graph (Platform Adoption)
    
    plt.style.use('fivethirtyeight')
    
    # Graph 1: User Growth (New Signups per Day)
    # Suited for: Tracking platform adoption and marketing effectiveness
    user_data = db.session.query(
        func.date(User.created_at), func.count(User.id)
    ).group_by(func.date(User.created_at)).order_by(func.date(User.created_at)).all()
    
    dates_curr = []
    values_curr = []
    if user_data:
        dates_curr = [str(r[0]) for r in user_data]
        values_curr = [int(r[1]) for r in user_data]
    else:
        dates_curr = ['No Data']
        values_curr = [0]

    fig1 = plt.figure(figsize=(10, 5))
    ax1 = plt.gca()
    # Plot formatting: Green line for growth
    ax1.plot(dates_curr, values_curr, color='#198754', linewidth=3, marker='o', markersize=8)
    ax1.fill_between(dates_curr, values_curr, color='#198754', alpha=0.15)
    
    ax1.set_title('User Growth (New Signups)', fontsize=14, fontweight='bold', pad=15)
    ax1.set_ylabel('New Users', fontsize=12)
    plt.xticks(rotation=45, fontsize=10)
    plt.yticks(fontsize=10)
    plt.tight_layout()
    
    # Save Graph 1
    img1 = io.BytesIO()
    fig1.savefig(img1, format='png', dpi=100, bbox_inches='tight', facecolor='white')
    img1.seek(0)
    user_graph = base64.b64encode(img1.getvalue()).decode()
    plt.close(fig1)

    # Graph 2: Top Categories (Bar Chart)
    # Suited for: Understanding market demand
    cat_data = db.session.query(Category.name, func.count(Service.id)).outerjoin(Service).group_by(Category.name).order_by(func.count(Service.id).desc()).limit(8).all()
    
    if cat_data:
        cat_names = [r[0] for r in cat_data]
        cat_counts = [r[1] for r in cat_data]
        # Reverse for horizontal bar chart
        cat_names.reverse()
        cat_counts.reverse()
    else:
        cat_names = ['No Categories']
        cat_counts = [0]

    fig2 = plt.figure(figsize=(10, 5))
    ax2 = plt.gca()
    # Plot formatting: Distinct colors for bars
    colors = plt.cm.Paired(np.arange(len(cat_names)))
    bars = ax2.barh(cat_names, cat_counts, color=colors)
    
    ax2.set_title('Top Service Categories', fontsize=14, fontweight='bold', pad=15)
    ax2.set_xlabel('Number of Services', fontsize=12)
    plt.xticks(fontsize=10)
    plt.yticks(fontsize=10)
    plt.tight_layout()
    
    # Save Graph 2
    img2 = io.BytesIO()
    fig2.savefig(img2, format='png', dpi=100, bbox_inches='tight', facecolor='white')
    img2.seek(0)
    category_graph = base64.b64encode(img2.getvalue()).decode()
    plt.close(fig2)
    
    stats = {
        'total_users': total_users,
        'total_services': total_services,
        'total_orders': total_orders,
        'total_reviews': total_reviews
    }
    
    return render_template('admin/dashboard.html',
                         stats=stats,
                         recent_users=recent_users,
                         recent_services=recent_services,
                         recent_orders=recent_orders,
                         user_graph=user_graph,
                         category_graph=category_graph,
                         pending_services_count=pending_services_count)


@admin_bp.route('/users')
@admin_required
def users():
    """
    Manage users
    
    Returns:
        Rendered template
    """
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)


@admin_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_user_status(user_id):
    """
    Toggle user active status
    
    Args:
        user_id: User ID
        
    Returns:
        Redirect
    """
    user = User.query.get_or_404(user_id)
    
    # SECURITY: Prevent admin from deactivating themselves
    if user.id == current_user.id:
        flash('You cannot deactivate your own account!', 'danger')
        return redirect(url_for('admin.users'))
    
    user.is_active = not user.is_active
    db.session.commit()
    
    status = 'activated' if user.is_active else 'deactivated'
    flash(f'User {user.username} has been {status}.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/services')
@admin_required
def services():
    """
    Manage services
    
    Returns:
        Rendered template
    """
    services = Service.query.order_by(Service.created_at.desc()).all()
    pending_count = service_manager.get_pending_count()
    return render_template('admin/services.html', services=services, pending_count=pending_count)


@admin_bp.route('/services/pending')
@admin_required
def pending_services():
    """View services pending admin approval"""
    pending = service_manager.get_pending_services()
    return render_template('admin/pending_services.html', services=pending)


@admin_bp.route('/services/<int:service_id>/approve', methods=['POST'])
@admin_required
def approve_service(service_id):
    """Approve a service"""
    service = service_manager.approve_service(service_id)
    if service:
        flash(f'Service "{service.title}" has been approved.', 'success')
    else:
        flash('Service not found.', 'danger')
    return redirect(url_for('admin.pending_services'))


@admin_bp.route('/services/<int:service_id>/reject', methods=['POST'])
@admin_required
def reject_service(service_id):
    """Reject a service with reason"""
    reason = request.form.get('reason', '')
    service = service_manager.reject_service(service_id, reason)
    if service:
        flash(f'Service "{service.title}" has been rejected.', 'warning')
    else:
        flash('Service not found.', 'danger')
    return redirect(url_for('admin.pending_services'))


@admin_bp.route('/categories', methods=['GET', 'POST'])
@admin_required
def categories():
    """
    Manage categories
    
    GET: Display categories
    POST: Create new category
    
    Returns:
        Rendered template or redirect
    """
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description', '')
        icon = request.form.get('icon', '')
        color = request.form.get('color', '')
        
        category = category_manager.create_category(name, description, icon, color)
        
        if category:
            flash('Category created successfully!', 'success')
        else:
            flash('Category already exists.', 'danger')
        
        return redirect(url_for('admin.categories'))
    
    categories = category_manager.get_all_categories()
    return render_template('admin/categories.html', categories=categories)


@admin_bp.route('/orders')
@admin_required
def orders():
    """
    Manage orders
    
    Returns:
        Rendered template
    """
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin/orders.html', orders=orders)


@admin_bp.route('/bookings')
@login_required
@admin_required
def bookings():
    """Admin page to view all bookings"""
    bookings = Booking.query.order_by(Booking.created_at.desc()).all()
    return render_template('admin/bookings.html', bookings=bookings)


@admin_bp.route('/availability')
@login_required
@admin_required
def availability():
    """Admin page to view all availability slots"""
    slots = AvailabilitySlot.query.order_by(AvailabilitySlot.start_time.desc()).all()
    return render_template('admin/availability.html', slots=slots)


@admin_bp.route('/messages')
@admin_required
def messages():
    """Contact messages"""
    messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
    return render_template('admin/messages.html', messages=messages)


# ============================================================================
# API ROUTES (JSON)
# ============================================================================

@api_bp.route('/search/autocomplete')
def search_autocomplete():
    """
    Autocomplete API for search
    
    Query Parameters:
    - q: Search query
    
    Returns:
        JSON: List of suggestions
    """
    query = request.args.get('q', '')
    suggestions = search_engine.get_autocomplete_suggestions(query, limit=5)
    
    return jsonify({'suggestions': suggestions})


@api_bp.route('/categories')
def get_categories():
    """
    Get all categories
    
    Returns:
        JSON: List of categories with stats
    """
    category_stats = category_manager.get_category_stats()
    return jsonify({'categories': category_stats})


@api_bp.route('/services/featured')
def get_featured_services():
    """
    Get featured services
    
    Returns:
        JSON: List of featured services
    """
    limit = request.args.get('limit', 4, type=int)
    services = service_manager.get_featured_services(limit)
    
    services_data = [{
        'id': s.id,
        'title': s.title,
        'price': s.price,
        'rating': s.get_average_rating(),
        'provider': s.provider.username,
        'image_url': s.image_url
    } for s in services]
    
    return jsonify({'services': services_data})


@api_bp.route('/services/<int:service_id>/stats')
def get_service_stats(service_id):
    """
    Get service statistics
    
    Args:
        service_id: Service ID
        
    Returns:
        JSON: Service stats
    """
    service = Service.query.get_or_404(service_id)
    
    stats = {
        'views': service.view_count,
        'rating': service.get_average_rating(),
        'reviews': service.get_review_count(),
        'favorites': service.favorited_by.count()
    }
    
    return jsonify(stats)


@api_bp.route('/notifications')
@login_required
def get_notifications():
    """
    Get user notifications for real-time polling
    
    Returns:
        JSON: List of notifications with unread count
    """
    import pytz
    from datetime import datetime
    
    notifications = current_user.get_recent_notifications(10)
    unread_count = current_user.get_unread_notifications_count()
    
    # Convert to IST for display
    ist_tz = pytz.timezone('Asia/Kolkata')
    
    notifications_data = []
    for n in notifications:
        # Convert created_at to IST
        created_at = n.created_at
        if created_at.tzinfo is None:
            utc_tz = pytz.UTC
            created_at = utc_tz.localize(created_at)
        ist_time = created_at.astimezone(ist_tz)
        
        notifications_data.append({
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'link': n.link or '#',
            'is_read': n.is_read,
            'time': ist_time.strftime('%I:%M %p')
        })
    
    return jsonify({
        'notifications': notifications_data,
        'unread_count': unread_count
    })


# ============================================================================
# AVAILABILITY ROUTES
# ============================================================================

@availability_bp.route('/manage')
@provider_required
def manage():
    """
    Provider Availability Management Page
    """
    from models import Booking, AvailabilitySlot
    # Get pending bookings for this provider
    pending_bookings = Booking.query.join(AvailabilitySlot).filter(
        AvailabilitySlot.provider_id == current_user.id,
        Booking.status == 'pending'
    ).all()
    
    return render_template('user/availability_manage.html', pending_bookings=pending_bookings)

@availability_bp.route('/api/slots', methods=['GET'])
@provider_required
def get_my_slots():
    """Get provider's slots for FullCalendar"""
    start = request.args.get('start')
    end = request.args.get('end')
    
    # FullCalendar sends ISO strings
    try:
        # Parse ISO string (usually contains 'Z' or offset)
        start_date = datetime.fromisoformat(start.replace('Z', '+00:00'))
        end_date = datetime.fromisoformat(end.replace('Z', '+00:00'))
    except:
        return jsonify([])

    # Convert to UTC first, then remove timezone info to make it naive
    # This ensures consistency with DB which stores naive UTC
    if start_date.tzinfo:
        start_date = start_date.astimezone(timezone.utc).replace(tzinfo=None)
    if end_date.tzinfo:
        end_date = end_date.astimezone(timezone.utc).replace(tzinfo=None)

    slots = availability_manager.get_provider_slots(current_user.id, start_date, end_date)
    
    events = []
    for slot in slots:
        color = '#28a745' # Green (Available)
        title = 'Available'
        
        if slot.is_booked:
            if slot.booking and slot.booking.status == 'pending':
                color = '#ffc107' # Yellow (Pending)
                title = 'Pending Request'
            else:
                color = '#0d6efd' # Blue (Confirmed) instead of Red (Booked)
                title = 'Booked'
            
        events.append({
            'id': slot.id,
            'title': title,
            # Force UTC 'Z' so FullCalendar converts to local time
            'start': slot.start_time.isoformat() + 'Z',
            'end': slot.end_time.isoformat() + 'Z',
            'color': color,
            'extendedProps': {
                'is_booked': slot.is_booked,
                'status': slot.booking.status if slot.booking else None
            }
        })
        
    return jsonify(events)





@availability_bp.route('/api/slots/add', methods=['POST'])
@provider_required
def add_slot():
    """Add availability slot"""
    data = request.json
    try:
        start_time = datetime.fromisoformat(data['start'].replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(data['end'].replace('Z', '+00:00'))
        is_recurring = data.get('is_recurring', False)
        
        # Convert to UTC first, then remove timezone info to make it naive
        if start_time.tzinfo:
            start_time = start_time.astimezone(timezone.utc).replace(tzinfo=None)
        if end_time.tzinfo:
            end_time = end_time.astimezone(timezone.utc).replace(tzinfo=None)
            
        # Ensure we are using naive UTC datetimes for DB
        result, error = availability_manager.create_slots(current_user.id, start_time, end_time, is_recurring)
        
        if error:
            return jsonify({'status': 'error', 'message': error}), 400
            
        return jsonify({'status': 'success', 'result': result})
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@availability_bp.route('/api/slots/<int:slot_id>', methods=['DELETE'])
@provider_required
def delete_slot(slot_id):
    """Delete availability slot"""
    success, error = availability_manager.delete_slot(slot_id, current_user.id)
    if not success:
        return jsonify({'status': 'error', 'message': error}), 400
    return jsonify({'status': 'success'})

@availability_bp.route('/provider/<int:provider_id>/slots')
def get_provider_public_slots(provider_id):
    """Public API to get available slots for booking"""
    start = request.args.get('start')
    end = request.args.get('end')
    
    try:
        start_date = datetime.fromisoformat(start.replace('Z', '+00:00'))
        end_date = datetime.fromisoformat(end.replace('Z', '+00:00'))
    except:
        return jsonify([])

    # Convert to UTC first, then remove timezone info to make it naive
    if start_date.tzinfo:
        start_date = start_date.astimezone(timezone.utc).replace(tzinfo=None)
    if end_date.tzinfo:
        end_date = end_date.astimezone(timezone.utc).replace(tzinfo=None)

    slots = availability_manager.get_provider_slots(provider_id, start_date, end_date)
    
    events = []
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    
    for slot in slots:
        # Only show available slots (not booked)
        # Check explicitly for False to be safe
        is_blocked = slot.is_booked
        
        if not is_blocked and slot.start_time > now:
            events.append({
                'id': slot.id,
                'title': 'Available',
                # Force UTC 'Z' for frontend timezone conversion
                'start': slot.start_time.isoformat() + 'Z',
                'end': slot.end_time.isoformat() + 'Z',
                'color': '#28a745',
                'display': 'block',
                'extendedProps': {'booked': False}
            })
        
    return jsonify(events)

@availability_bp.route('/book', methods=['POST'])
@login_required
def book_slot():
    """Book a slot"""
    slot_id = request.form.get('slot_id')
    service_id = request.form.get('service_id')
    order_id = request.form.get('order_id')
    notes = request.form.get('notes', '')
    
    booking, error = availability_manager.book_slot(slot_id, current_user.id, service_id, notes, order_id)
    
    if error:
        flash(f'Booking failed: {error}', 'danger')
        if order_id:
             return redirect(url_for('user.order_detail', order_id=order_id))
        if service_id:
            return redirect(url_for('service.detail', service_id=service_id))
        return redirect(url_for('main.index'))
        
    flash('Booking request sent! Waiting for admin approval.', 'success')
    if order_id:
        return redirect(url_for('user.order_detail', order_id=order_id))
    return redirect(url_for('user.bookings_list'))


@availability_bp.route('/booking/<int:booking_id>/approve', methods=['POST'])
@login_required
@provider_required
def approve_booking(booking_id):
    """Approve a booking request"""
    success, error = availability_manager.approve_booking(booking_id, current_user.id)
    if success:
        # Send confirmation email
        from models import Booking, Notification
        booking = Booking.query.get(booking_id)
        from email_utils import send_booking_confirmation_email
        if booking:
            send_booking_confirmation_email(booking)
            
            # Create notification for the client
            slot_time = booking.slot.start_time.strftime('%d %b %Y at %I:%M %p')
            notification = Notification(
                user_id=booking.client_id,
                title='Booking Approved! ✅',
                message=f'Your booking request with {current_user.username} for {slot_time} has been approved.',
                link=url_for('user.dashboard')
            )
            db.session.add(notification)
            db.session.commit()
             
        flash('Booking approved successfully!', 'success')
    else:
        flash(f'Error: {error}', 'danger')
        
    # Redirect to dashboard as My Bookings page is removed
    return redirect(request.referrer or url_for('user.dashboard'))

@availability_bp.route('/booking/<int:booking_id>/reject', methods=['POST'])
@login_required
@provider_required
def reject_booking(booking_id):
    """Reject a booking request"""
    # Get booking info BEFORE rejecting (so we have the slot time)
    from models import Booking, Notification
    booking = Booking.query.get(booking_id)
    client_id = booking.client_id if booking else None
    slot_time = booking.slot.start_time.strftime('%d %b %Y at %I:%M %p') if booking else ''
    
    success, error = availability_manager.reject_booking(booking_id, current_user.id)
    if success:
        # Send rejection email
        from email_utils import send_booking_rejection_email
        if booking:
            send_booking_rejection_email(booking)
            
            # Create notification for the client
            notification = Notification(
                user_id=client_id,
                title='Booking Declined ❌',
                message=f'Your booking request with {current_user.username} for {slot_time} has been declined. Please try another time slot.',
                link=url_for('user.dashboard')
            )
            db.session.add(notification)
            db.session.commit()
             
        flash('Booking rejected.', 'warning')
    else:
        flash(f'Error: {error}', 'danger')
        
    return redirect(request.referrer or url_for('user.dashboard'))

# My Bookings page removed as per request. Redirecting to dashboard.
@user_bp.route('/bookings')
@login_required
def bookings_list():
    """Redirect to dashboard - My Bookings page has been removed"""
    return redirect(url_for('user.dashboard'))


# ============================================================================
# API ROUTES - Advanced Product/Service Search & Filter
# ============================================================================

@api_bp.route('/services/search', methods=['GET'])
def search_services_api():
    """
    Advanced service search and filter API endpoint
    """
    try:
        # 1. Extract filters (Basic Data Types)
        search_query = request.args.get('search', '').strip()
        min_price = request.args.get('min_price', type=float)
        max_price = request.args.get('max_price', type=float)
        min_rating = request.args.get('min_rating', type=float)
        delivery_time = request.args.get('delivery_time', '').strip()
        category = request.args.get('category', '').strip()
        sort_by = request.args.get('sort', 'newest')
        
        # 2. Base Query
        query = Service.query.filter_by(is_active=True)
        
        # 3. Apply SQL Filters (Filter Logic)
        if search_query:
            search_filter = db.or_(
                Service.title.ilike(f'%{search_query}%'),
                Service.description.ilike(f'%{search_query}%'),
                Service.tags.ilike(f'%{search_query}%')
            )
            query = query.filter(search_filter)
        
        if min_price is not None:
            query = query.filter(Service.price >= min_price)
        if max_price is not None:
            query = query.filter(Service.price <= max_price)
        
        if delivery_time:
            query = query.filter(Service.delivery_time.ilike(f'%{delivery_time}%'))
        
        if category:
            # Check if category is ID or Name
            if category.isdigit():
                query = query.filter(Service.category_id == int(category))
            else:
                query = query.join(Category).filter(Category.name.ilike(f'%{category}%'))
        
        # Execute DB Query
        services = query.all()
        
        # 4. Apply Python Filters (Syllabus: Lambda, Filter)
        if min_rating is not None:
            # Filtering list using lambda
            services = list(filter(lambda s: s.get_average_rating() >= min_rating, services))
        
        # 5. Apply Sorting (Syllabus: Logic, Sorted)
        if sort_by == 'newest':
            services = sorted(services, key=lambda s: s.created_at, reverse=True)
        elif sort_by == 'popular':
            services = sorted(services, key=lambda s: s.view_count, reverse=True)
        elif sort_by == 'highest_rated':
            services = sorted(services, key=lambda s: s.get_average_rating(), reverse=True)
        elif sort_by == 'price_low':
            services = sorted(services, key=lambda s: s.price)
        elif sort_by == 'price_high':
            services = sorted(services, key=lambda s: s.price, reverse=True)
        
        # 6. Transform Data for JSON (List Comprehension/Loops)
        services_data = []
        for service in services:
            # Safety check for provider
            provider_name = "Unknown"
            provider_avatar = "/static/avatars/default.png"
            if service.provider:
                provider_name = service.provider.username
                provider_avatar = service.provider.get_avatar_url()
                
            services_data.append({
                'id': service.id,
                'title': service.title,
                'description': service.description,
                'price': service.price or 0.0,
                'rating': service.get_average_rating() or 0.0,
                'review_count': service.get_review_count(),
                'delivery_time': service.delivery_time or 'N/A',
                'category': service.category.name if service.category else 'Uncategorized',
                'image_url': service.get_image_url(),
                'provider_name': provider_name,
                'provider_avatar': provider_avatar,
                'view_count': service.view_count,
                'url': url_for('service.detail', service_id=service.id, _external=True)
            })
        
        return jsonify({
            'success': True,
            'count': len(services_data),
            'services': services_data
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/services/filters/options', methods=['GET'])
def get_filter_options():
    """Get available filter options"""
    try:
        categories = Category.query.all()
        # Syllabus: List Comprehension
        category_list = [{'id': c.id, 'name': c.name} for c in categories]
        
        # Syllabus: Set for unique values
        delivery_times = db.session.query(Service.delivery_time).filter(
            Service.is_active == True
        ).distinct().all()
        
        # Flatten tuple list using list comprehension
        delivery_time_list = sorted([dt[0] for dt in delivery_times if dt[0]])
        
        return jsonify({
            'success': True,
            'options': {
                'categories': category_list,
                'delivery_times': delivery_time_list
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/services/autocomplete', methods=['GET'])
def service_autocomplete_api():
    """Search suggestions API"""
    try:
        query = request.args.get('q', '').strip()
        if len(query) < 2:
            return jsonify({'success': True, 'suggestions': []})
            
        services = Service.query.filter(
            Service.is_active == True,
            Service.title.ilike(f'%{query}%')
        ).limit(5).all()
        
        # Syllabus: List Comprehension
        suggestions = [s.title for s in services]
        
        return jsonify({'success': True, 'suggestions': suggestions})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


