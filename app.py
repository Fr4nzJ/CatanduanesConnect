import os
import uuid
import json
import logging
from logging.handlers import RotatingFileHandler
import random
from datetime import datetime, timedelta
from functools import wraps
from neo4j import GraphDatabase, exceptions as neo4j

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, g, send_file
from werkzeug.exceptions import HTTPException
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_cors import CORS
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from neo4j import GraphDatabase, exceptions as neo4j_exceptions

from email_service import (
    send_verification_email, 
    send_password_reset_email,
    send_business_verification_result, 
    send_application_status_update
)

from models import (
    User, Business, Job, Application, 
    Review, Service, Notification, Activity
)
from decorators import admin_required
from admin_routes import admin
from chatbot_routes import bp as chatbot_bp
from dashboard_routes import dashboard
from routes.job_routes import bp as jobs_bp
from routes.service_routes import bp as services_bp
from routes.business_routes import bp as business_bp

# Initialize Flask app
app = Flask(__name__)

# Initialize a simple module logger early so startup code can log before
# the full logging configuration is applied later in this file. This
# prevents NameError when early startup code (like ProxyFix or config
# import handling) needs to emit logs.
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Load application configuration from config.py (reads environment variables)
try:
    from config import Config
    app.config.from_object(Config)
except Exception:
    # If config import fails, continue with existing config and rely on os.environ
    logger.warning('Could not import Config from config.py; falling back to environment variables')

# Trust proxy headers so request.url reflects the original https scheme when behind Railway
try:
    from werkzeug.middleware.proxy_fix import ProxyFix
    # Railway terminates TLS at the edge. Trust a single proxy hop for X-Forwarded headers
    # (x_for and x_proto = 1). Keep x_host/x_port = 1 as well so host/port forwarded values are trusted.
    proxy_fix = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)
    app.wsgi_app = proxy_fix
    logger.info('Applied ProxyFix middleware (x_for=1, x_proto=1, x_host=1, x_port=1)')
except Exception:
    logger.warning('Could not apply ProxyFix middleware')

# Log the ProxyFix configuration so we can verify trusted hop counts at runtime
if 'proxy_fix' in locals():
    try:
        x_for = getattr(proxy_fix, 'x_for', None)
        x_proto = getattr(proxy_fix, 'x_proto', None)
        x_host = getattr(proxy_fix, 'x_host', None)
        x_port = getattr(proxy_fix, 'x_port', None)
        x_prefix = getattr(proxy_fix, 'x_prefix', None)
        logger.info('ProxyFix configuration: x_for=%s, x_proto=%s, x_host=%s, x_port=%s, x_prefix=%s', x_for, x_proto, x_host, x_port, x_prefix)
    except Exception:
        logger.exception('Could not introspect ProxyFix configuration')
else:
    logger.info('ProxyFix not configured')

# Enable CORS
CORS(app)

# Register blueprints
app.register_blueprint(admin, name='admin_blueprint')
app.register_blueprint(chatbot_bp)
app.register_blueprint(dashboard)
app.register_blueprint(jobs_bp)
app.register_blueprint(services_bp)

# Custom template filters
@app.template_filter('datetime')
def format_datetime(value):
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            return value
    
    now = datetime.now()
    diff = now - value
    
    if diff.days == 0:
        if diff.seconds < 60:
            return 'just now'
        if diff.seconds < 3600:
            minutes = diff.seconds // 60
            return f'{minutes} minute{"s" if minutes != 1 else ""} ago'
        if diff.seconds < 86400:
            hours = diff.seconds // 3600
            return f'{hours} hour{"s" if hours != 1 else ""} ago'
    if diff.days == 1:
        return 'yesterday'
    if diff.days < 7:
        return f'{diff.days} days ago'
    return value.strftime('%B %d, %Y')

# Import and register auth blueprint
from auth_routes import auth
app.register_blueprint(auth)

# Set up enhanced logging
if not os.path.exists('logs'):
    os.mkdir('logs')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        RotatingFileHandler(
            'logs/app.log', 
            maxBytes=10240,
            backupCount=10
        )
    ])

# Routes
@app.route('/about')
def about():
    """Render the about us page."""
    return render_template('about.html')


@app.route('/map', endpoint='map')
def map_view():
    """Render the standalone map page. Kept for backward compatibility with templates linking to 'map'.

    Note: interactive maps are used inline and in modals across the site, but some templates
    still link to a dedicated map page. This route renders templates/map.html.
    """
    return render_template('map.html')

# Error handlers
@app.errorhandler(HTTPException)
def handle_http_error(e):
    """Handle HTTP exceptions."""
    app.logger.error(f'HTTP error occurred: {e}')
    return render_template('errors/error.html', error=e), e.code

@app.errorhandler(Exception)
def handle_error(e):
    """Handle non-HTTP exceptions."""
    app.logger.error(f'Unhandled exception: {str(e)}', exc_info=True)
    return render_template('errors/500.html'), 500

@app.before_request
def log_request_info():
    """Log request details."""
    if not request.path.startswith('/static'):
        app.logger.info('Headers: %s', request.headers)
        app.logger.info('Body: %s', request.get_data())
logger = logging.getLogger(__name__)

