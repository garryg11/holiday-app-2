from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from models import User
from extensions import db
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handles user login. If user is already authenticated:
      - If HR, redirect to home page.
      - Otherwise, redirect to main.calendar (or any default page).
    """
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

            # -------------------------------------------
            #   REDIRECT LOGIC FOR HR USERS
            # -------------------------------------------
            if user.role == 'hr':
                # If HR logs in, go to home page
                return redirect(url_for('main.home'))
            else:
                # Otherwise, go to the default page
                return redirect(url_for('main.calendar'))
        else:
            flash("Invalid email or password.", "danger")

    return render_template('login.html')

@auth_bp.route('/reset_password', methods=['GET', 'POST'])
@login_required
def reset_password():
    # Example reset password route
    if request.method == 'POST':
        # handle new password, etc.
        pass
    return render_template('auth_reset_password.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for('auth.login'))
