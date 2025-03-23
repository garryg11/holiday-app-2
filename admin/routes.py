from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from models import User, PublicHoliday, AuditLog, HolidayRequest
from datetime import datetime, date
from extensions import db
from functools import wraps
from flask_babel import _  # Import the translation function

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Decorator to restrict access to admin and sub-admin
def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if current_user.role not in ['admin', 'sub-admin']:
            flash(_("Access denied: Admins only."), "danger")
            return redirect(url_for('main.calendar'))
        return func(*args, **kwargs)
    return wrapper

# ---------------- Admin Dashboard ----------------
@admin_bp.route('/dashboard', methods=['GET'])
@login_required
@admin_required
def dashboard():
    total_users = User.query.count()
    total_requests = HolidayRequest.query.count()
    pending_requests = HolidayRequest.query.filter_by(status='pending').count()
    approved_requests = HolidayRequest.query.filter_by(status='approved').count()
    audit_logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(5).all()
    
    # Process search/filter for the user management section on the dashboard
    search_term = request.args.get('search', '').strip()
    role_filter = request.args.get('role', '').strip()
    query = User.query
    if search_term:
        like_pattern = f"%{search_term}%"
        query = query.filter((User.email.ilike(like_pattern)) | (User.name.ilike(like_pattern)))
    if role_filter:
        query = query.filter_by(role=role_filter)
    users_list = query.order_by(User.id.desc()).all()
    
    return render_template(
        'admin_dashboard.html',
        total_users=total_users,
        total_requests=total_requests,
        pending_requests=pending_requests,
        approved_requests=approved_requests,
        audit_logs=audit_logs,
        users=users_list
    )

# ---------------- User Management ----------------
@admin_bp.route('/users', methods=['GET'])
@login_required
@admin_required
def users():
    """
    Displays a list of users with optional search and role filtering.
    Renders 'admin_users.html', which includes:
      - A search bar (by email or name)
      - A role dropdown filter
      - A table of users with checkboxes for bulk actions
      - 'Add New User' button
      - Individual Edit/Delete buttons
    """
    search_term = request.args.get('search', '').strip()
    role_filter = request.args.get('role', '').strip()
    
    query = User.query
    if search_term:
        like_pattern = f"%{search_term}%"
        query = query.filter((User.email.ilike(like_pattern)) | (User.name.ilike(like_pattern)))
    if role_filter:
        query = query.filter_by(role=role_filter)
        
    users_list = query.order_by(User.id.desc()).all()
    return render_template('admin_users.html', users=users_list)

@admin_bp.route('/users/bulk_action', methods=['POST'])
@login_required
@admin_required
def bulk_user_action():
    """
    Applies a bulk action (activate, deactivate, delete) to selected users.
    Expects:
      - 'action' field in the POST data
      - 'user_ids' checkboxes in the POST data
    """
    action = request.form.get('action')
    user_ids = request.form.getlist('user_ids')
    
    if not user_ids:
        flash(_("No users selected."), "warning")
        return redirect(url_for('admin.users'))
    
    selected_users = User.query.filter(User.id.in_(user_ids)).all()
    
    if action == 'activate':
        for user in selected_users:
            user.active = True
    elif action == 'deactivate':
        for user in selected_users:
            user.active = False
    elif action == 'delete':
        for user in selected_users:
            db.session.delete(user)
    else:
        flash(_("Invalid action selected."), "danger")
        return redirect(url_for('admin.users'))
    
    db.session.commit()
    flash(_("Bulk action '{action}' applied to {count} user(s).").format(action=action, count=len(selected_users)), "success")
    
    # Log the bulk action in AuditLog
    audit = AuditLog(
        action=_("Bulk user action: {action}").format(action=action),
        user_email=current_user.email,
        details=_("Applied {action} to user_ids={ids}").format(action=action, ids=user_ids),
        timestamp=datetime.utcnow()
    )
    db.session.add(audit)
    db.session.commit()
    
    return redirect(url_for('admin.users'))