# Error tracking
@app.errorhandler(500)
def internal_error(error):
    logger.error(f'Server Error: {error}')
    return 'Internal Server Error', 500

@app.errorhandler(404)
def not_found_error(error):
    return 'Not Found', 404

@app.before_request
def log_request_info():
    logger.info('Headers: %s', request.headers)
    logger.info('Body: %s', request.get_data())

# Load environment variables
load_dotenv()

# Load required environment variables
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

# Configure app
app.config.update(
    SECRET_KEY=os.getenv('FLASK_SECRET_KEY', os.urandom(24).hex()),
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax'
)

if not all([NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD]):
    logger.error("Missing required Neo4j environment variables!")
    raise ValueError("Missing required Neo4j environment variables!")

# Neo4j AuraDB setup
try:
    driver = GraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
    )
    # Test the connection
    with driver.session(database=DATABASE) as session:
        session.run("RETURN 1")
    logger.info("Successfully connected to Neo4j database")
except Exception as e:
    logger.error(f"Failed to connect to Neo4j: {str(e)}")
    raise

# Configure Flask app
FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY')
if not FLASK_SECRET_KEY:
    FLASK_SECRET_KEY = os.urandom(24)
    logger.warning('No FLASK_SECRET_KEY set. Using random secret key.')

app.config.update(
    SECRET_KEY=FLASK_SECRET_KEY,
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax'
)

# Startup diagnostics: log Google OAuth config and ensure User model has expected method
try:
    logger.info("Google OAuth configured? client_id=%s redirect_uri=%s",
                bool(app.config.get('GOOGLE_CLIENT_ID')), app.config.get('GOOGLE_REDIRECT_URI'))
    # Check that User model exposes get_by_email
    logger.info("models.User has get_by_email: %s", hasattr(User, 'get_by_email'))
except Exception:
    logger.exception('Error logging startup diagnostics')

# Initialize extensions
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Initialize CSRF protection
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect(app)

# File upload configuration
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
ALLOWED_EXTENSIONS = {
    'resume': {'pdf', 'doc', 'docx'},
    'permit': {'pdf', 'png', 'jpg', 'jpeg'}
}
MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB max file size

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Create upload directories with proper permissions
try:
    # Create parent uploads directory
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
        logger.info(f'Created main upload directory: {UPLOAD_FOLDER}')
    
    # Create subdirectories with proper permissions
    for dir_name in ['resumes', 'permits']:
        dir_path = os.path.join(UPLOAD_FOLDER, dir_name)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
            # Set directory permissions (readable/writable by app)
            os.chmod(dir_path, 0o755)
            logger.info(f'Created upload directory with permissions: {dir_path}')
except Exception as e:
    logger.error(f'Error setting up upload directories: {str(e)}')




def allowed_file(filename, file_type):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS[file_type]

def secure_upload(file, file_type):
    """
    Securely upload a file and return its filename.
    Args:
        file: FileStorage object from request.files
        file_type: Type of file ('resume' or 'permit')
    Returns:
        str: The saved filename or None if file is invalid
    Raises:
        ValueError: If file type is not allowed
        OSError: If there are file system errors
    """
    if not file or not file.filename:
        return None
        
    if not allowed_file(file.filename, file_type):
        raise ValueError(f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS[file_type])}")
    
    try:
        # Create a secure filename with UUID to prevent collisions
        filename = secure_filename(f"{file_type}_{uuid.uuid4()}_{file.filename}")
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_type}s", filename)
        
        # Save the file
        file.save(file_path)
        
        # Set proper file permissions
        os.chmod(file_path, 0o644)
        
        logger.info(f'Successfully uploaded {file_type}: {filename}')
        return filename
        
    except Exception as e:
        logger.error(f'Error uploading {file_type}: {str(e)}')
        raise OSError(f"Error saving {file_type} file: {str(e)}")

# Create necessary directories
os.makedirs('static/resumes', exist_ok=True)

# Admin required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Unauthorized access', 'danger')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

# Create initial admin if none exists
def create_admin_if_none_exists():
    """Create the default admin account if it doesn't exist."""
    try:
        # Check if admin exists
        admin = User.get_by_email('ermido09@gmail.com')
        
        if not admin:
            # Create new admin user
            admin = User(
                email='ermido09@gmail.com',
                name='Franz Jermido',
                role='admin',
                verification_status='verified'
            )
            admin.set_password('Fr4nzJermido')
            admin.save()
            logger.info('Default admin account created successfully')
        else:
            # Ensure existing admin has correct role and password
            if admin.role != 'admin':
                admin.role = 'admin'
                admin.save()
            if not admin.check_password('Fr4nzJermido'):
                admin.set_password('Fr4nzJermido')
                admin.save()
            logger.info('Existing admin account verified')
        
        return admin
    except Exception as e:
        logger.error(f'Error creating default admin: {str(e)}')
        return None

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(user_id)

# Ensure the default admin account exists at startup (safe, non-fatal)
try:
    created_admin = create_admin_if_none_exists()
    if created_admin:
        logger.info('Admin verified/created at startup: %s', getattr(created_admin, 'email', 'unknown'))
    else:
        logger.info('Admin check completed at startup (no changes)')
except Exception:
    logger.exception('Error while ensuring admin account at startup')

