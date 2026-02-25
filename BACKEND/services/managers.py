"""
Business Logic Managers for SkillVerse Application

This module demonstrates:
1. OOP Concepts: Classes, Encapsulation, Abstraction
2. Data Structures: Dictionary, Heap, Trie, Set, Queue
3. Algorithms: Search, Sorting, Filtering

These manager classes handle business logic separately from routes (MVC pattern)

Author: SkillVerse Team
Purpose: Centralized business logic with data structure demonstrations
"""

import random
from collections import defaultdict
from data_structures import HashMap, MaxHeap, Queue, Trie
from datetime import datetime, timedelta
from models import db, Service, User, Category, Review, Order, Favorite, Notification, Message
from sqlalchemy.orm import joinedload

from flask import current_app

class ServiceManager:
    """
    Service Manager Class - Handles all service-related operations
    
    OOP Concepts:
    - ENCAPSULATION: Internal caching mechanism
    - ABSTRACTION: Simple interface for complex operations
    - SINGLETON PATTERN: Single instance manages all services
    
    Data Structures Used:
    - DICTIONARY (HashMap): For caching - O(1) lookup time
    - HEAP: For efficient top-N selection
    - SET: For unique tag management
    """
    
    def __init__(self):
        """
        Initialize ServiceManager with cache
        
        Data Structure: DICTIONARY for caching
        - Key: cache identifier (string)
        - Value: cached data
        - Benefit: O(1) lookup time for frequently accessed data
        """
        self._cache = HashMap()  # Custom HashMap (built from scratch) for O(1) caching
        self._cache_timeout = 300  # Cache timeout in seconds (5 minutes)

    def get_featured_services(self, limit=4):
        """
        Get top-rated featured services using HEAP data structure
        
        Data Structure: HEAP (Priority Queue)
        Algorithm: heapq.nlargest() for efficient top-N selection
        Time Complexity: O(n log k) where k = limit
        
        Args:
            limit (int): Number of services to return
            
        Returns:
            list: Top-rated Service objects
        """
        # Check cache first
        cache_key = f'featured_services_{limit}'
        if cache_key in self._cache:
            cached_data, timestamp = self._cache[cache_key]
            if (datetime.now() - timestamp).seconds < self._cache_timeout:
                return cached_data
        
        # Get all active AND approved services with eager loading
        # Eager load category and provider (user) to prevent DetachedInstanceError when caching
        services = Service.query.options(
            joinedload(Service.category),
            joinedload(Service.provider)
        ).filter_by(is_active=True, is_approved=True).all()
        
        # Use custom MaxHeap (built from scratch) to get top N services by rating
        # MaxHeap.nlargest uses heapify-up/down internally — O(n log k)
        featured = MaxHeap.nlargest(
            limit,
            services,
            key=lambda s: (s.get_average_rating(), s.get_review_count())
        )
        
        # Cache the result
        self._cache[cache_key] = (featured, datetime.now())
        
        return featured
    
    def search_services(self, query, filters=None):
        """
        Search services with advanced filtering
        
        Algorithm:
        1. Tokenize search query
        2. Search in title, description, and tags
        3. Apply filters (category, price range, etc.)
        4. Rank results by relevance
        
        Args:
            query (str): Search query
            filters (dict): Optional filters (category_id, min_price, max_price, etc.)
            
        Returns:
            list: Matching Service objects sorted by relevance
        """
        if not query and not filters:
            return []
        
        # Start with all active and approved services
        results = Service.query.filter_by(is_active=True, is_approved=True)
        
        # Apply text search if query provided
        if query:
            search_term = f'%{query.lower()}%'
            results = results.filter(
                db.or_(
                    Service.title.ilike(search_term),
                    Service.description.ilike(search_term),
                    Service.tags.ilike(search_term)
                )
            )
        
        # Apply filters if provided
        if filters:
            if 'category_id' in filters and filters['category_id']:
                results = results.filter_by(category_id=filters['category_id'])
            
            if 'min_price' in filters and filters['min_price']:
                results = results.filter(Service.price >= filters['min_price'])
            
            if 'max_price' in filters and filters['max_price']:
                results = results.filter(Service.price <= filters['max_price'])
        
        # Get all results
        services = results.all()
        
        # Rank by relevance (simple scoring algorithm)
        if query:
            scored_services = []
            query_lower = query.lower()
            
            for service in services:
                score = 0
                # Title match gets highest score
                if query_lower in service.title.lower():
                    score += 10
                # Tag match gets medium score
                if service.tags and query_lower in service.tags.lower():
                    score += 5
                # Description match gets lower score
                if query_lower in service.description.lower():
                    score += 2
                # Boost by rating
                score += service.get_average_rating()
                
                scored_services.append((score, service))
            
            # Sort by score (highest first)
            scored_services.sort(reverse=True, key=lambda x: x[0])
            return [service for score, service in scored_services]
        
        return services
    
    def get_recommendations(self, user, limit=6):
        """
        Get personalized service recommendations for user
        
        Algorithm:
        1. Get user's favorite categories
        2. Get user's order history
        3. Find similar services
        4. Rank by relevance
        
        Args:
            user (User): User object
            limit (int): Number of recommendations
            
        Returns:
            list: Recommended Service objects
        """
        if not user or not user.is_authenticated:
            # Return popular services for non-authenticated users
            return self.get_featured_services(limit)
        
        # Get categories from user's favorites and orders
        favorite_categories = set()
        
        # From favorites
        favorites = Favorite.query.filter_by(user_id=user.id).all()
        for fav in favorites:
            if fav.service.category_id:
                favorite_categories.add(fav.service.category_id)
        
        # From orders
        orders = Order.query.filter_by(buyer_id=user.id).all()
        for order in orders:
            if order.service.category_id:
                favorite_categories.add(order.service.category_id)
        
        # Get services from favorite categories
        if favorite_categories:
            recommendations = Service.query.filter(
                Service.category_id.in_(favorite_categories),
                Service.is_active == True,
                Service.is_approved == True
            ).limit(limit * 2).all()
            
            # Sort by rating and return top N
            recommendations.sort(
                key=lambda s: s.get_average_rating(),
                reverse=True
            )
            return recommendations[:limit]
        
        # Fallback to featured services
        return self.get_featured_services(limit)
    
    def get_all_tags(self):
        """
        Get all unique tags from services
        
        Data Structure: SET for unique values
        
        Returns:
            list: Sorted list of unique tags
        """
        # Use SET to store unique tags
        all_tags = set()
        
        services = Service.query.filter_by(is_active=True).all()
        for service in services:
            if service.tags:
                tags = service.get_tags_list()
                all_tags.update(tags)
        
        # Return sorted list
        return sorted(all_tags)
    
    def filter_by_category(self, category_id):
        """
        Get all services in a category
        
        Args:
            category_id (int): Category ID
            
        Returns:
            list: Service objects in category
        """
        return Service.query.filter_by(
            category_id=category_id,
            is_active=True
        ).all()
    
    def create_service(self, user_id, data):
        """
        Create a new service
        
        Args:
            user_id (int): Provider user ID
            data (dict): Service data
            
        Returns:
            Service: Created service object
        """
        # Handle default images if not provided
        image_url = data.get('image_url')
        if not image_url or image_url == 'default-service.jpg' or image_url.strip() == '':
            # List of high-quality default images from Unsplash
            default_images = [
                'https://images.unsplash.com/photo-1498050108023-c5249f4df085?w=500&q=80', # Coding
                'https://images.unsplash.com/photo-1542744173-8e7e53415bb0?w=500&q=80', # Analysis
                'https://images.unsplash.com/photo-1558655146-d09347e0b7a9?w=500&q=80', # Marketing
                'https://images.unsplash.com/photo-1561070791-2526d30994b5?w=500&q=80', # Design
                'https://images.unsplash.com/photo-1553877607-3fa983197609?w=500&q=80', # Discussion
                'https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=500&q=80', # Analytics
                'https://images.unsplash.com/photo-1552664730-d307ca884978?w=500&q=80'  # Team
            ]
            image_url = random.choice(default_images)
        
        # Check if the creator is admin — auto-approve admin-created services
        creator = User.query.get(user_id)
        auto_approve = creator and creator.is_admin()
        
        service = Service(
            user_id=user_id,
            title=data['title'],
            description=data['description'],
            price=data['price'],
            delivery_time=data.get('delivery_time', ''),
            category_id=data['category_id'],
            tags=data.get('tags', ''),
            image_url=image_url,
            is_approved=auto_approve
        )
        
        db.session.add(service)
        db.session.commit()
        
        # Clear cache
        self._cache.clear()
        
        # Notify all admins about the new service pending approval
        if not auto_approve:
            admins = User.query.filter_by(user_type='admin').all()
            for admin in admins:
                notification_manager.create_notification(
                    user_id=admin.id,
                    title='New Service Pending Approval 📋',
                    message=f'{creator.username} submitted "{data["title"]}" for review.',
                    link='/admin/services/pending'
                )
        
        return service

    def approve_service(self, service_id):
        """
        Approve a service (Admin only)
        
        Args:
            service_id (int): Service ID
            
        Returns:
            Service: Approved service object or None
        """
        service = Service.query.get(service_id)
        if not service:
            return None
        
        service.is_approved = True
        service.rejection_reason = None
        db.session.commit()
        
        # Clear cache so the new service appears in listings
        self._cache.clear()
        
        # Notify the provider
        notification_manager.create_notification(
            user_id=service.user_id,
            title='Service Approved! ✅',
            message=f'Your service "{service.title}" has been approved and is now live on SkillVerse.',
            link=f'/service/{service.id}'
        )
        
        return service

    def reject_service(self, service_id, reason=''):
        """
        Reject a service (Admin only)
        
        Args:
            service_id (int): Service ID
            reason (str): Rejection reason
            
        Returns:
            Service: Rejected service object or None
        """
        service = Service.query.get(service_id)
        if not service:
            return None
        
        service.is_approved = False
        service.rejection_reason = reason or 'Service does not meet community guidelines.'
        db.session.commit()
        
        # Clear cache
        self._cache.clear()
        
        # Notify the provider
        notification_manager.create_notification(
            user_id=service.user_id,
            title='Service Rejected ❌',
            message=f'Your service "{service.title}" was not approved. Reason: {service.rejection_reason}',
            link=f'/service/{service.id}'
        )
        
        return service

    def get_pending_services(self):
        """
        Get all services pending approval
        
        Returns:
            list: List of Service objects awaiting approval
        """
        return Service.query.filter_by(
            is_active=True, is_approved=False
        ).filter(
            Service.rejection_reason.is_(None)
        ).order_by(Service.created_at.desc()).all()

    def get_pending_count(self):
        """
        Get count of services pending approval
        
        Returns:
            int: Number of pending services
        """
        return Service.query.filter_by(
            is_active=True, is_approved=False
        ).filter(
            Service.rejection_reason.is_(None)
        ).count()


