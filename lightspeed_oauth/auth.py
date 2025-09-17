"""OAuth authentication flow implementation."""

import os
import secrets
import webbrowser
from urllib.parse import urlencode, parse_qs, urlparse
from typing import Optional, Tuple
import asyncio
from datetime import datetime, timedelta

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import uvicorn
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption

from .models import OAuthConfig, TokenResponse, StoredTokens


class OAuthClient:
    """Handles OAuth authentication flow for Lightspeed Retail API."""
    
    # Lightspeed OAuth endpoints
    AUTHORIZE_URL = "https://cloud.lightspeedapp.com/auth/oauth/authorize"
    TOKEN_URL = "https://cloud.lightspeedapp.com/auth/oauth/token"
    
    def __init__(self, config: OAuthConfig):
        """Initialize OAuth client with configuration."""
        self.config = config
        self.client = httpx.Client(timeout=30.0)
    
    def generate_state(self) -> str:
        """Generate a random state parameter for OAuth flow."""
        return secrets.token_urlsafe(32)
    
    def build_authorize_url(self, state: str) -> str:
        """Build the OAuth authorization URL.
        
        Args:
            state: Random state parameter for security
            
        Returns:
            Complete authorization URL
        """
        params = {
            "response_type": "code",
            "client_id": self.config.client_id,
            "scope": self.config.scope,
            "redirect_uri": self.config.redirect_uri,
            "state": state,
        }
        
        return f"{self.AUTHORIZE_URL}?{urlencode(params)}"
    
    def exchange_code_for_tokens(self, code: str) -> StoredTokens:
        """Exchange authorization code for access and refresh tokens.
        
        Args:
            code: Authorization code from OAuth callback
            
        Returns:
            StoredTokens with access and refresh tokens
            
        Raises:
            httpx.HTTPError: If token exchange fails
        """
        data = {
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "grant_type": "authorization_code",
            "code": code,
        }
        
        response = self.client.post(
            self.TOKEN_URL,
            json=data,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        
        token_response = TokenResponse(**response.json())
        
        # Calculate expiry time with 60 second buffer
        expires_at = datetime.utcnow() + timedelta(seconds=token_response.expires_in - 60)
        
        return StoredTokens(
            access_token=token_response.access_token,
            refresh_token=token_response.refresh_token,
            expires_at=expires_at,
            scope=token_response.scope,
            token_type=token_response.token_type,
        )
    
    def refresh_tokens(self, refresh_token: str) -> StoredTokens:
        """Refresh access token using refresh token.
        
        Args:
            refresh_token: The refresh token
            
        Returns:
            New StoredTokens with refreshed access token
            
        Raises:
            httpx.HTTPError: If token refresh fails
        """
        data = {
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        
        response = self.client.post(
            self.TOKEN_URL,
            json=data,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        
        token_response = TokenResponse(**response.json())
        
        # Calculate expiry time with 60 second buffer
        expires_at = datetime.utcnow() + timedelta(seconds=token_response.expires_in - 60)
        
        return StoredTokens(
            access_token=token_response.access_token,
            refresh_token=token_response.refresh_token or refresh_token,  # Keep old refresh token if not provided
            expires_at=expires_at,
            scope=token_response.scope,
            token_type=token_response.token_type,
        )
    
    def create_self_signed_cert(self, cert_path: str, key_path: str) -> None:
        """Create a self-signed certificate for local HTTPS server."""
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        
        # Create certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Lightspeed OAuth"),
            x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=365)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.IPAddress("127.0.0.1"),
            ]),
            critical=False,
        ).sign(private_key, hashes.SHA256())
        
        # Write certificate and key to files
        with open(cert_path, "wb") as f:
            f.write(cert.public_bytes(Encoding.PEM))
        
        with open(key_path, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=PrivateFormat.PKCS8,
                encryption_algorithm=NoEncryption()
            ))
    
    async def start_callback_server(self, state: str, port: int = 8080) -> Tuple[str, str]:
        """Start a local HTTPS server to capture OAuth callback.
        
        Args:
            state: Expected state parameter for security
            port: Port to run the server on
            
        Returns:
            Tuple of (authorization_code, error_message)
        """
        app = FastAPI()
        result = {"code": None, "error": None}
        
        @app.get("/callback")
        async def callback(request: Request):
            """Handle OAuth callback."""
            query_params = request.query_params
            
            # Check for error
            if "error" in query_params:
                error = query_params["error"]
                error_description = query_params.get("error_description", "Unknown error")
                result["error"] = f"OAuth error: {error} - {error_description}"
                return HTMLResponse("""
                    <html>
                        <body>
                            <h1>OAuth Error</h1>
                            <p>Error: {}</p>
                            <p>Description: {}</p>
                            <p>You can close this window.</p>
                        </body>
                    </html>
                """.format(error, error_description))
            
            # Check state parameter
            received_state = query_params.get("state")
            if received_state != state:
                result["error"] = f"State mismatch. Expected: {state}, Got: {received_state}"
                return HTMLResponse("""
                    <html>
                        <body>
                            <h1>Security Error</h1>
                            <p>State parameter mismatch. This may be a security issue.</p>
                            <p>You can close this window.</p>
                        </body>
                    </html>
                """)
            
            # Get authorization code
            code = query_params.get("code")
            if not code:
                result["error"] = "No authorization code received"
                return HTMLResponse("""
                    <html>
                        <body>
                            <h1>Error</h1>
                            <p>No authorization code received.</p>
                            <p>You can close this window.</p>
                        </body>
                    </html>
                """)
            
            result["code"] = code
            return HTMLResponse("""
                <html>
                    <body>
                        <h1>Success!</h1>
                        <p>Authorization code received. You can close this window.</p>
                    </body>
                </html>
            """)
        
        # Create self-signed certificate
        cert_path = "localhost.pem"
        key_path = "localhost.key"
        
        try:
            self.create_self_signed_cert(cert_path, key_path)
            
            # Start server
            config = uvicorn.Config(
                app,
                host="0.0.0.0",
                port=port,
                ssl_keyfile=key_path,
                ssl_certfile=cert_path,
                log_level="error"
            )
            server = uvicorn.Server(config)
            
            # Run server in background
            server_task = asyncio.create_task(server.serve())
            
            # Wait for callback or timeout
            timeout = 300  # 5 minutes
            start_time = asyncio.get_event_loop().time()
            
            while asyncio.get_event_loop().time() - start_time < timeout:
                if result["code"] is not None or result["error"] is not None:
                    break
                await asyncio.sleep(0.1)
            
            # Stop server
            server.should_exit = True
            await server_task
            
            # Clean up certificate files
            try:
                os.unlink(cert_path)
                os.unlink(key_path)
            except OSError:
                pass
            
            return result["code"], result["error"]
            
        except Exception as e:
            # Clean up certificate files
            try:
                os.unlink(cert_path)
                os.unlink(key_path)
            except OSError:
                pass
            raise e
    
    def manual_auth_flow(self, state: str) -> Tuple[str, str]:
        """Handle manual authentication flow (user pastes code).
        
        Args:
            state: Expected state parameter for security
            
        Returns:
            Tuple of (authorization_code, error_message)
        """
        auth_url = self.build_authorize_url(state)
        
        print(f"\nPlease visit this URL to authorize the application:")
        print(f"{auth_url}\n")
        
        # Prompt for code
        code = input("Enter the authorization code: ").strip()
        
        if not code:
            return None, "No authorization code provided"
        
        return code, None
    
    def close(self):
        """Close the HTTP client."""
        self.client.close()
