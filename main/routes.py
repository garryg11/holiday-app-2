from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, jsonify, current_app
from flask_login import login_required, current_user
from models import HolidayRequest, User
from datetime import timedelta, datetime, date
from extensions import db, mail
from flask_mail import Message
import io
import pandas as pd
from functools import wraps
from sqlalchemy import or_
import secrets
import calendar

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@login_required
def home():
    return render_template('home.html')

@main_bp.route('/calendar')
@login_required
def calendar():
    suggestion = ""
    if current_user.role == 'employee':
        if current_user.time_off_balance >= 10:
            suggestion = "Consider planning a vacation next month!"
        else:
            suggestion = "Your time off balance is low."
    else:
        suggestion = "View the overall leave calendar for your team."
    return render_template('calendar.html', suggestion=suggestion)

@main_bp.route('/holiday_requests')
@login_required
def holiday_requests():
    if current_user.role == 'employee':
        requests_list = HolidayRequest.query.filter_by(user_id=current_user.id).all()
    else:
        requests_list = HolidayRequest.query.all()
    return render_template('holiday_requests.html', requests=requests_list)

@main_bp.route('/holiday_request/new', methods=['GET', 'POST'])
@login_required
def new_holiday_request():
    """
    Allows an employee or HR to submit a new holiday request.
    - GET: Render the form.
    - POST: Process form data, validate dates, and save request to DB.
    Redirects to Employee Dashboard if employee, or HR Dashboard if HR.
    """
    if current_user.role not in ['employee', 'hr']:
        flash("Only employees or HR can submit new holiday requests.", "danger")
        return redirect(url_for('main.calendar'))
    
    if request.method == 'POST':
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        request_type = request.form.get('request_type')
        comment = request.form.get('comment', '')
        
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')
            return redirect(url_for('main.new_holiday_request'))
        
        if end_date < start_date:
            flash('End date cannot be before start date.', 'danger')
            return redirect(url_for('main.new_holiday_request'))
        
        holiday_request = HolidayRequest(
            user_id=current_user.id,
            start_date=start_date,
            end_date=end_date,
            request_type=request_type,
            comment=comment,
            status='pending'
        )
        
        db.session.add(holiday_request)
        db.session.commit()
        
        flash('Holiday request submitted successfully.', 'success')
        
        if current_user.role == 'employee':
            return redirect(url_for('main.employee_dashboard'))
        else:  # current_user.role == 'hr'
            return redirect(url_for('hr.dashboard'))
    
    return render_template('new_holiday_request.html')

@main_bp.route('/approval_requests')
@login_required
def approval_requests():
    if current_user.role not in ['supervisor', 'manager', 'admin']:
        flash('Access denied: you do not have permission to view this page.', 'danger')
        return redirect(url_for('main.calendar'))
    pending_requests = HolidayRequest.query.filter_by(status='pending').all()
    return render_template('approval_requests.html', requests=pending_requests)

@main_bp.route('/approval_request/<int:request_id>/<action>')
@login_required
def update_request(request_id, action):
    if current_user.role not in ['supervisor', 'manager', 'admin']:
        flash('Access denied: you do not have permission to perform this action.', 'danger')
        return redirect(url_for('main.calendar'))
    holiday_request = HolidayRequest.query.get_or_404(request_id)
    if holiday_request.status != 'pending':
        flash('This request has already been processed.', 'warning')
        return redirect(url_for('main.approval_requests'))
    if action not in ['approve', 'reject']:
        flash('Invalid action.', 'danger')
        return redirect(url_for('main.approval_requests'))
    
    if action == 'approve':
        requested_days = (holiday_request.end_date - holiday_request.start_date).days + 1
        if holiday_request.user.time_off_balance < requested_days:
            flash('Insufficient time off balance to approve this request.', 'danger')
            return redirect(url_for('main.approval_requests'))
        holiday_request.user.time_off_balance -= requested_days
    
    holiday_request.status = 'approved' if action == 'approve' else 'rejected'
    db.session.commit()
    
    subject = f"Holiday Request {action.capitalize()}d"
    sender = current_app.config['MAIL_USERNAME']
    recipients = [holiday_request.user.email]
    msg_body = (
        f"Hello,\n\n"
        f"Your holiday request from {holiday_request.start_date} to {holiday_request.end_date} "
        f"has been {holiday_request.status}.\n\n"
        "Thank you,\nHoliday Approval App Team"
    )
    msg = Message(subject, sender=sender, recipients=recipients, body=msg_body)
    mail.send(msg)
    
    flash(f'Request {action}d successfully. An email notification has been sent.', 'success')
    return redirect(url_for('main.approval_requests'))

