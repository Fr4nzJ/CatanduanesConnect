from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from flask_mail import Mail, Message
from flask_bootstrap import Bootstrap
from datetime import datetime, timedelta
from functools import wraps
from models import User, Business, Job, Application, Review, Service, Notification
import os, uuid, json, logging, random
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from neo4j import GraphDatabase
from models import User, Business, Job, Application, Review, Service
from decorators import admin_required

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configure Flask app
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')

if not app.secret_key:
    logger.error("No secret key set! Please set FLASK_SECRET_KEY environment variable.")
    raise ValueError("No secret key set! Please set FLASK_SECRET_KEY environment variable.")

# Custom Chatbot class
class SimpleBot:
    def __init__(self):
        self.responses = {
            'greetings': [
                "Hello! 👋 How can I help you today?",
                "Hi there! Welcome to Catanduanes Connect! What would you like to know?",
                "Greetings! I'm here to help you navigate Catanduanes Connect."
            ],
            'job_search': [
                "You can find jobs by using our search feature. Would you like me to show you how?",
                "To find jobs, click on 'Jobs' in the menu and use filters to narrow your search.",
                "I can help you search for jobs. What type of work are you looking for?"
            ],
            'business': [
                "Our business directory features local companies in Catanduanes. Want to take a look?",
                "You can browse businesses by category or location. Would you like me to show you?",
                "Are you interested in finding businesses or creating a business profile?"
            ],
            'application': [
                "To apply for a job: 1️⃣ Create an account 2️⃣ Find a job 3️⃣ Click 'Apply' 4️⃣ Submit your application",
                "Job applications are easy! Would you like me to guide you through the process?",
                "I can help you with your job application. Have you found a job you're interested in?"
            ],
            'profile': [
                "You can manage your profile by clicking on your name in the top right corner.",
                "Need help setting up your profile? I can guide you through the process.",
                "Your profile is important! Make sure to keep it updated with your latest information."
            ],
            'platform_info': [
                "Welcome to Catanduanes Connect! 👋 We're your one-stop platform for connecting job seekers with local businesses in Catanduanes. Whether you're looking for work or growing your business, we're here to help!",
                "Catanduanes Connect is a local job and business platform. We help connect talented individuals with great opportunities in Catanduanes.",
                "We're your local connection to jobs and businesses in Catanduanes! How can we help you today?"
            ],
            'services': [
                "Our services section is perfect for short-term or project-based work! Would you like to explore available opportunities?",
                "You can find freelance and temporary work in our services section. Want to take a look?",
                "Whether you need services or want to offer your skills, our services section can help. What are you interested in?"
            ],
            'map_help': [
                "Our interactive map 🗺️ shows businesses and job opportunities across Catanduanes! Want to explore?",
                "You can use our map to find jobs and businesses near you. Would you like me to show you how?",
                "Looking for opportunities in a specific area? Our map feature can help you find them!"
            ],
            'default': [
                "I'm not sure about that. Could you rephrase your question?",
                "I might need more information to help you better. What specifically would you like to know?",
                "I'm still learning! Could you try asking that in a different way?"
            ]
        }
        
    def get_response(self, message):
        message = message.lower()
        
        # Check message content and return appropriate response
        if any(word in message for word in ['hi', 'hello', 'hey', 'greetings']):
            return random.choice(self.responses['greetings'])
        elif any(word in message for word in ['job', 'work', 'position', 'career']):
            return random.choice(self.responses['job_search'])
        elif any(word in message for word in ['business', 'company', 'employer']):
            return random.choice(self.responses['business'])
        elif any(word in message for word in ['apply', 'application', 'submit']):
            return random.choice(self.responses['application'])
        elif any(word in message for word in ['profile', 'account', 'settings']):
            return random.choice(self.responses['profile'])
        elif any(word in message for word in ['what is', 'about', 'platform']):
            return random.choice(self.responses['platform_info'])
        elif any(word in message for word in ['service', 'freelance', 'project']):
            return random.choice(self.responses['services'])
        elif any(word in message for word in ['map', 'location', 'area', 'near']):
            return random.choice(self.responses['map_help'])
        else:
            return random.choice(self.responses['default'])

