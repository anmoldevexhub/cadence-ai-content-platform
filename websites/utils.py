import base64
import hashlib
import json
import logging
import re
import requests
from django.conf import settings
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

def get_encryption_key():
    secret_bytes = settings.SECRET_KEY.encode('utf-8')
    key_hash = hashlib.sha256(secret_bytes).digest()
    return base64.urlsafe_b64encode(key_hash)

def encrypt_value(value: str) -> str:
    if not value:
        return ""
    key = get_encryption_key()
    f = Fernet(key)
    return f.encrypt(value.encode('utf-8')).decode('utf-8')

def decrypt_value(encrypted_str: str) -> str:
    if not encrypted_str:
        return ""
    key = get_encryption_key()
    f = Fernet(key)
    return f.decrypt(encrypted_str.encode('utf-8')).decode('utf-8')

def test_connection_helper(platform, url, auth_type, auth_payload):
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*"
    }
    params = {}
    auth_credentials = None

    if auth_type == 'api_key':
        key_name = auth_payload.get('api_key_name', '').strip()
        key_value = auth_payload.get('api_key_value', '').strip()
        if not key_name or not key_value:
            logger.warning("Connection test failed: api_key requires both api_key_name and api_key_value.")
            return False
        headers[key_name] = key_value
    elif auth_type == 'api_key_query':
        key_name = auth_payload.get('api_key_name', '').strip()
        key_value = auth_payload.get('api_key_value', '').strip()
        if not key_name or not key_value:
            logger.warning("Connection test failed: api_key_query requires both api_key_name and api_key_value.")
            return False
        params[key_name] = key_value
    elif auth_type == 'bearer_token':
        token = auth_payload.get('token_value', '').strip()
        if not token:
            logger.warning("Connection test failed: bearer_token requires token_value.")
            return False
        headers['Authorization'] = f"Bearer {token}"
    elif auth_type == 'basic_auth':
        username = auth_payload.get('username', '').strip()
        password = auth_payload.get('password', '').strip()
        if not username or not password:
            logger.warning("Connection test failed: basic_auth requires both username and password.")
            return False
        from requests.auth import HTTPBasicAuth
        auth_credentials = HTTPBasicAuth(username, password)

    try:
        # 1. Social Webhooks (Make.com)
        if 'make.com' in url or platform != 'blog':
            # Send a simple ping POST request to check connection
            resp = requests.post(url, json={"ping": True}, headers=headers, timeout=10)
            return resp.status_code in [200, 201, 202, 400]

        # 2. Custom Blog Endpoints
        # Send a GET request to verify authentication
        resp = requests.get(
            url, 
            headers=headers, 
            params=params, 
            auth=auth_credentials if auth_type == 'basic_auth' else None, 
            timeout=10
        )
        
        # 401/403 indicate authentication failed
        if resp.status_code in [401, 403]:
            logger.warning(f"Connection test failed for URL {url} (auth_type: {auth_type}): HTTP {resp.status_code}")
            return False
            
        # 200 OK with HTML content type is likely a generic landing page/website rather than a publishing API
        if resp.status_code == 200 and 'text/html' in resp.headers.get('Content-Type', '').lower():
            logger.warning(f"Connection test failed: URL {url} returned a standard HTML webpage instead of an API/webhook response.")
            return False
            
        # 200, 405 (Method Not Allowed), or 400 mean the endpoint is live and credentials did not reject us (excluding 404)
        return resp.status_code in [200, 201, 202, 204, 400, 405]

    except Exception as e:
        logger.error(f"Error testing connection to URL {url} (auth_type: {auth_type}): {e}")
        return False
