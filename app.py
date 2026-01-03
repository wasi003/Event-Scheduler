from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime, date
from functools import wraps

from models import db, User, Event, Resource, EventResourceAllocation

# -------------------------------------------------
# Flask App Configuration
# -------------------------------------------------
app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///events.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = "simple-secret-key"

db.init_app(app)

# -------------------------------------------------
# Login Required Decorator
# -------------------------------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# -------------------------------------------------
# Home
# -------------------------------------------------
@app.route('/')
def home():
    return render_template('base.html')


# -------------------------------------------------
# Authentication
# -------------------------------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if User.query.filter_by(username=username).first():
            flash("Username already exists")
            return redirect(url_for('register'))

        user = User(username=username)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash("Registration successful. Please login.")
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            session['user'] = user.username
            return redirect(url_for('events'))

        flash("Invalid username or password")
        return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))


# -------------------------------------------------
# Events
# -------------------------------------------------
@app.route('/events')
@login_required
def events():
    events = Event.query.all()
    return render_template('events.html', events=events)


@app.route('/events/add', methods=['GET', 'POST'])
@login_required
def add_event():
    if request.method == 'POST':
        event = Event(
            title=request.form['title'],
            start_time=datetime.fromisoformat(request.form['start_time']),
            end_time=datetime.fromisoformat(request.form['end_time']),
            description=request.form['description']
        )
        db.session.add(event)
        db.session.commit()
        return redirect(url_for('events'))

    return render_template('add_event.html')


# -------------------------------------------------
# Resources
# -------------------------------------------------
@app.route('/resources')
@login_required
def resources():
    resources = Resource.query.all()
    return render_template('resources.html', resources=resources)


@app.route('/resources/add', methods=['GET', 'POST'])
@login_required
def add_resource():
    if request.method == 'POST':
        resource = Resource(
            resource_name=request.form['name'],
            resource_type=request.form['type']
        )
        db.session.add(resource)
        db.session.commit()
        return redirect(url_for('resources'))

    return render_template('add_resource.html')


# -------------------------------------------------
# Allocation & Conflict Detection
# -------------------------------------------------
@app.route('/allocate', methods=['GET', 'POST'])
@login_required
def allocate_resource():
    events = Event.query.all()
    resources = Resource.query.all()
    error = None

    if request.method == 'POST':
        event_id = int(request.form['event_id'])
        resource_id = int(request.form['resource_id'])
        event = Event.query.get(event_id)

        conflict = (
            EventResourceAllocation.query
            .join(Event)
            .filter(
                EventResourceAllocation.resource_id == resource_id,
                Event.start_time < event.end_time,
                Event.end_time > event.start_time
            ).first()
        )

        if conflict:
            error = "This resource is already booked for another event during this time."
        else:
            allocation = EventResourceAllocation(
                event_id=event_id,
                resource_id=resource_id
            )
            db.session.add(allocation)
            db.session.commit()
            return redirect(url_for('view_allocations'))

    return render_template(
        'allocate.html',
        events=events,
        resources=resources,
        error=error
    )


@app.route('/allocations')
@login_required
def view_allocations():
    allocations = EventResourceAllocation.query.all()
    return render_template('allocations.html', allocations=allocations)


# -------------------------------------------------
# Resource Utilization Report
# -------------------------------------------------
@app.route('/report', methods=['GET', 'POST'])
@login_required
def utilization_report():
    report_data = []

    if request.method == 'POST':
        start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()

        for resource in Resource.query.all():
            total_hours = bookings = upcoming = 0

            for alloc in resource.allocations:
                event = alloc.event
                event_date = event.start_time.date()

                if start_date <= event_date <= end_date:
                    total_hours += (event.end_time - event.start_time).total_seconds() / 3600
                    bookings += 1

                if event.start_time.date() > date.today():
                    upcoming += 1

            report_data.append({
                'name': resource.resource_name,
                'type': resource.resource_type,
                'hours': round(total_hours, 2),
                'bookings': bookings,
                'upcoming': upcoming
            })

    return render_template('report.html', report_data=report_data)


# -------------------------------------------------
# Run Application
# -------------------------------------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
