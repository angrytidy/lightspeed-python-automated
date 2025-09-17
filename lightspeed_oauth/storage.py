"""Token storage and retrieval from local filesystem."""

import json
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

from .models import StoredTokens


class TokenStorage:
    """Handles reading and writing OAuth tokens to local storage."""
    
    def __init__(self, credentials_dir: Optional[Path] = None):
        """Initialize token storage.
        
        Args:
            credentials_dir: Directory to store credentials. Defaults to ~/.lightspeed/credentials/
        """
        if credentials_dir is None:
            self.credentials_dir = Path.home() / ".lightspeed" / "credentials"
        else:
            self.credentials_dir = Path(credentials_dir)
        
        self.credentials_file = self.credentials_dir / "retail.json"
        self.credentials_dir.mkdir(parents=True, exist_ok=True)
    
    def save_tokens(self, tokens: StoredTokens) -> None:
        """Save tokens to local storage.
        
        Args:
            tokens: The tokens to save
        """
        token_data = {
            "access_token": tokens.access_token,
            "refresh_token": tokens.refresh_token,
            "expires_at": tokens.expires_at.isoformat(),
            "scope": tokens.scope,
            "token_type": tokens.token_type,
        }
        
        with open(self.credentials_file, "w") as f:
            json.dump(token_data, f, indent=2)
    
    def load_tokens(self) -> Optional[StoredTokens]:
        """Load tokens from local storage.
        
        Returns:
            StoredTokens if found and valid, None otherwise
        """
        if not self.credentials_file.exists():
            return None
        
        try:
            with open(self.credentials_file, "r") as f:
                token_data = json.load(f)
            
            # Convert expires_at string back to datetime
            token_data["expires_at"] = datetime.fromisoformat(token_data["expires_at"])
            
            return StoredTokens(**token_data)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # If file is corrupted or missing required fields, return None
            return None
    
    def clear_tokens(self) -> None:
        """Remove stored tokens."""
        if self.credentials_file.exists():
            self.credentials_file.unlink()
    
    def has_tokens(self) -> bool:
        """Check if tokens are stored."""
        return self.credentials_file.exists() and self.load_tokens() is not None
    
    def get_storage_info(self) -> dict:
        """Get information about token storage location and status."""
        tokens = self.load_tokens()
        
        info = {
            "storage_path": str(self.credentials_file),
            "has_tokens": self.has_tokens(),
        }
        
        if tokens:
            info.update({
                "access_token": tokens.get_masked_access_token(),
                "refresh_token": tokens.get_masked_refresh_token(),
                "expires_at": tokens.expires_at.isoformat(),
                "is_expired": tokens.is_expired(),
                "scope": tokens.scope,
            })
        
        return info
