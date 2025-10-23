from flask import Blueprint, render_template, request, jsonify, current_app, redirect, url_for, flash
from flask_login import login_required, current_user
from models import Job, Business, Service, Review, Application, User, Notification
from models.base import Chat  # Import Chat directly from base
from decorators import job_seeker_required
from database import driver, DATABASE
from werkzeug.utils import secure_filename
import os
from datetime import datetime

job_seeker_bp = Blueprint('job_seeker', __name__, url_prefix='/job-seeker')

# Dashboard route
@job_seeker_bp.route('/dashboard')
@login_required
@job_seeker_required
def dashboard():
    """Main dashboard view for job seekers"""
    # Get stats for dashboard
    pending_applications = Application.count_by_user_and_status(current_user.id, 'pending')
    profile_completion = calculate_profile_completion(current_user)
    new_job_matches = Job.count_matches_for_user(current_user.id)
    
    return render_template('job_seeker/profile/dashboard.html',
                         pending_applications=pending_applications,
                         profile_completion=profile_completion,
                         new_job_matches=new_job_matches)

# Profile Management Routes
@job_seeker_bp.route('/profile/edit/picture', methods=['GET', 'POST'])
@login_required
@job_seeker_required
def edit_profile_picture():
    if request.method == 'POST':
        if 'picture' not in request.files:
            flash('No file uploaded', 'error')
            return redirect(request.url)
        
        file = request.files['picture']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
            
        if file and allowed_file(file.filename, {'png', 'jpg', 'jpeg'}):
            filename = secure_filename(f"profile_{current_user.id}_{file.filename}")
            filepath = os.path.join('static', 'uploads', 'job_seeker', filename)
            file.save(filepath)
            
            # Update user profile picture path in database
            User.update_profile_picture(current_user.id, filepath)
            flash('Profile picture updated successfully', 'success')
            return redirect(url_for('job_seeker.dashboard'))
            
    return render_template('job_seeker/profile/edit_picture.html')

@job_seeker_bp.route('/profile/edit/resume', methods=['GET', 'POST'])
@login_required
@job_seeker_required
def edit_resume():
    if request.method == 'POST':
        if 'resume' not in request.files:
            flash('No file uploaded', 'error')
            return redirect(request.url)
        
        file = request.files['resume']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
            
        if file and allowed_file(file.filename, {'pdf', 'doc', 'docx'}):
            filename = secure_filename(f"resume_{current_user.id}_{file.filename}")
            filepath = os.path.join('static', 'uploads', 'job_seeker', filename)
            file.save(filepath)
            
            # Update user resume path in database
            User.update_resume(current_user.id, filepath)
            flash('Resume updated successfully', 'success')
            return redirect(url_for('job_seeker.dashboard'))
            
    return render_template('job_seeker/profile/edit_resume.html')

@job_seeker_bp.route('/profile/edit/bio', methods=['GET', 'POST'])
@login_required
@job_seeker_required
def edit_bio():
    if request.method == 'POST':
        bio = request.form.get('bio')
        User.update_bio(current_user.id, bio)
        flash('Bio updated successfully', 'success')
        return redirect(url_for('job_seeker.dashboard'))
    return render_template('job_seeker/profile/edit_bio.html')

@job_seeker_bp.route('/profile/edit/preferred-jobs', methods=['GET', 'POST'])
@login_required
@job_seeker_required
def edit_preferred_jobs():
    if request.method == 'POST':
        preferred_jobs = request.form.getlist('preferred_jobs')
        User.update_preferred_jobs(current_user.id, preferred_jobs)
        flash('Preferred jobs updated successfully', 'success')
        return redirect(url_for('job_seeker.dashboard'))
    job_categories = Job.get_categories()
    return render_template('job_seeker/profile/edit_preferred_jobs.html', 
                         job_categories=job_categories)

@job_seeker_bp.route('/profile/edit/skills', methods=['GET', 'POST'])
@login_required
@job_seeker_required
def edit_skills():
    if request.method == 'POST':
        skills = request.form.getlist('skills')
        User.update_skills(current_user.id, skills)
        flash('Skills updated successfully', 'success')
        return redirect(url_for('job_seeker.dashboard'))
    return render_template('job_seeker/profile/edit_skills.html')

# View Profile Routes
@job_seeker_bp.route('/profile/view/picture')
@login_required
@job_seeker_required
def view_profile_picture():
    return render_template('job_seeker/profile/view_picture.html')

@job_seeker_bp.route('/profile/view/resume')
@login_required
@job_seeker_required
def view_resume():
    return render_template('job_seeker/profile/view_resume.html')

@job_seeker_bp.route('/profile/view/bio')
@login_required
@job_seeker_required
def view_bio():
    return render_template('job_seeker/profile/view_bio.html')

@job_seeker_bp.route('/profile/view/preferred-jobs')
@login_required
@job_seeker_required
def view_preferred_jobs():
    return render_template('job_seeker/profile/view_preferred_jobs.html')

@job_seeker_bp.route('/profile/view/skills')
@login_required
@job_seeker_required
def view_skills():
    return render_template('job_seeker/profile/view_skills.html')

