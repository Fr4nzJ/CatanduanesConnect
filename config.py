import os

from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY') or 'your-secret-key-here'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///instance/catanduanes_connect.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Environment detection
    PRODUCTION = os.getenv('RAILWAY_STATIC_URL') is not None
    
    # Base URL configuration
    BASE_URL = 'https://catanduanesconnect.up.railway.app' if PRODUCTION else 'http://localhost:5000'
    
    # Google OAuth Config
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"
    
    # OAuth redirect URI
    # Allow explicit override via environment (useful on hosting platforms)
    GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI') or f"{BASE_URL}/callback/google"
    
    # Email Configuration
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.getenv('GMAIL_USER')
    MAIL_PASSWORD = os.getenv('GMAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = ('Catanduanes Connect', os.getenv('GMAIL_USER'))
    
    # Admin notification emails (comma-separated)
    ADMIN_EMAILS = os.getenv('ADMIN_EMAILS', '').split(',')
    
    # Support email for user contact
    SUPPORT_EMAIL = os.getenv('SUPPORT_EMAIL', 'support@catanduanesconnect.com')