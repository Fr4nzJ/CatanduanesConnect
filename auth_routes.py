from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import User
from oauth import get_google_auth_flow, get_google_user_info
import json

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        user = User.query.filter_by(email=email).first()
        
        if not user or not check_password_hash(user.password, password):
            flash('Please check your login details and try again.', 'danger')
            return redirect(url_for('auth.login'))
            
        login_user(user, remember=remember)
        next_page = request.args.get('next')
        return redirect(next_page or url_for('dashboard'))
        
    return render_template('auth/login.html')

@auth.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user:
            flash('Email address already exists', 'danger')
            return redirect(url_for('auth.signup'))
            
        new_user = User(
            email=email,
            name=name,
            password=generate_password_hash(password, method='sha256')
        )
        
        try:
            new_user.save()
            flash('Successfully registered! Please log in.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            flash('An error occurred during registration. Please try again.', 'danger')
            return redirect(url_for('auth.signup'))
            
    return render_template('auth/signup.html')

@auth.route('/login/google')
def google_login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    flow = get_google_auth_flow()
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    
    session['google_state'] = state
    return redirect(authorization_url)

@auth.route('/callback/google')
def google_callback():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    state = session.get('google_state')
    if not state or state != request.args.get('state'):
        flash('Invalid state parameter.', 'danger')
        return redirect(url_for('auth.login'))

    flow = get_google_auth_flow()
    try:
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials
        user_info = get_google_user_info(credentials.id_token)
        
        if not user_info:
            flash('Failed to get user info from Google.', 'danger')
            return redirect(url_for('auth.login'))
        
        # Check if user exists
        user = User.query.filter_by(email=user_info['email']).first()
        
        if not user:
            # Create new user
            user = User(
                name=user_info['name'],
                email=user_info['email'],
                google_id=user_info['google_id'],
                profile_picture=user_info.get('picture'),
                password=generate_password_hash(str(user_info['google_id'])),  # Generate a secure password
                is_verified=True  # Google accounts are pre-verified
            )
            user.save()
        else:
            # Update existing user's Google info
            user.google_id = user_info['google_id']
            user.profile_picture = user_info.get('picture')
            user.is_verified = True
            user.save()
        
        # Log in the user
        login_user(user)
        flash('Successfully logged in with Google!', 'success')
        return redirect(url_for('dashboard'))
        
    except Exception as e:
        flash('Failed to log in with Google.', 'danger')
        return redirect(url_for('auth.login'))