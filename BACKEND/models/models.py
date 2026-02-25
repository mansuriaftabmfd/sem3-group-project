"""
Database Models for SkillVerse Application

This module demonstrates multiple OOP concepts:
1. INHERITANCE - All models inherit from db.Model
2. ENCAPSULATION - Private methods and password hashing
3. ABSTRACTION - Clean interfaces for complex operations
4. POLYMORPHISM - Different models with similar methods

DBMS Concepts Demonstrated:
- Primary Keys (id fields)
- Foreign Keys (user_id, service_id, etc.)
- One-to-Many Relationships (User -> Services, Service -> Reviews)
- Many-to-Many Relationships (via association tables)
- Indexes for query optimization
- Constraints (UNIQUE, NOT NULL)

Author: SkillVerse Team
Purpose: Define database schema and model behavior
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize SQLAlchemy database object
# This will be configured in app.py
db = SQLAlchemy()


class User(UserMixin, db.Model):
    """
    User Model - Represents both service providers and clients
    
    OOP Concepts:
    - INHERITANCE: Inherits from db.Model and UserMixin
    - ENCAPSULATION: Password is hashed and never stored in plain text
    - METHODS: Custom methods for password handling and relationships
    
    DBMS Concepts:
    - Primary Key: id
    - Unique Constraints: username, email
    - One-to-Many: User has many Services
    - One-to-Many: User has many Reviews
    """
    
    # Table name in database
    __tablename__ = 'users'
    
    # Primary Key - Unique identifier for each user
    id = db.Column(db.Integer, primary_key=True)
    
    # User credentials and basic info
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # User type: 'client', 'provider', or 'admin'
    user_type = db.Column(db.String(20), nullable=False, default='client')
    
    # Profile information
    full_name = db.Column(db.String(100))
    bio = db.Column(db.Text)
    avatar_url = db.Column(db.String(255), default='default-avatar.png')
    phone = db.Column(db.String(20))
    
    # Account status
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)

    # Wallet balance - stored in DB so it persists across redeploys
    wallet_balance = db.Column(db.Float, default=0.0, nullable=False)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships (One-to-Many)
    # One user can have many services
    services = db.relationship('Service', backref='provider', lazy='dynamic', 
                              foreign_keys='Service.user_id')
    
    # One user can write many reviews
    reviews = db.relationship('Review', backref='reviewer', lazy='dynamic',
                             foreign_keys='Review.user_id')
    
    # One user can have many orders as buyer
    orders_as_buyer = db.relationship('Order', backref='buyer', lazy='dynamic',
                                     foreign_keys='Order.buyer_id')
    
    # One user can have many orders as seller
    orders_as_seller = db.relationship('Order', backref='seller', lazy='dynamic',
                                      foreign_keys='Order.seller_id')
    
    # One user can have many favorites
    favorites = db.relationship('Favorite', backref='user', lazy='dynamic',
                               cascade='all, delete-orphan')

    # One user can have many notifications
    notifications = db.relationship('Notification', backref='user', lazy='dynamic',
                                   cascade='all, delete-orphan')
    
    def get_reset_token(self, expires_sec=1800):
        """
        Generate password reset JWT token
        expires_sec: expiration time in seconds (default 30 mins)
        """
        import jwt
        import time
        from flask import current_app
        
        payload = {
            'user_id': self.id,
            'exp': time.time() + expires_sec
        }
        return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')

    @staticmethod
    def verify_reset_token(token):
        """
        Verify password reset token and return User
        """
        import jwt
        from flask import current_app
        
        try:
            payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            user_id = payload['user_id']
            return User.query.get(user_id)
        except:
            return None
    
    def set_password(self, password):
        """
        Hash and set user password
        
        OOP Concept: ENCAPSULATION - Password is never stored in plain text
        Security: Uses Werkzeug's generate_password_hash with strong algorithm
        
        Args:
            password (str): Plain text password
        """
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """
        Verify password against stored hash
        
        OOP Concept: ENCAPSULATION - Password checking without exposing hash
        
        Args:
            password (str): Plain text password to check
            
        Returns:
            bool: True if password matches, False otherwise
        """
        return check_password_hash(self.password_hash, password)
    
    def get_services(self):
        """
        Get all services offered by this user
        
        Returns:
            list: List of Service objects
        """
        return self.services.filter_by(is_active=True).all()
    
    def get_average_rating(self):
        """
        Calculate average rating for user's services
        
        Algorithm:
        1. Get all services by this user
        2. For each service, get its average rating
        3. Calculate overall average
        
        Returns:
            float: Average rating (0.0 to 5.0)
        """
        services = self.get_services()
        if not services:
            return 0.0
        
        total_rating = sum(service.get_average_rating() for service in services)
        return round(total_rating / len(services), 1)
    
    def get_total_reviews(self):
        """
        Get total number of reviews across all services
        
        Returns:
            int: Total review count
        """
        return sum(service.reviews.count() for service in self.get_services())
    
    def is_admin(self):
        """
        Check if user is an administrator
        
        Returns:
            bool: True if user is admin
        """
        return self.user_type == 'admin'
    
    def get_unread_notifications_count(self):
        """Get count of unread notifications"""
        return self.notifications.filter_by(is_read=False).count()
    
    def get_recent_notifications(self, limit=5):
        """Get recent notifications ordered by date"""
        return self.notifications.order_by(db.text('created_at desc')).limit(limit)

    def get_avatar_url(self):
        """
        Get resolved avatar URL
        
        Returns:
            str: Full URL to avatar image
        """
        from flask import url_for
        
        if not self.avatar_url or self.avatar_url == 'default-avatar.png':
            return f"https://ui-avatars.com/api/?name={self.username}&background=random&color=fff&size=128"
        
        if self.avatar_url.startswith('http'):
            return self.avatar_url
            
        return url_for('static', filename='avatars/' + self.avatar_url)


    def __repr__(self):
        """String representation of User object"""
        return f'<User {self.username}>'


class Transaction(db.Model):
    """
    Transaction Model - Stores all wallet transactions persistently in PostgreSQL.

    Replaces transactions.txt so history survives Render redeploys.

    DBMS Concepts:
    - Primary Key: id (auto-increment)
    - Foreign Key: user_id -> users.id
    - Index on user_id for fast per-user queries
    - Index on timestamp for date-range queries
    """

    __tablename__ = 'transactions'

    id          = db.Column(db.Integer, primary_key=True)
    txn_id      = db.Column(db.String(50), nullable=False, index=True)   # e.g. TXN20260204215100110
    user_id     = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    username    = db.Column(db.String(80))
    amount      = db.Column(db.Float, nullable=False)
    method      = db.Column(db.String(20))          # card / wallet / upi
    status      = db.Column(db.String(20))          # success / failed
    txn_type    = db.Column(db.String(10))          # debit / credit / None for recharge
    description = db.Column(db.Text)
    new_balance = db.Column(db.Float)               # balance after this transaction
    timestamp   = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Relationship
    user = db.relationship('User', backref=db.backref('transactions', lazy='dynamic'))

    def to_dict(self):
        """Return a plain dict matching the old transactions.txt JSON format."""
        # Convert stored UTC timestamp to IST for display
        ts = self.timestamp
        if ts:
            try:
                import pytz
                utc = pytz.utc
                ist = pytz.timezone('Asia/Kolkata')
                if ts.tzinfo is None:
                    ts = utc.localize(ts)
                ts_ist = ts.astimezone(ist)
            except Exception:
                ts_ist = ts
        else:
            ts_ist = None

        return {
            'id':          self.txn_id,
            'user_id':     str(self.user_id),
            'username':    self.username or f'User #{self.user_id}',
            'amount':      self.amount,
            'method':      self.method,
            'status':      self.status,
            'type':        self.txn_type,
            'description': self.description,
            'date':        ts_ist.strftime('%Y-%m-%d') if ts_ist else '',
            'time':        ts_ist.strftime('%H:%M:%S') if ts_ist else '',
            'timestamp':   ts_ist.isoformat() if ts_ist else '',
            'new_balance': self.new_balance,
        }

    def __repr__(self):
        return f'<Transaction {self.txn_id} user={self.user_id} ₹{self.amount}>'


class Category(db.Model):
    """
    Category Model - Represents service categories
    
    OOP Concepts:
    - ENCAPSULATION: Service count is calculated dynamically
    - METHODS: Helper methods for category operations
    
    DBMS Concepts:
    - Primary Key: id
    - Unique Constraint: name
    - One-to-Many: Category has many Services
    """
    
    __tablename__ = 'categories'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Category details
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    icon = db.Column(db.String(50))  # Icon class name (e.g., 'bi-code')
    color = db.Column(db.String(50))  # Color class for styling
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    # One category can have many services
    services = db.relationship('Service', backref='category', lazy='dynamic')
    
    def get_service_count(self):
        """
        Get number of active services in this category
        
        OOP Concept: ENCAPSULATION - Calculated property
        
        Returns:
            int: Number of active services
        """
        return self.services.filter_by(is_active=True).count()
    
    def get_top_services(self, limit=4):
        """
        Get top-rated services in this category
        
        Data Structure: Uses Python's sorted() with custom key
        Algorithm: Sort by average rating descending
        
        Args:
            limit (int): Maximum number of services to return
            
        Returns:
            list: Top-rated Service objects
        """
        services = self.services.filter_by(is_active=True).all()
        # Sort by average rating (highest first)
        sorted_services = sorted(services, 
                                key=lambda s: s.get_average_rating(), 
                                reverse=True)
        return sorted_services[:limit]
    
    def __repr__(self):
        """String representation of Category object"""
        return f'<Category {self.name}>'


class Service(db.Model):
    """
    Service Model - Represents services offered by providers
    
    OOP Concepts:
    - INHERITANCE: Inherits from db.Model
    - ENCAPSULATION: Rating calculation is internal
    - ABSTRACTION: Clean interface for service operations
    
    DBMS Concepts:
    - Primary Key: id
    - Foreign Keys: user_id, category_id
    - Many-to-One: Service belongs to User
    - Many-to-One: Service belongs to Category
    - One-to-Many: Service has many Reviews
    """
    
    __tablename__ = 'services'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Service details
    title = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    delivery_time = db.Column(db.String(50))  # e.g., "3 days", "1 week"
    
    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False, index=True)
    
    # Relationships
    favorited_by = db.relationship('Favorite', backref='service', lazy='dynamic', cascade='all, delete-orphan')
    
    # Media
    image_url = db.Column(db.String(255), default='default-service.jpg')
    
    # Tags for search (stored as comma-separated string)
    tags = db.Column(db.String(255))
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    is_approved = db.Column(db.Boolean, default=False)  # Requires admin approval
    rejection_reason = db.Column(db.String(500), nullable=True)  # Reason for rejection (if rejected)
    
    # Statistics
    view_count = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    # One service can have many reviews
    reviews = db.relationship('Review', backref='service', lazy='dynamic',
                             cascade='all, delete-orphan')
    
    # One service can have many orders
    orders = db.relationship('Order', backref='service', lazy='dynamic')
    
    # One service can be favorited by many users
    favorited_by = db.relationship('Favorite', backref='service', lazy='dynamic',
                                   cascade='all, delete-orphan')
    
    def get_average_rating(self):
        """
        Calculate average rating for this service
        
        Algorithm:
        1. Get all reviews for this service
        2. Calculate sum of ratings
        3. Divide by count
        
        Returns:
            float: Average rating (0.0 to 5.0)
        """
        reviews = self.reviews.all()
        if not reviews:
            return 0.0
        
        total_rating = sum(review.rating for review in reviews)
        return round(total_rating / len(reviews), 1)
    
    def get_review_count(self):
        """
        Get total number of reviews
        
        Returns:
            int: Review count
        """
        return self.reviews.count()
    
    def get_tags_list(self):
        """
        Convert tags string to list
        
        Data Structure: Converts comma-separated string to LIST
        
        Returns:
            list: List of tag strings
        """
        if self.tags:
            return [tag.strip() for tag in self.tags.split(',')]
        return []
    
    def increment_views(self):
        """
        Increment view count for this service
        
        OOP Concept: ENCAPSULATION - Internal state modification
        """
        self.view_count += 1
        db.session.commit()
    
    def is_favorited_by(self, user):
        """
        Check if service is favorited by given user
        
        Args:
            user (User): User object to check
            
        Returns:
            bool: True if favorited
        """
        if not user or not user.is_authenticated:
            return False
        # Fix for DetachedInstanceError: Query Favorite model directly
        from models import Favorite
        return Favorite.query.filter_by(service_id=self.id, user_id=user.id).first() is not None
    
    def get_image_url(self):
        """
        Get resolved image URL
        
        Returns:
            str: Full URL to service image
        """
        from flask import url_for
        
        if not self.image_url or self.image_url == 'default-service.jpg':
            # Return a high-quality placeholder from Unsplash
            return "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=500&q=80"
        
        if self.image_url.startswith('http'):
            return self.image_url
            
        return url_for('static', filename='images/' + self.image_url)

    def __repr__(self):
        """String representation of Service object"""
        return f'<Service {self.title}>'


class Review(db.Model):
    """
    Review Model - Represents user reviews for services
    
    OOP Concepts:
    - VALIDATION: Rating must be between 1 and 5
    - ENCAPSULATION: Validation logic is internal
    
    DBMS Concepts:
    - Primary Key: id
    - Foreign Keys: service_id, user_id
    - Many-to-One: Review belongs to Service
    - Many-to-One: Review belongs to User
    - Composite Index: (service_id, user_id) for faster lookups
    """
    
    __tablename__ = 'reviews'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Review content
    rating = db.Column(db.Integer, nullable=False)  # 1 to 5
    comment = db.Column(db.Text)
    
    # Foreign Keys
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Composite index for faster queries
    __table_args__ = (
        db.Index('idx_service_user', 'service_id', 'user_id'),
    )
    
    def validate_rating(self):
        """
        Validate that rating is between 1 and 5
        
        OOP Concept: VALIDATION - Data integrity check
        
        Returns:
            bool: True if valid, False otherwise
        """
        return 1 <= self.rating <= 5
    
    def __repr__(self):
        """String representation of Review object"""
        return f'<Review for Service {self.service_id} by User {self.user_id}>'


class Order(db.Model):
    """
    Order Model - Represents service orders/transactions
    
    OOP Concepts:
    - STATE MANAGEMENT: Order status changes
    - ENCAPSULATION: Status update logic
    
    DBMS Concepts:
    - Primary Key: id
    - Foreign Keys: service_id, buyer_id, seller_id
    - Many-to-One relationships
    - Index on status for filtering
    """
    
    __tablename__ = 'orders'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign Keys
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'), nullable=False, index=True)
    buyer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Order details
    total_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending', index=True)
    # Status values: 'pending', 'in_progress', 'completed', 'cancelled'
    
    # Additional details
    requirements = db.Column(db.Text)  # Buyer's requirements
    scope = db.Column(db.Text)  # Detailed scope
    budget_tier = db.Column(db.String(20)) # Basic, Standard, Premium
    deadline = db.Column(db.DateTime)  # Agreed deadline
    delivery_note = db.Column(db.Text)  # Seller's delivery note
    rejection_reason = db.Column(db.Text)  # Reason for order rejection
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    def update_status(self, new_status):
        """
        Update order status with validation
        
        OOP Concept: STATE MANAGEMENT
        
        Args:
            new_status (str): New status value
            
        Returns:
            bool: True if update successful
        """
        valid_statuses = ['pending', 'in_progress', 'completed', 'cancelled']
        if new_status in valid_statuses:
            self.status = new_status
            if new_status == 'completed':
                self.completed_at = datetime.utcnow()
            return True
        return False
    
    def calculate_platform_fee(self, fee_percentage=10):
        """
        Calculate platform fee
        
        Args:
            fee_percentage (float): Platform fee percentage
            
        Returns:
            float: Platform fee amount
        """
        return round(self.total_price * (fee_percentage / 100), 2)
    
    def __repr__(self):
        """String representation of Order object"""
        return f'<Order {self.id} - {self.status}>'


class Favorite(db.Model):
    """
    Favorite Model - Represents user's favorite services
    
    DBMS Concepts:
    - Many-to-Many relationship between Users and Services
    - Composite unique constraint to prevent duplicates
    """
    
    __tablename__ = 'favorites'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'), nullable=False, index=True)
    
    # Timestamp
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Ensure a user can't favorite the same service twice
    __table_args__ = (
        db.UniqueConstraint('user_id', 'service_id', name='unique_user_service_favorite'),
    )
    
    def __repr__(self):
        """String representation of Favorite object"""
        return f'<Favorite User {self.user_id} - Service {self.service_id}>'


class Notification(db.Model):
    """
    Notification Model - Represents user notifications
    """
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    link = db.Column(db.String(255))
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Notification {self.title}>'


class Message(db.Model):
    """
    Message Model - Chat messages for orders
    """
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False, index=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    order = db.relationship('Order', backref=db.backref('messages', lazy='dynamic'))
    sender = db.relationship('User', backref='sent_messages')


class ProjectShowcase(db.Model):
    """
    Project Showcase Model - Portfolio items for users
    """
    __tablename__ = 'project_showcase'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(255))
    link = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('portfolio', lazy='dynamic', cascade='all, delete-orphan'))

    
    def __repr__(self):
        return f'<Message {self.id} Order {self.order_id}>'


class AvailabilitySlot(db.Model):
    """
    Availability Slot Model - Represents provider's available time slots
    
    DBMS Concepts:
    - Indexing for range queries (provider_id, start_time)
    - Check Constraint via application logic (start < end)
    """
    __tablename__ = 'availability_slots'

    id = db.Column(db.Integer, primary_key=True)
    provider_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    start_time = db.Column(db.DateTime, nullable=False, index=True)
    end_time = db.Column(db.DateTime, nullable=False)
    
    is_booked = db.Column(db.Boolean, default=False, index=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    booking = db.relationship('Booking', backref='slot', uselist=False, cascade='all, delete-orphan')
    provider = db.relationship('User', backref='availability_slots')

    def __repr__(self):
        return f'<Slot {self.id} {self.start_time}>'


class Booking(db.Model):
    """
    Booking Model - Represents a client booking a slot
    """
    __tablename__ = 'bookings'

    id = db.Column(db.Integer, primary_key=True)
    slot_id = db.Column(db.Integer, db.ForeignKey('availability_slots.id'), nullable=False, unique=True)
    client_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'), nullable=True) # Optional link to specific service
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=True) # Link to the paid order
    
    status = db.Column(db.String(20), default='pending', index=True) 
    # Statuses: 'confirmed', 'completed', 'cancelled'
    
    notes = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    client = db.relationship('User', backref='bookings_made')
    service = db.relationship('Service', backref='bookings')

class Testimonial(db.Model):
    """
    Testimonial Model - Represents user testimonials
    """
    __tablename__ = 'testimonials'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    role = db.Column(db.String(100)) # Optional role/title
    rating = db.Column(db.Integer, default=5)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Establish relationship for easier access to user info (avatar, name)
    user = db.relationship('User', backref=db.backref('testimonials', lazy=True))

    def __repr__(self):
        return f'<Testimonial {self.id} by {self.user_id}>'


class Certificate(db.Model):
    """
    Certificate Model - Stores issued completion certificates.

    DBMS Concepts:
    - Primary Key: id
    - Foreign Keys: order_id, student_id, provider_id
    - Unique constraint on order_id (one cert per order)
    """

    __tablename__ = 'certificates'

    id           = db.Column(db.Integer, primary_key=True)
    cert_id      = db.Column(db.String(20), unique=True, nullable=False)
    order_id     = db.Column(db.Integer, db.ForeignKey('orders.id'), unique=True, nullable=False)
    student_id   = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    provider_id  = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    skill_name   = db.Column(db.String(200), nullable=False)
    pdf_filename = db.Column(db.String(255), nullable=False)
    issued_at    = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    order    = db.relationship('Order', backref=db.backref('certificate', uselist=False))
    student  = db.relationship('User', foreign_keys=[student_id],  backref='certificates_received')
    provider = db.relationship('User', foreign_keys=[provider_id], backref='certificates_issued')

    def __repr__(self):
        return f'<Certificate {self.cert_id} Order {self.order_id}>'


class ContactMessage(db.Model):
    """
    ContactMessage Model - Stores messages from the contact form
    """
    __tablename__ = 'contact_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<ContactMessage {self.email} - {self.subject}>'


class HiddenChat(db.Model):
    """
    HiddenChat Model - Tracks which users have hidden which chat conversations
    
    When a user "deletes" a chat from their chat list, we don't remove the order
    or messages — we just hide the conversation from that user's view.
    If a new message arrives, the chat can be un-hidden automatically.
    
    DBMS Concepts:
    - Composite unique constraint to prevent duplicate entries
    - Foreign Keys: user_id, order_id
    """
    __tablename__ = 'hidden_chats'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Ensure a user can't hide the same chat twice
    __table_args__ = (
        db.UniqueConstraint('user_id', 'order_id', name='unique_user_order_hidden'),
    )

    def __repr__(self):
        return f'<HiddenChat User {self.user_id} - Order {self.order_id}>'
