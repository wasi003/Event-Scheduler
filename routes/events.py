from flask import Blueprint, request, jsonify, g
from datetime import datetime
from models import (
    db,
    Event,
    EventAttendee,
    Resource,
    EventResourceAllocation
)
from utils.helpers import token_required, admin_required
from utils.conflict_checker import has_resource_conflict

events_bp = Blueprint('events', __name__)

# =====================================================
# GET ALL EVENTS
# =====================================================
@events_bp.route('/', methods=['GET'])
def get_events():
    try:
        category = request.args.get('category')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        location = request.args.get('location')
        organizer = request.args.get('organizer')
        active_only = request.args.get('active_only', 'true').lower() == 'true'

        query = Event.query

        if active_only:
            query = query.filter_by(is_active=True)

        if category:
            query = query.filter_by(category=category)

        if location:
            query = query.filter(Event.location.ilike(f'%{location}%'))

        if organizer:
            from models import User
            query = query.join(User).filter(User.username.ilike(f'%{organizer}%'))

        if start_date:
            try:
                start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                query = query.filter(Event.start_time >= start)
            except ValueError:
                pass

        if end_date:
            try:
                end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                query = query.filter(Event.start_time <= end)
            except ValueError:
                pass

        sort_by = request.args.get('sort_by', 'start_time')
        sort_order = request.args.get('sort_order', 'asc')

        if sort_by == 'created_at':
            sort_column = Event.created_at
        elif sort_by == 'title':
            sort_column = Event.title
        else:
            sort_column = Event.start_time

        query = query.order_by(
            sort_column.desc() if sort_order.lower() == 'desc' else sort_column.asc()
        )

        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 10)), 100)

        paginated_events = query.paginate(
            page=page, per_page=per_page, error_out=False
        )

        return jsonify({
            'events': [event.to_dict() for event in paginated_events.items],
            'total': paginated_events.total,
            'page': paginated_events.page,
            'per_page': paginated_events.per_page,
            'pages': paginated_events.pages
        }), 200

    except Exception as e:
        return jsonify({'message': str(e)}), 500


# =====================================================
# GET SINGLE EVENT
# =====================================================
@events_bp.route('/<int:event_id>', methods=['GET'])
def get_event(event_id):
    event = Event.query.get_or_404(event_id)
    return jsonify(event.to_dict()), 200


# =====================================================
# CREATE EVENT
# =====================================================
@events_bp.route('/', methods=['POST'])
@token_required
def create_event():
    try:
        data = request.json

        if not data.get('title') or not data.get('start_time') or not data.get('end_time'):
            return jsonify({'message': 'Missing required fields!'}), 400

        start_time = datetime.fromisoformat(data['start_time'].replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(data['end_time'].replace('Z', '+00:00'))

        if start_time >= end_time:
            return jsonify({'message': 'End time must be after start time!'}), 400

        event = Event(
            title=data['title'],
            description=data.get('description', ''),
            start_time=start_time,
            end_time=end_time,
            location=data.get('location'),
            category=data.get('category'),
            max_attendees=data.get('max_attendees'),
            user_id=g.current_user.id
        )

        db.session.add(event)
        db.session.commit()

        return jsonify({
            'message': 'Event created successfully!',
            'event': event.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'message': str(e)}), 500


# =====================================================
# UPDATE EVENT
# =====================================================
@events_bp.route('/<int:event_id>', methods=['PUT'])
@token_required
def update_event(event_id):
    event = Event.query.get_or_404(event_id)

    if event.user_id != g.current_user.id and not g.current_user.is_admin:
        return jsonify({'message': 'You can only update your own events!'}), 403

    try:
        data = request.json

        for field in ['title', 'description', 'location', 'category', 'max_attendees', 'is_active']:
            if field in data:
                setattr(event, field, data[field])

        if 'start_time' in data:
            event.start_time = datetime.fromisoformat(data['start_time'].replace('Z', '+00:00'))
        if 'end_time' in data:
            event.end_time = datetime.fromisoformat(data['end_time'].replace('Z', '+00:00'))

        if event.start_time >= event.end_time:
            return jsonify({'message': 'End time must be after start time!'}), 400

        db.session.commit()

        return jsonify({
            'message': 'Event updated successfully!',
            'event': event.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'message': str(e)}), 500


# =====================================================
# DELETE EVENT
# =====================================================
@events_bp.route('/<int:event_id>', methods=['DELETE'])
@token_required
def delete_event(event_id):
    event = Event.query.get_or_404(event_id)

    if event.user_id != g.current_user.id and not g.current_user.is_admin:
        return jsonify({'message': 'You can only delete your own events!'}), 403

    try:
        db.session.delete(event)
        db.session.commit()
        return jsonify({'message': 'Event deleted successfully!'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'message': str(e)}), 500


# =====================================================
# REGISTER / UNREGISTER
# =====================================================
@events_bp.route('/<int:event_id>/register', methods=['POST'])
@token_required
def register_for_event(event_id):
    event = Event.query.get_or_404(event_id)

    if not event.is_active or not event.check_availability():
        return jsonify({'message': 'Event unavailable!'}), 400

    existing = EventAttendee.query.filter_by(
        user_id=g.current_user.id,
        event_id=event_id
    ).first()

    if existing:
        return jsonify({'message': 'Already registered!'}), 400

    registration = EventAttendee(
        user_id=g.current_user.id,
        event_id=event_id
    )

    event.current_attendees += 1

    db.session.add(registration)
    db.session.commit()

    return jsonify({'message': 'Registered successfully!'}), 201


@events_bp.route('/<int:event_id>/unregister', methods=['POST'])
@token_required
def unregister_from_event(event_id):
    registration = EventAttendee.query.filter_by(
        user_id=g.current_user.id,
        event_id=event_id
    ).first_or_404()

    event = Event.query.get(event_id)
    if event:
        event.current_attendees = max(0, event.current_attendees - 1)

    db.session.delete(registration)
    db.session.commit()

    return jsonify({'message': 'Unregistered successfully!'}), 200


# =====================================================
# RESOURCE ALLOCATION WITH CONFLICT DETECTION 🔥
# =====================================================
@events_bp.route('/<int:event_id>/allocate-resource', methods=['POST'])
@token_required
def allocate_resource(event_id):
    data = request.json
    resource_id = data.get('resource_id')

    if not resource_id:
        return jsonify({'message': 'Resource ID required'}), 400

    event = Event.query.get_or_404(event_id)
    resource = Resource.query.get_or_404(resource_id)

    conflict_event = has_resource_conflict(
        resource_id,
        event.start_time,
        event.end_time
    )

    if conflict_event:
        return jsonify({
            'message': 'Resource conflict detected!',
            'resource': resource.name,
            'conflicting_event': conflict_event.title,
            'conflict_time': f'{conflict_event.start_time} - {conflict_event.end_time}'
        }), 400

    allocation = EventResourceAllocation(
        event_id=event.id,
        resource_id=resource.id
    )

    db.session.add(allocation)
    db.session.commit()

    return jsonify({
        'message': 'Resource allocated successfully!',
        'event': event.title,
        'resource': resource.name
    }), 200
