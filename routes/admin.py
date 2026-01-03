from flask import Blueprint, jsonify
from models import db, User, Event, EventAttendee
from utils.helpers import token_required, admin_required

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/stats', methods=['GET'])
@token_required
@admin_required
def get_stats():
    total_events = Event.query.count()
    total_users = User.query.count()
    active_events = Event.query.filter_by(is_active=True).count()
    total_registrations = EventAttendee.query.count()
    
    category_stats = db.session.query(
        Event.category,
        db.func.count(Event.id).label('count')
    ).group_by(Event.category).all()
    
    recent_events = Event.query.order_by(Event.created_at.desc()).limit(5).all()
    
    return jsonify({
        'total_events': total_events,
        'total_users': total_users,
        'active_events': active_events,
        'total_registrations': total_registrations,
        'events_by_category': dict(category_stats),
        'recent_events': [event.to_dict() for event in recent_events]
    }), 200