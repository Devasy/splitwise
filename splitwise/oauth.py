"""Async OAuth support for Splitwise API.

Provides OAuth 1.0 and OAuth 2.0 authentication helpers for aiohttp.
"""

import hmac
import hashlib
import base64
import time
import secrets
from typing import Optional, Dict, Any, Tuple, List
from urllib.parse import urlencode, quote, parse_qs

import aiohttp

from splitwise import base
from splitwise.exception import SplitwiseUnauthorizedException


class AsyncOAuth1:
    """OAuth 1.0 authentication for async requests.
    
    Implements OAuth 1.0a signature generation for aiohttp.
    """
    
    def __init__(
        self,
        consumer_key: str,
        consumer_secret: str,
        resource_owner_key: Optional[str] = None,
        resource_owner_secret: Optional[str] = None,
        verifier: Optional[str] = None
    ):
        """Initialize OAuth 1.0 auth.
        
        Args:
            consumer_key: OAuth consumer key
            consumer_secret: OAuth consumer secret
            resource_owner_key: OAuth token (access token)
            resource_owner_secret: OAuth token secret
            verifier: OAuth verifier for token exchange
        """
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.resource_owner_key = resource_owner_key
        self.resource_owner_secret = resource_owner_secret
        self.verifier = verifier
    
    def _generate_nonce(self, length: int = 32) -> str:
        """Generate a random nonce."""
        return secrets.token_hex(length // 2)
    
    def _generate_timestamp(self) -> str:
        """Generate OAuth timestamp."""
        return str(int(time.time()))
    
    def _percent_encode(self, value: str) -> str:
        """Percent-encode a string per OAuth spec."""
        return quote(str(value), safe='')
    
    def _generate_signature_base_string(
        self,
        method: str,
        url: str,
        params: Dict[str, Any]
    ) -> str:
        """Generate the signature base string.
        
        Args:
            method: HTTP method
            url: Request URL (without query string)
            params: All OAuth and request parameters
            
        Returns:
            Signature base string
        """
        # RFC 5849 §3.4.1.3.2: encode first, then sort encoded key/value pairs
        flattened: List[Tuple[str, str]] = []
        for k, v in params.items():
            values = v if isinstance(v, (list, tuple)) else [v]
            for value in values:
                flattened.append(
                    (
                        self._percent_encode(str(k)),
                        self._percent_encode(str(value))
                    )
                )

        encoded_pairs = sorted(flattened, key=lambda item: (item[0], item[1]))
        param_string = '&'.join(f"{k}={v}" for k, v in encoded_pairs)
        
        # Build base string
        base_string = '&'.join([
            method.upper(),
            self._percent_encode(url.split('?')[0]),
            self._percent_encode(param_string)
        ])
        
        return base_string
    
    def _generate_signature(
        self,
        method: str,
        url: str,
        params: Dict[str, Any]
    ) -> str:
        """Generate HMAC-SHA1 signature.
        
        Args:
            method: HTTP method
            url: Request URL
            params: OAuth and request parameters
            
        Returns:
            Base64-encoded signature
        """
        base_string = self._generate_signature_base_string(method, url, params)
        
        # Build signing key
        signing_key = '&'.join([
            self._percent_encode(self.consumer_secret),
            self._percent_encode(self.resource_owner_secret or '')
        ])
        
        # Generate signature
        signature = hmac.new(
            signing_key.encode('utf-8'),
            base_string.encode('utf-8'),
            hashlib.sha1
        ).digest()
        
        return base64.b64encode(signature).decode('utf-8')
    
    def get_oauth_params(
        self,
        method: str,
        url: str,
        body_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """Get OAuth parameters including signature.
        
        Args:
            method: HTTP method
            url: Request URL
            body_params: Request body parameters
            
        Returns:
            Complete OAuth parameters dict
        """
        oauth_params = {
            'oauth_consumer_key': self.consumer_key,
            'oauth_nonce': self._generate_nonce(),
            'oauth_signature_method': 'HMAC-SHA1',
            'oauth_timestamp': self._generate_timestamp(),
            'oauth_version': '1.0',
        }
        
        if self.resource_owner_key:
            oauth_params['oauth_token'] = self.resource_owner_key
        
        if self.verifier:
            oauth_params['oauth_verifier'] = self.verifier
        
        # Combine all params for signature
        all_params = dict(oauth_params)
        if body_params:
            for k, v in body_params.items():
                if v is not None:
                    all_params[k] = str(v)
        
        # Parse URL params
        if '?' in url:
            url_params = parse_qs(url.split('?')[1])
            for k, v in url_params.items():
                all_params[k] = v[0] if len(v) == 1 else v
        
        # Generate signature
        oauth_params['oauth_signature'] = self._generate_signature(
            method, url, all_params
        )
        
        return oauth_params
    
    def get_auth_header(
        self,
        method: str,
        url: str,
        body_params: Optional[Dict[str, Any]] = None
    ) -> str:
        """Get OAuth Authorization header value.
        
        Args:
            method: HTTP method
            url: Request URL
            body_params: Request body parameters
            
        Returns:
            Authorization header value
        """
        oauth_params = self.get_oauth_params(method, url, body_params)
        
        header_params = ', '.join(
            f'{self._percent_encode(k)}="{self._percent_encode(v)}"'
            for k, v in sorted(oauth_params.items())
        )
        
        return f'OAuth {header_params}'


class AsyncOAuth2:
    """OAuth 2.0 authentication for async requests."""
    
    def __init__(self, access_token: str, token_type: str = "Bearer"):
        """Initialize OAuth 2.0 auth.
        
        Args:
            access_token: OAuth 2.0 access token
            token_type: Token type (default: Bearer)
        """
        self.access_token = access_token
        self.token_type = token_type
    
    def get_auth_header(self) -> str:
        """Get Authorization header value.
        
        Returns:
            Authorization header value
        """
        return f'{self.token_type} {self.access_token}'


class AsyncOAuthClient:
    """Async OAuth client for Splitwise authentication flows.
    
    Handles OAuth 1.0 and OAuth 2.0 token exchanges asynchronously.
    """
    
    def __init__(self, consumer_key: str, consumer_secret: str):
        """Initialize OAuth client.
        
        Args:
            consumer_key: OAuth consumer key
            consumer_secret: OAuth consumer secret
        """
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
    
    async def get_request_token(self) -> Tuple[str, str]:
        """Get OAuth 1.0 request token.
        
        Returns:
            Tuple of (oauth_token, oauth_token_secret)
        """
        oauth = AsyncOAuth1(self.consumer_key, self.consumer_secret)
        
        async with aiohttp.ClientSession() as session:
            auth_header = oauth.get_auth_header('POST', base.REQUEST_TOKEN_URL)
            
            async with session.post(
                base.REQUEST_TOKEN_URL,
                headers={'Authorization': auth_header}
            ) as response:
                if response.status != 200:
                    raise SplitwiseUnauthorizedException(
                        "Failed to get request token",
                        response=response
                    )
                
                content = await response.text()
                credentials = parse_qs(content)
                
                return (
                    credentials.get('oauth_token', [''])[0],
                    credentials.get('oauth_token_secret', [''])[0]
                )
    
    def get_authorize_url(self, oauth_token: str) -> str:
        """Get authorization URL for user.
        
        Args:
            oauth_token: Request token
            
        Returns:
            URL to redirect user to
        """
        return f"{base.AUTHORIZE_URL}?oauth_token={oauth_token}"
    
    async def get_access_token(
        self,
        oauth_token: str,
        oauth_token_secret: str,
        oauth_verifier: str
    ) -> Dict[str, str]:
        """Exchange request token for access token.
        
        Args:
            oauth_token: OAuth token from redirect
            oauth_token_secret: Token secret from get_request_token
            oauth_verifier: Verifier from redirect
            
        Returns:
            Dict with oauth_token and oauth_token_secret
        """
        oauth = AsyncOAuth1(
            self.consumer_key,
            self.consumer_secret,
            resource_owner_key=oauth_token,
            resource_owner_secret=oauth_token_secret,
            verifier=oauth_verifier
        )
        
        async with aiohttp.ClientSession() as session:
            auth_header = oauth.get_auth_header('POST', base.ACCESS_TOKEN_URL)
            
            async with session.post(
                base.ACCESS_TOKEN_URL,
                headers={'Authorization': auth_header}
            ) as response:
                if response.status != 200:
                    raise SplitwiseUnauthorizedException(
                        "Your oauth token could be expired or check your consumer id and secret",
                        response=response
                    )
                
                content = await response.text()
                credentials = parse_qs(content)
                
                return {
                    'oauth_token': credentials.get('oauth_token', [''])[0],
                    'oauth_token_secret': credentials.get('oauth_token_secret', [''])[0]
                }
    
    async def get_oauth2_access_token(
        self,
        code: str,
        redirect_uri: str
    ) -> Optional[Dict[str, Any]]:
        """Exchange OAuth 2.0 authorization code for access token.
        
        Args:
            code: Authorization code from redirect
            redirect_uri: Redirect URI used for authorization
            
        Returns:
            Dict with access_token and token_type, or None on failure
        """
        data = {
            'client_id': self.consumer_key,
            'client_secret': self.consumer_secret,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                base.OAUTH2_TOKEN_URL,
                data=urlencode(data),
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            ) as response:
                content = await response.text()
                
                if content == "false" or response.status != 200:
                    return None
                
                import json
                return json.loads(content)
    
    def get_oauth2_authorize_url(self, redirect_uri: str, state: Optional[str] = None) -> str:
        """Get OAuth 2.0 authorization URL.
        
        Args:
            redirect_uri: Redirect URI for callback
            state: Optional state parameter for CSRF protection
            
        Returns:
            Authorization URL
        """
        params = {
            'client_id': self.consumer_key,
            'redirect_uri': redirect_uri,
            'response_type': 'code'
        }
        
        if state:
            params['state'] = state
        
        return f"{base.OAUTH_AUTHORIZE_URL}?{urlencode(params)}"
