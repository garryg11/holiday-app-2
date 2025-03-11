from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from models import User
from extensions import db

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handles user login. If the user is already authenticated, 
    they are redirected to the main calendar. Otherwise, 
    we check their credentials and log them in.
    
    If force_password_reset is True, the user is redirected 
    to reset_password to update their temporary password.
    """
    if current_user.is_authenticated:
        return redirect(url_for('main.calendar'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            
            # If the user has a temporary password, force a reset
            if user.force_password_reset:
                flash("Please reset your password.", "warning")
                return redirect(url_for('auth.reset_password'))
            
            return redirect(url_for('main.calendar'))
        else:
            flash("Invalid email or password.", "danger")
    
    # Render the login form using the login.html template
    return render_template('login.html')

@auth_bp.route('/reset_password', methods=['GET', 'POST'])
@login_required
def reset_password():
    """
    Forces a user with a temporary password to set a new password. 
    If the two passwords do not match or are too short, 
    the user is prompted again.
    """
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if new_password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for('auth.reset_password'))
        
        if len(new_password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return redirect(url_for('auth.reset_password'))
        
        # Update the user's password and clear the temporary flag
        current_user.set_password(new_password)
        current_user.force_password_reset = False
        db.session.commit()
        
        flash("Your password has been updated.", "success")
        return redirect(url_for('main.calendar'))
    
    # Render the reset password form using the auth_reset_password.html template
    return render_template('auth_reset_password.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """
    Logs the user out and redirects them to the login page.
    """
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for('auth.login'))