# Job related routes
@job_seeker_bp.route('/jobs')
@login_required
@job_seeker_required
def view_jobs():
    """View all job offers for job seekers"""
    jobs = Job.get_all()
    return render_template('job_seeker/jobs/list.html', jobs=jobs)

@job_seeker_bp.route('/jobs/<job_id>')
@login_required
@job_seeker_required
def view_job_details(job_id):
    """View specific job details for job seekers"""
    job = Job.get_by_id(job_id)
    if not job:
        return render_template('errors/404.html'), 404
    return render_template('job_seeker/jobs/details.html', job=job)

@job_seeker_bp.route('/jobs/<job_id>/apply', methods=['POST'])
@login_required
@job_seeker_required
def apply_for_job(job_id):
    """Apply for a specific job"""
    job = Job.get_by_id(job_id)
    if not job:
        flash('Job not found', 'error')
        return redirect(url_for('job_seeker.view_jobs'))
    
    application = Application.create(job_id=job_id, user_id=current_user.id)
    if application:
        flash('Application submitted successfully', 'success')
    else:
        flash('Error submitting application', 'error')
    return redirect(url_for('job_seeker.view_job_details', job_id=job_id))

# Business related routes
@job_seeker_bp.route('/businesses/<business_id>/rate', methods=['POST'])
@login_required
@job_seeker_required
def rate_business(business_id):
    rating = request.form.get('rating')
    comment = request.form.get('comment')
    if not rating:
        flash('Rating is required', 'error')
        return redirect(url_for('job_seeker.view_business_details', business_id=business_id))
    
    if Review.create(business_id=business_id, user_id=current_user.id, rating=rating, comment=comment):
        flash('Review submitted successfully', 'success')
    else:
        flash('Error submitting review', 'error')
    return redirect(url_for('job_seeker.view_business_details', business_id=business_id))

# Helper Functions
def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def calculate_profile_completion(user):
    """Calculate the profile completion percentage"""
    total_fields = 5  # profile picture, resume, bio, preferred jobs, skills
    completed = 0
    
    if user.profile_picture:
        completed += 1
    if user.resume_path:
        completed += 1
    if user.bio:
        completed += 1
    if user.preferred_jobs:
        completed += 1
    if user.skills:
        completed += 1
        
    return int((completed / total_fields) * 100)
    """Rate a business"""
    rating = request.form.get('rating')
    comment = request.form.get('comment')
    review = Review.create(business_id=business_id, user_id=current_user.id,
                         rating=rating, comment=comment)
    if review:
        flash('Review submitted successfully', 'success')
    else:
        flash('Error submitting review', 'error')
    return redirect(url_for('job_seeker.view_business_details', business_id=business_id))

# Profile related routes
@job_seeker_bp.route('/profile')
@login_required
@job_seeker_required
def view_profile():
    """View job seeker profile"""
    applications = Application.get_user_applications(current_user.id)
    updates = Notification.get_user_notifications(current_user.id)
    return render_template('job_seeker/profile/view.html', 
                         user=current_user,
                         applications=applications,
                         updates=updates)

@job_seeker_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
@job_seeker_required
def edit_profile():
    """Edit job seeker profile"""
    if request.method == 'POST':
        # Handle profile update
        data = request.form
        profile_picture = request.files.get('profile_picture')
        resume = request.files.get('resume')
        
        current_user.update_profile(
            bio=data.get('bio'),
            preferred_jobs=data.getlist('preferred_jobs'),
            skills=data.getlist('skills'),
            profile_picture=profile_picture,
            resume=resume
        )
        flash('Profile updated successfully', 'success')
        return redirect(url_for('job_seeker.view_profile'))
        
    return render_template('job_seeker/profile/edit.html', user=current_user)

# Chat related routes
@job_seeker_bp.route('/chats')
@login_required
@job_seeker_required
def view_chats():
    """View all conversations"""
    conversations = Chat.get_user_conversations(current_user.id)
    return render_template('job_seeker/chats/list.html', conversations=conversations)

@job_seeker_bp.route('/chats/<conversation_id>')
@login_required
@job_seeker_required
def view_chat(conversation_id):
    """View specific chat conversation"""
    conversation = Chat.get_conversation(conversation_id)
    messages = Chat.get_messages(conversation_id)
    return render_template('job_seeker/chats/view.html', 
                         conversation=conversation,
                         messages=messages)

# Settings routes
@job_seeker_bp.route('/settings', methods=['GET', 'POST'])
@login_required
@job_seeker_required
def settings():
    """Manage account settings"""
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'update_email':
            email = request.form.get('email')
            current_user.update_email(email)
            flash('Email updated successfully', 'success')
        elif action == 'update_password':
            password = request.form.get('password')
            current_user.update_password(password)
            flash('Password updated successfully', 'success')
        elif action == 'update_notifications':
            preferences = request.form.getlist('notifications')
            current_user.update_notification_preferences(preferences)
            flash('Notification preferences updated', 'success')
        elif action == 'delete_account':
            if current_user.delete_account():
                flash('Account deleted successfully', 'success')
                return redirect(url_for('auth.logout'))
            flash('Error deleting account', 'error')
            
    return render_template('job_seeker/settings.html', user=current_user)

# Additional routes as needed...