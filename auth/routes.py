from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from models import User
from extensions import db
from urllib.parse import urlparse  # Using Python's standard library

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

def role_based_dashboard(user):
    # Redirect users based on their role
    if user.role == 'employee':
        return url_for('main.employee_dashboard')
    elif user.role == 'supervisor':
        return url_for('main.supervisor_dashboard')
    elif user.role == 'manager':
        return url_for('main.manager_dashboard')
    elif user.role == 'admin':
        return url_for('admin.dashboard')
    elif user.role == 'hr':
        return url_for('hr.dashboard')
    return url_for('main.calendar')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(role_based_dashboard(current_user))
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully.', 'success')
            return redirect(role_based_dashboard(user))
        else:
            flash('Invalid email or password.', 'danger')
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(role_based_dashboard(current_user))
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        # For simplicity, all new registrations will have role 'employee'
        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "danger")
            return redirect(url_for('auth.register'))
        new_user = User(email=email, role='employee', time_off_balance=20.0)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful. Please log in.", "success")
        return redirect(url_for('auth.login'))
    return render_template('register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
