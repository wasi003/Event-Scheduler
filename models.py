from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# -------------------------------------------------
# Database Initialization
# -------------------------------------------------
db = SQLAlchemy()

# -------------------------------------------------
# User Model
# -------------------------------------------------
class User(db.Model):
    __tablename__ = 'users'

    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"


# -------------------------------------------------
# Event Model
# -------------------------------------------------
class Event(db.Model):
    __tablename__ = 'events'

    event_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    description = db.Column(db.Text)

    allocations = db.relationship(
        'EventResourceAllocation',
        backref='event',
        cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f"<Event {self.title}>"


# -------------------------------------------------
# Resource Model
# -------------------------------------------------
class Resource(db.Model):
    __tablename__ = 'resources'

    resource_id = db.Column(db.Integer, primary_key=True)
    resource_name = db.Column(db.String(100), nullable=False)
    resource_type = db.Column(db.String(50), nullable=False)

    allocations = db.relationship(
        'EventResourceAllocation',
        backref='resource',
        cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f"<Resource {self.resource_name}>"


# -------------------------------------------------
# Event – Resource Allocation Model
# -------------------------------------------------
class EventResourceAllocation(db.Model):
    __tablename__ = 'event_resource_allocations'

    allocation_id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.event_id'), nullable=False)
    resource_id = db.Column(db.Integer, db.ForeignKey('resources.resource_id'), nullable=False)

    __table_args__ = (
        db.UniqueConstraint('event_id', 'resource_id', name='unique_event_resource'),
    )

    def __repr__(self):
        return f"<Allocation Event:{self.event_id} Resource:{self.resource_id}>"
