"""Pydantic models for OAuth tokens and configuration."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class OAuthConfig(BaseModel):
    """OAuth configuration loaded from environment variables."""
    
    client_id: str = Field(..., description="Lightspeed Retail Client ID")
    client_secret: str = Field(..., description="Lightspeed Retail Client Secret")
    redirect_uri: str = Field(..., description="OAuth redirect URI")
    scope: str = Field(default="employee:all", description="OAuth scope")
    
    class Config:
        env_prefix = "LIGHTSPEED_RETAIL_"


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
        return datetime.utcnow() >= (self.expires_at.timestamp() - buffer_seconds)
    
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
