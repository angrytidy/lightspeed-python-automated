"""Pydantic models for OAuth tokens and configuration."""

import os
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class OAuthConfig(BaseSettings):
    """OAuth configuration loaded from environment variables."""
    
    client_id: str = Field(..., description="Lightspeed Retail Client ID")
    client_secret: str = Field(..., description="Lightspeed Retail Client Secret")
    redirect_uri: str = Field(..., description="OAuth redirect URI")
    scope: str = Field(default="employee:all", description="OAuth scope")
    publicly_distributed: bool = Field(default=False, description="Enable PKCE public client flow (omit client_secret)")
    
    model_config = {
        "env_prefix": "LIGHTSPEED_RETAIL_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


class TokenResponse(BaseModel):
    """Response from OAuth token endpoint."""
    
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_in: int = Field(..., description="Token expiry in seconds")
    scope: str


class StoredTokens(BaseModel):
    """Tokens stored locally with metadata."""
    
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: datetime = Field(..., description="When the access token expires")
    scope: str
    token_type: str = "Bearer"
    
    def is_expired(self, buffer_seconds: int = 60) -> bool:
        """Check if the access token is expired (with buffer)."""
        import datetime as dt
        buffer_time = dt.timedelta(seconds=buffer_seconds)
        return dt.datetime.utcnow() >= (self.expires_at - buffer_time)
    
    def mask_token(self, token: str) -> str:
        """Mask a token for display (show first 4 and last 4 chars)."""
        if len(token) <= 8:
            return "*" * len(token)
        return f"{token[:4]}...{token[-4:]}"
    
    def get_masked_access_token(self) -> str:
        """Get masked access token for display."""
        return self.mask_token(self.access_token)
    
    def get_masked_refresh_token(self) -> str:
        """Get masked refresh token for display."""
        if not self.refresh_token:
            return "None"
        return self.mask_token(self.refresh_token)
