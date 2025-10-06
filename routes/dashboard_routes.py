from flask import Blueprint, redirect, render_template, url_for, jsonify, request
from flask_login import login_required, current_user
from models import JobOffer, ServiceRequest
from decorators import role_required

dashboard = Blueprint('dashboard', __name__)

@dashboard.route('/dashboard')
@login_required
def dashboard_redirect():
    """Redirect users to their role-specific dashboard."""
    if current_user.verification_status == 'pending_verification':
        return redirect(url_for('auth.restricted_access'))
        
    role_routes = {
        'job_seeker': 'dashboard.job_seeker_dashboard',
        'business_owner': 'dashboard.business_owner_dashboard',
        'client': 'dashboard.client_dashboard'
    }
    
    return redirect(url_for(role_routes.get(current_user.role, 'home.index')))

@dashboard.route('/dashboard/job_seeker')
@login_required
@role_required('job_seeker')
def job_seeker_dashboard():
    """Job seeker dashboard view."""
    # Fetch open job offers from Neo4j
    job_offers = JobOffer.get_all_active()
    return render_template('dashboard/job_seeker.html', 
                         job_offers=job_offers,
                         user=current_user)

@dashboard.route('/dashboard/business_owner')
@login_required
@role_required('business_owner')
def business_owner_dashboard():
    """Business owner dashboard view."""
    # Fetch this owner's job offers
    job_offers = JobOffer.get_by_owner(current_user.id)
    # Get analytics
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
                         job_offers=job_offers,
                         analytics=analytics,
                         user=current_user)

@dashboard.route('/dashboard/client')
@login_required
@role_required('client')
def client_dashboard():
    """Client dashboard view."""
    # Fetch this client's service requests
    service_requests = ServiceRequest.get_by_client(current_user.id)
    return render_template('dashboard/client.html',
                         service_requests=service_requests,
                         user=current_user)

# API endpoints for map data
@dashboard.route('/api/map/jobs')
@login_required
def get_map_jobs():
    """Get all active job offers for map display."""
    jobs = JobOffer.get_all_active()
    return jsonify([job.to_dict() for job in jobs])

@dashboard.route('/api/map/services')
@login_required
def get_map_services():
    """Get all active service requests for map display."""
    services = ServiceRequest.get_all_active()
    return jsonify([service.to_dict() for service in services])