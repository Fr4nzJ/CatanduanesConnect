import os
import json
import logging
import uuid
from datetime import datetime
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import User
from werkzeug.utils import secure_filename
from oauth import get_google_auth_flow_from_config, get_google_user_info
from pathlib import Path
from database import driver, DATABASE, get_neo4j_driver
from utils.email_utils import notify_admins_new_submission, send_document_received_email

# Ensure we have a driver
if driver is None:
    driver = get_neo4j_driver()

auth = Blueprint('auth', __name__)

# File upload configuration
UPLOAD_FOLDER = Path('static') / 'uploads'
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
ALLOWED_EXTENSIONS = {
    'job_seeker': {'pdf', 'doc', 'docx'},
    'business_owner': {'pdf', 'png', 'jpg', 'jpeg'},
    'client': {'png', 'jpg', 'jpeg'}
}

@auth.route('/restricted_access')
def restricted_access():
    return render_template('auth/restricted_access.html')

@auth.route('/complete_registration', methods=['GET', 'POST'])
def complete_registration():
    google_user = session.get('google_user')
    if not google_user:
        flash('Please sign up with Google first.', 'warning')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        role = request.form.get('role')
        if not role or role not in ['job_seeker', 'business_owner', 'client']:
            flash('Please select a valid role.', 'danger')
            return redirect(url_for('auth.complete_registration'))

        document_path = None
        id_front_path = None
        id_back_path = None

        if role == 'client':
            front = request.files.get('id_front')
            back = request.files.get('id_back')
            if not front or not back:
                flash('Please upload both ID front and back.', 'danger')
                return redirect(url_for('auth.complete_registration'))

            # Validate extensions
            if not front.filename.lower().endswith(tuple(ALLOWED_EXTENSIONS['client'])) or not back.filename.lower().endswith(tuple(ALLOWED_EXTENSIONS['client'])):
                flash('Invalid file type for ID images. Allowed types: PNG, JPG, JPEG', 'danger')
                return redirect(url_for('auth.complete_registration'))

            # Check sizes
            for f in [front, back]:
                f.seek(0, os.SEEK_END)
                if f.tell() > 5 * 1024 * 1024:
                    flash('Each ID image must be less than 5MB.', 'danger')
                    return redirect(url_for('auth.complete_registration'))
                f.seek(0)

            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            upload_dir = UPLOAD_FOLDER / 'client'
            upload_dir.mkdir(parents=True, exist_ok=True)
            front_fn = secure_filename(f"client_id_front_{ts}_{front.filename}")
            back_fn = secure_filename(f"client_id_back_{ts}_{back.filename}")
            front.save(upload_dir / front_fn)
            back.save(upload_dir / back_fn)
            id_front_path = f"uploads/client/{front_fn}"
            id_back_path = f"uploads/client/{back_fn}"

        elif role in ['job_seeker', 'business_owner']:
            file = request.files.get('document')
            if not file or file.filename == '':
                flash('Please upload the required document.', 'danger')
                return redirect(url_for('auth.complete_registration'))

            if not file.filename.lower().endswith(tuple(ALLOWED_EXTENSIONS[role])):
                flash(f'Invalid file type. Allowed types: {", ".join(ALLOWED_EXTENSIONS[role])}', 'danger')
                return redirect(url_for('auth.complete_registration'))

            file.seek(0, os.SEEK_END)
            if file.tell() > 5 * 1024 * 1024:
                flash('File must be less than 5MB.', 'danger')
                return redirect(url_for('auth.complete_registration'))
            file.seek(0)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            upload_dir = UPLOAD_FOLDER / role
            upload_dir.mkdir(parents=True, exist_ok=True)
            filename = secure_filename(f"{role}_{timestamp}_{file.filename}")
            file.save(upload_dir / filename)
            document_path = f"uploads/{role}/{filename}"

        try:
            # Build a new user id
            new_id = str(uuid.uuid4())

            user = User(
                email=google_user['email'],
                first_name=google_user['given_name'],
                last_name=google_user['family_name'],
                google_id=google_user.get('google_id'),
                profile_picture=google_user.get('picture'),
                role=role,
                resume_path=document_path if role == 'job_seeker' else None,
                permit_path=document_path if role == 'business_owner' else None,
                id_front_path=id_front_path if role == 'client' else None,
                id_back_path=id_back_path if role == 'client' else None
            )

            with driver.session(database=DATABASE) as db_session:
                db_session.run("""
                    CREATE (u:User {
                        id: $id,
                        email: $email,
                        first_name: $first_name,
                        last_name: $last_name,
                        google_id: $google_id,
                        profile_picture: $profile_picture,
                        role: $role,
                        resume_path: $resume_path,
                        permit_path: $permit_path,
                        id_front_path: $id_front_path,
                        id_back_path: $id_back_path,
                        verification_status: 'pending_verification'
                    })
                """, {
                    'id': new_id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'google_id': user.google_id,
                    'profile_picture': user.profile_picture,
                    'role': user.role,
                    'resume_path': user.resume_path,
                    'permit_path': user.permit_path,
                    'id_front_path': user.id_front_path,
                    'id_back_path': user.id_back_path
                })

                user = User.get_by_email(google_user['email'])
                # Notify admins for any document submission
                if user and role in ['job_seeker', 'business_owner', 'client']:
                    try:
                        notify_admins_new_submission(user)
                        send_document_received_email(user)
                    except Exception as mail_exc:
                        current_app.logger.warning(f"Email failed: {mail_exc}")

            session.pop('google_user', None)
            login_user(user)
            flash('Registration completed successfully. Your account is pending verification.', 'success')
            return redirect(url_for('auth.restricted_access'))

        except Exception as e:
            current_app.logger.error(f'Error creating user: {str(e)}')
            flash('An error occurred during registration. Please try again.', 'danger')
            return redirect(url_for('auth.complete_registration'))

    return render_template('auth/complete_registration.html', google_user=google_user)


