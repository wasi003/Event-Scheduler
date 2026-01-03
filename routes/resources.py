from flask import Blueprint, request, jsonify
from datetime import datetime
from models import Resource, Event, EventResourceAllocation

resource_bp = Blueprint('resources', __name__)

@resource_bp.route('/utilization-report', methods=['GET'])
def resource_utilization_report():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None

    report = []

    resources = Resource.query.all()

    for resource in resources:
        allocations = EventResourceAllocation.query.filter_by(
            resource_id=resource.id
        ).all()

        total_hours = 0
        upcoming = 0

        for alloc in allocations:
            event = Event.query.get(alloc.event_id)
            if not event:
                continue

            if start and event.start_time < start:
                continue
            if end and event.end_time > end:
                continue

            duration = (event.end_time - event.start_time).total_seconds() / 3600
            total_hours += duration

            if event.start_time > datetime.utcnow():
                upcoming += 1

        report.append({
            'resource_name': resource.name,
            'resource_type': resource.type,
            'total_hours_utilized': round(total_hours, 2),
            'total_bookings': len(allocations),
            'upcoming_bookings': upcoming
        })

    return jsonify(report), 200
