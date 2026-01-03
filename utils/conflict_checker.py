from models import Event, EventResourceAllocation

def has_resource_conflict(resource_id, start_time, end_time):
    allocations = EventResourceAllocation.query.all()

    for allocation in allocations:
        if allocation.resource_id != resource_id:
            continue

        event = Event.query.get(allocation.event_id)
        if not event:
            continue

        # Overlap check
        if start_time < event.end_time and end_time > event.start_time:
            return event

    return None