class UserManager:
    """
    User Manager Class - Handles user operations
    
    OOP Concepts:
    - ENCAPSULATION: User authentication logic
    - ABSTRACTION: Simple interface for user management
    """
    
    def authenticate(self, email, password):
        """
        Authenticate user with email and password
        
        Args:
            email (str): User email
            password (str): Plain text password
            
        Returns:
            User: User object if authenticated, None otherwise
        """
        if email:
            email = email.lower().strip()
            
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            return user
        
        return None
    
    def create_user(self, data):
        """
        Create new user with validation
        
        Args:
            data (dict): User data (username, email, password, user_type)
            
        Returns:
            tuple: (User object or None, error message or None)
        """
        # Normalize email
        if 'email' in data:
            data['email'] = data['email'].lower().strip()
            
        # Check if email already exists
        if User.query.filter_by(email=data['email']).first():
            return None, "Email already registered"
        
        # Check if username already exists
        if User.query.filter_by(username=data['username']).first():
            return None, "Username already taken"
        
        # Set default avatar if not provided
        # Use UI Avatars API for consistent, nice default avatars
        username = data['username']
        default_avatar = f"https://ui-avatars.com/api/?name={username}&background=random&color=fff"
        
        # Create new user
        user = User(
            username=data['username'],
            email=data['email'],
            user_type=data.get('user_type', 'client'),
            full_name=data.get('full_name', ''),
            avatar_url=default_avatar
        )
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.commit()
        
        # Send welcome notification (placeholder call)
        # In a real app, we would use NotificationManager here
        
        return user, None
    
    def get_user_stats(self, user_id):
        """
        Calculate user statistics
        
        Returns:
            dict: User statistics
        """
        user = User.query.get(user_id)
        if not user:
            return {}
        
        stats = {
            'total_services': user.services.filter_by(is_active=True).count(),
            'total_reviews': user.get_total_reviews(),
            'average_rating': user.get_average_rating(),
            'total_orders_as_seller': user.orders_as_seller.count(),
            'total_orders_as_buyer': user.orders_as_buyer.count(),
            'completed_projects': user.orders_as_seller.filter_by(status='completed').count(),
            'member_since': user.created_at.strftime('%B %Y')
        }
        
        return stats


