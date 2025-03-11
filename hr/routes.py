from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from models import User, HolidayRequest, AuditLog
from datetime import datetime, date
from extensions import db
from functools import wraps

hr_bp = Blueprint('hr', __name__, url_prefix='/hr')

# Decorator to restrict access to HR role
def hr_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if current_user.role != 'hr':
            flash("Access denied: HR only.", "danger")
            return redirect(url_for('main.calendar'))
        return func(*args, **kwargs)
    return wrapper

@hr_bp.route('/dashboard')
@login_required
@hr_required
def dashboard():
    total_employees = User.query.count()
    total_requests = HolidayRequest.query.count()
    approved_requests = HolidayRequest.query.filter_by(status='approved').count()
    pending_requests = HolidayRequest.query.filter_by(status='pending').count()
    # Only include users that HR is allowed to manage
    employees = User.query.filter(~User.role.in_(['admin', 'sub-admin', 'hr'])).all()
    return render_template('hr_dashboard.html',
                           total_employees=total_employees,
                           total_requests=total_requests,
                           approved_requests=approved_requests,
                           pending_requests=pending_requests,
                           employees=employees)

@hr_bp.route('/register', methods=['GET', 'POST'])
@login_required
@hr_required
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name')
        password = request.form.get('password')
        role = request.form.get('role')
        cost_center = request.form.get('cost_center')
        department = request.form.get('department')
        time_off_balance = float(request.form.get('time_off_balance') or 20.0)
        if User.query.filter_by(email=email).first():
            flash("User with that email already exists.", "danger")
            return redirect(url_for('hr.register'))
        new_user = User(
            email=email,
            name=name,
            role=role,
            cost_center=cost_center,
            department=department,
            time_off_balance=time_off_balance
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash("New user registered successfully.", "success")
        return redirect(url_for('hr.dashboard'))
    return render_template('hr_register.html')

@hr_bp.route('/toggle_user/<int:user_id>', methods=['POST'])
@login_required
@hr_required
def toggle_user(user_id):
    user_obj = User.query.get_or_404(user_id)
    # HR cannot toggle itself.
    if user_obj.id == current_user.id:
        flash("HR cannot activate/deactivate itself.", "danger")
        return redirect(url_for('hr.dashboard'))
    # HR cannot toggle Admin, Sub-Admin, or other HR accounts.
    if user_obj.role in ['admin', 'sub-admin', 'hr']:
        flash("HR cannot activate/deactivate Admin, Sub-Admin, or other HR accounts.", "danger")
        return redirect(url_for('hr.dashboard'))
    # Otherwise, toggle the user's active status.
    user_obj.active = not user_obj.active
    db.session.commit()
    status = "activated" if user_obj.active else "deactivated"
    flash(f"User {user_obj.email} has been {status}.", "success")
    return redirect(url_for('hr.dashboard'))
    
# Placeholder for HRIS/Payroll integration page
@hr_bp.route('/integrations')
@login_required
@hr_required
def integrations():
    return render_template('hr_integrations.html')