# Load environment variables
load_dotenv()

# Neo4j AuraDB setup
driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
)
DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')

# Initialize extensions
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
bootstrap = Bootstrap(app)

# File upload configuration
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
ALLOWED_EXTENSIONS = {
    'resume': {'pdf', 'doc', 'docx'},
    'permit': {'pdf', 'png', 'jpg', 'jpeg'}
}
MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB max file size

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Create upload directories
os.makedirs(os.path.join(UPLOAD_FOLDER, 'resumes'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'permits'), exist_ok=True)

# Initialize the simple chatbot
chatbot = SimpleBot()


def allowed_file(filename, file_type):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS[file_type]

def secure_upload(file, file_type):
    if file and file.filename:
        if not allowed_file(file.filename, file_type):
            raise ValueError(f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS[file_type])}")
        
        filename = secure_filename(f"{file_type}_{uuid.uuid4()}_{file.filename}")
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_type}s", filename)
        file.save(file_path)
        return filename
    return None

# Email configuration
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
mail = Mail(app)

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

# Routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
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
        
        # Handle file uploads based on role
        try:
            if role == 'job_seeker' and 'resume' in request.files:
                filename = secure_upload(request.files['resume'], 'resume')
                if filename:
                    user.resume_path = filename
                    
            elif role == 'business_owner' and 'permit' in request.files:
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
        
        user.save()
        login_user(user)
        
        flash('Account created successfully!', 'success')
        if role == 'business_owner':
            flash('Your account will be reviewed by an admin before you can post jobs.', 'info')
            
        return redirect(url_for('dashboard'))

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

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        if current_user.role == 'job_seeker':
            job_applications = Application.get_by_applicant_id(current_user.id)
            service_offers = Service.get_offers_by_job_seeker(current_user.id)
            return render_template('dashboard/job_seeker.html', 
                                applications=job_applications,
                                service_offers=service_offers)
                                
        elif current_user.role == 'business_owner':
            business = Business.get_by_owner_id(current_user.id)
            jobs = Job.get_by_business_id(business.id) if business else []
            applications = Application.get_by_business_id(business.id) if business else []
            return render_template('dashboard/business_owner.html',
                                business=business,
                                jobs=jobs,
                                applications=applications)
                                
        elif current_user.role == 'client':
            services = Service.get_all(client_id=current_user.id)
            return render_template('dashboard/client.html',
                                services=services)
                                
        else:  # admin
            users = User.get_all()
            businesses = Business.get_all()
            jobs = Job.get_all()
            services = Service.get_all()
            return render_template('dashboard/admin.html',
                                users=users,
                                businesses=businesses,
                                jobs=jobs,
                                services=services)
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

@app.route('/map')
def map():
    try:
        # Get all businesses and jobs for the map
        businesses = Business.get_all() or []
        jobs = Job.get_all() or []
        
        # Add default coordinates for businesses and jobs that don't have them
        for business in businesses:
            if not hasattr(business, 'latitude') or not hasattr(business, 'longitude'):
                # Default coordinates for Catanduanes
                business.latitude = 13.5
                business.longitude = 124.3
        
        for job in jobs:
            if not hasattr(job, 'latitude') or not hasattr(job, 'longitude'):
                # Use business coordinates if available, otherwise default
                if job.business and hasattr(job.business, 'latitude') and hasattr(job.business, 'longitude'):
                    job.latitude = job.business.latitude
                    job.longitude = job.business.longitude
                else:
                    job.latitude = 13.5
                    job.longitude = 124.3
        
        # Ensure we have valid data for the template
        if not businesses and not jobs:
            flash('No businesses or jobs found to display on the map.', 'info')
        
        return render_template('map.html', businesses=businesses, jobs=jobs)
    except Exception as e:
        flash(f'Error loading map: {str(e)}', 'danger')
        return redirect(url_for('home'))

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
            job = Job(
                title=request.form.get('title'),
                description=request.form.get('description'),
                requirements=request.form.get('requirements'),
                salary=request.form.get('salary'),
                job_type=request.form.get('job_type'),
                location=request.form.get('location'),
                category=request.form.get('category'),
                latitude=float(request.form.get('latitude', 13.5)),
                longitude=float(request.form.get('longitude', 124.3))
            )
            business = Business.get_by_owner_id(current_user.id)
            if business:
                job.save(business.id)
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
                        filename = f"resume_{current_user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                        resume.save(os.path.join('static', 'resumes', filename))
                        current_user.resume_path = filename
            
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