# Routes
@app.route('/')
def home():
    return render_template('home.html')


# Diagnostic probe endpoint to verify how Flask sees the incoming request
# Use this to check request.scheme, wsgi.url_scheme and X-Forwarded-Proto from the proxy
@app.route('/_probe')
def probe():
    try:
        info = {
            'request_scheme': request.scheme,
            'wsgi_url_scheme': request.environ.get('wsgi.url_scheme'),
            'x_forwarded_proto': request.headers.get('X-Forwarded-Proto') or request.environ.get('HTTP_X_FORWARDED_PROTO'),
            'host': request.host,
            'url': request.url,
            'headers_sample': {
                'X-Forwarded-Proto': request.headers.get('X-Forwarded-Proto'),
                'X-Forwarded-For': request.headers.get('X-Forwarded-For')
            }
        }
        app.logger.info('Probe endpoint hit: %s', info)
        return jsonify(info), 200
    except Exception as e:
        app.logger.exception('Error in probe endpoint')
        return jsonify({'error': str(e)}), 500

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            role = request.form.get('role')

            # Validate input
            if not all([name, email, password, confirm_password, role]):
                flash('All fields are required', 'danger')
                return redirect(url_for('signup'))

            if password != confirm_password:
                flash('Passwords do not match', 'danger')
                return redirect(url_for('signup'))

            if role not in User.SIGNUP_ROLES:
                flash('Invalid user role', 'danger')
                return redirect(url_for('signup'))

            # Check if email already exists
            if User.get_by_email(email):
                flash('Email already registered', 'danger')
                return redirect(url_for('signup'))

            # Create new user
            user = User()
            user.name = name
            user.email = email
            user.role = role
            user.set_password(password)
            user.id = str(uuid.uuid4())  # Ensure ID is set before saving
            
            # Handle file uploads based on role
            try:
                if role == 'business_owner':
                    # Business owner must upload permit
                    if 'permit' not in request.files or not request.files['permit'].filename:
                        flash('Business permit is required for business owners', 'danger')
                        return redirect(url_for('signup'))
                        
                    permit_file = request.files['permit']
                    if not allowed_file(permit_file.filename, 'permit'):
                        flash('Invalid permit file type. Allowed types: PDF, PNG, JPG, JPEG', 'danger')
                        return redirect(url_for('signup'))
                        
                    try:
                        filename = secure_upload(permit_file, 'permit')
                        if filename:
                            user.permit_path = filename
                            user.verification_status = 'pending'
                    except Exception as e:
                        logger.error(f'Error uploading permit: {str(e)}')
                        flash('Error uploading business permit. Please try again.', 'danger')
                        return redirect(url_for('signup'))
                
                elif role == 'job_seeker':
                    # Resume is optional for job seekers
                    if 'resume' in request.files and request.files['resume'].filename:
                        resume_file = request.files['resume']
                        if not allowed_file(resume_file.filename, 'resume'):
                            flash('Invalid resume file type. Allowed types: PDF, DOC, DOCX', 'danger')
                            return redirect(url_for('signup'))
                            
                        try:
                            filename = secure_upload(resume_file, 'resume')
                            if filename:
                                user.resume_path = filename
                        except Exception as e:
                            logger.error(f'Error uploading resume: {str(e)}')
                            flash('Error uploading resume. You can upload it later from your profile.', 'warning')
            except Exception as e:
                logger.error(f'Error handling file uploads: {str(e)}')
                flash('Error processing file uploads. Please try again.', 'danger')
                return redirect(url_for('signup'))
                            
            except Exception as e:
                logger.error(f'File upload error: {str(e)}')
                filename = secure_upload(request.files['permit'], 'permit')
                if filename:
                    user.permit_path = filename
                    user.verification_status = 'pending'
                else:
                    flash('Business permit is required for business owners', 'danger')
                    return redirect(url_for('signup'))
                    
        except ValueError as e:
            flash(str(e), 'danger')
            return redirect(url_for('signup'))
        except Exception as e:
            flash('Error uploading file. Please try again.', 'danger')
            return redirect(url_for('signup'))
            
        try:
            if not user.save():
                logger.error('Failed to save user to database')
                flash('Error creating account. Please try again.', 'danger')
                return redirect(url_for('signup'))
                
            login_user(user)
            flash('Account created successfully!', 'success')
            
            if role == 'business_owner':
                flash('Your account will be reviewed by an admin before you can post jobs.', 'info')
                
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            logger.error(f'Database error during signup: {str(e)}')
            flash('Error creating account. Please try again later. If the problem persists, contact support.', 'danger')
            return redirect(url_for('signup'))
            
        except neo4j.exceptions.ServiceUnavailable:
            logger.error('Neo4j database is unavailable')
            flash('Service temporarily unavailable. Please try again later.', 'danger')
            return redirect(url_for('signup'))
            
        except Exception as e:
            logger.error(f'Unexpected error during signup: {str(e)}')
            flash('An unexpected error occurred. Please try again later.', 'danger')
            return redirect(url_for('signup'))
    
    return render_template('auth/signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.get_by_email(email)
        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'danger')

    return render_template('auth/login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/download/resume/<user_id>')
