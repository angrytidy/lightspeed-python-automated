"""Base HTTP client with retry logic and rate limiting."""

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
import logging

from ..config import AuthTokens


logger = logging.getLogger(__name__)


class APIError(Exception):
    """Base API error."""
    pass


class RateLimitError(APIError):
    """Rate limit exceeded."""
    pass


class NotFoundError(APIError):
    """Resource not found."""
    pass


class AuthenticationError(APIError):
    """Authentication failed."""
    pass


class BaseClient(ABC):
    """Base HTTP client with retry logic and rate limiting."""
    
    def __init__(self, tokens: AuthTokens, rate_limit_delay: float = 0.25, max_retries: int = 3):
        self.tokens = tokens
        self.rate_limit_delay = rate_limit_delay
        self.max_retries = max_retries
        self.last_request_time = 0.0
        
        # Create HTTP client with reasonable defaults
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
        )
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    @property
    @abstractmethod
    def base_url(self) -> str:
        """Base URL for the API."""
        pass
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        return {
            "Authorization": f"Bearer {self.tokens.access_token}",
            "Content-Type": "application/json",
            "User-Agent": "Lightspeed-Sync/1.0.0"
        }
    
    async def _rate_limit_wait(self) -> None:
        """Implement rate limiting between requests."""
        now = time.time()
        time_since_last = now - self.last_request_time
        
        if time_since_last < self.rate_limit_delay:
            wait_time = self.rate_limit_delay - time_since_last
            await asyncio.sleep(wait_time)
        
        self.last_request_time = time.time()
    
    def _handle_response_errors(self, response: httpx.Response) -> None:
        """Handle common HTTP errors."""
        if response.status_code == 401:
            raise AuthenticationError("Authentication failed - token may be expired")
        elif response.status_code == 404:
            raise NotFoundError("Resource not found")
        elif response.status_code == 429:
            # Check for Retry-After header
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                raise RateLimitError(f"Rate limit exceeded. Retry after {retry_after} seconds")
            raise RateLimitError("Rate limit exceeded")
        elif response.status_code >= 500:
            raise APIError(f"Server error: {response.status_code} - {response.text}")
        elif not response.is_success:
            raise APIError(f"API error: {response.status_code} - {response.text}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((RateLimitError, httpx.TimeoutException, httpx.ConnectError)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make an HTTP request with retry logic."""
        await self._rate_limit_wait()
        
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        headers = self._get_headers()
        
        try:
            response = await self.client.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_data,
                data=data
            )
            
            self._handle_response_errors(response)
            
            # Return JSON response or empty dict for successful requests
            try:
                return response.json()
            except:
                return {"success": True, "status_code": response.status_code}
                
        except httpx.TimeoutException:
            raise APIError("Request timed out")
        except httpx.ConnectError:
            raise APIError("Connection failed")
    
    async def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make a GET request."""
        return await self._make_request("GET", endpoint, params=params)
    
    async def post(
        self,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make a POST request."""
        return await self._make_request("POST", endpoint, json_data=json_data, data=data)
    
    async def put(
        self,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make a PUT request."""
        return await self._make_request("PUT", endpoint, json_data=json_data, data=data)
    
    async def patch(
        self,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make a PATCH request."""
        return await self._make_request("PATCH", endpoint, json_data=json_data, data=data)
    
    async def delete(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make a DELETE request."""
        return await self._make_request("DELETE", endpoint, params=params)
