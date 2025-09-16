from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from flask_mail import Mail, Message
from flask_bootstrap import Bootstrap
from datetime import datetime
import os
from dotenv import load_dotenv
from models import User, Business, Job, Application, Review
import json

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')

# Initialize extensions
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
bootstrap = Bootstrap(app)

# Email configuration
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
mail = Mail(app)

# Create necessary directories
os.makedirs('static/resumes', exist_ok=True)

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
        role = request.form.get('role')

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
        user.save()

        login_user(user)
        flash('Account created successfully!', 'success')
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
    if current_user.role == 'job_seeker':
        return render_template('dashboard/job_seeker.html')
    elif current_user.role == 'business_owner':
        return render_template('dashboard/business_owner.html')
    else:
        return render_template('dashboard/admin.html')

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
            
            flash('Application submitted successfully!', 'success')
            return redirect(url_for('job_details', id=job_id))

        return render_template('jobs/apply.html', job=job)
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

@app.route('/chatbot', methods=['GET', 'POST'])
def chatbot():
    if request.method == 'POST':
        try:
            message = request.json.get('message', '').strip()
            if not message:
                return jsonify({'error': 'Message is required'}), 400
            
            # Placeholder for AI chatbot response
            # In a real implementation, this would call an AI service
            response = {
                'message': f"I'm a placeholder chatbot. You said: {message}",
                'suggestions': ['Find jobs', 'Browse businesses', 'View map']
            }
            
            return jsonify(response)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    return render_template('chatbot.html')

if __name__ == '__main__':
    app.run(debug=True) 