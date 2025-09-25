import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import logging

# Set up logging
logger = logging.getLogger(__name__)

def send_email(to_email, subject, body, html=None):
    """
    Send an email using SMTP.
    
    Args:
        to_email (str): Recipient's email address
        subject (str): Email subject
        body (str): Plain text email body
        html (str, optional): HTML version of the email body
        
    Raises:
        smtplib.SMTPException: If there's an error sending the email
        ValueError: If required environment variables are missing
    """
    try:
        # Get email configuration from environment
        smtp_server = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('MAIL_PORT', 587))
        sender_email = os.getenv('MAIL_USERNAME')
        sender_password = os.getenv('MAIL_PASSWORD')
        
        if not all([sender_email, sender_password]):
            raise ValueError("Missing email credentials in environment variables")
            
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Add plain text body
        msg.attach(MIMEText(body, 'plain'))
        
        # Add HTML version if provided
        if html:
            msg.attach(MIMEText(html, 'html'))
            
        # Connect to SMTP server and send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            
        logger.info(f"Email sent successfully to {to_email}")
        return True
        
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error sending email to {to_email}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error sending email to {to_email}: {str(e)}")
        raise