@login_required
@admin_required
def download_resume(user_id):
    """Download a user's resume."""
    try:
        user = User.get_by_id(user_id)
        if not user or not user.resume_path:
            flash('Resume not found.', 'danger')
            return redirect(url_for('admin.verify_users_list'))
            
        return send_file(
            user.resume_path,
            as_attachment=True,
            download_name=f"{user.name}_resume.{user.resume_path.split('.')[-1]}"
        )
    except Exception as e:
        logger.error(f"Error downloading resume: {str(e)}")
        flash('Error downloading resume.', 'danger')
        return redirect(url_for('admin.verify_users_list'))

@app.route('/download/permit/<user_id>')
@login_required
@admin_required
def download_permit(user_id):
    """Download a user's business permit."""
    try:
        user = User.get_by_id(user_id)
        if not user or not user.permit_path:
            flash('Business permit not found.', 'danger')
            return redirect(url_for('admin.verify_users_list'))
            
        return send_file(
            user.permit_path,
            as_attachment=True,
            download_name=f"{user.name}_permit.{user.permit_path.split('.')[-1]}"
        )
    except Exception as e:
        logger.error(f"Error downloading permit: {str(e)}")
        flash('Error downloading permit.', 'danger')
        return redirect(url_for('admin.verify_users_list'))

