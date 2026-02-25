from flask import Blueprint, request, jsonify, current_app
# NOTE: If not using Flask-Login, adjust the following import and user logic
from flask_login import current_user
from chat_manager import chat_manager
from models import Service, db
from sqlalchemy import desc, func

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/ask', methods=['POST'])
def ask():
    if not current_app.config.get('ENABLE_ASKVERA'):
        return jsonify({"error": "Feature disabled"}), 404
        
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({"error": "Message required"}), 400
        
    user_message = data['message']
    context = data.get('context', {})
    
    # Add service data to context for better recommendations
    try:
        # Get recent services (last 5)
        recent_services = Service.query.filter_by(is_approved=True).order_by(desc(Service.created_at)).limit(5).all()
        context['recent_services'] = [
            {
                'title': s.title,
                'price': s.price,
                'provider': s.provider.full_name if s.provider else 'Unknown',
                'category': s.category.name if s.category else 'Uncategorized'
            } for s in recent_services
        ]
        
        # Get high rated services (top 5 by average rating)
        high_rated = db.session.query(
            Service,
            func.avg(Service.reviews.property.mapper.class_.rating).label('avg_rating')
        ).join(Service.reviews).filter(Service.is_approved == True).group_by(Service.id).order_by(desc('avg_rating')).limit(5).all()
        
        context['high_rated_services'] = [
            {
                'title': s.title,
                'price': s.price,
                'provider': s.provider.full_name if s.provider else 'Unknown',
                'rating': round(float(rating), 1) if rating else 0
            } for s, rating in high_rated
        ] if high_rated else []
        
        # Get total service count
        context['total_services'] = Service.query.filter_by(is_approved=True).count()
        
    except Exception as e:
        print(f"Error fetching service data: {e}")
        # Continue without service data
    
    # Determine Identity (Edit this if your User model differs)
    if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
        user_identity = f"user_{current_user.id}"
        # Check user type
        if current_user.user_type == 'admin':
            user_role = 'admin'
        elif current_user.user_type == 'provider':
            user_role = 'provider'
        else:
            user_role = 'client'
    else:
        user_identity = f"ip_{request.remote_addr}"
        user_role = 'guest'
        
    result = chat_manager.get_response(user_message, context, user_identity, user_role)
    return jsonify(result)

@chat_bp.route('/init', methods=['GET'])
def init_chat():
    if not current_app.config.get('ENABLE_ASKVERA'):
        return jsonify({"error": "Feature disabled"}), 404

    # Reuse role logic
    if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
        if current_user.user_type == 'admin':
            user_role = 'admin'
        elif current_user.user_type == 'provider':
            user_role = 'provider'
        else:
            user_role = 'client'
    else:
        user_role = 'guest'
        
    suggestions = chat_manager.get_initial_suggestions(user_role)
    return jsonify({"suggestions": suggestions})
