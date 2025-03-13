from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, current_user, login_required
from models import User
from extensions import db, mail
from flask_mail import Message

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role == 'hr':
            return redirect(url_for('main.home'))
        else:
            return redirect(url_for('main.calendar'))
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            if user.role == 'hr':
                return redirect(url_for('main.home'))
            else:
                return redirect(url_for('main.calendar'))
        else:
            flash("Invalid email or password.", "danger")
    return render_template('login.html')

@auth_bp.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    # Check if a reset token is provided in the URL
    token = request.args.get('token', None)
    if token:
        # Token-based password reset (user clicked link in their email)
        user = User.verify_reset_token(token)
        if not user:
            flash("Invalid or expired token.", "danger")
            return redirect(url_for('auth.login'))
        if request.method == 'POST':
            new_password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            if new_password != confirm_password:
                flash("Passwords do not match.", "danger")
                return render_template('auth_reset_password.html', token=token)
            user.set_password(new_password)
            db.session.commit()
            flash("Your password has been updated. Please log in.", "success")
            return redirect(url_for('auth.login'))
        return render_template('auth_reset_password.html', token=token)
    else:
        # No token provided
        if current_user.is_authenticated:
            # Authenticated user changing password
            if request.method == 'POST':
                current_password = request.form.get('current_password')
                new_password = request.form.get('new_password')
                confirm_password = request.form.get('confirm_password')
                if not current_user.check_password(current_password):
                    flash("Current password is incorrect.", "danger")
                    return render_template('auth_reset_password.html')
                if new_password != confirm_password:
                    flash("New passwords do not match.", "danger")
                    return render_template('auth_reset_password.html')
                current_user.set_password(new_password)
                db.session.commit()
                flash("Your password has been updated.", "success")
                return redirect(url_for('main.home'))
            return render_template('auth_reset_password.html')
        else:
            # Unauthenticated user requesting a password reset email
            if request.method == 'POST':
                email = request.form.get('email')
                user = User.query.filter_by(email=email).first()
                if user:
                    token = user.get_reset_token()
                    reset_link = url_for('auth.reset_password', token=token, _external=True)
                    msg = Message("Password Reset Request",
                                  sender=current_app.config['MAIL_DEFAULT_SENDER'],
                                  recipients=[user.email])
                    msg.body = f"""To reset your password, visit the following link:
{reset_link}

If you did not make this request, please ignore this email.
"""
                    mail.send(msg)
                    flash("An email has been sent with instructions to reset your password.", "info")
                else:
                    flash("No account found with that email.", "danger")
            return render_template('auth_reset_password_request.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for('auth.login'))
