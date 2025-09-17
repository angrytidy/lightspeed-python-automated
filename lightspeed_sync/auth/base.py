"""Base authentication functionality for Lightspeed APIs."""

import json
import time
import webbrowser
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Optional, Tuple
from urllib.parse import urlencode, parse_qs, urlparse

import httpx
from rich.console import Console
from rich.prompt import Prompt

from ..config import AuthTokens


class AuthError(Exception):
    """Authentication-related error."""
    pass


class AuthBase(ABC):
    """Base class for Lightspeed API authentication."""
    
    def __init__(self, client_id: str, client_secret: str, credentials_dir: Path):
        self.client_id = client_id
        self.client_secret = client_secret
        self.credentials_dir = credentials_dir
        self.console = Console()
        
        # Ensure credentials directory exists
        self.credentials_dir.mkdir(parents=True, exist_ok=True)
    
    @property
    @abstractmethod
    def service_name(self) -> str:
        """Name of the service (e.g., 'retail', 'ecom')."""
        pass
    
    @property
    @abstractmethod
    def auth_base_url(self) -> str:
        """Base URL for OAuth authorization."""
        pass
    
    @property
    @abstractmethod
    def token_url(self) -> str:
        """URL for token exchange."""
        pass
    
    @property
    @abstractmethod
    def scopes(self) -> str:
        """Required OAuth scopes."""
        pass
    
    @property
    def credentials_file(self) -> Path:
        """Path to credentials file for this service."""
        return self.credentials_dir / f"{self.service_name}_tokens.json"
    
    def load_tokens(self) -> Optional[AuthTokens]:
        """Load stored authentication tokens."""
        if not self.credentials_file.exists():
            return None
        
        try:
            with open(self.credentials_file, 'r') as f:
                data = json.load(f)
            return AuthTokens(**data)
        except (json.JSONDecodeError, ValueError) as e:
            self.console.print(f"[red]Error loading tokens: {e}[/red]")
            return None
    
    def save_tokens(self, tokens: AuthTokens) -> None:
        """Save authentication tokens to disk."""
        with open(self.credentials_file, 'w') as f:
            json.dump(tokens.model_dump(), f, indent=2)
        
        # Set restrictive permissions
        self.credentials_file.chmod(0o600)
        self.console.print(f"[green]Tokens saved to {self.credentials_file}[/green]")
    
    def get_authorization_url(self, redirect_uri: str = "http://localhost:8080/callback") -> str:
        """Generate OAuth authorization URL."""
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "scope": self.scopes,
            "state": f"{self.service_name}_{int(time.time())}"
        }
        
        return f"{self.auth_base_url}?{urlencode(params)}"
    
    async def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> AuthTokens:
        """Exchange authorization code for access tokens."""
        data = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.token_url, data=data)
                response.raise_for_status()
                token_data = response.json()
                
                # Calculate expiry time
                expires_in = token_data.get("expires_in", 3600)
                expires_at = int(time.time() + expires_in)
                
                tokens = AuthTokens(
                    access_token=token_data["access_token"],
                    refresh_token=token_data.get("refresh_token"),
                    expires_at=expires_at,
                )
                
                # Add service-specific fields
                await self._enrich_tokens(tokens, token_data)
                
                return tokens
                
            except httpx.HTTPStatusError as e:
                error_detail = ""
                try:
                    error_data = e.response.json()
                    error_detail = error_data.get("error_description", str(error_data))
                except:
                    error_detail = e.response.text
                
                raise AuthError(f"Token exchange failed: {error_detail}")
    
    @abstractmethod
    async def _enrich_tokens(self, tokens: AuthTokens, token_data: Dict) -> None:
        """Add service-specific data to tokens (e.g., account_id, shop_id)."""
        pass
    
    async def refresh_access_token(self, tokens: AuthTokens) -> AuthTokens:
        """Refresh an expired access token."""
        if not tokens.refresh_token:
            raise AuthError("No refresh token available")
        
        data = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": tokens.refresh_token,
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.token_url, data=data)
                response.raise_for_status()
                token_data = response.json()
                
                # Calculate new expiry time
                expires_in = token_data.get("expires_in", 3600)
                expires_at = int(time.time() + expires_in)
                
                # Update tokens
                tokens.access_token = token_data["access_token"]
                tokens.refresh_token = token_data.get("refresh_token", tokens.refresh_token)
                tokens.expires_at = expires_at
                
                self.console.print(f"[green]{self.service_name} tokens refreshed[/green]")
                return tokens
                
            except httpx.HTTPStatusError as e:
                raise AuthError(f"Token refresh failed: {e.response.text}")
    
    def start_interactive_auth(self) -> None:
        """Start interactive OAuth flow with local callback server."""
        self.console.print(f"\n[bold cyan]{self.service_name.title()} OAuth2 Authentication[/bold cyan]")
        
        # Get redirect URI from config
        from ..config import load_config_from_env
        config = load_config_from_env()
        if self.service_name == "retail":
            redirect_uri = config.retail.redirect_uri
        else:
            redirect_uri = config.ecom.redirect_uri
        
        # Generate authorization URL
        auth_url = self.get_authorization_url(redirect_uri)
        
        self.console.print(f"\n[bold]Step 1:[/bold] Visit this URL in your browser:")
        self.console.print(f"[blue]{auth_url}[/blue]")
        
        # Try to open browser
        try:
            webbrowser.open(auth_url)
            self.console.print("[green]✓ Browser opened automatically[/green]")
        except Exception:
            self.console.print("[yellow]Could not open browser automatically[/yellow]")
        
        self.console.print(f"\n[bold]Step 2:[/bold] After logging in, you'll be redirected to a page that shows an error.")
        self.console.print("This is normal! Look at the URL in your browser's address bar.")
        self.console.print("You should see something like: http://localhost:8080/callback?code=ABC123...")
        self.console.print("Copy the 'code' parameter from the URL.")
        
        # Get authorization code from user
        code = input("\nEnter the authorization code: ").strip()
        
        if not code:
            raise AuthError("No authorization code provided")
        
        # Exchange code for tokens
        self.console.print("Exchanging authorization code for tokens...")
        try:
            # Use synchronous token exchange
            tokens = self._sync_exchange_code_for_tokens(code, redirect_uri)
            
            # Save tokens
            self.save_tokens(tokens)
            
            self.console.print(f"[green]✓ {self.service_name.title()} authentication complete![/green]")
            self.console.print(f"[green]Tokens saved to: {self.credentials_file}[/green]")
            
        except Exception as e:
            raise AuthError(f"Token exchange failed: {e}")
    
    async def _interactive_auth_flow(self) -> None:
        """Run the interactive OAuth flow."""
        from http.server import HTTPServer, BaseHTTPRequestHandler
        import threading
        from urllib.parse import urlparse, parse_qs
        
        redirect_uri = "http://localhost:8080/callback"
        auth_url = self.get_authorization_url(redirect_uri)
        
        # Storage for the authorization code
        auth_result = {"code": None, "error": None}
        
        class CallbackHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed_url = urlparse(self.path)
                query_params = parse_qs(parsed_url.query)
                
                if "code" in query_params:
                    auth_result["code"] = query_params["code"][0]
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    self.wfile.write(b"""
                    <html>
                        <body>
                            <h1>Authorization Successful!</h1>
                            <p>You can close this window and return to the terminal.</p>
                        </body>
                    </html>
                    """)
                elif "error" in query_params:
                    auth_result["error"] = query_params["error"][0]
                    self.send_response(400)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    self.wfile.write(f"""
                    <html>
                        <body>
                            <h1>Authorization Failed</h1>
                            <p>Error: {query_params["error"][0]}</p>
                        </body>
                    </html>
                    """.encode())
                
                # Signal that we're done
                threading.Thread(target=lambda: httpd.shutdown()).start()
            
            def log_message(self, format, *args):
                # Suppress server logs
                pass
        
        # Start local server
        httpd = HTTPServer(("localhost", 8080), CallbackHandler)
        server_thread = threading.Thread(target=httpd.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        
        self.console.print(f"\n[bold cyan]{self.service_name.title()} Authentication[/bold cyan]")
        self.console.print(f"Opening browser for authorization...")
        self.console.print(f"If browser doesn't open, visit: {auth_url}")
        
        # Open browser
        webbrowser.open(auth_url)
        
        # Wait for callback
        self.console.print("Waiting for authorization...")
        server_thread.join(timeout=300)  # 5 minute timeout
        
        if auth_result["error"]:
            raise AuthError(f"Authorization failed: {auth_result['error']}")
        
        if not auth_result["code"]:
            raise AuthError("Authorization timed out or was cancelled")
        
        # Exchange code for tokens
        self.console.print("Exchanging authorization code for tokens...")
        tokens = await self.exchange_code_for_tokens(auth_result["code"], redirect_uri)
        
        # Save tokens
        self.save_tokens(tokens)
        
        self.console.print(f"[green]✓ {self.service_name.title()} authentication complete![/green]")
    
    def _sync_interactive_auth_flow(self) -> None:
        """Synchronous OAuth flow for when async is problematic."""
        import webbrowser
        import time
        from http.server import HTTPServer, BaseHTTPRequestHandler
        import threading
        from urllib.parse import urlparse, parse_qs
        
        redirect_uri = "http://localhost:8080/callback"
        auth_url = self.get_authorization_url(redirect_uri)
        
        # Storage for the authorization code
        auth_result = {"code": None, "error": None, "done": False}
        
        class CallbackHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed_url = urlparse(self.path)
                query_params = parse_qs(parsed_url.query)
                
                if "code" in query_params:
                    auth_result["code"] = query_params["code"][0]
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    self.wfile.write(b"""
                    <html>
                        <body>
                            <h1>Authorization Successful!</h1>
                            <p>You can close this window and return to the terminal.</p>
                            <script>setTimeout(function(){window.close()}, 2000);</script>
                        </body>
                    </html>
                    """)
                elif "error" in query_params:
                    auth_result["error"] = query_params["error"][0]
                    self.send_response(400)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    self.wfile.write(f"""
                    <html>
                        <body>
                            <h1>Authorization Failed</h1>
                            <p>Error: {query_params["error"][0]}</p>
                        </body>
                    </html>
                    """.encode())
                
                auth_result["done"] = True
            
            def log_message(self, format, *args):
                # Suppress server logs
                pass
        
        # Start local server
        try:
            httpd = HTTPServer(("localhost", 8080), CallbackHandler)
        except OSError as e:
            if "address already in use" in str(e).lower():
                self.console.print("[red]Port 8080 is already in use. Please close any applications using this port and try again.[/red]")
                raise AuthError("Port 8080 is already in use")
            raise
        
        server_thread = threading.Thread(target=httpd.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        
        self.console.print(f"\n[bold cyan]{self.service_name.title()} Authentication[/bold cyan]")
        self.console.print(f"Opening browser for authorization...")
        self.console.print(f"If browser doesn't open, visit: {auth_url}")
        
        # Open browser
        webbrowser.open(auth_url)
        
        # Wait for callback with timeout
        self.console.print("Waiting for authorization...")
        timeout = 300  # 5 minutes
        start_time = time.time()
        
        while not auth_result["done"] and (time.time() - start_time) < timeout:
            time.sleep(0.5)
        
        httpd.shutdown()
        server_thread.join(timeout=1)
        
        if auth_result["error"]:
            raise AuthError(f"Authorization failed: {auth_result['error']}")
        
        if not auth_result["code"]:
            raise AuthError("Authorization timed out or was cancelled")
        
        # Exchange code for tokens synchronously
        self.console.print("Exchanging authorization code for tokens...")
        tokens = self._sync_exchange_code_for_tokens(auth_result["code"], redirect_uri)
        
        # Save tokens
        self.save_tokens(tokens)
        
        self.console.print(f"[green]✓ {self.service_name.title()} authentication complete![/green]")
    
    def _sync_exchange_code_for_tokens(self, code: str, redirect_uri: str) -> 'AuthTokens':
        """Synchronous version of token exchange."""
        import requests
        from ..config import AuthTokens
        
        data = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
        }
        
        try:
            response = requests.post(self.token_url, data=data, timeout=30)
            response.raise_for_status()
            token_data = response.json()
            
            # Calculate expiry time
            expires_in = token_data.get("expires_in", 3600)
            expires_at = int(time.time() + expires_in)
            
            tokens = AuthTokens(
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token"),
                expires_at=expires_at,
            )
            
            # Add service-specific fields synchronously
            self._sync_enrich_tokens(tokens, token_data)
            
            return tokens
            
        except requests.RequestException as e:
            raise AuthError(f"Token exchange failed: {str(e)}")
    
    def _sync_enrich_tokens(self, tokens: 'AuthTokens', token_data: dict) -> None:
        """Synchronous version of token enrichment - override in subclasses."""
        pass
    
    def _manual_token_input(self) -> None:
        """Manual token input as fallback when browser flow fails."""
        from ..config import AuthTokens
        import time
        
        self.console.print(f"\n[bold cyan]Manual {self.service_name.title()} Token Input[/bold cyan]")
        self.console.print("Since browser authentication failed, please provide tokens manually.")
        self.console.print("\nTo get your tokens:")
        self.console.print("1. Visit the authorization URL below in your browser")
        self.console.print("2. Complete the OAuth flow")
        self.console.print("3. Copy the access token from the response")
        
        # Generate authorization URL
        redirect_uri = "http://localhost:8080/callback"
        auth_url = self.get_authorization_url(redirect_uri)
        
        self.console.print(f"\n[bold]Authorization URL:[/bold]")
        self.console.print(f"[blue]{auth_url}[/blue]")
        
        # Get access token from user
        access_token = input("\nEnter your access token: ").strip()
        
        if not access_token:
            raise AuthError("No access token provided")
        
        # Create tokens object
        tokens = AuthTokens(
            access_token=access_token,
            refresh_token="",  # Manual input doesn't provide refresh token
            expires_at=int(time.time() + 3600),  # Assume 1 hour expiry
        )
        
        # Enrich tokens with service-specific data
        try:
            self._sync_enrich_tokens(tokens, {})
        except Exception as e:
            self.console.print(f"[yellow]Warning: Could not enrich tokens: {e}[/yellow]")
        
        # Save tokens
        self.save_tokens(tokens)
        
        self.console.print(f"[green]✓ {self.service_name.title()} authentication complete![/green]")
        self.console.print("[yellow]Note: Manual tokens may not auto-refresh. You may need to re-authenticate when they expire.[/yellow]")
    
    def _client_credentials_auth(self) -> None:
        """Use client credentials grant type (no redirect URI needed)."""
        from ..config import AuthTokens
        import time
        import requests
        
        self.console.print(f"\n[bold cyan]{self.service_name.title()} Client Credentials Authentication[/bold cyan]")
        self.console.print("Using client credentials grant type...")
        
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        
        try:
            response = requests.post(self.token_url, data=data, timeout=30)
            response.raise_for_status()
            token_data = response.json()
            
            # Calculate expiry time
            expires_in = token_data.get("expires_in", 3600)
            expires_at = int(time.time() + expires_in)
            
            tokens = AuthTokens(
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token", ""),
                expires_at=expires_at,
            )
            
            # Enrich tokens with service-specific data
            try:
                self._sync_enrich_tokens(tokens, token_data)
            except Exception as e:
                self.console.print(f"[yellow]Warning: Could not enrich tokens: {e}[/yellow]")
            
            # Save tokens
            self.save_tokens(tokens)
            
            self.console.print(f"[green]✓ {self.service_name.title()} authentication complete![/green]")
            
        except requests.RequestException as e:
            self.console.print(f"[red]Client credentials authentication failed: {e}[/red]")
            self.console.print("[yellow]Falling back to manual token input...[/yellow]")
            self._manual_token_input()
    
    async def get_valid_tokens(self) -> AuthTokens:
        """Get valid tokens, refreshing if necessary."""
        tokens = self.load_tokens()
        
        if not tokens:
            raise AuthError(f"No {self.service_name} tokens found. Run authentication first.")
        
        # Check if tokens need refresh
        if tokens.is_expired and tokens.refresh_token:
            self.console.print(f"[yellow]Refreshing {self.service_name} tokens...[/yellow]")
            tokens = await self.refresh_access_token(tokens)
            self.save_tokens(tokens)
        elif tokens.is_expired:
            raise AuthError(f"{self.service_name} tokens expired and no refresh token available. Re-authenticate.")
        
        return tokens
