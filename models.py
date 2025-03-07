from extensions import db, bcrypt
from flask_login import UserMixin
from datetime import datetime

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # Options: 'employee', 'supervisor', 'manager', 'admin'
    time_off_balance = db.Column(db.Float, nullable=False, default=20.0, server_default="20.0")

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.email}>'

class HolidayRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    request_type = db.Column(db.String(50), nullable=False)  # e.g., 'vacation', 'time compensation'
    status = db.Column(db.String(20), nullable=False, default='pending')
    comment = db.Column(db.String(200))

    user = db.relationship('User', backref=db.backref('holiday_requests', lazy=True))

    def __repr__(self):
        return f'<HolidayRequest {self.id} - {self.status}>'

class PublicHoliday(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    holiday_date = db.Column(db.Date, nullable=False)
    name = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f"<PublicHoliday {self.name} on {self.holiday_date}>"

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_email = db.Column(db.String(120), nullable=False)
    details = db.Column(db.Text)

    def __repr__(self):
        return f"<AuditLog {self.action} by {self.user_email} at {self.timestamp}>"
