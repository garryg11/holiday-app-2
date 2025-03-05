from extensions import db, bcrypt
from flask_login import UserMixin

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # Options: 'employee', 'supervisor', 'manager', 'admin'

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
