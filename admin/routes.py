from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from models import User, PublicHoliday, AuditLog, HolidayRequest
from datetime import datetime, date
from extensions import db
from functools import wraps

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Decorator to restrict access to admin only
def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if current_user.role != 'admin':
            flash("Access denied: Admins only.", "danger")
            return redirect(url_for('main.calendar'))
        return func(*args, **kwargs)
    return wrapper

# ---------------- Admin Dashboard ----------------
@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    total_users = User.query.count()
    total_requests = HolidayRequest.query.count()
    pending_requests = HolidayRequest.query.filter_by(status='pending').count()
    approved_requests = HolidayRequest.query.filter_by(status='approved').count()
    
    # Show the 5 most recent logs
    audit_logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(5).all()
    
    return render_template('admin_dashboard.html',
                           total_users=total_users,
                           total_requests=total_requests,
                           pending_requests=pending_requests,
                           approved_requests=approved_requests,
                           audit_logs=audit_logs)

# ---------------- User Management ----------------
@admin_bp.route('/users')
@login_required
@admin_required
def users():
    users_list = User.query.all()
    return render_template('admin_users.html', users=users_list)

@admin_bp.route('/users/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_user():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        time_off_balance = float(request.form.get('time_off_balance') or 20.0)
        
        # Check if user already exists
        if User.query.filter_by(email=email).first():
            flash("User with that email already exists.", "danger")
            return redirect(url_for('admin.new_user'))
        
        # Create new user
        new_user = User(email=email, role=role, time_off_balance=time_off_balance)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        # Create an audit log entry
        audit = AuditLog(
            action="Create User",
            user_email=current_user.email,
            details=f"Created user: {email} with role {role}"
        )
        db.session.add(audit)
        db.session.commit()
        
        flash("New user created successfully.", "success")
        return redirect(url_for('admin.users'))
    
    return render_template('admin_new_user.html')

@admin_bp.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user_obj = User.query.get_or_404(user_id)
    if request.method == 'POST':
        old_email = user_obj.email
        old_role = user_obj.role
        
        user_obj.email = request.form.get('email')
        user_obj.role = request.form.get('role')
        user_obj.time_off_balance = float(request.form.get('time_off_balance') or user_obj.time_off_balance)
        
        password = request.form.get('password')
        if password:
            user_obj.set_password(password)
        
        db.session.commit()
        
        # Create an audit log entry
        audit = AuditLog(
            action="Edit User",
            user_email=current_user.email,
            details=f"Edited user from (email={old_email}, role={old_role}) to (email={user_obj.email}, role={user_obj.role})"
        )
        db.session.add(audit)
        db.session.commit()
        
        flash("User updated successfully.", "success")
        return redirect(url_for('admin.users'))
    
    return render_template('admin_edit_user.html', user=user_obj)

@admin_bp.route('/users/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user_obj = User.query.get_or_404(user_id)
    db.session.delete(user_obj)
    db.session.commit()
    
    # Create an audit log entry
    audit = AuditLog(
        action="Delete User",
        user_email=current_user.email,
        details=f"Deleted user: {user_obj.email}"
    )
    db.session.add(audit)
    db.session.commit()
    
    flash("User deleted successfully.", "success")
    return redirect(url_for('admin.users'))

# ---------------- System Configuration: Public Holidays ----------------
@admin_bp.route('/holidays')
@login_required
@admin_required
def holidays():
    holidays_list = PublicHoliday.query.order_by(PublicHoliday.holiday_date).all()
    return render_template('admin_holidays.html', holidays=holidays_list)

@admin_bp.route('/holidays/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_holiday():
    if request.method == 'POST':
        holiday_date_str = request.form.get('holiday_date')
        name = request.form.get('name')
        try:
            holiday_date = datetime.strptime(holiday_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash("Invalid date format. Use YYYY-MM-DD.", "danger")
            return redirect(url_for('admin.new_holiday'))
        
        new_hol = PublicHoliday(holiday_date=holiday_date, name=name)
        db.session.add(new_hol)
        db.session.commit()
        
        # Create an audit log entry
        audit = AuditLog(
            action="Create Holiday",
            user_email=current_user.email,
            details=f"Created holiday: {name} on {holiday_date_str}"
        )
        db.session.add(audit)
        db.session.commit()
        
        flash("Holiday added successfully.", "success")
        return redirect(url_for('admin.holidays'))
    return render_template('admin_new_holiday.html')

@admin_bp.route('/holidays/edit/<int:holiday_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_holiday(holiday_id):
    holiday = PublicHoliday.query.get_or_404(holiday_id)
    if request.method == 'POST':
        old_name = holiday.name
        old_date = holiday.holiday_date
        
        holiday_date_str = request.form.get('holiday_date')
        name = request.form.get('name')
        try:
            holiday.holiday_date = datetime.strptime(holiday_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash("Invalid date format. Use YYYY-MM-DD.", "danger")
            return redirect(url_for('admin.edit_holiday', holiday_id=holiday_id))
        holiday.name = name
        db.session.commit()
        
        # Create an audit log entry
        audit = AuditLog(
            action="Edit Holiday",
            user_email=current_user.email,
            details=f"Changed holiday from (name={old_name}, date={old_date}) to (name={holiday.name}, date={holiday.holiday_date})"
        )
        db.session.add(audit)
        db.session.commit()
        
        flash("Holiday updated successfully.", "success")
        return redirect(url_for('admin.holidays'))
    
    return render_template('admin_edit_holiday.html', holiday=holiday)

@admin_bp.route('/holidays/delete/<int:holiday_id>', methods=['POST'])
@login_required
@admin_required
def delete_holiday(holiday_id):
    holiday = PublicHoliday.query.get_or_404(holiday_id)
    db.session.delete(holiday)
    db.session.commit()
    
    # Create an audit log entry
    audit = AuditLog(
        action="Delete Holiday",
        user_email=current_user.email,
        details=f"Deleted holiday: {holiday.name} on {holiday.holiday_date}"
    )
    db.session.add(audit)
    db.session.commit()
    
    flash("Holiday deleted successfully.", "success")
    return redirect(url_for('admin.holidays'))

# ---------------- Integration Management ----------------
@admin_bp.route('/integrations')
@login_required
@admin_required
def integrations():
    # Placeholder for future integration functionality
    return render_template('admin_integrations.html')

# ---------------- Security: Audit Logs ----------------
@admin_bp.route('/security')
@login_required
@admin_required
def security():
    audit_logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).all()
    return render_template('admin_security.html', audit_logs=audit_logs)

# ---------------- Notification Settings ----------------
@admin_bp.route('/notifications', methods=['GET', 'POST'])
@login_required
@admin_required
def notifications():
    if request.method == 'POST':
        # For simplicity, simulate saving notification settings
        # You could log changes to notification settings here as well.
        flash("Notification settings updated successfully.", "success")
        return redirect(url_for('admin.notifications'))
    return render_template('admin_notifications.html')
