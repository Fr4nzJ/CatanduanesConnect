from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import logging
from models import User
from decorators import verified_required

logger = logging.getLogger(__name__)
dashboard = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@dashboard.route('/')
@login_required
def index():
    """User dashboard showing verification status and document management."""
    return render_template('dashboard.html', user=current_user)

@dashboard.route('/reupload-document', methods=['POST'])
@login_required
def reupload_document():
    """Handle document re-upload for rejected users."""
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