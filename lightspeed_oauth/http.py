"""HTTP client with automatic token refresh for Lightspeed API calls."""

import json
from typing import Optional, Dict, Any
import httpx
from rich.console import Console
from rich.json import JSON

from .models import OAuthConfig, StoredTokens
from .storage import TokenStorage
from .auth import OAuthClient


class LightspeedAPIClient:
    """HTTP client for Lightspeed Retail API with automatic token refresh."""
    
    BASE_URL = "https://api.lightspeedapp.com"
    
    def __init__(self, config: OAuthConfig, storage: TokenStorage):
        """Initialize API client.
        
        Args:
            config: OAuth configuration
            storage: Token storage instance
        """
        self.config = config
        self.storage = storage
        self.console = Console()
        self.client = httpx.Client(timeout=30.0)
        self._oauth_client = None
    
    @property
    def oauth_client(self) -> OAuthClient:
        """Get OAuth client instance."""
        if self._oauth_client is None:
            self._oauth_client = OAuthClient(self.config)
        return self._oauth_client
    
    def _refresh_tokens(self) -> bool:
        """Refresh tokens if possible.
        
        Returns:
            True if tokens were refreshed successfully, False otherwise
        """
        tokens = self.storage.load_tokens()
        if not tokens or not tokens.refresh_token:
            return False
        
        try:
            new_tokens = self.oauth_client.refresh_tokens(tokens.refresh_token)
            self.storage.save_tokens(new_tokens)
            return True
        except httpx.HTTPError as e:
            self.console.print(f"[red]Failed to refresh tokens: {e}[/red]")
            return False
    
    def _get_valid_tokens(self) -> Optional[StoredTokens]:
        """Get valid tokens, refreshing if necessary.
        
        Returns:
            Valid StoredTokens or None if refresh failed
        """
        tokens = self.storage.load_tokens()
        if not tokens:
            return None
        
        # If tokens are expired, try to refresh
        if tokens.is_expired():
            self.console.print("[yellow]Access token expired, attempting refresh...[/yellow]")
            if not self._refresh_tokens():
                return None
            tokens = self.storage.load_tokens()
        
        return tokens
    
    def call_api(self, path: str, method: str = "GET", **kwargs) -> Dict[str, Any]:
        """Make an authenticated API call to Lightspeed.
        
        Args:
            path: API endpoint path (e.g., "/API/V3/Account.json")
            method: HTTP method (GET, POST, etc.)
            **kwargs: Additional arguments for httpx request
            
        Returns:
            JSON response as dictionary
            
        Raises:
            httpx.HTTPError: If API call fails after retry
            ValueError: If no valid tokens available
        """
        # Ensure path starts with /
        if not path.startswith("/"):
            path = "/" + path
        
        url = f"{self.BASE_URL}{path}"
        
        # Get valid tokens
        tokens = self._get_valid_tokens()
        if not tokens:
            raise ValueError("No valid tokens available. Run 'lsr-auth init' to authenticate.")
        
        # Prepare headers
        headers = kwargs.get("headers", {})
        headers["Authorization"] = f"Bearer {tokens.access_token}"
        kwargs["headers"] = headers
        
        # Make the request
        try:
            response = self.client.request(method, url, **kwargs)
            
            # If 401, try to refresh tokens and retry once
            if response.status_code == 401:
                self.console.print("[yellow]Received 401, attempting token refresh...[/yellow]")
                
                if self._refresh_tokens():
                    # Update headers with new token
                    new_tokens = self.storage.load_tokens()
                    if new_tokens:
                        headers["Authorization"] = f"Bearer {new_tokens.access_token}"
                        kwargs["headers"] = headers
                        
                        # Retry the request
                        response = self.client.request(method, url, **kwargs)
                    else:
                        raise ValueError("Failed to refresh tokens")
                else:
                    raise ValueError("Token refresh failed. Please run 'lsr-auth init' to re-authenticate.")
            
            response.raise_for_status()
            
            # Try to parse as JSON
            try:
                return response.json()
            except json.JSONDecodeError:
                return {"content": response.text, "status_code": response.status_code}
                
        except httpx.HTTPError as e:
            self.console.print(f"[red]API call failed: {e}[/red]")
            raise
    
    def get(self, path: str, **kwargs) -> Dict[str, Any]:
        """Make a GET request to the API.
        
        Args:
            path: API endpoint path
            **kwargs: Additional arguments for httpx request
            
        Returns:
            JSON response as dictionary
        """
        return self.call_api(path, "GET", **kwargs)
    
    def post(self, path: str, **kwargs) -> Dict[str, Any]:
        """Make a POST request to the API.
        
        Args:
            path: API endpoint path
            **kwargs: Additional arguments for httpx request
            
        Returns:
            JSON response as dictionary
        """
        return self.call_api(path, "POST", **kwargs)
    
    def put(self, path: str, **kwargs) -> Dict[str, Any]:
        """Make a PUT request to the API.
        
        Args:
            path: API endpoint path
            **kwargs: Additional arguments for httpx request
            
        Returns:
            JSON response as dictionary
        """
        return self.call_api(path, "PUT", **kwargs)
    
    def delete(self, path: str, **kwargs) -> Dict[str, Any]:
        """Make a DELETE request to the API.
        
        Args:
            path: API endpoint path
            **kwargs: Additional arguments for httpx request
            
        Returns:
            JSON response as dictionary
        """
        return self.call_api(path, "DELETE", **kwargs)
    
    def close(self):
        """Close the HTTP client."""
        self.client.close()
        if self._oauth_client:
            self._oauth_client.close()
