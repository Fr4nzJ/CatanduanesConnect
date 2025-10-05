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


