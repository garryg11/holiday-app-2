from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_file
from flask_login import login_required, current_user
from models import HolidayRequest
from extensions import db, mail
from datetime import datetime
from flask_mail import Message
import io
import pandas as pd

# Define the Blueprint before using it in any routes.
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

@main_bp.route('/approval_requests')
@login_required
def approval_requests():
    if current_user.role not in ['supervisor', 'manager', 'admin']:
        flash('Access denied: you do not have permission to view this page.', 'danger')
        return redirect(url_for('main.home'))
    # Get only pending requests
    requests = HolidayRequest.query.filter_by(status='pending').all()
    return render_template('approval_requests.html', requests=requests)

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
    
    # Send email notification to the user who submitted the request
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
    """
    Export holiday requests as an Excel file.
    - Employees export only their own requests.
    - Other roles export all requests.
    """
    if current_user.role == 'employee':
        requests = HolidayRequest.query.filter_by(user_id=current_user.id).all()
    else:
        requests = HolidayRequest.query.all()

    # Build a list of dictionaries representing each holiday request
    data = []
    for req in requests:
        data.append({
            "Request ID": req.id,
            "User Email": req.user.email,
            "Start Date": req.start_date.strftime('%Y-%m-%d'),
            "End Date": req.end_date.strftime('%Y-%m-%d'),
            "Request Type": req.request_type,
            "Status": req.status,
            "Comment": req.comment or ""
        })
    
    # Create a Pandas DataFrame
    df = pd.DataFrame(data)
    
    # Write the DataFrame to an Excel file in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Holiday Requests')
    output.seek(0)
    
    # Send the file to the user for download using the 'download_name' parameter
    return send_file(
        output,
        download_name="holiday_requests.xlsx",
        as_attachment=True,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
