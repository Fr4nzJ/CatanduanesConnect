from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
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
                flash(f'Access denied. Must be one of: {", ".join(roles)}', 'danger')
                return redirect(url_for('home'))
            if current_user.verification_status != 'verified':
                flash('Your account needs to be verified first.', 'warning')
                return redirect(url_for('home'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator