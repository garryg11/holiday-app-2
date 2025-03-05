from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import HolidayRequest
from extensions import db
from datetime import datetime

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@login_required
def home():
    return render_template('home.html')

@main_bp.route('/holiday_requests')
@login_required
def holiday_requests():
    # Employees see only their own requests; other roles see all requests.
    if current_user.role == 'employee':
        requests = HolidayRequest.query.filter_by(user_id=current_user.id).all()
    else:
        requests = HolidayRequest.query.all()
    return render_template('holiday_requests.html', requests=requests)

@main_bp.route('/holiday_request/new', methods=['GET', 'POST'])
@login_required
def new_holiday_request():
    if request.method == 'POST':
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        request_type = request.form.get('request_type')
        # Convert dates from string to date objects
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')
            return redirect(url_for('main.new_holiday_request'))
        if end_date < start_date:
            flash('End date cannot be before start date.', 'danger')
            return redirect(url_for('main.new_holiday_request'))
        # Create and add the new holiday request
        holiday_request = HolidayRequest(
            user_id=current_user.id,
            start_date=start_date,
            end_date=end_date,
            request_type=request_type,
            status='pending'
        )
        db.session.add(holiday_request)
        db.session.commit()
        flash('Holiday request submitted successfully.', 'success')
        return redirect(url_for('main.holiday_requests'))
    return render_template('new_holiday_request.html')

# New route: List pending requests for approval (accessible only for supervisors, managers, and admins)
@main_bp.route('/approval_requests')
@login_required
def approval_requests():
    if current_user.role not in ['supervisor', 'manager', 'admin']:
        flash('Access denied: you do not have permission to view this page.', 'danger')
        return redirect(url_for('main.home'))
    # Get only pending requests
    requests = HolidayRequest.query.filter_by(status='pending').all()
    return render_template('approval_requests.html', requests=requests)

# New route: Update a holiday request's status (approve or reject)
@main_bp.route('/approval_request/<int:request_id>/<action>')
@login_required
def update_request(request_id, action):
    if current_user.role not in ['supervisor', 'manager', 'admin']:
        flash('Access denied: you do not have permission to perform this action.', 'danger')
        return redirect(url_for('main.home'))
    holiday_request = HolidayRequest.query.get_or_404(request_id)
    if holiday_request.status != 'pending':
        flash('This request has already been processed.', 'warning')
        return redirect(url_for('main.approval_requests'))
    if action not in ['approve', 'reject']:
        flash('Invalid action.', 'danger')
        return redirect(url_for('main.approval_requests'))
    holiday_request.status = 'approved' if action == 'approve' else 'rejected'
    db.session.commit()
    flash(f'Request {action}d successfully.', 'success')
    return redirect(url_for('main.approval_requests'))
