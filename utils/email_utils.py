import os
import threading
from flask import current_app, render_template
from flask_mail import Message, Mail
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

mail = Mail()

def send_async_email(app, msg):
    """Send email asynchronously."""
    with app.app_context():
        try:
            mail.send(msg)
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")

def send_email_async(to, subject, template, **kwargs):
    """
    Send an email asynchronously using a template.
    
    Args:
        to: Recipient email address
        subject: Email subject
        template: Name of the HTML template (without .html extension)
        **kwargs: Variables to pass to the template
    """
    try:
        app = current_app._get_current_object()
        
        # Add some common template variables
        kwargs.update({
            'year': datetime.now().year,
            'app_name': 'Catanduanes Connect',
            'support_email': os.getenv('SUPPORT_EMAIL', 'support@catanduanesconnect.com')
        })
        
        # Render both HTML and text versions
        html_body = render_template(f'emails/{template}.html', **kwargs)
        text_body = render_template(f'emails/{template}.txt', **kwargs)
        
        msg = Message(
            subject=subject,
            recipients=[to],
            body=text_body,
            html=html_body,
            sender=('Catanduanes Connect', os.getenv('GMAIL_USER'))
        )
        
        threading.Thread(
            target=send_async_email,
            args=(app, msg)
        ).start()
        
        return True
    except Exception as e:
        logger.error(f"Error preparing email: {str(e)}")
        return False

def send_document_received_email(user):
    """Send confirmation email when document is submitted."""
    return send_email_async(
        to=user.email,
        subject="Document Received - Verification Pending",
        template="document_received",
        user=user
    )

def send_account_verified_email(user):
    """Send notification when account is verified."""
    return send_email_async(
        to=user.email,
        subject="Account Verified - You're Approved!",
        template="account_verified",
        user=user
    )

def send_verification_failed_email(user, reason=None):
    """Send notification when document is rejected."""
    return send_email_async(
        to=user.email,
        subject="Verification Failed - Action Required",
        template="verification_failed",
        user=user,
        reason=reason or "Incomplete or invalid document"
    )

def notify_admins_new_submission(user):
    """
    Notify all admins when a new document is submitted for verification.
    
    Args:
        user: User object containing details of the submitter
    """
    admin_emails = current_app.config.get('ADMIN_EMAILS', '').split(',')
    admin_emails = [email.strip() for email in admin_emails if email.strip()]
    
    if not admin_emails:
        logger.warning("No admin emails configured for notifications")
        return False
    
    success = True
    for admin_email in admin_emails:
        result = send_email_async(
            to=admin_email,
            subject=f"New Document Submission from {user.name}",
            template="admin_document_submission",
            user=user
        )
        success = success and result
    
    return success

def init_app(app):
    """Initialize the mail extension with the app."""
    mail.init_app(app)