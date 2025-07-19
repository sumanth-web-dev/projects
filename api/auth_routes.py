"""
Authentication routes for the Job Application Agent.
"""
import time
import datetime
import secrets
from flask import Blueprint, request, jsonify, redirect, url_for, render_template, session, flash
from services.auth_service import auth_service
from services.otp_service import otp_service
from services.notification_service import notification_service
from api.security_middleware import validate_json_schema, sanitize_inputs, check_content_type
from utils.input_sanitizer import validate_email
from models.user import User


# Create blueprint for auth routes
auth_bp = Blueprint('auth', __name__)

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
        
        # Authenticate user
        success, user_data, message = auth_service.authenticate_user(email, password)
        print(f"Login attempt for {email}: {message}")
        if not success:
            flash(message, 'error')
            return render_template('login.html')
        
        # Get user details to determine role
        user_id = user_data.get('id')
        
        try:
            user = User.query.get(user_id)
            
            if not user:
                flash('User not found', 'error')
                return render_template('login.html')
            
            # Create a session for the user
            session['authenticated'] = True
            session['user_id'] = user_id
            session['login_time'] = time.time()
            session['created_at'] = datetime.datetime.utcnow().isoformat()
            session.permanent = True
            
            # Generate CSRF token if not already present
            if 'csrf_token' not in session:
                session['csrf_token'] = secrets.token_hex(16)
            
            # Get user roles
            personal_data = user.personal_data or {}
            roles = personal_data.get('roles', [])
            
            # Store roles in session for easier access
            session['user_roles'] = roles
            
            flash('Login successful', 'success')
            
            # Direct role-based redirection with hash fragments
            if 'admin' in roles:
                return redirect(url_for('admin.dashboard') + '#admin')
            elif 'hr' in roles:
                return redirect(url_for('hr.dashboard') + '#hr')    
            elif 'user' in roles:
                return redirect(url_for('student.dashboard') + '#student')
            else:
                # Default users go to a generic dashboard
                return redirect(url_for('main.index') + '#user-dashboard')
                
        except Exception as e:
            # If any error occurs during user processing, log it and show error
            print(f"Login error: {str(e)}")
            flash('An error occurred during login. Please try again.', 'error')
            return render_template('login.html')
    
    # GET request - show login form
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Handle user registration - Step 1: Collect user information and send OTP."""
    if request.method == 'POST':
        # Get form data
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        role = request.form.get('user_type')  # Default role is 'user'


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
        
        # Store registration data in session for later use
        session['registration_email'] = email
        session['registration_password'] = password
        session['registration_role'] = role
        # Generate OTP
        otp = otp_service.generate_otp(email)
        print(f"Generated OTP for {email}: {otp}, type: {type(otp)}")
        # Send OTP via email
        html_message = f"""
        <h2>Email Verification</h2>
        <p>Thank you for registering with Job Application Agent. Please use the following OTP to verify your email address:</p>
        <h3 style="font-size: 24px; letter-spacing: 5px; background-color: #f5f5f5; padding: 10px; text-align: center;">{otp}</h3>
        <p>This OTP will expire in 5 minutes.</p>
        <p>If you did not request this verification, please ignore this email.</p>
        """
        
        notification_service.send_email_notification(
            user_id=None,  # No user ID yet
            subject="Email Verification - Job Application Agent",
            message=f"Your OTP for email verification is: {otp}. This code will expire in 5 minutes.",
            html_message=html_message
        )
        
        # Redirect to OTP verification page
        return redirect(url_for('auth.verify_otp'))
    
    # GET request - show registration form
    return render_template('register.html')

@auth_bp.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    """Handle OTP verification - Step 2: Verify OTP and complete registration."""
    # Check if registration data exists in session
    if 'registration_email' not in session or 'registration_password' not in session:
        flash('Registration session expired. Please start again.', 'error')
        return redirect(url_for('auth.register'))
    
    email = session['registration_email']
    password = session['registration_password']
    role = session.get('registration_role')  # Default to 'user' if not set
    if request.method == 'POST':
        # Get OTP from form
        otp = request.form.get('otp')
        
        if not otp:
            flash('OTP is required', 'error')
            return render_template('verify_otp.html', email=email)
        
        # Verify OTP
        print("#" * 20)
        print(f"Verifying OTP for {email}: {otp}, type: {type(otp)}")
        success, message = otp_service.verify_otp(email, otp)
        
        if not success:
            flash(message, 'error')
            return render_template('verify_otp.html', email=email)
        
        # OTP verified, create user
        success, user_id, message = auth_service.create_user(email, password, personal_data={'roles': [role] if role else ['user']})
        
        if success:
            # Clear registration data from session
            session.pop('registration_email', None)
            session.pop('registration_password', None)
            session.pop('registration_role', None)

            # Clear OTP record
            otp_service.clear_otp(email)
            
            flash('Registration successful. Please log in.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash(message, 'error')
            return render_template('verify_otp.html', email=email)
    
    # GET request - show OTP verification form
    return render_template('verify_otp.html', email=email)

@auth_bp.route('/resend-otp', methods=['POST'])
def resend_otp():
    """Resend OTP for email verification."""
    # Check if registration data exists in session
    if 'registration_email' not in session:
        return jsonify({'success': False, 'message': 'Registration session expired. Please start again.'})
    
    email = session['registration_email']
    
    # Generate new OTP
    otp = otp_service.generate_otp(email)
    
    # Send OTP via email
    html_message = f"""
    <h2>Email Verification</h2>
    <p>You requested a new OTP. Please use the following code to verify your email address:</p>
    <h3 style="font-size: 24px; letter-spacing: 5px; background-color: #f5f5f5; padding: 10px; text-align: center;">{otp}</h3>
    <p>This OTP will expire in 5 minutes.</p>
    <p>If you did not request this verification, please ignore this email.</p>
    """
    
    notification_service.send_email_notification(
        user_id=None,  # No user ID yet
        subject="Email Verification - Job Application Agent",
        message=f"Your new OTP for email verification is: {otp}. This code will expire in 5 minutes.",
        html_message=html_message
    )
    
    return jsonify({'success': True, 'message': 'OTP resent successfully'})

@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    """Handle user logout."""
    auth_service.end_session()
    flash('You have been logged out', 'info')
    return redirect(url_for('auth.login'))