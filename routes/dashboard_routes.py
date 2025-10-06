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
    # Get filter parameters
    category = request.args.get('category')
    location = request.args.get('location')
    
    # Fetch open job offers from Neo4j with filters
    job_offers = JobOffer.get_all_active(category=category, location=location)
    categories = JobOffer.get_categories()
    
    # Get active service requests for the map
    service_requests = ServiceRequest.get_all_active()
    
    return render_template('dashboard/job_seeker.html',
                         job_offers=job_offers,
                         categories=categories,
                         service_requests=service_requests,
                         filters={'category': category, 'location': location},
                         user=current_user)

@dashboard.route('/dashboard/business_owner')
@login_required
@role_required('business_owner')
def business_owner_dashboard():
    """Business owner dashboard view."""
    # Fetch this owner's job offers
    job_offers = JobOffer.get_by_owner(current_user.email)
    categories = JobOffer.get_categories()
    
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
                         categories=categories,
                         analytics=analytics,
                         user=current_user)

@dashboard.route('/dashboard/business_owner/create_offer', methods=['POST'])
@login_required
@role_required('business_owner')
def create_job_offer():
    """Create a new job offer."""
    try:
        data = {
            'title': request.form['title'],
            'description': request.form['description'],
            'category': request.form['category'],
            'salary': request.form['salary'],
            'location': request.form['location'],
            'latitude': float(request.form['latitude']),
            'longitude': float(request.form['longitude']),
            'business_name': request.form['business_name'],
            'status': 'open'
        }
        
        job = JobOffer.create(data, current_user.email)
        if job:
            return jsonify({'status': 'success', 'message': 'Job offer created successfully'})
        return jsonify({'status': 'error', 'message': 'Failed to create job offer'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@dashboard.route('/dashboard/business_owner/edit_offer/<job_id>', methods=['POST'])
@login_required
@role_required('business_owner')
def edit_job_offer(job_id):
    """Edit an existing job offer."""
    try:
        data = {
            'title': request.form['title'],
            'description': request.form['description'],
            'category': request.form['category'],
            'salary': request.form['salary'],
            'location': request.form['location'],
            'latitude': float(request.form['latitude']),
            'longitude': float(request.form['longitude']),
            'business_name': request.form['business_name']
        }
        
        job = JobOffer.update(job_id, data)
        if job:
            return jsonify({'status': 'success', 'message': 'Job offer updated successfully'})
        return jsonify({'status': 'error', 'message': 'Failed to update job offer'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@dashboard.route('/dashboard/business_owner/delete_offer/<job_id>', methods=['POST'])
@login_required
@role_required('business_owner')
def delete_job_offer(job_id):
    """Delete a job offer."""
    try:
        if JobOffer.delete(job_id):
            return jsonify({'status': 'success', 'message': 'Job offer deleted successfully'})
        return jsonify({'status': 'error', 'message': 'Failed to delete job offer'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@dashboard.route('/dashboard/client')
@login_required
@role_required('client')
def client_dashboard():
    """Client dashboard view."""
    # Fetch this client's service requests
    service_requests = ServiceRequest.get_by_client(current_user.email)
    categories = ServiceRequest.get_categories()
    
    return render_template('dashboard/client.html',
                         service_requests=service_requests,
                         categories=categories,
                         user=current_user)

@dashboard.route('/dashboard/client/create_service', methods=['POST'])
@login_required
@role_required('client')
def create_service_request():
    """Create a new service request."""
    try:
        data = {
            'service_type': request.form['service_type'],
            'description': request.form['description'],
            'payment_offer': request.form['payment_offer'],
            'location': request.form['location'],
            'latitude': float(request.form['latitude']),
            'longitude': float(request.form['longitude']),
            'status': 'open'
        }
        
        service = ServiceRequest.create(data, current_user.email)
        if service:
            return jsonify({'status': 'success', 'message': 'Service request created successfully'})
        return jsonify({'status': 'error', 'message': 'Failed to create service request'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@dashboard.route('/dashboard/client/edit_service/<service_id>', methods=['POST'])
@login_required
@role_required('client')
def edit_service_request(service_id):
    """Edit an existing service request."""
    try:
        data = {
            'service_type': request.form['service_type'],
            'description': request.form['description'],
            'payment_offer': request.form['payment_offer'],
            'location': request.form['location'],
            'latitude': float(request.form['latitude']),
            'longitude': float(request.form['longitude'])
        }
        
        service = ServiceRequest.update(service_id, data)
        if service:
            return jsonify({'status': 'success', 'message': 'Service request updated successfully'})
        return jsonify({'status': 'error', 'message': 'Failed to update service request'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@dashboard.route('/dashboard/client/delete_service/<service_id>', methods=['POST'])
@login_required
@role_required('client')
def delete_service_request(service_id):
    """Delete a service request."""
    try:
        if ServiceRequest.delete(service_id):
            return jsonify({'status': 'success', 'message': 'Service request deleted successfully'})
        return jsonify({'status': 'error', 'message': 'Failed to delete service request'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

# API endpoints for map data
@dashboard.route('/api/map/jobs')
@login_required
def get_map_jobs():
    """Get all active job offers for map display."""
    if current_user.role == 'business_owner':
        jobs = JobOffer.get_by_owner(current_user.email)
    else:
        jobs = JobOffer.get_all_active()
    return jsonify([{
        'id': job.id,
        'title': job.title,
        'location': job.location,
        'latitude': job.latitude,
        'longitude': job.longitude,
        'business_name': job.business_name,
        'type': 'job'
    } for job in jobs])

@dashboard.route('/api/map/services')
@login_required
def get_map_services():
    """Get all active service requests for map display."""
    if current_user.role == 'client':
        services = ServiceRequest.get_by_client(current_user.email)
    else:
        services = ServiceRequest.get_all_active()
    return jsonify([{
        'id': service.id,
        'title': service.service_type,
        'location': service.location,
        'latitude': service.latitude,
        'longitude': service.longitude,
        'payment_offer': service.payment_offer,
        'type': 'service'
    } for service in services])

@dashboard.route('/api/map/categories')
@login_required
def get_map_categories():
    """Get categories for map filtering."""
    return jsonify({
        'jobs': JobOffer.get_categories(),
        'services': ServiceRequest.get_categories()
    })