class SearchEngine:
    """
    Advanced Search Engine with Autocomplete
    
    Data Structures (Built from scratch in data_structures.py):
    - TRIE: For efficient prefix-based autocomplete — O(L) lookup
    - HASHMAP: For O(1) average-case caching of suggestions
    """
    
    def __init__(self):
        """
        Initialize search engine with custom data structures
        
        Uses:
        - HashMap (custom built): For caching autocomplete results
        - Trie (custom built): For efficient prefix-based word lookups
        """
        self.suggestions_cache = HashMap()  # Custom HashMap for caching
        self._trie = Trie()                 # Custom Trie for autocomplete
        self._trie_built_at = None          # Timestamp for freshness check
        self._trie_timeout = 300            # Rebuild Trie every 5 minutes
    
    def _build_trie(self):
        """
        Build/rebuild the Trie from all active service titles and tags.
        
        Algorithm:
        1. Query all active, approved services from database
        2. Insert each service title into the Trie
        3. Insert each individual tag into the Trie
        4. Record build timestamp for freshness tracking
        
        Time Complexity: O(N * L) where N = number of services, L = avg title length
        """
        self._trie = Trie()  # Reset Trie
        services = Service.query.filter_by(is_active=True, is_approved=True).all()
        for service in services:
            # Insert full title into Trie
            self._trie.insert(service.title)
            # Insert individual tags into Trie
            if service.tags:
                for tag in service.get_tags_list():
                    self._trie.insert(tag)
        self._trie_built_at = datetime.now()
    
    def _ensure_trie_fresh(self):
        """Ensure the Trie is built and not stale. Rebuilds if older than timeout."""
        if (self._trie_built_at is None or 
            (datetime.now() - self._trie_built_at).seconds > self._trie_timeout):
            self._build_trie()
    
    def get_autocomplete_suggestions(self, query, limit=5):
        """
        Get autocomplete suggestions using custom Trie data structure.
        
        Algorithm:
        1. Check custom HashMap cache for previously computed results — O(1)
        2. Ensure Trie is built and fresh
        3. Use Trie prefix search for O(L) lookup (L = query length)
        4. Cache result in HashMap for future O(1) retrieval
        
        Args:
            query (str): Partial search query (prefix)
            limit (int): Maximum suggestions to return
            
        Returns:
            list: Suggestion strings matching the prefix
        """
        if not query or len(query) < 2:
            return []
        
        # Check custom HashMap cache first — O(1) average lookup
        cache_key = query.lower()
        if cache_key in self.suggestions_cache:
            return self.suggestions_cache[cache_key]
        
        # Ensure Trie is built and fresh
        self._ensure_trie_fresh()
        
        # Use Trie prefix search — O(L) traversal to prefix node
        result = self._trie.get_suggestions(query, limit)
        
        # Cache in custom HashMap — O(1) average insertion
        self.suggestions_cache[cache_key] = result
        
        return result
    
    def search_by_tags(self, tags):
        """
        Search services by multiple tags
        
        Args:
            tags (list): List of tag strings
            
        Returns:
            list: Matching services
        """
        if not tags:
            return []
        
        # Find services that match any of the tags
        services = []
        for tag in tags:
            search_term = f'%{tag}%'
            matching = Service.query.filter(
                Service.is_active == True,
                Service.tags.ilike(search_term)
            ).all()
            services.extend(matching)
        
        # Remove duplicates using SET
        unique_services = list(set(services))
        
        return unique_services


class ReviewSystem:
    """
    Review Management System
    
    OOP Concepts:
    - VALIDATION: Review validation
    - BUSINESS LOGIC: Rating calculations
    """
    
    def add_review(self, service_id, user_id, rating, comment):
        """
        Add review with validation
        
        Args:
            service_id (int): Service ID
            user_id (int): Reviewer user ID
            rating (int): Rating (1-5)
            comment (str): Review comment
            
        Returns:
            tuple: (Review object or None, error message or None)
        """
        # Validate rating
        if not (1 <= rating <= 5):
            return None, "Rating must be between 1 and 5"
        
        # Check if user already reviewed this service
        existing = Review.query.filter_by(
            service_id=service_id,
            user_id=user_id
        ).first()
        
        if existing:
            return None, "You have already reviewed this service"
        
        # Create review
        review = Review(
            service_id=service_id,
            user_id=user_id,
            rating=rating,
            comment=comment
        )
        
        db.session.add(review)
        db.session.commit()
        
        # Clear the featured services cache so ratings stay in sync
        # across Featured Services (homepage) and Browse Skills pages
        service_manager._cache.clear()
        
        return review, None
    
    def get_service_reviews(self, service_id, limit=None):
        """
        Get reviews for a service
        
        Args:
            service_id (int): Service ID
            limit (int): Optional limit
            
        Returns:
            list: Review objects
        """
        query = Review.query.filter_by(service_id=service_id)\
                           .order_by(Review.created_at.desc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def calculate_rating_distribution(self, service_id):
        """
        Calculate rating distribution for a service
        
        Returns:
            dict: Rating distribution (1-5 stars with counts)
        """
        reviews = Review.query.filter_by(service_id=service_id).all()
        
        # Initialize distribution dictionary
        distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        
        for review in reviews:
            distribution[review.rating] += 1
        
        return distribution


class OrderManager:
    """
    Order Management System
    
    Data Structure: QUEUE for order processing
    OOP Concepts: STATE MANAGEMENT
    """
    
    def __init__(self):
        """
        Initialize with order queue
        
        Data Structure: DEQUE (Double-ended queue)
        - Efficient for adding/removing from both ends
        - Used for order processing queue
        """
        self.processing_queue = Queue()  # Custom Queue (built from scratch) for order processing
    
    def create_order(self, service_id, buyer_id, requirements='', scope='', budget_tier='Standard', deadline=None):
        """
        Create new order
        
        Args:
            service_id (int): Service ID
            buyer_id (int): Buyer user ID
            requirements (str): Order requirements
            scope (str): Detailed scope
            budget_tier (str): Budget tier
            deadline (datetime): Agreed deadline
            
        Returns:
            Order: Created order object
        """
        service = Service.query.get(service_id)
        if not service:
            return None
            
        # Pricing Logic based on Tier
        price = service.price
        if budget_tier == 'Basic':
            price = price * 0.80  # 20% Less
        elif budget_tier == 'Premium':
            price = price * 1.50  # 50% Extra
        # Standard: Base Price
            
        order = Order(
            service_id=service_id,
            buyer_id=buyer_id,
            seller_id=service.user_id,
            total_price=round(price), # Round to nearest integer for clean display
            requirements=requirements,
            scope=scope,
            budget_tier=budget_tier,
            deadline=deadline
        )
        
        db.session.add(order)
        db.session.commit()
        
        # Add to processing queue
        self.processing_queue.append(order.id)
        
        # Send notification to seller about new order
        buyer = User.query.get(buyer_id)
        if buyer:
            notification = Notification(
                user_id=service.user_id,
                title='New Order! 🎉',
                message=f'{buyer.username} has purchased your service "{service.title}" ({budget_tier} package) for ₹{round(price)}.',
                link=f'/user/orders'
            )
            db.session.add(notification)
            db.session.commit()
        
        return order
    
    def accept_order(self, order_id):
        """Provider accepts order"""
        order = Order.query.get(order_id)
        if order and order.status == 'pending':
            order.update_status('in_progress')
            db.session.commit()
            return True
        return False

    def complete_order(self, order_id):
        """Provider marks order as complete"""
        order = Order.query.get(order_id)
        if order and order.status == 'in_progress':
            order.update_status('completed')
            db.session.commit()
            return True
        return False
        

    
    def get_user_orders(self, user_id, as_buyer=True):
        """
        Get orders for a user
        
        Args:
            user_id (int): User ID
            as_buyer (bool): True for buyer orders, False for seller orders
            
        Returns:
            list: Order objects
        """
        if as_buyer:
            return Order.query.filter_by(buyer_id=user_id)\
                             .order_by(Order.created_at.desc()).all()
        else:
            return Order.query.filter_by(seller_id=user_id)\
                             .order_by(Order.created_at.desc()).all()
    
    def update_order_status(self, order_id, new_status):
        """
        Update order status
        
        Args:
            order_id (int): Order ID
            new_status (str): New status
            
        Returns:
            bool: True if successful
        """
        order = Order.query.get(order_id)
        if order:
            return order.update_status(new_status)
        return False


class CategoryManager:
    """
    Category Management System
    
    OOP Concepts:
    - CRUD operations for categories
    - Dynamic category management
    """
    
    def get_all_categories(self):
        """
        Get all categories with service counts
        
        Returns:
            list: Category objects
        """
        return Category.query.all()
    
    def create_category(self, name, description='', icon='', color=''):
        """
        Create new category (Admin function)
        
        Args:
            name (str): Category name
            description (str): Category description
            icon (str): Icon class name
            color (str): Color class
            
        Returns:
            Category: Created category object
        """
        # Check if category already exists
        existing = Category.query.filter_by(name=name).first()
        if existing:
            return None
        
        category = Category(
            name=name,
            description=description,
            icon=icon,
            color=color
        )
        
        db.session.add(category)
        db.session.commit()
        
        return category
    
    def get_category_stats(self):
        """
        Get statistics for all categories
        
        Returns:
            list: Category stats with service counts
        """
        categories = self.get_all_categories()
        stats = []
        
        for category in categories:
            stats.append({
                'id': category.id,
                'name': category.name,
                'service_count': category.get_service_count(),
                'icon': category.icon,
                'color': category.color
            })
        
        return stats


class NotificationManager:
    """
    Notification Management System
    
    Handles creation and retrieval of user notifications
    """
    
    def create_notification(self, user_id, title, message, link=None):
        """Create a new notification"""
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            link=link
        )
        db.session.add(notification)
        db.session.commit()
        return notification
    
    def get_unread_count(self, user_id):
        """Get number of unread notifications"""
        return Notification.query.filter_by(user_id=user_id, is_read=False).count()
    
    def mark_as_read(self, notification_id):
        """Mark notification as read"""
        notification = Notification.query.get(notification_id)
        if notification:
            notification.is_read = True
            db.session.commit()
            return True
        return False
    
    def get_user_notifications(self, user_id, limit=10):
        """Get latest notifications"""
        return Notification.query.filter_by(user_id=user_id)\
            .order_by(Notification.created_at.desc())\
            .limit(limit).all()

    def mark_all_read(self, user_id):
        """Mark all notifications as read for a user"""
        Notification.query.filter_by(user_id=user_id, is_read=False).update({'is_read': True})
        db.session.commit()
        return True

    def delete_notification(self, notification_id):
        """Delete a single notification"""
        notification = Notification.query.get(notification_id)
        if notification:
            db.session.delete(notification)
            db.session.commit()
            return True
        return False

    def clear_all(self, user_id):
        """Delete all notifications for a user"""
        Notification.query.filter_by(user_id=user_id).delete()
        db.session.commit()
        return True