# --------------------------
# Email/Password Login
# --------------------------
@auth.route("/login", methods=["GET", "POST"])
def login():
    # Handle GET request
    if request.method == "GET":
        return render_template("auth/login.html")

    # Handle POST request
    email = request.form.get("email")
    password = request.form.get("password")
    remember = True if request.form.get("remember") else False

    if not email or not password:
        flash("Please provide both email and password.", "danger")
        return redirect(url_for("auth.login"))

    try:
        user = User.get_by_email(email)
        if not user or not check_password_hash(user.password, password):
            flash("Please check your login details and try again.", "danger")
            return redirect(url_for("auth.login"))
    except Exception as e:
        current_app.logger.error(f"Error retrieving user: {str(e)}")
        flash("An error occurred during login. Please try again.", "danger")
        return redirect(url_for("auth.login"))

    # Ensure default attributes
    if not hasattr(user, 'is_active'):
        user.is_active = True
    if not hasattr(user, 'role') or not user.role:
        user.role = 'job_seeker'
        try:
            user.save()
        except Exception as e:
            current_app.logger.error(f"Error updating user role: {str(e)}")

    # Log the user in
    try:
        login_user(user, remember=remember)
    except Exception as e:
        current_app.logger.error(f"Error during login_user: {str(e)}")
        flash("An unexpected error occurred. Please try again.", "danger")
        return redirect(url_for("auth.login"))

    # Determine redirect
    next_page = request.args.get("next")
    if user.role == 'admin':
        if next_page and next_page.startswith('/'):
            return redirect(next_page)
        return redirect(url_for("admin.dashboard"))

    # Non-admin user redirect
    return redirect(next_page or url_for("dashboard"))


