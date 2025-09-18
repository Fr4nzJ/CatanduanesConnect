from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import current_user, login_required
from models import User, Business, Job, Application, Service, Activity
from datetime import datetime
from neo4j import GraphDatabase
import uuid
import logging

# Initialize Neo4j driver
import os
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

if not all([NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD]):
    raise ValueError("Missing required Neo4j environment variables!")

driver = GraphDatabase.driver(
    NEO4J_URI,
    auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
)

logger = logging.getLogger(__name__)

admin = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Unauthorized access', 'danger')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

@admin.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """Admin dashboard main view."""
    try:
        # Test Neo4j connection first
        try:
            driver.verify_connectivity()
        except Exception as e:
            logger.error(f"Neo4j connection test failed: {str(e)}")
            flash("Database connection error. Please check database configuration.", "error")
            return render_template('admin/dashboard.html', error="Database connection error")

        with driver.session(database=DATABASE) as session:
            try:
                # Get user statistics
                user_stats = session.run("""
                    MATCH (u:User)
                    WITH u.role as role, count(u) as count
                    RETURN collect({role: role, count: count}) as roles
                """).single()['roles']
                
                # Get total counts using the correct CALL subquery syntax
                total_counts = session.run("""
                    MATCH (u:User)
                    WITH count(u) AS users
                    MATCH (b:Business)
                    WITH users, count(b) AS businesses
                    MATCH (j:Job)
                    WITH users, businesses, count(j) AS jobs
                    MATCH (s:Service)
                    WITH users, businesses, jobs, count(s) AS services
                    MATCH (a:Application)
                    WITH users, businesses, jobs, services, count(a) AS applications
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
                
                # Get recent activities
                recent_activities = Activity.get_recent(10)
                
                return render_template('admin/dashboard.html',
                                    user_stats=user_stats,
                                    total_counts=total_counts,
                                    app_stats=app_stats,
                                    recent_activities=recent_activities)
            except Exception as e:
                logger.error(f"Error executing Neo4j queries: {str(e)}")
                flash("Error retrieving dashboard data. Please try again.", "error")
                return render_template('admin/dashboard.html', error="Query execution error")
                                
    except Exception as e:
        logger.error(f'Error loading admin dashboard: {str(e)}')
        flash('Database connection error. Please check configuration.', 'danger')
        return render_template('admin/dashboard.html', error="Database connection error")

@admin.route('/dashboard/data')
@login_required
@admin_required
def dashboard_data():
    """AJAX endpoint for dashboard data refresh."""
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
                                CALL {
                    MATCH (u:User)
                    WITH count(u) AS users
                    RETURN users
                }
                WITH users
                CALL {
                    MATCH (b:Business)
                    WITH count(b) AS businesses
                    RETURN businesses
                }
                WITH users, businesses
                CALL {
                    MATCH (j:Job)
                    WITH count(j) AS jobs
                    RETURN jobs
                }
                WITH users, businesses, jobs
                CALL {
                    MATCH (s:Service)
                    WITH count(s) AS services
                    RETURN services
                }
                WITH users, businesses, jobs, services
                CALL {
                    MATCH (a:Application)
                    WITH count(a) AS applications
                    RETURN applications
                }
                WITH users, businesses, jobs, services, applications
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
            
            # Get recent activities
            activities = Activity.get_recent(10)
            
            return jsonify({
                'users': user_stats,
                'total_counts': total_counts,
                'applications': app_stats,
                'recent_activity': activities
            })
    except Exception as e:
        logger.error(f'Error fetching admin dashboard data: {str(e)}')
        return jsonify({'error': str(e)}), 500

@admin.route('/users', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_users():
    """Manage users endpoint."""
    if request.method == 'POST':
        try:
            action = request.form.get('action')
            user_id = request.form.get('user_id')
            
            if not all([action, user_id]):
                return jsonify({'error': 'Missing required parameters'}), 400
                
            with driver.session(database=DATABASE) as session:
                if action == 'deactivate':
                    session.run("""
                        MATCH (u:User {id: $user_id})
                        SET u.is_active = false
                        RETURN u
                    """, {'user_id': user_id})
                    
                    # Log activity
                    Activity(
                        type='user_management',
                        action='deactivate',
                        user_id=current_user.id,
                        target_id=user_id,
                        target_type='user'
                    ).save()
                    
                    return jsonify({'success': True, 'message': 'User deactivated'})
                    
                elif action == 'delete':
                    session.run("""
                        MATCH (u:User {id: $user_id})
                        DETACH DELETE u
                    """, {'user_id': user_id})
                    
                    # Log activity
                    Activity(
                        type='user_management',
                        action='delete',
                        user_id=current_user.id,
                        target_id=user_id,
                        target_type='user'
                    ).save()
                    
                    return jsonify({'success': True, 'message': 'User deleted'})
                    
                else:
                    return jsonify({'error': 'Invalid action'}), 400
                    
        except Exception as e:
            logger.error(f'Error managing user: {str(e)}')
            return jsonify({'error': str(e)}), 500
            
    # GET request - return user list
    try:
        users = User.get_all()
        return jsonify({'users': [user.to_dict() for user in users]})
    except Exception as e:
        logger.error(f'Error fetching users: {str(e)}')
        return jsonify({'error': str(e)}), 500

@admin.route('/businesses', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_businesses():
    """Manage businesses endpoint."""
    if request.method == 'POST':
        try:
            action = request.form.get('action')
            business_id = request.form.get('business_id')
            
            if not all([action, business_id]):
                return jsonify({'error': 'Missing required parameters'}), 400
                
            with driver.session(database=DATABASE) as session:
                if action in ['approve', 'deny']:
                    session.run("""
                        MATCH (b:Business {id: $business_id})
                        SET b.is_verified = $is_verified
                        RETURN b
                    """, {
                        'business_id': business_id,
                        'is_verified': action == 'approve'
                    })
                    
                    # Log activity
                    Activity(
                        type='business_verification',
                        action=action,
                        user_id=current_user.id,
                        target_id=business_id,
                        target_type='business'
                    ).save()
                    
                    return jsonify({
                        'success': True,
                        'message': f'Business {action}d successfully'
                    })
                else:
                    return jsonify({'error': 'Invalid action'}), 400
                    
        except Exception as e:
            logger.error(f'Error managing business: {str(e)}')
            return jsonify({'error': str(e)}), 500
            
    # GET request - return business list
    try:
        businesses = Business.get_all()
        return jsonify({'businesses': [business.to_dict() for business in businesses]})
    except Exception as e:
        logger.error(f'Error fetching businesses: {str(e)}')
        return jsonify({'error': str(e)}), 500

@admin.route('/content', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_content():
    """Manage jobs and services endpoint."""
    if request.method == 'POST':
        try:
            action = request.form.get('action')
            content_type = request.form.get('content_type')
            content_id = request.form.get('content_id')
            
            if not all([action, content_type, content_id]):
                return jsonify({'error': 'Missing required parameters'}), 400
                
            with driver.session(database=DATABASE) as session:
                if action == 'remove':
                    if content_type == 'job':
                        session.run("""
                            MATCH (j:Job {id: $content_id})
                            DETACH DELETE j
                        """, {'content_id': content_id})
                    elif content_type == 'service':
                        session.run("""
                            MATCH (s:Service {id: $content_id})
                            DETACH DELETE s
                        """, {'content_id': content_id})
                    else:
                        return jsonify({'error': 'Invalid content type'}), 400
                        
                    # Log activity
                    Activity(
                        type='content_moderation',
                        action='remove',
                        user_id=current_user.id,
                        target_id=content_id,
                        target_type=content_type
                    ).save()
                    
                    return jsonify({
                        'success': True,
                        'message': f'{content_type.capitalize()} removed successfully'
                    })
                else:
                    return jsonify({'error': 'Invalid action'}), 400
                    
        except Exception as e:
            logger.error(f'Error managing content: {str(e)}')
            return jsonify({'error': str(e)}), 500
            
    # GET request - return jobs and services lists
    try:
        jobs = Job.get_all()
        services = Service.get_all()
        return jsonify({
            'jobs': [job.to_dict() for job in jobs],
            'services': [service.to_dict() for service in services]
        })
    except Exception as e:
        logger.error(f'Error fetching content: {str(e)}')
        return jsonify({'error': str(e)}), 500