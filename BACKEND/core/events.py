"""
Socket.IO Event Handlers for Real-Time Chat

This module handles WebSocket events for real-time messaging
"""

from flask import request
from flask_login import current_user
from flask_socketio import emit, join_room, leave_room
from models import db, Message, Order
from managers import chat_manager
import pytz

# Global set to track online users (simple in-memory storage)
# In production with multiple workers, use Redis
online_users = set()

def register_socketio_events(socketio):
    """Register all socket.io event handlers"""
    
    @socketio.on('connect')
    def handle_connect():
        """Handle client connection"""
        if current_user.is_authenticated:
            online_users.add(current_user.id)
            print(f'User {current_user.username} connected')
            # Broadcast user online status
            socketio.emit('user_status', {'user_id': current_user.id, 'status': 'online'})
        
    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        if current_user.is_authenticated:
            if current_user.id in online_users:
                online_users.remove(current_user.id)
            print(f'User {current_user.username} disconnected')
            # Broadcast user offline status
            socketio.emit('user_status', {'user_id': current_user.id, 'status': 'offline'})

    @socketio.on('check_users_status')
    def handle_check_status(data):
        """Check status for a list of user IDs"""
        user_ids = data.get('user_ids', [])
        status_map = {}
        for uid in user_ids:
            uid = int(uid) # Ensure int
            status_map[uid] = 'online' if uid in online_users else 'offline'
        
        emit('users_status_response', status_map)
    
    @socketio.on('join')
    def handle_join(data):
        """Join a chat room (order-based)"""
        if not current_user.is_authenticated:
            return
        
        order_id = data.get('order_id')
        if not order_id:
            return
        
        # Verify user is part of this order
        order = Order.query.get(order_id)
        if not order or current_user.id not in [order.buyer_id, order.seller_id]:
            return
        
        room = f'order_{order_id}'
        join_room(room)
        emit('joined', {'order_id': order_id}, room=room)
        print(f'User {current_user.username} joined room {room}')
    
    @socketio.on('leave')
    def handle_leave(data):
        """Leave a chat room"""
        if not current_user.is_authenticated:
            return
        
        order_id = data.get('order_id')
        if not order_id:
            return
        
        room = f'order_{order_id}'
        leave_room(room)
        print(f'User {current_user.username} left room {room}')
    
    @socketio.on('send_message')
    def handle_send_message(data):
        """Handle incoming chat message"""
        if not current_user.is_authenticated:
            return
        
        order_id = data.get('order_id')
        content = data.get('content')
        
        if not order_id or not content:
            return
        
        # Save message to database
        message, error = chat_manager.send_message(order_id, current_user.id, content)
        
        if error:
            emit('error', {'message': error})
            return
        
        # Create notification for the recipient (with rate limiting)
        order = Order.query.get(order_id)
        if order:
            from models import Notification
            from flask import url_for
            from datetime import datetime, timedelta
            
            # Determine who should receive the notification (the other person)
            if current_user.id == order.buyer_id:
                recipient_id = order.seller_id
            else:
                recipient_id = order.buyer_id
            
            # Rate limiting: Check if there's already an unread notification 
            # for this order from this sender within the last 5 minutes
            five_mins_ago = datetime.utcnow() - timedelta(minutes=5)
            existing_notification = Notification.query.filter(
                Notification.user_id == recipient_id,
                Notification.title == 'New Message 💬',
                Notification.link.contains(str(order_id)),
                Notification.is_read == False,
                Notification.created_at >= five_mins_ago
            ).first()
            
            # Only create notification if no recent unread notification exists
            if not existing_notification:
                notification = Notification(
                    user_id=recipient_id,
                    title='New Message 💬',
                    message=f'{current_user.username} sent you a message in Order #{order_id}',
                    link=url_for('user.order_detail', order_id=order_id)
                )
                db.session.add(notification)
                db.session.commit()
        
        # Convert to IST for display
        ist_tz = pytz.timezone('Asia/Kolkata')
        created_at = message.created_at
        if created_at.tzinfo is None:
            utc_tz = pytz.UTC
            created_at = utc_tz.localize(created_at)
        ist_time = created_at.astimezone(ist_tz)
        
        # Broadcast to room
        room = f'order_{order_id}'
        emit('new_message', {
            'id': message.id,
            'sender_id': message.sender_id,
            'sender_name': current_user.username,
            'content': message.content,
            'created_at': ist_time.isoformat(),
            'time_display': ist_time.strftime('%I:%M %p')
        }, room=room)