@admin_bp.route('/users/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_user():
    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name')
        password = request.form.get('password')
        role = request.form.get('role')
        cost_center = request.form.get('cost_center')
        department = request.form.get('department')
        time_off_balance = float(request.form.get('time_off_balance') or 20.0)
        
        if User.query.filter_by(email=email).first():
            flash(_("User with that email already exists."), "danger")
            return redirect(url_for('admin.new_user'))
        
        new_user_obj = User(
            email=email,
            name=name,
            role=role,
            cost_center=cost_center,
            department=department,
            time_off_balance=time_off_balance
        )
        new_user_obj.set_password(password)
        db.session.add(new_user_obj)
        db.session.commit()
        
        # Audit Log Entry
        audit = AuditLog(
            action=_("Create User"),
            user_email=current_user.email,
            details=_("Created user: {email} (Name: {name}, Role: {role}, Cost Center: {cc}, Department: {dept})").format(
                email=email, name=name, role=role, cc=cost_center, dept=department
            ),
            timestamp=datetime.utcnow()
        )
        db.session.add(audit)
        db.session.commit()
        
        flash(_("New user created successfully."), "success")
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
        user_obj.name = request.form.get('name')
        user_obj.role = request.form.get('role')
        user_obj.cost_center = request.form.get('cost_center')
        user_obj.department = request.form.get('department')
        user_obj.time_off_balance = float(request.form.get('time_off_balance') or user_obj.time_off_balance)
        password = request.form.get('password')
        if password:
            user_obj.set_password(password)
        db.session.commit()
        
        # Audit Log Entry
        audit = AuditLog(
            action=_("Edit User"),
            user_email=current_user.email,
            details=_("Edited user from (Email: {old_email}, Role: {old_role}) to (Email: {new_email}, Role: {new_role})").format(
                old_email=old_email, old_role=old_role, new_email=user_obj.email, new_role=user_obj.role
            ),
            timestamp=datetime.utcnow()
        )
        db.session.add(audit)
        db.session.commit()
        
        flash(_("User updated successfully."), "success")
        return redirect(url_for('admin.users'))
    return render_template('admin_edit_user.html', user=user_obj)

@admin_bp.route('/users/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user_obj = User.query.get_or_404(user_id)
    db.session.delete(user_obj)
    db.session.commit()
    
    # Audit Log Entry
    audit = AuditLog(
        action=_("Delete User"),
        user_email=current_user.email,
        details=_("Deleted user: {email}").format(email=user_obj.email),
        timestamp=datetime.utcnow()
    )
    db.session.add(audit)
    db.session.commit()
    
    flash(_("User deleted successfully."), "success")
    return redirect(url_for('admin.users'))

@admin_bp.route('/toggle_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def toggle_user(user_id):
    user_obj = User.query.get_or_404(user_id)
    # If current user is sub-admin, they cannot deactivate an admin.
    if current_user.role == 'sub-admin' and user_obj.role == 'admin':
        flash(_("Sub-Admin cannot deactivate an Admin."), "danger")
        return redirect(url_for('admin.users'))
    user_obj.active = not user_obj.active
    db.session.commit()
    status = _("activated") if user_obj.active else _("deactivated")
    flash(_("User {email} has been {status}.").format(email=user_obj.email, status=status), "success")
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
            flash(_("Invalid date format. Use YYYY-MM-DD."), "danger")
            return redirect(url_for('admin.new_holiday'))
        new_hol = PublicHoliday(holiday_date=holiday_date, name=name)
        db.session.add(new_hol)
        db.session.commit()
        
        # Audit Log Entry
        audit = AuditLog(
            action=_("Create Holiday"),
            user_email=current_user.email,
            details=_("Created holiday: {name} on {date}").format(name=name, date=holiday_date_str),
            timestamp=datetime.utcnow()
        )
        db.session.add(audit)
        db.session.commit()
        
        flash(_("Holiday added successfully."), "success")
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
            flash(_("Invalid date format. Use YYYY-MM-DD."), "danger")
            return redirect(url_for('admin.edit_holiday', holiday_id=holiday_id))
        holiday.name = name
        db.session.commit()
        
        # Audit Log Entry
        audit = AuditLog(
            action=_("Edit Holiday"),
            user_email=current_user.email,
            details=_("Changed holiday from (Name: {old_name}, Date: {old_date}) to (Name: {new_name}, Date: {new_date})").format(
                old_name=old_name, old_date=old_date, new_name=holiday.name, new_date=holiday.holiday_date
            ),
            timestamp=datetime.utcnow()
        )
        db.session.add(audit)
        db.session.commit()
        
        flash(_("Holiday updated successfully."), "success")
        return redirect(url_for('admin.holidays'))
    return render_template('admin_edit_holiday.html', holiday=holiday)

@admin_bp.route('/holidays/delete/<int:holiday_id>', methods=['POST'])
@login_required
@admin_required
def delete_holiday(holiday_id):
    holiday = PublicHoliday.query.get_or_404(holiday_id)
    db.session.delete(holiday)
    db.session.commit()
    
    # Audit Log Entry
    audit = AuditLog(
        action=_("Delete Holiday"),
        user_email=current_user.email,
        details=_("Deleted holiday: {name} on {date}").format(name=holiday.name, date=holiday.holiday_date),
        timestamp=datetime.utcnow()
    )
    db.session.add(audit)
    db.session.commit()
    
    flash(_("Holiday deleted successfully."), "success")
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
        # Simulate saving notification settings
        flash(_("Notification settings updated successfully."), "success")
        return redirect(url_for('admin.notifications'))
    return render_template('admin_notifications.html')
