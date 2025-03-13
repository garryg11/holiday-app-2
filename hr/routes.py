from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import User, HolidayRequest, AuditLog
from datetime import datetime
from extensions import db, bcrypt, mail
from functools import wraps
import secrets
from sqlalchemy import or_

hr_bp = Blueprint('hr', __name__, url_prefix='/hr')

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
    # Key metrics
    total_employees = User.query.count()
    total_requests = HolidayRequest.query.count()
    approved_requests = HolidayRequest.query.filter_by(status='approved').count()
    pending_requests = HolidayRequest.query.filter_by(status='pending').count()

    # Retrieve page number and search query from URL parameters.
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    
    # Build a query for employees excluding high-privilege roles.
    employees_query = User.query.filter(~User.role.in_(['admin', 'sub-admin', 'hr']))
    if search:
        # Search both by email and by name (case-insensitive).
        employees_query = employees_query.filter(
            or_(
                User.email.ilike(f"%{search}%"),
                User.name.ilike(f"%{search}%")
            )
        )
    
    # Paginate the results (25 per page)
    employees_paginated = employees_query.order_by(User.id.asc()).paginate(page=page, per_page=25, error_out=False)
    
    return render_template('hr_dashboard.html',
                           total_employees=total_employees,
                           total_requests=total_requests,
                           approved_requests=approved_requests,
                           pending_requests=pending_requests,
                           employees=employees_paginated)

@hr_bp.route('/register', methods=['GET', 'POST'])
@login_required
@hr_required
def register():
    """
    Allows HR to register new users.
    HR is not allowed to create accounts with role 'admin', 'sub-admin', or 'hr'.
    """
    if request.method == 'POST':
        employee_id = request.form.get('employee_id')  # Optional field if used
        email = request.form.get('email')
        name = request.form.get('name')
        role = request.form.get('role')
        cost_center = request.form.get('cost_center')
        department = request.form.get('department')
        time_off_balance = float(request.form.get('time_off_balance') or 20.0)
        
        # Prevent HR from creating high-privilege accounts.
        if role in ['admin', 'sub-admin', 'hr']:
            flash("HR cannot create Admin, Sub-Admin, or HR accounts.", "danger")
            return redirect(url_for('hr.register'))
        
        if User.query.filter_by(email=email).first():
            flash("User with that email already exists.", "danger")
            return redirect(url_for('hr.register'))
        
        # Generate a system-generated temporary password.
        temp_password = secrets.token_urlsafe(8)
        
        new_user = User(
            email=email,
            name=name,
            role=role,
            cost_center=cost_center,
            department=department,
            time_off_balance=time_off_balance
        )
        new_user.set_password(temp_password)
        new_user.force_password_reset = True
        
        db.session.add(new_user)
        db.session.commit()
        
        flash(f"New user registered successfully. Temporary password: {temp_password}", "success")
        return redirect(url_for('hr.dashboard'))
    
    return render_template('hr_register.html')

@hr_bp.route('/toggle_user/<int:user_id>', methods=['POST'])
@login_required
@hr_required
def toggle_user(user_id):
    user_obj = User.query.get_or_404(user_id)
    if user_obj.id == current_user.id:
        flash("HR cannot activate/deactivate itself.", "danger")
        return redirect(url_for('hr.dashboard'))
    if user_obj.role in ['admin', 'sub-admin', 'hr']:
        flash("HR cannot activate/deactivate Admin, Sub-Admin, or other HR accounts.", "danger")
        return redirect(url_for('hr.dashboard'))
    user_obj.active = not user_obj.active
    db.session.commit()
    status = "activated" if user_obj.active else "deactivated"
    flash(f"User {user_obj.email} has been {status}.", "success")
    return redirect(url_for('hr.dashboard'))

@hr_bp.route('/integrations')
@login_required
@hr_required
def integrations():
    return render_template('hr_integrations.html')
