from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import logging
from models import User, JobOffer, ServiceRequest
from decorators import verified_required, role_required
from database import get_neo4j_driver, get_database_name

logger = logging.getLogger(__name__)
dashboard = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@dashboard.route('/')
@login_required
def index():
    """Redirect users to their role-specific dashboard."""
    if current_user.verification_status == 'pending_verification':
        return redirect(url_for('auth.restricted_access'))
        
    role_routes = {
        'job_seeker': 'dashboard.job_seeker_dashboard',
        'business_owner': 'dashboard.business_owner_dashboard',
        'client': 'dashboard.client_dashboard'
    }
    
    return redirect(url_for(role_routes.get(current_user.role, 'home.index')))

@dashboard.route('/job_seeker')
@login_required
@role_required('job_seeker')
def job_seeker_dashboard():
    """Job seeker dashboard view."""
    # Fetch open job offers from Neo4j
    job_offers = JobOffer.get_all_active()
    
    # Get available job categories
    job_categories = JobOffer.get_categories()
    
    return render_template('dashboard/job_seeker.html', 
                         user=current_user,
                         job_offers=job_offers,
                         job_categories=job_categories)

@dashboard.route('/business_owner')
@login_required
@role_required('business_owner')
def business_owner_dashboard():
    """Business owner dashboard view."""
    # Fetch this owner's job offers
    job_offers = JobOffer.get_by_owner(current_user.id)
    
    # Get job categories
    job_categories = JobOffer.get_categories()
    
    # Calculate analytics
    analytics = {
        'total_jobs': len(job_offers),
        'active_jobs': sum(1 for job in job_offers if job.status == 'open'),
        'total_applications': sum(len(job.applications) for job in job_offers if hasattr(job, 'applications')),
        'pending_applications': sum(1 for job in job_offers 
                                  if hasattr(job, 'applications') 
                                  for app in job.applications 
                                  if app.status == 'pending')
    }
    
    return render_template('dashboard/business_owner.html',
                         user=current_user,
                         job_offers=job_offers,
                         job_categories=job_categories,
                         analytics=analytics)

@dashboard.route('/client')
@login_required
@role_required('client')
def client_dashboard():
    """Client dashboard view."""
    # Fetch this client's service requests
    service_requests = ServiceRequest.get_by_client(current_user.id)
    
    # Get service categories
    service_categories = ServiceRequest.get_categories()
    
    return render_template('dashboard/client.html',
                         user=current_user,
                         service_requests=service_requests,
                         service_categories=service_categories)

# API endpoints for map data
@dashboard.route('/api/map/jobs')
@login_required
def get_map_jobs():
    """Get job offers for map display."""
    owner_id = request.args.get('owner')
    category = request.args.get('category')
    location = request.args.get('location')
    
    # Fetch jobs with filters
    jobs = JobOffer.get_filtered(
        owner_id=owner_id,
        category=category,
        location=location,
        status='open'
    )
    
    return jsonify([job.to_dict() for job in jobs])

@dashboard.route('/api/map/services')
@login_required
def get_map_services():
    """Get service requests for map display."""
    client_id = request.args.get('client')
    category = request.args.get('category')
    location = request.args.get('location')
    
    # Fetch services with filters
    services = ServiceRequest.get_filtered(
        client_id=client_id,
        category=category,
        location=location,
        status='open'
    )
    
    return jsonify([service.to_dict() for service in services])
    try:
        if current_user.verification_status != 'rejected':
            flash('You can only re-upload documents if your previous submission was rejected.', 'warning')
            return redirect(url_for('dashboard.index'))

        if 'document' not in request.files:
            flash('No document file provided.', 'danger')
            return redirect(url_for('dashboard.index'))

        file = request.files['document']
        if file.filename == '':
            flash('No selected file.', 'danger')
            return redirect(url_for('dashboard.index'))

        # Check file extension
        allowed_extensions = {
            'job_seeker': {'pdf', 'doc', 'docx'},
            'business_owner': {'pdf', 'jpg', 'jpeg', 'png'}
        }[current_user.role]

        if not file.filename.lower().endswith(tuple('.' + ext for ext in allowed_extensions)):
            flash(f'Invalid file type. Allowed types: {", ".join(allowed_extensions)}', 'danger')
            return redirect(url_for('dashboard.index'))

        # Check file size (5MB limit)
        if len(file.read()) > 5 * 1024 * 1024:  # 5MB
            flash('File size must be less than 5MB.', 'danger')
            return redirect(url_for('dashboard.index'))
        file.seek(0)  # Reset file pointer after reading

        # Generate secure filename and save
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{current_user.role}_{timestamp}_{filename}"
        
        # Create upload directory if it doesn't exist
        upload_dir = os.path.join('uploads', current_user.role)
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)

        # Update user record in Neo4j
        with get_neo4j_driver().session(database=get_database_name()) as session:
            result = session.run("""
                MATCH (u:User {id: $user_id})
                SET u.verification_status = 'pending_verification',
                    u.document_path = $document_path,
                    u.updated_at = datetime()
                RETURN u
            """, {
                'user_id': current_user.id,
                'document_path': file_path
            })

            if result.single():
                flash('Your document has been resubmitted for review.', 'success')
            else:
                flash('Error updating your record. Please try again.', 'danger')

    except Exception as e:
        logger.error(f"Error handling document re-upload: {str(e)}")
        flash('An error occurred while processing your document. Please try again.', 'danger')

    return redirect(url_for('dashboard.index'))