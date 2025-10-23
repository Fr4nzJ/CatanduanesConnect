from flask import Blueprint, render_template, request, jsonify, current_app, redirect, url_for, flash
from flask_login import login_required, current_user
from models import Service, Business, Job, Review, Application, User, Notification, Statistics
from decorators import service_client_required
from database import driver, DATABASE

service_client_bp = Blueprint('service_client', __name__)

# Dashboard routes
@service_client_bp.route('/dashboard')
@login_required
@service_client_required
def dashboard():
    """Service client dashboard"""
    services = Service.get_user_services(current_user.id)
    stats = Statistics.get_service_client_stats(current_user.id)
    notifications = Notification.get_user_notifications(current_user.id, limit=5)
    return render_template('service_client/dashboard.html',
                         services=services,
                         stats=stats,
                         notifications=notifications)

# Service management routes
@service_client_bp.route('/services', methods=['GET'])
@login_required
@service_client_required
def services():
    """List all services offered by the client"""
    services = Service.get_user_services(current_user.id)
    return render_template('service_client/services/list.html', services=services)

@service_client_bp.route('/services/new', methods=['GET', 'POST'])
@login_required
@service_client_required
def create_service():
    """Create a new service offer"""
    if request.method == 'POST':
        service_data = request.form
        service = Service.create(
            title=service_data.get('title'),
            description=service_data.get('description'),
            category=service_data.get('category'),
            price=service_data.get('price'),
            location=service_data.get('location'),
            user_id=current_user.id
        )
        if service:
            flash('Service created successfully', 'success')
            return redirect(url_for('service_client.services'))
        flash('Error creating service', 'error')
    return render_template('service_client/services/new.html')

@service_client_bp.route('/services/<service_id>/edit', methods=['GET', 'POST'])
@login_required
@service_client_required
def edit_service(service_id):
    """Edit an existing service"""
    service = Service.get_by_id(service_id)
    if not service or service.user_id != current_user.id:
        return render_template('errors/404.html'), 404
        
    if request.method == 'POST':
        service_data = request.form
        if service.update(service_data):
            flash('Service updated successfully', 'success')
            return redirect(url_for('service_client.services'))
        flash('Error updating service', 'error')
    return render_template('service_client/services/edit.html', service=service)

@service_client_bp.route('/services/<service_id>/delete', methods=['POST'])
@login_required
@service_client_required
def delete_service(service_id):
    """Delete a service"""
    service = Service.get_by_id(service_id)
    if not service or service.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Service not found'}), 404
        
    if service.delete():
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Error deleting service'})

@service_client_bp.route('/services/<service_id>/applicants')
@login_required
@service_client_required
def view_service_applicants(service_id):
    """View applicants for a service"""
    service = Service.get_by_id(service_id)
    if not service or service.user_id != current_user.id:
        return render_template('errors/404.html'), 404
        
    applicants = Application.get_service_applicants(service_id)
    return render_template('service_client/services/applicants.html',
                         service=service,
                         applicants=applicants)

# Profile routes
@service_client_bp.route('/profile')
@login_required
@service_client_required
def view_profile():
    """View service client profile"""
    services = Service.get_user_services(current_user.id)
    ratings = Review.get_user_ratings(current_user.id)
    return render_template('service_client/profile/view.html',
                         user=current_user,
                         services=services,
                         ratings=ratings)

@service_client_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
@service_client_required
def edit_profile():
    """Edit service client profile"""
    if request.method == 'POST':
        data = request.form
        picture = request.files.get('picture')
        
        current_user.update_profile(
            bio=data.get('bio'),
            service_category=data.get('service_category'),
            picture=picture
        )
        flash('Profile updated successfully', 'success')
        return redirect(url_for('service_client.view_profile'))
    return render_template('service_client/profile/edit.html', user=current_user)

# Reviews and feedback routes
@service_client_bp.route('/reviews')
@login_required
@service_client_required
def reviews():
    """View all reviews and ratings"""
    reviews = Review.get_user_reviews(current_user.id)
    return render_template('service_client/reviews/list.html', reviews=reviews)

@service_client_bp.route('/reviews/<review_id>/reply', methods=['POST'])
@login_required
@service_client_required
def reply_to_review(review_id):
    """Reply to a review"""
    review = Review.get_by_id(review_id)
    if not review:
        return jsonify({'success': False, 'message': 'Review not found'}), 404
        
    reply = request.form.get('reply')
    if review.add_reply(reply, current_user.id):
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Error adding reply'})

# Settings routes
@service_client_bp.route('/settings', methods=['GET', 'POST'])
@login_required
@service_client_required
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
            current_user.update_service_visibility(visibility)
            flash('Service visibility updated', 'success')
        elif action == 'delete_account':
            if current_user.delete_account():
                flash('Account deleted successfully', 'success')
                return redirect(url_for('auth.logout'))
            flash('Error deleting account', 'error')
    
    return render_template('service_client/settings.html', user=current_user)