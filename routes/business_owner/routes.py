from flask import Blueprint, render_template, request, jsonify, current_app, redirect, url_for, flash
from flask_login import login_required, current_user
from models import Business, Job, Service, Review, Application, User, Notification, Statistics
from models.base import Chat  # Import Chat directly from base
from decorators import business_owner_required
from database import driver, DATABASE
from werkzeug.utils import secure_filename
import os

business_owner_bp = Blueprint('business_owner', __name__)

# Dashboard routes
@business_owner_bp.route('/dashboard')
@login_required
@business_owner_required
def dashboard():
    """Business owner dashboard"""
    business = Business.get_user_business(current_user.id)
    stats = Statistics.get_business_stats(business.id)
    notifications = Notification.get_user_notifications(current_user.id, limit=5)
    return render_template('business_owner/dashboard.html',
                         business=business,
                         stats=stats,
                         notifications=notifications)

# Business profile routes
@business_owner_bp.route('/business/profile', methods=['GET', 'POST'])
@login_required
@business_owner_required
def business_profile():
    """View and edit business profile"""
    business = Business.get_user_business(current_user.id)
    
    if request.method == 'POST':
        data = request.form
        permit = request.files.get('permit')
        logo = request.files.get('logo')
        
        if business.update(
            name=data.get('name'),
            description=data.get('description'),
            category=data.get('category'),
            location=data.get('location'),
            permit=permit,
            contact=data.get('contact'),
            logo=logo
        ):
            flash('Business profile updated successfully', 'success')
            return redirect(url_for('business_owner.business_profile'))
        flash('Error updating business profile', 'error')
        
    return render_template('business_owner/business/profile.html', business=business)

# Job posting routes
@business_owner_bp.route('/jobs')
@login_required
@business_owner_required
def jobs():
    """List all job postings"""
    business = Business.get_user_business(current_user.id)
    jobs = Job.get_business_jobs(business.id)
    return render_template('business_owner/jobs/list.html', jobs=jobs)

@business_owner_bp.route('/jobs/new', methods=['GET', 'POST'])
@login_required
@business_owner_required
def create_job():
    """Create a new job posting"""
    if request.method == 'POST':
        business = Business.get_user_business(current_user.id)
        job_data = request.form
        
        job = Job.create(
            title=job_data.get('title'),
            description=job_data.get('description'),
            requirements=job_data.get('requirements'),
            salary=job_data.get('salary'),
            location=job_data.get('location'),
            business_id=business.id
        )
        if job:
            flash('Job posted successfully', 'success')
            return redirect(url_for('business_owner.jobs'))
        flash('Error creating job posting', 'error')
        
    return render_template('business_owner/jobs/new.html')

@business_owner_bp.route('/jobs/<job_id>/applicants')
@login_required
@business_owner_required
def view_job_applicants(job_id):
    """View applicants for a job"""
    job = Job.get_by_id(job_id)
    business = Business.get_user_business(current_user.id)
    
    if not job or job.business_id != business.id:
        return render_template('errors/404.html'), 404
        
    applicants = Application.get_job_applicants(job_id)
    return render_template('business_owner/jobs/applicants.html',
                         job=job,
                         applicants=applicants)

@business_owner_bp.route('/jobs/<job_id>/applicants/<application_id>', methods=['POST'])
@login_required
@business_owner_required
def handle_application(job_id, application_id):
    """Accept or reject a job application"""
    action = request.form.get('action')
    application = Application.get_by_id(application_id)
    
    if not application or application.job_id != job_id:
        return jsonify({'success': False, 'message': 'Application not found'}), 404
        
    if action == 'accept':
        success = application.accept()
    elif action == 'reject':
        success = application.reject()
    else:
        return jsonify({'success': False, 'message': 'Invalid action'}), 400
        
    if success:
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Error processing application'})

# Chat routes
@business_owner_bp.route('/chats')
@login_required
@business_owner_required
def chats():
    """View all chat conversations"""
    conversations = Chat.get_user_conversations(current_user.id)
    return render_template('business_owner/chats/list.html',
                         conversations=conversations)

@business_owner_bp.route('/chats/<conversation_id>')
@login_required
@business_owner_required
def view_chat(conversation_id):
    """View a specific chat conversation"""
    conversation = Chat.get_conversation(conversation_id)
    messages = Chat.get_messages(conversation_id)
    return render_template('business_owner/chats/view.html',
                         conversation=conversation,
                         messages=messages)

# Reviews and feedback routes
@business_owner_bp.route('/reviews')
@login_required
@business_owner_required
def reviews():
    """View business reviews and ratings"""
    business = Business.get_user_business(current_user.id)
    reviews = Review.get_business_reviews(business.id)
    return render_template('business_owner/reviews/list.html', reviews=reviews)

@business_owner_bp.route('/reviews/<review_id>/reply', methods=['POST'])
@login_required
@business_owner_required
def reply_to_review(review_id):
    """Reply to a review"""
    review = Review.get_by_id(review_id)
    business = Business.get_user_business(current_user.id)
    
    if not review or review.business_id != business.id:
        return jsonify({'success': False, 'message': 'Review not found'}), 404
        
    reply = request.form.get('reply')
    if review.add_reply(reply, current_user.id):
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Error adding reply'})

# Settings routes
@business_owner_bp.route('/settings', methods=['GET', 'POST'])
@login_required
@business_owner_required
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
        elif action == 'update_visibility':
            visibility = request.form.get('visibility')
            business = Business.get_user_business(current_user.id)
            business.update_visibility(visibility)
            flash('Business visibility updated', 'success')
        elif action == 'delete_account':
            if current_user.delete_account():
                flash('Account deleted successfully', 'success')
                return redirect(url_for('auth.logout'))
            flash('Error deleting account', 'error')
            
    return render_template('business_owner/settings.html', user=current_user)