@main_bp.route('/export_reports')
@login_required
def export_reports():
    if current_user.role == 'employee':
        requests_list = HolidayRequest.query.filter_by(user_id=current_user.id).all()
    else:
        requests_list = HolidayRequest.query.all()
    
    data = []
    for req in requests_list:
        data.append({
            "Request ID": req.id,
            "User Email": req.user.email,
            "Start Date": req.start_date.strftime('%Y-%m-%d'),
            "End Date": req.end_date.strftime('%Y-%m-%d'),
            "Request Type": req.request_type,
            "Status": req.status,
            "Comment": req.comment or ""
        })
    
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Holiday Requests')
    output.seek(0)
    return send_file(
        output,
        download_name="holiday_requests.xlsx",
        as_attachment=True,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ------------------- Color-Coded Calendar Endpoint ------------------- #
@main_bp.route('/api/calendar_events')
@login_required
def api_calendar_events():
    """
    Returns approved holiday requests as JSON events.
    Optionally filters by request_type if provided as a query parameter.
    Each event includes a "color" property based on the request type.
    """
    events = []
    request_type_filter = request.args.get('request_type', None)
    
    query = HolidayRequest.query.filter_by(status='approved')
    if request_type_filter and request_type_filter.lower() != 'all':
        query = query.filter(HolidayRequest.request_type.ilike(request_type_filter))
    
    approved_requests = query.all()
    for req in approved_requests:
        req_type = req.request_type.lower()
        if req_type == 'vacation':
            color = '#28a745'
        elif req_type == 'sick leave':
            color = '#dc3545'
        elif req_type == 'time compensation':
            color = '#ffc107'
        elif req_type == 'personal leave':
            color = '#17a2b8'
        else:
            color = '#007bff'
        events.append({
            "title": f"{req.user.email} - {req.request_type}",
            "start": req.start_date.isoformat(),
            "end": (req.end_date + timedelta(days=1)).isoformat(),
            "color": color
        })
    return jsonify(events=events)
# ---------------------------------------------------------------------- #

@main_bp.route('/currently_on_leave')
@login_required
def currently_on_leave():
    today = date.today()
    # Get current page number from query parameters, defaulting to 1
    page = request.args.get('page', 1, type=int)
    
    # Build the query for approved holiday requests overlapping today
    ongoing_requests_query = HolidayRequest.query.filter(
        HolidayRequest.status == 'approved',
        HolidayRequest.start_date <= today,
        HolidayRequest.end_date >= today
    ).order_by(HolidayRequest.start_date.asc())
    
    # Paginate the results (15 per page, adjust as needed)
    ongoing_requests = ongoing_requests_query.paginate(page=page, per_page=15, error_out=False)
    
    return render_template('currently_on_leave.html', ongoing_requests=ongoing_requests)

@main_bp.route('/holiday_request/edit/<int:request_id>', methods=['GET', 'POST'])
@login_required
def edit_holiday_request(request_id):
    holiday_request = HolidayRequest.query.get_or_404(request_id)
    if current_user.role != 'employee' or holiday_request.user_id != current_user.id:
        flash("You are not authorized to edit this request.", "danger")
        return redirect(url_for('main.holiday_requests'))
    if holiday_request.status != 'pending':
        flash("Only pending requests can be edited.", "warning")
        return redirect(url_for('main.holiday_requests'))
    
    if request.method == 'POST':
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        request_type = request.form.get('request_type')
        
        try:
            new_start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            new_end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash("Invalid date format. Please use YYYY-MM-DD.", "danger")
            return redirect(url_for('main.edit_holiday_request', request_id=request_id))
        
        if new_end_date < new_start_date:
            flash("End date cannot be before start date.", "danger")
            return redirect(url_for('main.edit_holiday_request', request_id=request_id))
        
        holiday_request.start_date = new_start_date
        holiday_request.end_date = new_end_date
        holiday_request.request_type = request_type
        db.session.commit()
        
        flash("Holiday request updated successfully.", "success")
        return redirect(url_for('main.holiday_requests'))
    
    return render_template('edit_holiday_request.html', holiday_request=holiday_request)

@main_bp.route('/holiday_request/delete/<int:request_id>', methods=['POST'])
@login_required
def delete_holiday_request(request_id):
    holiday_request = HolidayRequest.query.get_or_404(request_id)
    if current_user.role != 'employee' or holiday_request.user_id != current_user.id:
        flash("You are not authorized to delete this request.", "danger")
        return redirect(url_for('main.holiday_requests'))
    if holiday_request.status != 'pending':
        flash("Only pending requests can be deleted.", "warning")
        return redirect(url_for('main.holiday_requests'))
    
    db.session.delete(holiday_request)
    db.session.commit()
    flash("Holiday request deleted successfully.", "success")
    return redirect(url_for('main.holiday_requests'))

@main_bp.route('/employee_dashboard')
@login_required
def employee_dashboard():
    """
    Displays the Employee Dashboard for the current user.
    Shows up to 5 most recent holiday requests.
    """
    if current_user.role != 'employee':
        flash("Access denied: you are not an employee.", "danger")
        return redirect(url_for('main.calendar'))
    
    recent_requests = (
        HolidayRequest.query
        .filter_by(user_id=current_user.id)
        .order_by(HolidayRequest.id.desc())
        .limit(5)
        .all()
    )
    
    return render_template('employee_dashboard.html', recent_requests=recent_requests)

@main_bp.route('/supervisor_dashboard')
@login_required
def supervisor_dashboard():
    if current_user.role != 'supervisor':
        flash("Access denied: you are not a supervisor.", "danger")
        return redirect(url_for('main.calendar'))
    return render_template('supervisor_dashboard.html')

@main_bp.route('/manager_dashboard')
@login_required
def manager_dashboard():
    if current_user.role != 'manager':
        flash("Access denied: you are not a manager.", "danger")
        return redirect(url_for('main.calendar'))
    return render_template('manager_dashboard.html')

# ------------------- NEW MANAGEMENT DASHBOARD ------------------- #
@main_bp.route('/management_dashboard')
@login_required
def management_dashboard():
    """
    Management Dashboard with date-range filtering for departmental analysis
    and monthly trend data. Only accessible by users with role 'admin' or 'management'.
    """
    if current_user.role not in ['admin', 'management']:
        flash("Access denied: Management Dashboard is restricted.", "danger")
        return redirect(url_for('main.calendar'))
    
    # -- 1. Parse Optional Date Range from Query Parameters --
    # e.g. ?start_date=2025-01-01&end_date=2025-03-31
    start_date_str = request.args.get('start_date', '')
    end_date_str = request.args.get('end_date', '')
    
    # If no date range is provided, default to the entire current year.
    current_year = datetime.now().year
    default_start = date(current_year, 1, 1)
    default_end = date(current_year, 12, 31)
    
    try:
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        else:
            start_date = default_start
        
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        else:
            end_date = default_end
        
        if end_date < start_date:
            # If user enters invalid range
            flash("Invalid date range: end date cannot be before start date.", "danger")
            return redirect(url_for('main.management_dashboard'))
    except ValueError:
        # If parsing fails
        flash("Invalid date format. Please use YYYY-MM-DD.", "danger")
        return redirect(url_for('main.management_dashboard'))
    
    # -- 2. Overview & KPIs (unfiltered) --
    total_employees = User.query.count()
    total_requests = HolidayRequest.query.count()
    approved_requests = HolidayRequest.query.filter_by(status='approved').count()
    pending_requests = HolidayRequest.query.filter_by(status='pending').count()
    
    # -- 3. Departmental Analysis (Filtered by Date Range) --
    # We'll consider only 'approved' requests that overlap the selected date range
    dept_stats = {}
    approved_query = HolidayRequest.query.filter_by(status='approved')
    
    # Filter by chosen date range
    approved_query = approved_query.filter(
        HolidayRequest.start_date <= end_date,
        HolidayRequest.end_date >= start_date
    )
    
    approved_requests_list = approved_query.all()
    for req in approved_requests_list:
        dept = req.user.department if req.user.department else "Unassigned"
        dept_stats[dept] = dept_stats.get(dept, 0) + 1
    
    # -- 4. Trend Analysis & Forecasting (Filtered by Date Range) --
    # We'll build monthly counts only within the user-selected range
    from_date = start_date.replace(day=1)  # earliest possible month start
    to_date = end_date.replace(day=1)      # used for monthly iteration
    
    # If the user range spans multiple years, handle accordingly
    # For simplicity, assume same year or do multi-year logic
    # We'll do single-year approach for demonstration
    year_for_trend = from_date.year
    
    # Build a dictionary for each month in the selected year
    # If the user-specified range crosses a year boundary, you might extend this logic
    import calendar
    trend_data = {m: 0 for m in range(1, 13)}
    
    # Filter all requests overlapping the chosen range
    monthly_query = HolidayRequest.query.filter(
        HolidayRequest.start_date <= end_date,
        HolidayRequest.end_date >= start_date
    ).all()
    
    # For each request, if it starts in the chosen year and overlaps range, increment
    for req in monthly_query:
        # Only increment if the start_date is in the same year as from_date
        # or you can expand logic to handle multiple years if needed
        if req.start_date.year == year_for_trend:
            month = req.start_date.month
            # Check if it falls within the selected range
            if req.start_date <= end_date and req.end_date >= start_date:
                trend_data[month] += 1
    
    # Prepare data for the chart
    month_names = [calendar.month_abbr[m] for m in range(1, 13)]
    monthly_counts = [trend_data[m] for m in range(1, 13)]
    
    return render_template('management_dashboard.html',
                           total_employees=total_employees,
                           total_requests=total_requests,
                           approved_requests=approved_requests,
                           pending_requests=pending_requests,
                           dept_stats=dept_stats,
                           month_names=month_names,
                           monthly_counts=monthly_counts,
                           current_year=year_for_trend,
                           start_date_str=start_date_str,
                           end_date_str=end_date_str)

# ------------------- NEW ENDPOINT FOR REVERSED CALENDAR EVENTS ------------------- #
@main_bp.route('/api/reversed_calendar_events')
@login_required
def api_reversed_calendar_events():
    """
    Returns approved holiday requests as JSON events in descending order (newest first)
    by start date.
    """
    events_data = []
    approved_requests = HolidayRequest.query.filter_by(status='approved').all()
    
    # Build a list of event dictionaries
    for req in approved_requests:
        events_data.append({
            "title": f"{req.user.email} - {req.request_type}",
            "start": req.start_date.isoformat(),
            "end": (req.end_date + timedelta(days=1)).isoformat()
        })
    
    # Sort the events by start date descending (newest first)
    events_data.sort(key=lambda e: e["start"], reverse=True)
    
    return jsonify(events=events_data)
# ---------------------------------------------------------------------- #

# ------------------- NEW ROUTE FOR REVERSED LIST PAGE ------------------- #
@main_bp.route('/reversed_list')
@login_required
def reversed_list_page():
    """
    Renders a page displaying approved holiday requests in descending order (newest first).
    """
    return render_template('reversed_list.html')
# ---------------------------------------------------------------------- #
