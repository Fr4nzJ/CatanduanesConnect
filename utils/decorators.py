from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user, login_required


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if getattr(current_user, 'role', None) != 'admin':
            flash("Access denied. Admins only.", "danger")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if current_user.verification_status == 'pending_verification':
                return redirect(url_for('auth.restricted_access'))
            if not current_user.role or current_user.role not in roles:
                flash(f"Access denied. This page is for {', '.join(roles)} only.", "danger")
                return redirect(url_for("home.index"))
            return f(*args, **kwargs)
        return decorated_function
    return decorator
