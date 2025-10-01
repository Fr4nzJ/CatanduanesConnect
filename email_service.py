import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

SMTP_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('MAIL_PORT', 587))
SMTP_USERNAME = os.getenv('MAIL_USERNAME')
SMTP_PASSWORD = os.getenv('MAIL_PASSWORD')

def send_email(to_email, subject, body, html=True):
    """
    Send an email using the configured SMTP server.
    
    Args:
        to_email (str): Recipient email address
        subject (str): Email subject line
        body (str): Email body content
        html (bool): Whether the body content is HTML (default: True)
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    
    Raises:
        Exception: If there is an error sending the email
    """
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_USERNAME
        msg['To'] = to_email
        msg['Subject'] = subject
        
        if html:
            msg.attach(MIMEText(body, 'html'))
        else:
            msg.attach(MIMEText(body, 'plain'))
            
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
            
        logger.info(f"Email sent successfully to {to_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
        return False

def send_verification_email(to_email, user_name, verification_link):
    """Send email verification link."""
    subject = "Verify Your Catanduanes Connect Account"
    body = f"""
    <html>
        <body>
            <h2>Welcome to Catanduanes Connect!</h2>
            <p>Hello {user_name},</p>
            <p>Thank you for signing up. Please click the link below to verify your account:</p>
            <p><a href="{verification_link}">Verify Account</a></p>
            <p>If you did not create an account, you can safely ignore this email.</p>
            <br>
            <p>Best regards,</p>
            <p>The Catanduanes Connect Team</p>
        </body>
    </html>
    """
    return send_email(to_email, subject, body)

def send_password_reset_email(to_email, reset_link):
    """Send password reset link."""
    subject = "Reset Your Catanduanes Connect Password"
    body = f"""
    <html>
        <body>
            <h2>Password Reset Request</h2>
            <p>A password reset was requested for your Catanduanes Connect account.</p>
            <p>Click the link below to reset your password:</p>
            <p><a href="{reset_link}">Reset Password</a></p>
            <p>If you did not request this reset, you can safely ignore this email.</p>
            <p>This link will expire in 1 hour.</p>
            <br>
            <p>Best regards,</p>
            <p>The Catanduanes Connect Team</p>
        </body>
    </html>
    """
    return send_email(to_email, subject, body)

def send_business_verification_result(to_email, business_name, is_approved):
    """Send business verification result notification."""
    subject = "Business Verification Status Update"
    status = "approved" if is_approved else "not approved"
    body = f"""
    <html>
        <body>
            <h2>Business Verification Update</h2>
            <p>Dear Business Owner,</p>
            <p>Your business "{business_name}" has been {status} on Catanduanes Connect.</p>
            {"<p>You can now start posting jobs and managing your business profile.</p>" if is_approved else
             "<p>Please contact support for more information about why your verification was not approved.</p>"}
            <br>
            <p>Best regards,</p>
            <p>The Catanduanes Connect Team</p>
        </body>
    </html>
    """
    return send_email(to_email, subject, body)

def send_application_status_update(to_email, applicant_name, job_title, status):
    """Send job application status update."""
    subject = "Job Application Status Update"
    body = f"""
    <html>
        <body>
            <h2>Application Status Update</h2>
            <p>Dear {applicant_name},</p>
            <p>Your application for the position of "{job_title}" has been {status}.</p>
            {get_status_specific_message(status)}
            <br>
            <p>Best regards,</p>
            <p>The Catanduanes Connect Team</p>
        </body>
    </html>
    """
    return send_email(to_email, subject, body)

def get_status_specific_message(status):
    """Get status-specific message for job applications."""
    messages = {
        'accepted': """
            <p>Congratulations! The employer would like to move forward with your application.</p>
            <p>They will contact you soon with more details about the next steps.</p>
        """,
        'rejected': """
            <p>We regret to inform you that the employer has decided to move forward with other candidates.</p>
            <p>Don't be discouraged - keep applying and improving your profile!</p>
        """,
        'pending': """
            <p>Your application is currently under review.</p>
            <p>We'll notify you as soon as there's an update from the employer.</p>
        """
    }
    return messages.get(status.lower(), "")