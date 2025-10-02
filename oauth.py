from flask import current_app
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
import requests

def get_google_auth_flow():
    """
    Initialize Google OAuth2 flow using app config.
    """
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
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
        ],
        redirect_uri=current_app.config['GOOGLE_REDIRECT_URI']
    )


def get_google_user_info(access_token):
    """
    Fetch user profile info from Google using access token.
    """
    try:
        response = requests.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        if response.ok:
            data = response.json()
            return {
                "google_id": data.get("sub"),
                "email": data.get("email"),
                "name": data.get("name"),
                "picture": data.get("picture"),
                "given_name": data.get("given_name"),
                "family_name": data.get("family_name"),
                "locale": data.get("locale"),
            }
        else:
            current_app.logger.error(f"Failed to fetch Google user info: {response.text}")
            return None
    except Exception as e:
        current_app.logger.error(f"Error in get_google_user_info: {str(e)}")
        return None
