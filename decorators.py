from functools import wraps
from flask import flash, redirect, url_for, request
from flask_login import current_user

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        if current_user.role != 'admin':
            flash('Access denied. Admin privileges required.', 'danger')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

def verified_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        if current_user.verification_status != 'verified':
            flash('Your account is pending verification. Some features are restricted.', 'warning')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    """Decorator to check if current user has any of the specified roles."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login'))
            if current_user.role not in roles:
                flash(f'Access denied. Required role: {", ".join(roles)}', 'danger')
                return redirect(url_for('home'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def job_seeker_required(f):
    """Decorator to check if current user is a job seeker."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        if current_user.role != 'job_seeker':
            flash('Access denied. Job seeker privileges required.', 'danger')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
        if current_user.role != 'job_seeker':
            flash('Access denied. Job seeker account required.', 'danger')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

def business_owner_required(f):
    """Decorator to check if current user is a business owner."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        if current_user.role != 'business_owner':
            flash('Access denied. Business owner account required.', 'danger')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

def service_client_required(f):
    """Decorator to check if current user is a service client."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        if current_user.role != 'service_client':
            flash('Access denied. Service client account required.', 'danger')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function