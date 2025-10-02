import os
import json
import logging
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import User
from oauth import get_google_auth_flow, get_google_user_info

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
        # Validate that OAuth credentials are configured
        client_id = current_app.config.get('GOOGLE_CLIENT_ID')
        client_secret = current_app.config.get('GOOGLE_CLIENT_SECRET')
        redirect_uri = current_app.config.get('GOOGLE_REDIRECT_URI')
        if not client_id or not client_secret:
            current_app.logger.error('Google OAuth credentials not configured (GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET).')
            flash('Google OAuth is not configured on the server. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.', 'danger')
            return redirect(url_for('auth.login'))
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": current_app.config.get('GOOGLE_CLIENT_ID'),
                    "client_secret": current_app.config.get('GOOGLE_CLIENT_SECRET'),
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token"
                }
            },
            scopes=[
                'https://www.googleapis.com/auth/userinfo.email',
                'https://www.googleapis.com/auth/userinfo.profile',
                'openid'
            ],
            redirect_uri=current_app.config.get('GOOGLE_REDIRECT_URI')
        )
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        session['google_state'] = state
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
    try:
        # Validate that OAuth credentials are configured
        client_id = current_app.config.get('GOOGLE_CLIENT_ID')
        client_secret = current_app.config.get('GOOGLE_CLIENT_SECRET')
        redirect_uri = current_app.config.get('GOOGLE_REDIRECT_URI')
        if not client_id or not client_secret:
            current_app.logger.error('Google OAuth credentials not configured (GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET) on callback.')
            flash('Google OAuth is not configured on the server. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.', 'danger')
            return redirect(url_for('auth.login'))

        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": current_app.config.get('GOOGLE_CLIENT_ID'),
                    "client_secret": current_app.config.get('GOOGLE_CLIENT_SECRET'),
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token"
                }
            },
            scopes=[
                'https://www.googleapis.com/auth/userinfo.email',
                'https://www.googleapis.com/auth/userinfo.profile',
                'openid'
            ],
            state=session.get('google_state'),
            redirect_uri=current_app.config.get('GOOGLE_REDIRECT_URI')
        )
        # Debug: log incoming args and session state (no secrets)
        current_app.logger.info(f"Google callback request.args: {dict(request.args)}")
        current_app.logger.info(f"Google callback session keys: {list(session.keys())}")
        current_app.logger.info(f"Google callback stored state present: {'google_state' in session}")
        # Log what Flask sees as the request scheme
        current_app.logger.info(f"Flask request.scheme: {request.scheme}, wsgi.url_scheme: {request.environ.get('wsgi.url_scheme')}, request.url: {request.url}")

        # Exchange authorization code for tokens
        try:
            flow.fetch_token(authorization_response=request.url)
        except Exception as fetch_exc:
            # Provide rich diagnostic logs so we can see why the token exchange failed
            try:
                exc_type = type(fetch_exc).__name__
            except Exception:
                exc_type = 'UnknownException'

            current_app.logger.error(
                "Failed to fetch token from Google: %s -- exception_type=%s -- flow_redirect_uri=%s -- configured_redirect_uri=%s -- request_url=%s -- request_scheme=%s",
                str(fetch_exc),
                exc_type,
                getattr(flow, 'redirect_uri', None),
                current_app.config.get('GOOGLE_REDIRECT_URI'),
                request.url,
                request.scheme,
                exc_info=True
            )

            # Special-case insecure transport errors from oauthlib for clarity
            from oauthlib.oauth2.rfc6749.errors import InsecureTransportError
            if exc_type == 'InsecureTransportError' or isinstance(fetch_exc, InsecureTransportError):
                current_app.logger.error('OAuthlib raised InsecureTransportError: OAuth 2 requires HTTPS. Check that ProxyFix is applied and request.scheme is https.')

            flash('Failed to obtain tokens from Google. See server logs for details.', 'danger')
            return redirect(url_for('auth.login'))

        credentials = flow.credentials
        # Log presence of tokens (do NOT log token values)
        try:
            has_token = hasattr(credentials, 'token')
            has_id_token = bool(getattr(credentials, 'id_token', None))
        except Exception:
            has_token = False
            has_id_token = False
        current_app.logger.info(f"Credentials present: has_token={has_token}, has_id_token={has_id_token}")

        if not has_id_token:
            current_app.logger.error('Google credentials missing id_token after fetch_token')
            flash('Google did not return an ID token. Ensure the "openid" scope is requested and the OAuth client is configured correctly.', 'danger')
            return redirect(url_for('auth.login'))

        id_info = id_token.verify_oauth2_token(
            credentials.id_token,
            google_requests.Request(),
            current_app.config.get('GOOGLE_CLIENT_ID')
        )
        email = id_info.get('email')
        name = id_info.get('name')
        picture = id_info.get('picture')
        if not email or not name:
            raise ValueError('Missing email or name from Google response')

        user = User.get_by_email(email)
        if not user:
            user = User(
                name=name,
                email=email,
                profile_picture=picture,
                password=generate_password_hash(email),
                verification_status='verified'
            )
            user.save()
        else:
            user.profile_picture = picture
            user.verification_status = 'verified'
            user.save()

        # Set session for Flask-Login
        login_user(user)
        flash('Successfully logged in with Google!', 'success')
        return redirect(url_for('dashboard'))
    except Exception as e:
        import traceback
        current_app.logger.error(f"Google callback error: {str(e)}\n{traceback.format_exc()}")
        flash('Failed to log in with Google.', 'danger')
        return redirect(url_for('auth.login'))
