from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from app import db
from models import User
import logging

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = bool(request.form.get('remember'))
        
        if not email or not password:
            flash('Please fill in all fields', 'error')
            return render_template('login.html')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            if user.is_active:
                login_user(user, remember=remember)
                logging.info(f"User {user.email} logged in successfully")
                
                # Redirect to the page they were trying to access, or dashboard
                next_page = request.args.get('next')
                if not next_page or not next_page.startswith('/'):
                    next_page = url_for('dashboard')
                return redirect(next_page)
            else:
                flash('Your account has been deactivated. Please contact support.', 'error')
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        company_name = request.form.get('company_name')
        
        # Validation
        if not all([username, email, password, confirm_password]):
            flash('Please fill in all required fields', 'error')
            return render_template('login.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('login.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return render_template('login.html')
        
        # Check if user already exists
        if User.query.filter_by(email=email).first():
            flash('Email address already registered', 'error')
            return render_template('login.html')
        
        if User.query.filter_by(username=username).first():
            flash('Username already taken', 'error')
            return render_template('login.html')
        
        # Create new user
        user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            company_name=company_name
        )
        user.set_password(password)
        
        try:
            db.session.add(user)
            db.session.commit()
            logging.info(f"New user registered: {user.email}")
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error creating user: {str(e)}")
            flash('Registration failed. Please try again.', 'error')
    
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """User logout"""
    logging.info(f"User {current_user.email} logged out")
    logout_user()
    flash('You have been logged out successfully', 'info')
    return redirect(url_for('auth.login'))

# Register the blueprint
from app import app
app.register_blueprint(auth_bp, url_prefix='/auth')
