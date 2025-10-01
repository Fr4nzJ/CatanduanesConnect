from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from models import User
from oauth import get_google_auth_flow, get_google_user_info
import json

auth = Blueprint('auth', __name__)

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