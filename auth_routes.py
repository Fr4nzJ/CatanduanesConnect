from flask import Blueprint
auth = Blueprint('auth', __name__)
auth = Blueprint("auth", __name__)
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import User
from oauth import get_google_auth_flow, get_google_user_info
import json
import logging

auth = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)

# --------------------------
# Email/Password Login
# --------------------------
@auth.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        remember = True if request.form.get("remember") else False

        user = User.get_by_email(email)

        if not user or not check_password_hash(user.password, password):
            flash("Please check your login details and try again.", "danger")
            return redirect(url_for("auth.login"))

        login_user(user, remember=remember)
        next_page = request.args.get("next")
        return redirect(next_page or url_for("dashboard"))

    return render_template("auth/login.html")


# --------------------------
# Signup (Email/Password)
# --------------------------
@auth.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email")
        name = request.form.get("name")
        password = request.form.get("password")

        user = User.get_by_email(email)
        if user:
            flash("Email address already exists", "danger")
            return redirect(url_for("auth.signup"))

        new_user = User(
            email=email,
            name=name,
            password=generate_password_hash(password, method="sha256")
        )

        try:
            new_user.save()
            flash("Successfully registered! Please log in.", "success")
            return redirect(url_for("auth.login"))
        except Exception as e:
            current_app.logger.error(f"Signup error: {str(e)}")
            flash("An error occurred during registration. Please try again.", "danger")
            return redirect(url_for("auth.signup"))

    return render_template("auth/signup.html")


# --------------------------
# Google OAuth Login
# --------------------------
@auth.route("/login/google")
def google_login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    try:
        flow = get_google_auth_flow()
        current_app.logger.info(f"Google OAuth flow initialized: {flow}")
        authorization_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true"
        )
        current_app.logger.info(f"Google OAuth authorization_url: {authorization_url}, state: {state}")
        session["google_state"] = state
        return redirect(authorization_url)
    except Exception as e:
        import traceback
        current_app.logger.error(f"Error in Google login: {str(e)}\n{traceback.format_exc()}")
        flash("An error occurred during Google login. Please try again.", "danger")
        return redirect(url_for("auth.login"))


@auth.route("/callback/google")
def google_callback():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    state = session.get("google_state")
    if not state or state != request.args.get("state"):
        flash("Invalid state parameter.", "danger")
        return redirect(url_for("auth.login"))

    flow = get_google_auth_flow()
    try:
        current_app.logger.info(f"Google callback request args: {request.args}")
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials
        current_app.logger.info(f"Google credentials: {credentials}")

        # Fetch user info with id_token if available, else access token
        user_info = get_google_user_info(credentials.id_token if hasattr(credentials, 'id_token') else credentials.token)
        current_app.logger.info(f"Google user_info: {user_info}")
        if not user_info:
            flash("Failed to get user info from Google.", "danger")
            return redirect(url_for("auth.login"))

        # Check if user already exists
        user = User.get_by_email(user_info["email"])

        if not user:
            # New Google user
            user = User(
                name=user_info["name"],
                email=user_info["email"],
                google_id=user_info["google_id"],
                profile_picture=user_info.get("picture"),
                password=generate_password_hash(user_info["google_id"]),  # Set a dummy password
                verification_status='verified'  # Google users are pre-verified
            )
            user.save()
        else:
            # Update existing user with Google data
            user.google_id = user_info["google_id"]
            user.profile_picture = user_info.get("picture")
            user.verification_status = 'verified'
            user.save()

        login_user(user)
        flash("Successfully logged in with Google!", "success")
        return redirect(url_for("dashboard"))

    except Exception as e:
        import traceback
        current_app.logger.error(f"Google callback error: {str(e)}\n{traceback.format_exc()}")
        flash("Failed to log in with Google.", "danger")
        return redirect(url_for("auth.login"))