class ChatManager:
    """
    Chat Management System for Orders
    """
    def send_message(self, order_id, sender_id, content):
        """Send a message in an order chat"""
        from models import HiddenChat
        
        # Verify sender is part of order
        order = Order.query.get(order_id)
        if not order:
            return None, "Order not found"
            
        if sender_id not in [order.buyer_id, order.seller_id]:
            return None, "Unauthorized"
            
        message = Message(
            order_id=order_id,
            sender_id=sender_id,
            content=content
        )
        
        db.session.add(message)
        
        # Auto-unhide the chat for the receiver when a new message arrives
        receiver_id = order.buyer_id if sender_id == order.seller_id else order.seller_id
        hidden = HiddenChat.query.filter_by(user_id=receiver_id, order_id=order_id).first()
        if hidden:
            db.session.delete(hidden)
        
        db.session.commit()
        
        return message, None

    def get_messages(self, order_id, user_id):
        """Get messages for an order"""
        # Verify permissions
        order = Order.query.get(order_id)
        if not order:
            return []
            
        if user_id not in [order.buyer_id, order.seller_id] and not User.query.get(user_id).is_admin():
            return []
            
        return Message.query.filter_by(order_id=order_id).order_by(Message.created_at).all()

    def get_active_chats(self, user_id):
        """
        Get all active chats for a user (pending or in_progress only),
        excluding chats the user has hidden/deleted.
        
        Args:
            user_id (int): User ID
            
        Returns:
            list: List of Order objects that represent active chats
        """
        from models import HiddenChat
        
        # Get IDs of chats hidden by this user
        hidden_order_ids = db.session.query(HiddenChat.order_id).filter(
            HiddenChat.user_id == user_id
        ).subquery()
        
        # Find orders where the user is buyer or seller AND status is active
        # AND the chat is not hidden by this user
        orders = Order.query.filter(
            db.or_(Order.buyer_id == user_id, Order.seller_id == user_id),
            Order.status.in_(['pending', 'in_progress']),
            ~Order.id.in_(hidden_order_ids)
        ).order_by(Order.updated_at.desc()).all()
        
        return orders

    def hide_chat(self, order_id, user_id):
        """
        Hide a chat from the user's chat list (soft delete).
        The chat will reappear if a new message is sent.
        
        Args:
            order_id (int): Order/Chat ID
            user_id (int): User ID
            
        Returns:
            bool: True if successful
        """
        from models import HiddenChat
        
        # Verify user is part of this order
        order = Order.query.get(order_id)
        if not order:
            return False
        if user_id not in [order.buyer_id, order.seller_id]:
            return False
        
        # Check if already hidden
        existing = HiddenChat.query.filter_by(user_id=user_id, order_id=order_id).first()
        if existing:
            return True  # Already hidden
        
        hidden = HiddenChat(user_id=user_id, order_id=order_id)
        db.session.add(hidden)
        db.session.commit()
        return True

    def clear_all_chats(self, user_id):
        """
        Hide all active chats for a user (clear all).
        
        Args:
            user_id (int): User ID
            
        Returns:
            bool: True if successful
        """
        from models import HiddenChat
        
        # Get all active chat order IDs for this user
        active_orders = Order.query.filter(
            db.or_(Order.buyer_id == user_id, Order.seller_id == user_id),
            Order.status.in_(['pending', 'in_progress'])
        ).all()
        
        for order in active_orders:
            existing = HiddenChat.query.filter_by(user_id=user_id, order_id=order.id).first()
            if not existing:
                hidden = HiddenChat(user_id=user_id, order_id=order.id)
                db.session.add(hidden)
        
        db.session.commit()
        return True


