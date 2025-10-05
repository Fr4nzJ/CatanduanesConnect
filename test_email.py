from flask import Flask
from flask_mail import Mail, Message
from config import Config
import os

def test_email():
    # Create a Flask app with the configuration
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize Flask-Mail
    mail = Mail(app)
    
    try:
        # Create a test message
        msg = Message(
            "Test Email from Catanduanes Connect",
            sender=Config.MAIL_DEFAULT_SENDER,
            recipients=[Config.ADMIN_EMAILS[0] if Config.ADMIN_EMAILS else Config.MAIL_USERNAME]
        )
        msg.body = "This is a test email from Catanduanes Connect. If you receive this, the email functionality is working correctly."
        msg.html = "<h1>Test Email</h1><p>This is a test email from Catanduanes Connect. If you receive this, the email functionality is working correctly.</p>"
        
        # Send the message
        with app.app_context():
            mail.send(msg)
            print("Test email sent successfully!")
            print(f"Sent to: {msg.recipients[0]}")
            
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        
if __name__ == "__main__":
    if not Config.MAIL_USERNAME or not Config.MAIL_PASSWORD:
        print("Error: Email credentials not configured!")
        print("Please make sure GMAIL_USER and GMAIL_PASSWORD are set in your .env file")
    else:
        test_email()