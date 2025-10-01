from flask import current_app
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.oauth2 import id_token
import requests
import json

def get_google_provider_cfg():
    return requests.get(current_app.config['GOOGLE_DISCOVERY_URL']).json()

def get_google_auth_flow():
    config = {
        "web": {
            "client_id": current_app.config['GOOGLE_CLIENT_ID'],
            "client_secret": current_app.config['GOOGLE_CLIENT_SECRET'],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [current_app.config['GOOGLE_REDIRECT_URI']],
        }
    }
    
    return Flow.from_client_config(
        config,
        scopes=[
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/userinfo.email",
            "openid"
        ]
    )

def get_google_user_info(token):
    try:
        idinfo = id_token.verify_oauth2_token(
            token,
            Request(),
            current_app.config['GOOGLE_CLIENT_ID']
        )
        
        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Wrong issuer.')
            
        return {
            'google_id': idinfo['sub'],
            'email': idinfo['email'],
            'name': idinfo['name'],
            'picture': idinfo.get('picture', None),
            'given_name': idinfo.get('given_name', None),
            'family_name': idinfo.get('family_name', None),
            'locale': idinfo.get('locale', None)
        }
    except Exception as e:
        current_app.logger.error(f"Error verifying Google token: {str(e)}")
        return None