# --------------------------
# Signup (Email/Password)
# --------------------------
@auth.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email")
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        middle_name = request.form.get("middle_name")
        suffix = request.form.get("suffix")
        password = request.form.get("password")

        user = User.get_by_email(email)
        if user:
            flash("Email address already exists", "danger")
            return redirect(url_for("auth.signup"))

        new_user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            middle_name=middle_name or None,
            suffix=suffix or None,
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
        # Clear any existing OAuth session data
        session.pop('google_state', None)
        
        # Validate that OAuth credentials are configured inside request context
        client_id = current_app.config.get('GOOGLE_CLIENT_ID')
        client_secret = current_app.config.get('GOOGLE_CLIENT_SECRET')
        redirect_uri = current_app.config.get('GOOGLE_REDIRECT_URI')
        
        # Log OAuth configuration (without secrets)
        current_app.logger.info("OAuth Configuration Check:")
        current_app.logger.info(f"- Client ID configured: {bool(client_id)}")
        current_app.logger.info(f"- Client Secret configured: {bool(client_secret)}")
        current_app.logger.info(f"- Redirect URI: {redirect_uri}")
        
        if not client_id or not client_secret or not redirect_uri:
            current_app.logger.error('Google OAuth credentials not configured.')
            flash('Google OAuth is not configured on the server.', 'danger')
            return redirect(url_for('auth.login'))

        # Initialize OAuth flow
        flow = get_google_auth_flow_from_config(client_id, client_secret, redirect_uri)
        
        # Generate authorization URL with state
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        # Store state in session and log (not the actual state value)
        session['google_state'] = state
        current_app.logger.info("Generated new OAuth state and stored in session")
        
        # Log the authorization URL (without query parameters for security)
        base_auth_url = authorization_url.split('?')[0]
        current_app.logger.info(f"Redirecting to Google OAuth: {base_auth_url}")
        
        # Return the redirect response
        return redirect(authorization_url)
    except Exception as e:
        current_app.logger.error(f"Error in Google login: {str(e)}", exc_info=True)
        flash("An error occurred during Google login. Please try again.", "danger")
        return redirect(url_for("auth.login"))
    except Exception as e:
        import traceback
        current_app.logger.error(f"Error in Google login: {str(e)}\n{traceback.format_exc()}")
        flash("An error occurred during Google login. Please try again.", "danger")
        return redirect(url_for("auth.login"))