class AvailabilityManager:
    """
    Availability Management System
    
    Handles provider calendar slots and bookings.
    """
    
    def get_provider_slots(self, provider_id, start_date, end_date):
        """
        Get slots for a provider within a date range
        """
        from models import AvailabilitySlot, User, Booking
        
        # 1. Get SkillVerse Slots
        slots = AvailabilitySlot.query.filter(
            AvailabilitySlot.provider_id == provider_id,
            AvailabilitySlot.start_time >= start_date,
            AvailabilitySlot.start_time <= end_date
        ).order_by(AvailabilitySlot.start_time).all()
        
        # Self-healing: Ensure is_booked flag matches actual Booking table state
        # This fixes "Ghost Availability" where slot shows green but booking fails
        consistency_fix = False
        for slot in slots:
            if not slot.is_booked:
                active_booking = Booking.query.filter_by(slot_id=slot.id).first()
                if active_booking and active_booking.status not in ['cancelled', 'rejected']:
                    slot.is_booked = True
                    consistency_fix = True
        
        if consistency_fix:
            try:
                db.session.commit()
            except:
                db.session.rollback()
        
        return slots



    def create_slots(self, provider_id, start_time, end_time, is_recurring=False, weeks=12):
        """
        Create availability slot(s)
        If is_recurring=True, creates slots for the next 'weeks' weeks
        """
        from models import AvailabilitySlot
        
        # Validation: start < end
        if start_time >= end_time:
            return None, "End time must be after start time"
            
        created_count = 0
        error_count = 0
        
        # Determine number of iterations
        iterations = weeks if is_recurring else 1
        
        current_start = start_time
        current_end = end_time
        
        for i in range(iterations):
            # Check overlap for this specific instance
            overlap = AvailabilitySlot.query.filter(
                AvailabilitySlot.provider_id == provider_id,
                AvailabilitySlot.start_time < current_end,
                AvailabilitySlot.end_time > current_start
            ).first()
            
            if not overlap:
                slot = AvailabilitySlot(
                    provider_id=provider_id,
                    start_time=current_start,
                    end_time=current_end
                )
                db.session.add(slot)
                created_count += 1
            else:
                error_count += 1
            
            # Move to next week
            current_start += timedelta(weeks=1)
            current_end += timedelta(weeks=1)
            
        db.session.commit()
        
        if created_count == 0 and error_count > 0:
            return None, "All selected slots overlap with existing availability"
            
        return {"created": created_count, "skipped": error_count}, None

    def delete_slot(self, slot_id, provider_id):
        """Delete a slot if not booked"""
        from models import AvailabilitySlot
        
        slot = AvailabilitySlot.query.get(slot_id)
        if not slot:
            return False, "Slot not found"
            
        if slot.provider_id != provider_id:
            return False, "Unauthorized"
            
        if slot.is_booked:
            return False, "Cannot delete booked slot"
            
        db.session.delete(slot)
        db.session.commit()
        return True, None

    def book_slot(self, slot_id, client_id, service_id=None, notes='', order_id=None):
        """
        Book a slot
        Uses transaction to prevent double booking
        Includes self-healing for data inconsistencies
        """
        from models import AvailabilitySlot, Booking
        
        try:
            # Start transaction (implicit in SQLAlchemy commit)
            slot = AvailabilitySlot.query.with_for_update().get(slot_id)
            
            if not slot:
                return None, "Slot not found"
                
            from datetime import datetime, timezone
            if slot.start_time < datetime.now(timezone.utc).replace(tzinfo=None):
                return None, "Cannot book a time slot in the past"
            
            # SELF-HEALING: Check for existing bookings and clean up stale ones
            existing_booking = Booking.query.filter_by(slot_id=slot_id).first()
            if existing_booking:
                if existing_booking.status in ['cancelled', 'rejected']:
                    # Clean up cancelled/rejected booking and reset slot
                    db.session.delete(existing_booking)
                    slot.is_booked = False
                    db.session.flush()
                elif slot.is_booked:
                    # Genuinely booked - cannot book
                    return None, "Slot already booked"
                else:
                    # Inconsistency: booking exists but slot not marked booked
                    # This shouldn't happen, but if it does, the booking is active
                    return None, "Slot has an active booking"
            else:
                # No booking record exists - ensure slot is marked available
                if slot.is_booked:
                    # SELF-HEALING: Slot marked booked but no booking exists - fix it
                    slot.is_booked = False
                    db.session.flush()
                    
            # Now the slot should be available - proceed with booking
            slot.is_booked = True
            
            booking = Booking(
                slot_id=slot.id,
                client_id=client_id,
                service_id=service_id,
                order_id=order_id,
                notes=notes,
                status='pending'
            )
            
            db.session.add(booking)
            db.session.commit()
            return booking, None
            
        except Exception as e:
            db.session.rollback()
            return None, str(e)

    def cancel_booking(self, booking_id, user_id):
        """Cancel a booking (client or provider)"""
        from models import Booking
        
        booking = Booking.query.get(booking_id)
        if not booking:
            return False, "Booking not found"
            
        # Check permission
        if user_id != booking.client_id and user_id != booking.slot.provider_id:
            return False, "Unauthorized"
            
        if booking.status == 'cancelled':
            return False, "Already cancelled"
            
        booking.status = 'cancelled'
        booking.slot.is_booked = False
        
        db.session.commit()
        return True, None

    def approve_booking(self, booking_id, provider_id):
        """Approve a booking and create an order if needed"""
        from models import Booking, Order
        
        booking = Booking.query.get(booking_id)
        if not booking:
            return False, "Booking not found"
            
        if booking.slot.provider_id != provider_id:
            return False, "Unauthorized"
            
        if booking.status == 'confirmed':
            return False, "Already confirmed"
            
        booking.status = 'confirmed'
        
        # Create Order if not exists
        if not booking.order_id:
            service = booking.service
            if service:
                from managers import order_manager
                order = order_manager.create_order(
                    service_id=service.id,
                    buyer_id=booking.client_id,
                    requirements=f"Booking for {booking.slot.start_time}",
                    scope="Consultation",
                    budget_tier="Standard"
                )
                if order:
                     booking.order_id = order.id
                     # Order stays 'pending' — seller must press Accept Order on order page
        # If order already exists, it stays in its current status (pending)
        # The seller must manually accept the order from the order detail page
            
        db.session.commit()
        return True, None

    def reject_booking(self, booking_id, provider_id):
        """Reject a booking"""
        from models import Booking
        
        booking = Booking.query.get(booking_id)
        if not booking:
            return False, "Booking not found"
            
        if booking.slot.provider_id != provider_id:
            return False, "Unauthorized"
            
        booking.status = 'cancelled'
        booking.slot.is_booked = False
        
        db.session.commit()
        return True, None


# Create singleton instances
service_manager = ServiceManager()
user_manager = UserManager()
search_engine = SearchEngine()
review_system = ReviewSystem()
order_manager = OrderManager()
category_manager = CategoryManager()
notification_manager = NotificationManager()
chat_manager = ChatManager()
availability_manager = AvailabilityManager()
