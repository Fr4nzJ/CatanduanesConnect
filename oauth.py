from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
import requests
from typing import Optional
import logging


def get_google_auth_flow_from_config(client_id: str, client_secret: str, redirect_uri: str) -> Flow:
    """Create and return a google-auth-oauthlib Flow using explicit values."""
    import os
    # Allow HTTP for local development
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    
    config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "project_id": "catanduanes-connect",  # Add your project ID
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "redirect_uris": [redirect_uri],
            "javascript_origins": ["http://localhost:5000"]
        }
    }
    
    flow = Flow.from_client_config(
        config,
        scopes=[
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
        ],
        redirect_uri=redirect_uri
    )
    
    return flow

    return Flow.from_client_config(
        config,
        scopes=[
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
        ],
        redirect_uri=redirect_uri
    )


def get_google_user_info(access_token: str, logger: Optional[logging.Logger] = None) -> Optional[dict]:
    """Fetch user profile info from Google using access token.

    Accepts an optional logger so calling code can provide app.logger when
    inside an application context.
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
            if logger:
                logger.error(f"Failed to fetch Google user info: {response.text}")
            return None
    except Exception as e:
        if logger:
            logger.error(f"Error in get_google_user_info: {str(e)}")
        return None