@auth.route("/callback/google")
def google_callback():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("dashboard"))

    # Get state from session and request
    stored_state = session.get("google_state")
    received_state = request.args.get("state")
    
    # Log state information for debugging (don't log the actual state values)
    current_app.logger.info(f"OAuth state check: stored_exists={bool(stored_state)}, received_exists={bool(received_state)}")
    
    if not stored_state:
        current_app.logger.error("No state found in session")
        flash("Session expired. Please try signing in again.", "danger")
        return redirect(url_for("auth.login"))
        
    if not received_state:
        current_app.logger.error("No state parameter in callback URL")
        flash("No state parameter received. Please try signing in again.", "danger")
        return redirect(url_for("auth.login"))
        
    if stored_state != received_state:
        current_app.logger.error("State mismatch in OAuth callback")
        flash("Invalid state parameter. Please try signing in again.", "danger")
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
        flow = get_google_auth_flow_from_config(client_id, client_secret, redirect_uri)
        # restore state on the flow
        flow.state = session.get('google_state')
        # Debug: log incoming args and session state (no secrets)
        current_app.logger.info(f"Google callback request.args: {dict(request.args)}")
        current_app.logger.info(f"Google callback session keys: {list(session.keys())}")
        current_app.logger.info(f"Google callback stored state present: {'google_state' in session}")
        # Log what Flask sees as the request scheme
        current_app.logger.info(f"Flask request.scheme: {request.scheme}, wsgi.url_scheme: {request.environ.get('wsgi.url_scheme')}, request.url: {request.url}")

        # Exchange authorization code for tokens
        try:
            # Log critical OAuth parameters
            current_app.logger.info(f"OAuth Flow Debug:")
            current_app.logger.info(f"- Debug mode: {current_app.debug}")
            current_app.logger.info(f"- Configured redirect URI: {current_app.config.get('GOOGLE_REDIRECT_URI')}")
            current_app.logger.info(f"- Request URL: {request.url}")
            current_app.logger.info(f"- Authorization code present: {'code' in request.args}")
            current_app.logger.info(f"- Code parameter: {request.args.get('code', 'MISSING')[:5]}... (truncated)")
            current_app.logger.info(f"- Error parameter: {request.args.get('error', 'None')}")
            current_app.logger.info(f"- Error description: {request.args.get('error_description', 'None')}")
            
            # Some platforms (Railway, Heroku, etc.) terminate TLS at the edge
            # and send X-Forwarded-Proto: https to the backend. If ProxyFix
            # isn't causing Flask to see request.scheme as 'https', oauthlib
            # will raise InsecureTransportError. Detect this case and synthesize
            # an https authorization_response using the forwarded proto header.
            authorization_response = request.url
            xf_proto = (request.headers.get('X-Forwarded-Proto') or
                        request.environ.get('HTTP_X_FORWARDED_PROTO'))
            # If the request was forwarded with X-Forwarded-Proto=https but Flask sees it as http,
            # force the authorization_response to use https in non-debug mode so oauthlib doesn't raise InsecureTransportError.
            if request.scheme != 'https' and xf_proto and xf_proto.lower() == 'https' and not current_app.debug:
                authorization_response = authorization_response.replace('http://', 'https://', 1)
                current_app.logger.info('Overriding authorization_response to https based on X-Forwarded-Proto')
                current_app.logger.info('Original request.scheme=%s, X-Forwarded-Proto=%s, using authorization_response=%s', request.scheme, xf_proto, authorization_response)

            # Get authorization code and validate
            code = request.args.get('code')
            if not code:
                current_app.logger.error("No authorization code in callback")
                flash("Authorization code missing from callback. Please try again.", "danger")
                return redirect(url_for("auth.login"))

            # Check for error in callback
            if request.args.get('error'):
                error_msg = request.args.get('error_description', request.args.get('error'))
                current_app.logger.error(f"Google OAuth error: {error_msg}")
                flash(f"Authentication error: {error_msg}", "danger")
                return redirect(url_for("auth.login"))

            # Ensure flow matches configuration
            flow.redirect_uri = current_app.config.get('GOOGLE_REDIRECT_URI')
            current_app.logger.info(f"Using redirect URI: {flow.redirect_uri}")

            # Log token exchange attempt
            current_app.logger.info("Starting token exchange:")
            current_app.logger.info(f"- Authorization code present (first 5 chars): {code[:5]}...")
            current_app.logger.info(f"- Request scheme: {request.scheme}")
            current_app.logger.info(f"- Full request URL: {request.url}")

            # Perform token exchange
            flow.fetch_token(
                code=code,
                authorization_response=request.url
            )

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
            current_app.logger.warning('Google credentials missing id_token after fetch_token; attempting to fetch userinfo with access token')

        # Prefer to fetch userinfo using the access token (safer in many flows)
        user_info = None
        try:
            access_token = getattr(credentials, 'token', None)
            if access_token:
                user_info = get_google_user_info(access_token, logger=current_app.logger)
        except Exception:
            current_app.logger.exception('Error while fetching userinfo with access token')

        if not user_info and has_id_token:
            # Fall back to verifying id_token
            id_info = id_token.verify_oauth2_token(
                credentials.id_token,
                google_requests.Request(),
                client_id
            )
            user_info = {
                'email': id_info.get('email'),
                'given_name': id_info.get('given_name'),
                'family_name': id_info.get('family_name'),
                'picture': id_info.get('picture')
            }

        if not user_info:
            current_app.logger.error('Could not obtain user profile from Google (access_token or id_token)')
            flash('Could not retrieve Google profile. Please try again.', 'danger')
            return redirect(url_for('auth.login'))

        email = user_info.get('email')
        given_name = user_info.get('given_name')
        family_name = user_info.get('family_name')
        picture = user_info.get('picture')
        if not email or not given_name or not family_name:
            raise ValueError('Missing email or name components from Google response')

        user = User.get_by_email(email)
        google_id = user_info.get('google_id')
        
        # Try to find user by google_id first
        user = User.get_by_google_id(google_id) if google_id else None
        
        if not user:
            # Try finding by email as fallback
            user = User.get_by_email(email)
            
        if user:
            # Update existing user's Google info if needed
            if google_id and not user.google_id:
                user.google_id = google_id
            if picture and not user.profile_picture:
                user.profile_picture = picture
            user.save()

            # Log them in
            login_user(user)
            # If the user is verified, let them into the dashboard. Otherwise redirect to restricted access.
            if getattr(user, 'verification_status', None) == 'verified':
                flash('Successfully logged in with Google!', 'success')
                return redirect(url_for('dashboard'))
            else:
                # Provide a clear message and route unverified/rejected users to the restricted access flow
                if getattr(user, 'verification_status', None) == 'rejected':
                    flash('Your account has been rejected. Please contact support or re-submit required documents.', 'warning')
                else:
                    flash('Your account is pending verification. Some features are restricted until approval.', 'info')
                return redirect(url_for('auth.restricted_access'))
        else:
            # Store Google data in session and redirect to complete registration
            session['google_user'] = {
                'email': email,
                'given_name': given_name,
                'family_name': family_name,
                'picture': picture,
                'google_id': google_id
            }
            return redirect(url_for('auth.complete_registration'))
    except Exception as e:
        import traceback
        current_app.logger.error(f"Google callback error: {str(e)}\n{traceback.format_exc()}")
        flash('Failed to log in with Google.', 'danger')
        return redirect(url_for('auth.login'))