@app.route('/notifications')
@login_required
def view_notifications():
    """View user notifications."""
    try:
        # Get notification parameters
        limit = request.args.get('limit', 10, type=int)
        unread_only = request.args.get('unread_only', False, type=bool)
        
        # If it's an AJAX request, return JSON data
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            notifications = Notification.get_user_notifications(
                current_user.id, 
                limit=limit,
                unread_only=unread_only
            )
            unread_count = Notification.get_unread_count(current_user.id)
            
            return jsonify({
                'notifications': [vars(n) for n in notifications],
                'unread_count': unread_count
            })
            
        # For regular requests, return the template
        notifications = Notification.get_user_notifications(current_user.id)
        return render_template('notifications.html', notifications=notifications)
        
    except Exception as e:
        logger.error(f'Error fetching notifications: {str(e)}')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': str(e)}), 500
        flash('Error loading notifications', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/admin/dashboard/data')
@login_required
@admin_required
def admin_dashboard_data():
    try:
        with driver.session(database=DATABASE) as session:
            # Get user statistics by role
            user_stats = session.run("""
                MATCH (u:User)
                WITH u.role as role, count(u) as count
                RETURN collect({role: role, count: count}) as roles
            """).single()['roles']
            
            # Get total counts
            total_counts = session.run("""
                CALL { MATCH (u:User) RETURN count(u) AS users }
                CALL { MATCH (b:Business) RETURN count(b) AS businesses }
                CALL { MATCH (j:Job) RETURN count(j) AS jobs }
                CALL { MATCH (s:Service) RETURN count(s) AS services }
                CALL { MATCH (a:Application) RETURN count(a) AS applications }
                RETURN { 
                    users: users, 
                    businesses: businesses, 
                    jobs: jobs, 
                    services: services, 
                    applications: applications 
                } AS counts
            """).single()['counts']
            
            # Get application statistics by status
            app_stats = session.run("""
                MATCH (a:Application)
                WITH a.status as status, count(a) as count
                RETURN collect({status: status, count: count}) as statuses
            """).single()['statuses']
            
            # Get recent activities with user names
            activities = Activity.get_recent(10)
            
            return jsonify({
                'users': user_stats,
                'businesses': total_counts['businesses'],
                'jobs': total_counts['jobs'],
                'services': total_counts['services'],
                'applications': app_stats,
                'recent_activity': activities
            })
            
    except Exception as e:
        logger.error(f"Error fetching admin stats: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        if current_user.role == 'admin':
            return redirect(url_for('admin_blueprint.dashboard'))
        elif current_user.role == 'job_seeker':
            try:
                job_applications = Application.get_by_applicant_id(current_user.id)
                service_offers = Service.get_offers_by_job_seeker(current_user.id)
                return render_template('dashboard/job_seeker.html', 
                                    applications=job_applications,
                                    service_offers=service_offers)
            except Exception as e:
                logger.error(f'Error loading job seeker dashboard: {str(e)}')
                flash('Error loading your applications and offers. Please try again.', 'danger')
                return render_template('dashboard/job_seeker.html', 
                                    applications=[],
                                    service_offers=[])
                                
        elif current_user.role == 'business_owner':
            try:
                business = Business.get_by_owner_id(current_user.id)
                jobs = []
                applications = []
                if business:
                    jobs = Job.get_by_business_id(business.id)
                    # Get applications for each job
                    for job in jobs:
                        job_apps = Application.get_by_job_id(job.id)
                        applications.extend(job_apps if job_apps else [])
                return render_template('dashboard/business_owner.html',
                                    business=business,
                                    jobs=jobs,
                                    applications=applications)
            except Exception as e:
                logger.error(f'Error loading business owner dashboard: {str(e)}')
                flash('Error loading your business dashboard. Please try again.', 'danger')
                return render_template('dashboard/business_owner.html',
                                    business=None,
                                    jobs=[],
                                    applications=[])
                                
        elif current_user.role == 'client':
            try:
                # Get services where the current user is the client
                with driver.session(database=DATABASE) as session:
                    result = session.run("""
                        MATCH (s:Service)-[:REQUESTED_BY]->(u:User {id: $user_id})
                        RETURN s ORDER BY s.created_at DESC
                    """, {"user_id": current_user.id})
                    services = [Service(**record["s"]) for record in result]
                return render_template('dashboard/client.html', services=services)
            except neo4j_exceptions.ServiceUnavailable as e:
                logger.error(f'Database connection error in client dashboard: {str(e)}')
                flash('Database connection error. Please try again later.', 'danger')
                return render_template('dashboard/client.html', services=[])
            except Exception as e:
                logger.error(f'Error loading client dashboard: {str(e)}')
                flash('Error loading your services. Please try again.', 'danger')
                return render_template('dashboard/client.html', services=[])
                                
        else:  # admin
            try:
                with driver.session(database=DATABASE) as session:
                    # Get user statistics
                    user_stats = session.run("""
                        MATCH (u:User)
                        WITH u.role as role, count(u) as count
                        RETURN collect({role: role, count: count}) as roles
                    """).single()['roles']
                    
                    # Get total counts
                    total_counts = session.run("""
                        CALL { MATCH (u:User) RETURN count(u) AS users }
                        CALL { MATCH (b:Business) RETURN count(b) AS businesses }
                        CALL { MATCH (j:Job) RETURN count(j) AS jobs }
                        CALL { MATCH (s:Service) RETURN count(s) AS services }
                        CALL { MATCH (a:Application) RETURN count(a) AS applications }
                        RETURN { 
                            users: users, 
                            businesses: businesses, 
                            jobs: jobs, 
                            services: services, 
                            applications: applications 
                        } AS counts
                    """).single()['counts']
                    
                    # Get application statistics
                    app_stats = session.run("""
                        MATCH (a:Application) 
                        WITH a.status as status, count(a) as count 
                        RETURN collect({status: status, count: count}) as statuses;
                    """).single()['statuses']
                    
                    # Get recent activities (last 10) 
                    recent_activities = session.run("""
                        MATCH (a:Activity) 
                        RETURN a 
                        ORDER BY a.timestamp DESC 
                        LIMIT 10;
                    """).data()

                return render_template('dashboard/admin.html',
                                    user_stats=user_stats,
                                    total_counts=total_counts,
                                    app_stats=app_stats,
                                    recent_activities=recent_activities)
            except Exception as e:
                logger.error(f'Error loading admin dashboard: {str(e)}')
                flash(f'Error loading dashboard: {str(e)}', 'danger') 
                return redirect(url_for('home'))
                with driver.session(database=DATABASE) as session:
                    # Get user statistics
                    user_stats = session.run("""
                        MATCH (u:User)
                        WITH u.role as role, count(u) as count
                        RETURN collect({role: role, count: count}) as roles
                    """).single()['roles']
                    
                    # Get total counts
                    total_counts = session.run("""
                        CALL { MATCH (u:User) RETURN count(u) AS users }
                        CALL { MATCH (b:Business) RETURN count(b) AS businesses }
                        CALL { MATCH (j:Job) RETURN count(j) AS jobs }
                        CALL { MATCH (s:Service) RETURN count(s) AS services }
                        CALL { MATCH (a:Application) RETURN count(a) AS applications }
                        RETURN { 
                            users: users, 
                            businesses: businesses, 
                            jobs: jobs, 
                            services: services, 
                            applications: applications 
                        } AS counts
                    """).single()['counts']
                    
                    # Get application statistics
                    app_stats = session.run("""
                        MATCH (a:Application)
                        WITH a.status as status, count(a) as count
                        RETURN collect({status: status, count: count}) as statuses
                    """).single()['statuses']
                    
                    # Get recent activities (last 10)
                    recent_activities = session.run("""
                        MATCH (a:Activity)
                        RETURN a
                        ORDER BY a.timestamp DESC
                        LIMIT 10
                    """).data()

                return render_template('dashboard/admin.html',
                                    user_stats=user_stats,
                                    total_counts=total_counts,
                                    app_stats=app_stats,
                                    recent_activities=recent_activities)
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'danger')
        return redirect(url_for('home'))

@app.route('/jobs')
def jobs():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 10
        
        # Get all jobs
        jobs = Job.get_all()
        
        # Apply filters manually
        job_type = request.args.get('job_type')
        location = request.args.get('location')
        category = request.args.get('category')
        search_query = request.args.get('q')
        
        filtered_jobs = jobs
        if job_type:
            filtered_jobs = [job for job in filtered_jobs if job.job_type == job_type]
        if location:
            filtered_jobs = [job for job in filtered_jobs if job.location.lower() == location.lower()]
        if category:
            filtered_jobs = [job for job in filtered_jobs if job.category.lower() == category.lower()]
        if search_query:
            search_query = search_query.lower()
            filtered_jobs = [job for job in filtered_jobs if 
                           search_query in job.title.lower() or 
                           search_query in job.description.lower() or 
                           search_query in job.business.name.lower()]
        
        # Calculate pagination
        total_jobs = len(filtered_jobs)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_jobs = filtered_jobs[start_idx:end_idx]
        
        # Create pagination object
        pagination = {
            'page': page,
            'pages': (total_jobs + per_page - 1) // per_page if total_jobs else 0,
            'iter_pages': lambda: range(1, ((total_jobs + per_page - 1) // per_page) + 1) if total_jobs else []
        }
        
        return render_template('jobs/search.html', jobs=paginated_jobs, pagination=pagination)
    except Exception as e:
        flash(f'Error loading jobs: {str(e)}', 'danger')
        return redirect(url_for('home'))

@app.route('/businesses')
def businesses():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 10
        
        # Get all businesses
        businesses = Business.get_all()
        
        # Apply filters manually
        category = request.args.get('category')
        location = request.args.get('location')
        search_query = request.args.get('q')
        
        filtered_businesses = businesses
        if category:
            filtered_businesses = [b for b in filtered_businesses if b.category.lower() == category.lower()]
        if location:
            filtered_businesses = [b for b in filtered_businesses if b.location.lower() == location.lower()]
        if search_query:
            search_query = search_query.lower()
            filtered_businesses = [b for b in filtered_businesses if 
                                 search_query in b.name.lower() or 
                                 search_query in b.description.lower()]
        
        # Calculate pagination
        total_businesses = len(filtered_businesses)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_businesses = filtered_businesses[start_idx:end_idx]
        
        # Create pagination object
        pagination = {
            'page': page,
            'pages': (total_businesses + per_page - 1) // per_page if total_businesses else 0,
            'iter_pages': lambda: range(1, ((total_businesses + per_page - 1) // per_page) + 1) if total_businesses else []
        }
        
        return render_template('businesses/directory.html', businesses=paginated_businesses, pagination=pagination)
    except Exception as e:
        flash(f'Error loading businesses: {str(e)}', 'danger')
        return redirect(url_for('home'))

# NOTE: Standalone /map route removed. Maps are shown inline in pages and in modals using Leaflet.

@app.route('/profile')
@login_required
def profile():
    try:
        business = Business.get_by_owner_id(current_user.id) if current_user.role == 'business_owner' else None
        return render_template('profile.html', user=current_user, business=business)
    except Exception as e:
        flash(f'Error loading profile: {str(e)}', 'danger')
        return redirect(url_for('home'))

@app.route('/job')
def job_details():
    try:
        job_id = request.args.get('id')
        if not job_id:
            flash('Job ID is required', 'danger')
            return redirect(url_for('jobs'))
            
        job = Job.get_by_id(job_id)
        if not job:
            flash('Job not found', 'danger')
            return redirect(url_for('jobs'))
        
        has_applied = False
        if current_user.is_authenticated and current_user.role == 'job_seeker':
            has_applied = Application.has_applied(current_user.id, job_id)
        
        return render_template('jobs/details.html', job=job, has_applied=has_applied)
    except Exception as e:
        flash(f'Error loading job details: {str(e)}', 'danger')
        return redirect(url_for('jobs'))

@app.route('/business')
def business_details():
    try:
        business_id = request.args.get('id')
        if not business_id:
            flash('Business ID is required', 'danger')
            return redirect(url_for('businesses'))
            
        business = Business.get_by_id(business_id)
        if not business:
            flash('Business not found', 'danger')
            return redirect(url_for('businesses'))
        
        jobs = Job.get_by_business_id(business_id)
        return render_template('businesses/details.html', business=business, jobs=jobs)
    except Exception as e:
        flash(f'Error loading business details: {str(e)}', 'danger')
        return redirect(url_for('businesses'))

@app.route('/applications')
@login_required
def view_applications():
    if current_user.role == 'job_seeker':
        applications = Application.get_by_applicant_id(current_user.id)
        return render_template('applications/applicant_list.html', applications=applications)
    elif current_user.role == 'business_owner':
        business = Business.get_by_owner_id(current_user.id)
        if not business:
            flash('Please create a business profile first', 'danger')
            return redirect(url_for('create_business'))
            
        jobs = Job.get_by_business_id(business.id)
        job_applications = {}
        for job in jobs:
            job_applications[job.id] = Application.get_by_job_id(job.id)
        return render_template('applications/business_list.html', 
                             jobs=jobs, 
                             job_applications=job_applications)
    else:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/job/<id>/applications')
@login_required
def job_applications(id):
    if current_user.role != 'business_owner':
        flash('Only business owners can view job applications', 'danger')
        return redirect(url_for('dashboard'))
        
    job = Job.get_by_id(id)
    if not job:
        flash('Job not found', 'danger')
        return redirect(url_for('dashboard'))
        
    # Verify ownership
    business = Business.get_by_owner_id(current_user.id)
    if not business or job.business_id != business.id:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('dashboard'))
        
    applications = Application.get_by_job_id(id)
    return render_template('applications/job_applications.html', 
                         job=job, 
                         applications=applications)



@app.route('/application/<id>/update-status', methods=['POST'])
@login_required
def update_application_status(id):
    if current_user.role != 'business_owner':
        flash('Only business owners can update application status', 'danger')
        return redirect(url_for('dashboard'))
        
    try:
        application = Application.get_by_id(id)
        if not application:
            flash('Application not found', 'danger')
            return redirect(url_for('dashboard'))
            
        # Verify ownership
        business = Business.get_by_owner_id(current_user.id)
        if not business or application.job.business_id != business.id:
            flash('Unauthorized access', 'danger')
            return redirect(url_for('dashboard'))
            
        new_status = request.form.get('status')
        feedback = request.form.get('feedback', '').strip()
        
        if new_status not in Application.STATUSES:
            flash('Invalid status', 'danger')
            return redirect(url_for('job_applications', id=application.job.id))
            
        if application.update_status(new_status, feedback):
            flash('Application status updated successfully', 'success')
        else:
            flash('Error updating application status', 'danger')
            
        return redirect(url_for('job_applications', id=application.job.id))
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))
    except Exception as e:
        flash(f'Error processing application: {str(e)}', 'danger')
        return redirect(url_for('jobs'))

@app.route('/post-job', methods=['GET', 'POST'])
@login_required
def post_job():
    if current_user.role != 'business_owner':
        flash('Only business owners can post jobs', 'danger')
        return redirect(url_for('dashboard'))

    try:
        if request.method == 'POST':
            # Accept form-encoded or JSON payloads from the modal
            if request.is_json:
                data = request.get_json()
                title = data.get('title')
                description = data.get('description')
                category = data.get('category')
                location = data.get('location')
                latitude = data.get('lat') or data.get('latitude')
                longitude = data.get('lng') or data.get('longitude')
            else:
                title = request.form.get('title')
                description = request.form.get('description')
                category = request.form.get('category')
                location = request.form.get('location')
                latitude = request.form.get('latitude')
                longitude = request.form.get('longitude')

            job = Job(
                title=title,
                description=description,
                requirements=request.form.get('requirements') if not request.is_json else data.get('requirements'),
                salary=request.form.get('salary') if not request.is_json else data.get('salary'),
                job_type=request.form.get('job_type') if not request.is_json else data.get('job_type'),
                location=location,
                category=category,
                latitude=float(latitude) if latitude else 13.5,
                longitude=float(longitude) if longitude else 124.3
            )
            business = Business.get_by_owner_id(current_user.id)
            if business:
                job.save(business.id)
                if request.is_json:
                    return jsonify({'success': True, 'job_id': job.id})
                flash('Job posted successfully!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Please create a business profile first', 'danger')
                return redirect(url_for('profile'))

        return render_template('jobs/post.html')
    except Exception as e:
        flash(f'Error posting job: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/create-business', methods=['GET', 'POST'])
@login_required
def create_business():
    if current_user.role != 'business_owner':
        flash('Only business owners can create business profiles', 'danger')
        return redirect(url_for('dashboard'))

    try:
        if request.method == 'POST':
            business = Business(
                name=request.form.get('name'),
                description=request.form.get('description'),
                location=request.form.get('location'),
                category=request.form.get('category'),
                size=request.form.get('size'),
                phone=request.form.get('phone'),
                email=request.form.get('email'),
                website=request.form.get('website'),
                latitude=float(request.form.get('latitude', 13.5)),
                longitude=float(request.form.get('longitude', 124.3))
            )
            
            # Handle permit upload
            if 'permit' in request.files:
                try:
                    filename = secure_upload(request.files['permit'], 'permit')
                    if filename:
                        business.permit_path = filename
                except ValueError as e:
                    flash(str(e), 'danger')
                    return redirect(url_for('create_business'))
                except Exception as e:
                    flash('Error uploading permit. Please try again.', 'danger')
                    return redirect(url_for('create_business'))
            
            business.save(current_user.id)
            flash('Business profile created successfully!', 'success')
            return redirect(url_for('dashboard'))

        return render_template('businesses/create.html')
    except Exception as e:
        flash(f'Error creating business profile: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/system-design')
def system_design():
    return render_template('system_design.html')

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        try:
            # Only update allowed fields, never role
            current_user.name = request.form.get('name')
            current_user.phone = request.form.get('phone')
            current_user.address = request.form.get('address')
            
            if current_user.role == 'job_seeker':
                current_user.skills = request.form.get('skills', '').split(',')
                current_user.experience = json.loads(request.form.get('experience', '[]'))
                current_user.education = json.loads(request.form.get('education', '[]'))
                
                # Handle resume upload
                if 'resume' in request.files:
                    resume = request.files['resume']
                    if resume.filename:
                        from werkzeug.utils import secure_filename
                        upload_dir = os.path.join('static', 'uploads', 'resumes')
                        os.makedirs(upload_dir, exist_ok=True)
                        filename = secure_filename(f"resume_{current_user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{resume.filename}")
                        resume_path = os.path.join(upload_dir, filename)
                        resume.save(resume_path)
                        # store relative path under static/ for templates
                        current_user.resume_path = f"uploads/resumes/{filename}"
            
            current_user.save()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('profile'))
        except Exception as e:
            flash(f'Error updating profile: {str(e)}', 'danger')
    
    return render_template('profile/edit.html', user=current_user)

@app.route('/business/<business_id>/review', methods=['POST'])
@login_required
def add_review(business_id):
    try:
        business = Business.get_by_id(business_id)
        if not business:
            flash('Business not found', 'danger')
            return redirect(url_for('businesses'))
        
        rating = int(request.form.get('rating', 0))
        comment = request.form.get('comment', '').strip()
        
        if not (1 <= rating <= 5):
            flash('Rating must be between 1 and 5', 'danger')
            return redirect(url_for('business_details', id=business_id))
        
        if not comment:
            flash('Comment is required', 'danger')
            return redirect(url_for('business_details', id=business_id))
        
        review = Review(
            business=business,
            user=current_user,
            rating=rating,
            comment=comment
        )
        review.save()
        
        flash('Review added successfully!', 'success')
    except Exception as e:
        flash(f'Error adding review: {str(e)}', 'danger')
    
    return redirect(url_for('business_details', id=business_id))

# Service Request Routes
@app.route('/services')
def services():
    try:
        category = request.args.get('category')
        location = request.args.get('location')
        status = request.args.get('status', 'open')
        
        services = Service.get_all(status=status)
        
        # Apply filters
        if category:
            services = [s for s in services if s.category == category]
        if location:
            services = [s for s in services if location.lower() in s.location.lower()]
            
        return render_template('services/index.html', 
                             services=services,
                             categories=Service.CATEGORIES,
                             current_category=category,
                             current_location=location,
                             current_status=status)
    except Exception as e:
        flash(f'Error loading services: {str(e)}', 'danger')
        return redirect(url_for('home'))

@app.route('/service/create', methods=['GET', 'POST'])
@login_required
def create_service():
    if current_user.role != 'client':
        flash('Only clients can create service requests', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        try:
            service = Service(
                title=request.form.get('title'),
                description=request.form.get('description'),
                category=request.form.get('category'),
                budget=request.form.get('budget'),
                duration=request.form.get('duration'),
                location=request.form.get('location'),
                requirements=request.form.get('requirements'),
                client_id=current_user.id
            )
            service.save()
            flash('Service request created successfully!', 'success')
            return redirect(url_for('view_service', id=service.id))
        except Exception as e:
            flash(f'Error creating service request: {str(e)}', 'danger')
            return redirect(url_for('create_service'))

    return render_template('services/create.html')

@app.route('/service/view/<id>')
def view_service(id):
    try:
        service = Service.get_by_id(id)
        if not service:
            flash('Service request not found', 'danger')
            return redirect(url_for('dashboard'))
            
        return render_template('services/view.html', service=service)
    except Exception as e:
        flash(f'Error loading service request: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/service/offer/<id>', methods=['POST'])
@login_required
def offer_service(id):
    if current_user.role != 'job_seeker':
        flash('Only job seekers can offer services', 'danger')
        return redirect(url_for('view_service', id=id))

    try:
        service = Service.get_by_id(id)
        if not service:
            flash('Service request not found', 'danger')
            return redirect(url_for('dashboard'))
            
        proposal = request.form.get('proposal', '').strip()
        price = request.form.get('price', '').strip()
        
        if not proposal or not price:
            flash('Both proposal and price are required', 'danger')
            return redirect(url_for('view_service', id=id))
            
        if service.add_offer(current_user.id, proposal, price):
            flash('Offer submitted successfully!', 'success')
        else:
            flash('Error submitting offer', 'danger')
            
        return redirect(url_for('view_service', id=id))
    except Exception as e:
        flash(f'Error processing offer: {str(e)}', 'danger')
        return redirect(url_for('view_service', id=id))

@app.route('/service/accept/<service_id>/<job_seeker_id>', methods=['POST'])
@login_required
def accept_offer(service_id, job_seeker_id):
    try:
        service = Service.get_by_id(service_id)
        if not service:
            flash('Service request not found', 'danger')
            return redirect(url_for('dashboard'))
            
        if service.client_id != current_user.id:
            flash('Unauthorized action', 'danger')
            return redirect(url_for('view_service', id=service_id))
            
        if service.accept_offer(job_seeker_id):
            flash('Offer accepted successfully!', 'success')
        else:
            flash('Error accepting offer', 'danger')
            
        return redirect(url_for('view_service', id=service_id))
    except Exception as e:
        flash(f'Error accepting offer: {str(e)}', 'danger')
        return redirect(url_for('view_service', id=service_id))

# Removed duplicate route - this was causing the conflict

@app.route('/chatbot')
def chatbot_main():
    """General chat interface"""
    return render_template('chatbot/main.html')

@app.route('/chatbot/ai')
def chatbot_ai():
    """AI-powered job assistant"""
    return render_template('chatbot/ai.html')

@app.route('/chatbot/support')
def chatbot_support():
    """Customer support interface"""
    return render_template('chatbot/support.html')

@app.route('/admin/users', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_users():
    if request.method == 'POST':
        try:
            action = request.form.get('action')
            user_id = request.form.get('user_id')
            
            with driver.session(database=DATABASE) as session:
                if action == 'deactivate':
                    session.run("""
                        MATCH (u:User {id: $user_id})
                        SET u.is_active = false
                        RETURN u;
                    """, {'user_id': user_id})
                    flash('User deactivated successfully', 'success')
                elif action == 'delete':
                    session.run("""
                        MATCH (u:User {id: $user_id})
                        SET u.is_active = false
                        RETURN u;
                    """, {'user_id': user_id})
                    flash('User deleted successfully', 'success')
        except Exception as e:
            flash(f'Error processing user action: {str(e)}', 'danger')
            
    return render_template('admin/users.html')