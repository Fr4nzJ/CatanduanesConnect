from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, send_file
from flask_login import current_user, login_required
from models import User, Business, Job, Application, Service, Activity
import os
from datetime import datetime
from neo4j import GraphDatabase
import uuid
import logging

from database import get_neo4j_driver, get_database_name

# Get shared Neo4j driver and database name
driver = get_neo4j_driver()
DATABASE = get_database_name()

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
                # Get user statistics with OPTIONAL MATCH
                user_stats = session.run("""
                    OPTIONAL MATCH (u:User)
                    WITH u.role as role, count(u) as count
                    WHERE role IS NOT NULL
                    RETURN collect({role: role, count: count}) as roles
                """).single()['roles']
                
                # Get total counts with OPTIONAL MATCH for resilience
                total_counts = session.run("""
                    OPTIONAL MATCH (u:User)
                    WITH count(u) AS users
                    OPTIONAL MATCH (b:Business)
                    WITH users, count(b) AS businesses
                    OPTIONAL MATCH (j:Job)
                    WITH users, businesses, count(j) AS jobs
                    OPTIONAL MATCH (s:Service)
                    WITH users, businesses, jobs, count(s) AS services
                    OPTIONAL MATCH (a:Application)
                    WITH users, businesses, jobs, services, count(a) AS applications
                    RETURN {
                        users: users,
                        businesses: businesses,
                        jobs: jobs,
                        services: services,
                        applications: applications
                    } AS counts
                """).single()['counts']
            
                # Get application statistics with OPTIONAL MATCH
                app_stats = session.run("""
                    OPTIONAL MATCH (a:Application)
                    WITH a.status as status, count(a) as count
                    WHERE status IS NOT NULL
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

@admin.route('/users/list')
@login_required
@admin_required
def users_list():
    """API endpoint for getting user list."""
    try:
        # Test Neo4j connection first
        try:
            driver.verify_connectivity()
        except Exception as e:
            logger.error(f"Neo4j connection test failed: {str(e)}")
            return jsonify({"error": "Database connection error"}), 500

        with driver.session(database=DATABASE) as session:
            result = session.run("""
                MATCH (u:User)
                OPTIONAL MATCH (u)-[:OWNS]->(b:Business)
                WITH u, collect(b.name) as businesses
                RETURN u, businesses
                ORDER BY u.role, u.last_name
            """)
            
            users = []
            for record in result:
                user_data = dict(record["u"])
                businesses = record["businesses"]
                
                # Create User object to ensure proper name formatting
                user = User(
                    id=user_data.get('id'),
                    email=user_data.get('email'),
                    first_name=user_data.get('first_name'),
                    last_name=user_data.get('last_name'),
                    middle_name=user_data.get('middle_name'),
                    suffix=user_data.get('suffix'),
                    role=user_data.get('role'),
                    phone=user_data.get('phone'),
                    address=user_data.get('address'),
                    verification_status=user_data.get('verification_status'),
                    resume_path=user_data.get('resume_path'),
                    permit_path=user_data.get('permit_path')
                )
                
                user_dict = user.to_dict()
                user_dict['businesses'] = businesses
                users.append(user_dict)
            
            return jsonify(users)
            
    except Exception as e:
        logger.error(f"Error fetching users: {str(e)}")
        return jsonify({"error": f"Error fetching users: {str(e)}"}), 500

@admin.route('/users/<user_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_user(user_id):
    """Delete a user."""
    try:
        if user_id == current_user.id:
            return jsonify({"error": "You cannot delete your own account"}), 400
            
        with driver.session(database=DATABASE) as session:
            # First check if user exists
            result = session.run("""
                MATCH (u:User {id: $user_id})
                RETURN u.role as role
            """, {"user_id": user_id})
            
            user = result.single()
            if not user:
                return jsonify({"error": "User not found"}), 404
                
            if user["role"] == "admin":
                return jsonify({"error": "Cannot delete admin users"}), 403
                
            # Delete all relationships first
            session.run("""
                MATCH (u:User {id: $user_id})
                OPTIONAL MATCH (u)-[r]-()
                DELETE r
            """, {"user_id": user_id})
            
            # Then delete the user node
            session.run("""
                MATCH (u:User {id: $user_id})
                DELETE u
            """, {"user_id": user_id})
            
            # Log the activity
            activity = Activity(
                type="user_management",
                action="delete",
                user_id=current_user.id,
                target_id=user_id,
                target_type="User",
                details={"message": f"User {user_id} deleted by admin"}
            )
            activity.save()
            
            return jsonify({"success": True, "message": "User deleted successfully"})
            
    except Exception as e:
        logger.error(f"Error deleting user: {str(e)}")
        return jsonify({"error": str(e)}), 500

@admin.route('/documents/pending')
@login_required
@admin_required
def get_pending_documents():
    """Get all pending documents (resumes and permits)."""
    try:
        with driver.session(database=DATABASE) as session:
            result = session.run("""
                MATCH (u:User)
                WHERE (u.resume_path IS NOT NULL OR u.permit_path IS NOT NULL)
                  AND u.verification_status = 'pending'
                RETURN u
                ORDER BY u.role, u.last_name
            """)
            
            documents = []
            for record in result:
                user_data = dict(record["u"])
                user = User(
                    id=user_data.get('id'),
                    email=user_data.get('email'),
                    first_name=user_data.get('first_name'),
                    last_name=user_data.get('last_name'),
                    middle_name=user_data.get('middle_name'),
                    suffix=user_data.get('suffix'),
                    role=user_data.get('role'),
                    resume_path=user_data.get('resume_path'),
                    permit_path=user_data.get('permit_path'),
                    verification_status=user_data.get('verification_status')
                )
                user_dict = user.to_dict()
                
                if user.resume_path:
                    documents.append({
                        "id": f"{user.id}_resume",
                        "user_id": user.id,
                        "user_name": user_dict['name'],
                        "type": "Resume",
                        "path": user.resume_path,
                        "submitted_date": user_data.get('resume_submitted_date', datetime.now().isoformat())
                    })
                    
                if user.permit_path:
                    documents.append({
                        "id": f"{user.id}_permit",
                        "user_id": user.id,
                        "user_name": user_dict['name'],
                        "type": "Business Permit",
                        "path": user.permit_path,
                        "submitted_date": user_data.get('permit_submitted_date', datetime.now().isoformat())
                    })
            
            return jsonify(documents)
            
    except Exception as e:
        logger.error(f"Error fetching pending documents: {str(e)}")
        return jsonify({"error": str(e)}), 500

@admin.route('/documents/<doc_id>/view')
@login_required
@admin_required
def view_document(doc_id):
    """View a document."""
    try:
        user_id, doc_type = doc_id.rsplit('_', 1)
        
        with driver.session(database=DATABASE) as session:
            result = session.run("""
                MATCH (u:User {id: $user_id})
                RETURN u.resume_path as resume_path, u.permit_path as permit_path
            """, {"user_id": user_id})
            
            record = result.single()
            if not record:
                return jsonify({"error": "User not found"}), 404
            
            file_path = record['resume_path'] if doc_type == 'resume' else record['permit_path']
            if not file_path:
                return jsonify({"error": "Document not found"}), 404
            
            # Check if file exists
            if not os.path.isfile(file_path):
                return jsonify({"error": "Document file not found"}), 404
                
            return send_file(file_path)
            
    except Exception as e:
        logger.error(f"Error viewing document: {str(e)}")
        return jsonify({"error": str(e)}), 500

@admin.route('/documents/<doc_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_document(doc_id):
    """Approve a document."""
    try:
        user_id, doc_type = doc_id.rsplit('_', 1)
        
        with driver.session(database=DATABASE) as session:
            # Update user's verification status
            session.run("""
                MATCH (u:User {id: $user_id})
                SET u.verification_status = 'verified'
                RETURN u
            """, {"user_id": user_id})
            
            # Log the activity
            activity = Activity(
                type="user_management",
                action="verify",
                user_id=current_user.id,
                target_id=user_id,
                target_type="User",
                details={
                    "message": f"Document ({doc_type}) approved for user {user_id}",
                    "document_type": doc_type
                }
            )
            activity.save()
            
            return jsonify({"success": True, "message": "Document approved successfully"})
            
    except Exception as e:
        logger.error(f"Error approving document: {str(e)}")
        return jsonify({"error": str(e)}), 500

@admin.route('/documents/<doc_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_document(doc_id):
    """Reject a document."""
    try:
        data = request.get_json()
        if not data or 'reason' not in data:
            return jsonify({"error": "Rejection reason is required"}), 400
            
        user_id, doc_type = doc_id.rsplit('_', 1)
        
        with driver.session(database=DATABASE) as session:
            # Update user's verification status
            session.run("""
                MATCH (u:User {id: $user_id})
                SET u.verification_status = 'rejected'
                SET u.rejection_reason = $reason
                RETURN u
            """, {"user_id": user_id, "reason": data['reason']})
            
            # Log the activity
            activity = Activity(
                type="user_management",
                action="reject",
                user_id=current_user.id,
                target_id=user_id,
                target_type="User",
                details={
                    "message": f"Document ({doc_type}) rejected for user {user_id}",
                    "document_type": doc_type,
                    "reason": data['reason']
                }
            )
            activity.save()
            
            return jsonify({"success": True, "message": "Document rejected successfully"})
            
    except Exception as e:
        logger.error(f"Error rejecting document: {str(e)}")
        return jsonify({"error": str(e)}), 500

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