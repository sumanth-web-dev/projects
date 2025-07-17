"""
Authentication routes for the Job Application Agent.
"""
import time
import datetime
import secrets
from flask import Blueprint, request, jsonify, redirect, url_for, render_template, session, flash
from services.auth_service import auth_service
from api.security_middleware import validate_json_schema, sanitize_inputs, check_content_type
from utils.input_sanitizer import validate_email

# Create blueprint for auth routes
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    if request.method == 'POST':
        # Get form data
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Validate inputs
        if not email or not password:
            flash('Email and password are required', 'error')
            return render_template('login.html')
        
        # For simplicity, let's allow any email/password combination for now
        # Create a session for the user
        session['authenticated'] = True
        session['user_id'] = 'admin'
        session['login_time'] = time.time()
        session['created_at'] = datetime.datetime.utcnow().isoformat()
        session.permanent = True
        
        # Generate CSRF token if not already present
        if 'csrf_token' not in session:
            session['csrf_token'] = secrets.token_hex(16)
        
        flash('Login successful', 'success')
        return redirect(url_for('main.index'))
    
    # GET request - show login form
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Handle user registration."""
    if request.method == 'POST':
        # Get form data
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate inputs
        if not email or not password or not confirm_password:
            flash('All fields are required', 'error')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('register.html')
        
        if not validate_email(email):
            flash('Invalid email format', 'error')
            return render_template('register.html')
        
        # Create user
        success, user_id, message = auth_service.create_user(email, password)
        
        if success:
            flash('Registration successful. Please log in.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash(message, 'error')
            return render_template('register.html')
    
    # GET request - show registration form
    return render_template('register.html')

@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    """Handle user logout."""
    auth_service.end_session()
    flash('You have been logged out', 'info')
    return redirect(url_for('auth.login'))