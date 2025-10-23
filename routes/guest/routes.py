from flask import Blueprint, render_template, request, jsonify, current_app
from models import Job, Business, Service, Review
from database import driver, DATABASE
import logging

logger = logging.getLogger(__name__)

guest_bp = Blueprint('guest', __name__)

@guest_bp.route('/jobs')
def view_jobs():
    """View all job offers for guests"""
    try:
        jobs = Job.get_all() or []
        return render_template('guest/jobs/list.html', jobs=jobs)
    except Exception as e:
        logger.error(f"Error in view_jobs: {str(e)}")
        return render_template('guest/jobs/list.html', jobs=[])

@guest_bp.route('/jobs/<job_id>')
def view_job_details(job_id):
    """View specific job details for guests"""
    try:
        job = Job.get_by_id(job_id)
        if not job:
            return render_template('errors/404.html'), 404
        return render_template('guest/jobs/details.html', job=job)
    except Exception as e:
        logger.error(f"Error in view_job_details: {str(e)}")
        return render_template('errors/404.html'), 404

@guest_bp.route('/jobs/map')
def view_jobs_map():
    """View jobs on map for guests"""
    try:
        jobs = Job.get_all() or []
        return render_template('guest/jobs/map.html', jobs=jobs)
    except Exception as e:
        logger.error(f"Error in view_jobs_map: {str(e)}")
        return render_template('guest/jobs/map.html', jobs=[])

@guest_bp.route('/businesses')
def view_businesses():
    """View all businesses for guests"""
    try:
        businesses = Business.get_all()
        if businesses is None:
            businesses = []
        
        categories = []
        processed_businesses = []
        
        for business in businesses:
            if not business:
                continue
                
            try:
                # Process category
                if getattr(business, 'category', None):
                    if business.category not in categories:
                        categories.append(business.category)
                
                # Add missing attributes with default values
                business.rating = getattr(business, 'rating', 0)
                business.review_count = getattr(business, 'review_count', 0)
                business.verified = getattr(business, 'verified', False)
                business.logo_url = getattr(business, 'logo_url', None)
                
                # Ensure other required attributes exist
                business.name = getattr(business, 'name', 'Unnamed Business')
                business.description = getattr(business, 'description', '')
                business.location = getattr(business, 'location', 'Location not specified')
                
                processed_businesses.append(business)
            except Exception as e:
                logger.error(f"Error processing business: {str(e)}")
                continue
        
        return render_template(
            'guest/businesses/list.html',
            businesses=processed_businesses,
            categories=sorted(categories)
        )
    except Exception as e:
        logger.error(f"Error in view_businesses: {str(e)}")
        return render_template(
            'guest/businesses/list.html',
            businesses=[],
            categories=[]
        )

@guest_bp.route('/businesses/<business_id>')
def view_business_details(business_id):
    """View specific business details for guests"""
    try:
        business = Business.get_by_id(business_id)
        if not business:
            return render_template('errors/404.html'), 404
            
        # Add missing attributes with default values
        business.rating = getattr(business, 'rating', 0)
        business.review_count = getattr(business, 'review_count', 0)
        business.verified = getattr(business, 'verified', False)
        business.logo_url = getattr(business, 'logo_url', None)
        
        # Get reviews and ratings with error handling
        try:
            comments = Review.get_business_reviews(business_id) or []
        except Exception:
            comments = []
            
        try:
            ratings = Review.get_business_ratings(business_id) or []
        except Exception:
            ratings = []
            
        return render_template('guest/businesses/details.html', 
                             business=business, 
                             comments=comments, 
                             ratings=ratings)
    except Exception as e:
        logger.error(f"Error in view_business_details: {str(e)}")
        return render_template('errors/404.html'), 404

@guest_bp.route('/businesses/map')
def view_businesses_map():
    """View businesses on map for guests"""
    try:
        businesses = Business.get_all() or []
        return render_template('guest/businesses/map.html', businesses=businesses)
    except Exception as e:
        logger.error(f"Error in view_businesses_map: {str(e)}")
        return render_template('guest/businesses/map.html', businesses=[])

@guest_bp.route('/services')
def view_services():
    """View all service offers for guests"""
    try:
        services = Service.get_all() or []
        return render_template('guest/services/list.html', services=services)
    except Exception as e:
        logger.error(f"Error in view_services: {str(e)}")
        return render_template('guest/services/list.html', services=[])

@guest_bp.route('/services/<service_id>')
def view_service_details(service_id):
    """View specific service details for guests"""
    try:
        service = Service.get_by_id(service_id)
        if not service:
            return render_template('errors/404.html'), 404
        return render_template('guest/services/details.html', service=service)
    except Exception as e:
        logger.error(f"Error in view_service_details: {str(e)}")
        return render_template('errors/404.html'), 404

@guest_bp.route('/services/map')
def view_services_map():
    """View services on map for guests"""
    try:
        services = Service.get_all() or []
        return render_template('guest/services/map.html', services=services)
    except Exception as e:
        logger.error(f"Error in view_services_map: {str(e)}")
        return render_template('guest/services/map.html', services=[])

@guest_bp.route('/about')
def about():
    """View about page with system information"""
    try:
        return render_template(
            'guest/about.html',
            page_title="About Us - Catanduanes Connect",
            description="Learn more about Catanduanes Connect and our mission to connect local businesses and service providers with the community.",
            content={
                'mission': "Connecting local businesses and service providers with the community in Catanduanes.",
                'vision': "To be the premier platform for business and service connections in Catanduanes.",
                'features': [
                    "Business Directory",
                    "Service Marketplace",
                    "Job Listings",
                    "Local Community Connection"
                ]
            }
        )
    except Exception:
        logger.exception('Error rendering about page')
        return render_template('errors/500.html'), 500