@app.route('/chatbot')
def chatbot_main():
    """Main chatbot interface with job and business statistics"""
    try:
        job_count = len(Job.get_all())
        business_count = len(Business.get_all())
        stats = {
            'jobs': job_count,
            'businesses': business_count
        }
    except:
        stats = None
    return render_template('chatbot.html', stats=stats)

@app.route('/chatbot-ai')
def chatbot_ai():
    """AI-powered chatbot interface focused on job matching and career advice"""
    return render_template('chatbot/ai.html')

@app.route('/chatbot-support')
def chatbot_support():
    """Support chatbot for general inquiries and platform help"""
    return render_template('chatbot/support.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        message = request.json.get('message', '').strip()
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Get chatbot response
        bot_response = chatbot.get_response(message)
        response_text = str(bot_response)
        
        # Initialize actions and suggestions
        actions = []
        suggestions = ['Find Jobs', 'Browse Businesses', 'View Map']
        
        # Dynamic suggestions and actions based on message context
        msg_lower = message.lower()
        
        # Job-related queries
        if any(word in msg_lower for word in ['job', 'work', 'position', 'career', 'apply', 'hire']):
            if 'post' in msg_lower or 'create' in msg_lower:
                suggestions = [
                    'How to Post a Job',
                    'Job Requirements',
                    'View My Job Posts',
                    'Manage Applications'
                ]
                if current_user.is_authenticated and current_user.role == 'business_owner':
                    actions.append({
                        'type': 'button',
                        'text': 'Post a New Job',
                        'url': url_for('post_job')
                    })
            else:
                suggestions = [
                    'Search Jobs',
                    'Latest Jobs',
                    'Job Categories',
                    'Application Tips'
                ]
                actions.append({
                    'type': 'button',
                    'text': 'Browse All Jobs',
                    'url': url_for('jobs')
                })
        
        # Business-related queries
        elif any(word in msg_lower for word in ['business', 'company', 'employer', 'service']):
            if 'create' in msg_lower or 'register' in msg_lower:
                suggestions = [
                    'Business Registration',
                    'Required Documents',
                    'Business Categories',
                    'Verification Process'
                ]
                if current_user.is_authenticated and current_user.role == 'business_owner':
                    actions.append({
                        'type': 'button',
                        'text': 'Create Business Profile',
                        'url': url_for('create_business')
                    })
            else:
                suggestions = [
                    'Business Directory',
                    'Top Businesses',
                    'Business Reviews',
                    'Browse Services'
                ]
                actions.append({
                    'type': 'button',
                    'text': 'View Businesses',
                    'url': url_for('businesses')
                })
        
        # Location/Map queries
        elif any(word in msg_lower for word in ['map', 'location', 'address', 'where']):
            suggestions = [
                'View Map',
                'Business Locations',
                'Job Locations',
                'Search by Area'
            ]
            actions.append({
                'type': 'button',
                'text': 'Open Interactive Map',
                'url': url_for('map')
            })
        
        # Profile/Account queries
        elif any(word in msg_lower for word in ['profile', 'account', 'settings', 'resume']):
            if current_user.is_authenticated:
                suggestions = [
                    'Update Profile',
                    'Change Password',
                    'Privacy Settings',
                    'Notification Settings'
                ]
                actions.append({
                    'type': 'button',
                    'text': 'Edit Profile',
                    'url': url_for('edit_profile')
                })
            else:
                suggestions = [
                    'Create Account',
                    'Login Help',
                    'Account Types',
                    'Profile Tips'
                ]
                actions.append({
                    'type': 'button',
                    'text': 'Sign Up',
                    'url': url_for('signup')
                })
        
        # Application-related queries
        elif any(word in msg_lower for word in ['application', 'apply', 'status', 'applied']):
            if current_user.is_authenticated:
                if current_user.role == 'job_seeker':
                    suggestions = [
                        'Application Status',
                        'My Applications',
                        'Application Tips',
                        'Update Resume'
                    ]
                    actions.append({
                        'type': 'button',
                        'text': 'View My Applications',
                        'url': url_for('view_applications')
                    })
                elif current_user.role == 'business_owner':
                    suggestions = [
                        'Review Applications',
                        'Manage Candidates',
                        'Update Status',
                        'Send Feedback'
                    ]
                    actions.append({
                        'type': 'button',
                        'text': 'Manage Applications',
                        'url': url_for('view_applications')
                    })
            else:
                response_text += "\n\nTo manage applications, please sign in to your account first."
                suggestions = ['Sign Up', 'Login', 'Account Types', 'How to Apply']
                
        # Service-related queries
        elif any(word in msg_lower for word in ['service', 'freelance', 'project', 'offer']):
            if current_user.is_authenticated:
                if current_user.role == 'job_seeker':
                    suggestions = [
                        'Available Services',
                        'Post Service',
                        'My Services',
                        'Service Tips'
                    ]
                    actions.append({
                        'type': 'button',
                        'text': 'Browse Services',
                        'url': url_for('services')
                    })
                elif current_user.role == 'client':
                    suggestions = [
                        'Post Service Request',
                        'My Requests',
                        'Manage Services',
                        'Find Professionals'
                    ]
                    actions.append({
                        'type': 'button',
                        'text': 'Post Service Request',
                        'url': url_for('create_service')
                    })
            else:
                response_text += "\n\nTo access services, please sign in to your account first."
                suggestions = ['Sign Up', 'Login', 'Service Types', 'How Services Work']
        
        return jsonify({
            'message': response_text,
            'suggestions': suggestions,
            'actions': actions  # New field for interactive buttons
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/test-db')
def test_db():
    try:
        with driver.session(database=DATABASE) as session:
            result = session.run("MATCH (n) RETURN n LIMIT 5")
            nodes = [dict(record["n"].items()) for record in result]
            return jsonify({
                "status": "success",
                "message": "Database connection successful",
                "data": nodes
            })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

# Dashboard API Routes
@app.route('/api/dashboard/business-owner')
@login_required
def business_owner_stats():
    try:
        if current_user.role != 'business_owner':
            return jsonify({'error': 'Unauthorized'}), 403
            
        with driver.session(database=DATABASE) as session:
            business = Business.get_by_owner_id(current_user.id)
            if not business:
                return jsonify({'error': 'Business not found'}), 404
                
            # Get job applications stats
            stats = session.run("""
                MATCH (b:Business {id: $business_id})<-[:POSTED_BY]-(j:Job)<-[:APPLIES_TO]-(a:Application)
                WITH j, a.status as status, count(a) as count
                RETURN collect({
                    job_id: j.id,
                    job_title: j.title,
                    status: status,
                    count: count
                }) as applications
            """, business_id=business.id).single()['applications']
            
            return jsonify({'applications': stats})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard/client')
@login_required
def client_stats():
    try:
        if current_user.role != 'client':
            return jsonify({'error': 'Unauthorized'}), 403
            
        with driver.session(database=DATABASE) as session:
            # Get service offers stats
            stats = session.run("""
                MATCH (c:User {id: $client_id})<-[:REQUESTED_BY]-(s:Service)<-[:OFFERS_FOR]-(o:ServiceOffer)
                WITH s, count(o) as offer_count, 
                     collect({
                         job_seeker_id: o.job_seeker_id,
                         proposal: o.proposal,
                         price: o.price,
                         status: o.status
                     }) as offers
                RETURN collect({
                    service_id: s.id,
                    service_title: s.title,
                    offer_count: offer_count,
                    offers: offers
                }) as services
            """, client_id=current_user.id).single()['services']
            
            return jsonify({'services': stats})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard/job-seeker')
@login_required
def job_seeker_stats():
    try:
        if current_user.role != 'job_seeker':
            return jsonify({'error': 'Unauthorized'}), 403
            
        with driver.session(database=DATABASE) as session:
            # Get application status updates
            applications = session.run("""
                MATCH (js:User {id: $job_seeker_id})-[:SUBMITTED_BY]->(a:Application)-[:APPLIES_TO]->(j:Job)
                WITH j, a
                ORDER BY a.created_at DESC
                RETURN collect({
                    job_id: j.id,
                    job_title: j.title,
                    status: a.status,
                    feedback: a.feedback,
                    updated_at: a.updated_at
                }) as applications
            """, job_seeker_id=current_user.id).single()['applications']
            
            # Get service offer updates
            offers = session.run("""
                MATCH (js:User {id: $job_seeker_id})-[:MADE_BY]->(o:ServiceOffer)-[:OFFERS_FOR]->(s:Service)
                WITH s, o
                ORDER BY o.created_at DESC
                RETURN collect({
                    service_id: s.id,
                    service_title: s.title,
                    status: o.status,
                    price: o.price,
                    updated_at: o.updated_at
                }) as offers
            """, job_seeker_id=current_user.id).single()['offers']
            
            return jsonify({
                'applications': applications,
                'service_offers': offers
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Admin Dashboard Routes
@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    return render_template('admin/dashboard.html')

@app.route('/admin/stats')
@login_required
@admin_required
def admin_stats():
    try:
        with driver.session(database=DATABASE) as session:
            # Get user counts by role
            user_stats = session.run("""
                MATCH (u:User)
                WITH u.role as role, count(u) as count
                RETURN collect({role: role, count: count}) as roles
            """).single()['roles']
            
            # Get total businesses
            business_count = session.run("""
                MATCH (b:Business)
                RETURN count(b) as count
            """).single()['count']
            
            # Get total jobs
            job_count = session.run("""
                MATCH (j:Job)
                RETURN count(j) as count
            """).single()['count']
            
            # Get total services
            service_count = session.run("""
                MATCH (s:Service)
                RETURN count(s) as count
            """).single()['count']
            
            # Get application stats
            app_stats = session.run("""
                MATCH (a:Application)
                WITH a.status as status, count(a) as count
                RETURN collect({status: status, count: count}) as applications
            """).single()['applications']
            
            # Get recent activity (last 10 actions)
            recent_activity = session.run("""
                MATCH (n)
                WHERE n:User OR n:Business OR n:Job OR n:Service OR n:Application
                WITH n, 
                     CASE 
                         WHEN n:User THEN 'New user registered'
                         WHEN n:Business THEN 'New business added'
                         WHEN n:Job THEN 'New job posted'
                         WHEN n:Service THEN 'New service requested'
                         WHEN n:Application THEN 'New job application'
                     END as action,
                     n.created_at as timestamp
                ORDER BY timestamp DESC
                LIMIT 10
                RETURN collect({
                    action: action,
                    timestamp: timestamp
                }) as activities
            """).single()['activities']
            
            stats = {
                'users': user_stats,
                'businesses': business_count,
                'jobs': job_count,
                'services': service_count,
                'applications': app_stats,
                'recent_activity': recent_activity
            }
            
            return jsonify(stats)
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Notification Routes
@app.route('/notifications')
@login_required
def get_notifications():
    try:
        limit = request.args.get('limit', 10, type=int)
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        notifications = Notification.get_user_notifications(
            current_user.id,
            limit=limit,
            unread_only=unread_only
        )
        unread_count = Notification.get_unread_count(current_user.id)
        
        return jsonify({
            'notifications': [{
                'id': n.id,
                'message': n.message,
                'type': n.type,
                'status': n.status,
                'created_at': n.created_at,
                'link': n.link
            } for n in notifications],
            'unread_count': unread_count
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/notifications/read/<notification_id>', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    try:
        notifications = Notification.get_user_notifications(current_user.id)
        notification = next((n for n in notifications if n.id == notification_id), None)
        
        if not notification:
            return jsonify({'error': 'Notification not found'}), 404
            
        notification.mark_as_read()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/notifications/view')
@login_required
def view_notifications():
    return render_template('notifications/index.html')

# Add notification creation at various trigger points
def create_notification_for_application(application):
    # Notify business owner of new application
    Notification.create(
        application.job.business.owner_id,
        f"New application received for {application.job.title}",
        'info',
        f'/job/{application.job.id}/applications'
    )

def create_notification_for_application_update(application):
    # Notify job seeker of application status update
    status_type = 'success' if application.status == 'accepted' else 'warning'
    Notification.create(
        application.applicant.id,
        f"Your application for {application.job.title} has been {application.status}",
        status_type,
        f'/applications'
    )

def create_notification_for_service_request(service):
    # Notify admin of new service request
    admins = User.get_all_admins()
    for admin in admins:
        Notification.create(
            admin.id,
            f"New service request: {service.title}",
            'info',
            f'/service/view/{service.id}'
        )

def create_notification_for_service_offer(service, job_seeker):
    # Notify client of new service offer
    Notification.create(
        service.client_id,
        f"New offer received for {service.title} from {job_seeker.name}",
        'info',
        f'/service/view/{service.id}'
    )

def create_notification_for_permit_verification(business):
    # Notify admin of new business permit for verification
    admins = User.get_all_admins()
    for admin in admins:
        Notification.create(
            admin.id,
            f"New business permit uploaded by {business.name} requires verification",
            'warning',
            f'/admin/businesses'
        )

# Update existing routes to include notifications
@app.route('/apply', methods=['GET', 'POST'])
@login_required
def apply_job():
    if current_user.role != 'job_seeker':
        flash('Only job seekers can apply for jobs', 'danger')
        return redirect(url_for('jobs'))

    try:
        job_id = request.args.get('id')
        if not job_id:
            flash('Job ID is required', 'danger')
            return redirect(url_for('jobs'))

        job = Job.get_by_id(job_id)
        if not job:
            flash('Job not found', 'danger')
            return redirect(url_for('jobs'))

        if request.method == 'POST':
            cover_letter = request.form.get('cover_letter', '').strip()
            
            if not cover_letter:
                flash('Cover letter is required', 'danger')
                return redirect(url_for('apply_job', id=job_id))
            
            application = Application(
                job=job,
                applicant=current_user,
                cover_letter=cover_letter,
                resume_path=current_user.resume_path,
                status='pending'
            )
            application.save()
            
            # Create notification for business owner
            create_notification_for_application(application)
            
            flash('Application submitted successfully!', 'success')
            return redirect(url_for('job_details', id=job_id))

        return render_template('jobs/apply.html', job=job)
    except Exception as e:
        flash(f'Error processing application: {str(e)}', 'danger')
        return redirect(url_for('jobs'))

# Cleanup database connection on app shutdown
@app.teardown_appcontext
def cleanup(exc):
    driver.close()

# Create default admin account on startup
create_admin_if_none_exists()

if __name__ == '__main__':
    app.run(debug=True) 