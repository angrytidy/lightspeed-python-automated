"""Configuration models and settings for Lightspeed API integration."""

from pathlib import Path
from typing import Dict, Optional, Literal
from pydantic import BaseModel, Field, HttpUrl
import os


class RetailConfig(BaseModel):
    """Retail (R-Series) API configuration."""
    
    base_url: str = "https://api.lightspeedapp.com/API/V3"
    client_id: str
    client_secret: str
    redirect_uri: str = "http://localhost:8080/callback"
    scope: str = "employee:all"
    account_id: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    
    # Custom field mapping (discovered dynamically)
    custom_field_mapping: Dict[str, str] = Field(default_factory=dict)
    
    @property
    def is_authenticated(self) -> bool:
        """Check if we have valid authentication tokens."""
        return bool(self.access_token and self.account_id)


class EcomConfig(BaseModel):
    """eCom (C-Series) API configuration."""
    
    base_url: str = "https://api.webshopapp.com"
    client_id: str
    client_secret: str
    redirect_uri: str = "http://localhost:8080/callback"
    scope: str = "products"
    shop_id: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    
    @property
    def is_authenticated(self) -> bool:
        """Check if we have valid authentication tokens."""
        return bool(self.access_token and self.shop_id)


class Config(BaseModel):
    """Main application configuration."""
    
    # API configurations
    retail: RetailConfig
    ecom: EcomConfig
    
    # File paths
    credentials_dir: Path = Field(default_factory=lambda: Path.home() / ".lightspeed" / "credentials")
    cache_dir: Path = Field(default_factory=lambda: Path(".cache"))
    output_dir: Path = Field(default_factory=lambda: Path("./out"))
    
    # Processing options
    concurrency: int = Field(default=4, ge=1, le=20)
    rate_limit_delay: float = Field(default=0.25, ge=0.1, le=2.0)
    max_retries: int = Field(default=3, ge=1, le=10)
    
    # Image handling
    image_mode: Literal["url", "upload"] = "url"
    max_images_per_product: int = Field(default=12, ge=1, le=50)
    
    # Validation
    validate_urls: bool = True
    dry_run: bool = False
    force_update: bool = False
    
    def model_post_init(self, __context) -> None:
        """Create necessary directories after initialization."""
        self.credentials_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)


class AuthTokens(BaseModel):
    """OAuth token storage model."""
    
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[int] = None
    account_id: Optional[str] = None  # For Retail API
    shop_id: Optional[str] = None     # For eCom API
    
    @property
    def is_expired(self) -> bool:
        """Check if token is expired (with 5-minute buffer)."""
        if not self.expires_at:
            return False
        import time
        return time.time() > (self.expires_at - 300)  # 5-minute buffer


class ProductMatch(BaseModel):
    """Model for SKU to API ID mapping."""
    
    sku: str
    retail_item_id: Optional[str] = None
    ecom_product_id: Optional[str] = None
    last_updated: Optional[int] = None
    
    @property
    def has_retail_match(self) -> bool:
        return bool(self.retail_item_id)
    
    @property
    def has_ecom_match(self) -> bool:
        return bool(self.ecom_product_id)


class UpdateResult(BaseModel):
    """Result of an update operation."""
    
    sku: str
    service: Literal["retail", "ecom"]
    operation: str
    success: bool
    error: Optional[str] = None
    changes_made: Dict[str, str] = Field(default_factory=dict)


class ProcessingStats(BaseModel):
    """Statistics for a processing run."""
    
    total_rows: int = 0
    processed_rows: int = 0
    skipped_rows: int = 0
    retail_updates: int = 0
    ecom_updates: int = 0
    errors: int = 0
    warnings: int = 0
    
    def add_result(self, result: UpdateResult) -> None:
        """Add an update result to the statistics."""
        if result.success:
            if result.service == "retail":
                self.retail_updates += 1
            else:
                self.ecom_updates += 1
        else:
            self.errors += 1


def load_config_from_env() -> Config:
    """Load configuration from environment variables."""
    from dotenv import load_dotenv
    load_dotenv()
    retail_config = RetailConfig(
        client_id=os.getenv("LIGHTSPEED_RETAIL_CLIENT_ID", ""),
        client_secret=os.getenv("LIGHTSPEED_RETAIL_CLIENT_SECRET", ""),
        redirect_uri=os.getenv("LIGHTSPEED_RETAIL_REDIRECT_URI", "http://localhost:8080/callback"),
        scope=os.getenv("LIGHTSPEED_RETAIL_SCOPE", "employee:all"),
    )
    
    ecom_config = EcomConfig(
        client_id=os.getenv("LIGHTSPEED_ECOM_CLIENT_ID", ""),
        client_secret=os.getenv("LIGHTSPEED_ECOM_CLIENT_SECRET", ""),
        redirect_uri=os.getenv("LIGHTSPEED_ECOM_REDIRECT_URI", "http://localhost:8080/callback"),
        scope=os.getenv("LIGHTSPEED_ECOM_SCOPE", "products"),
    )
    
    return Config(
        retail=retail_config,
        ecom=ecom_config,
        concurrency=int(os.getenv("LIGHTSPEED_CONCURRENCY", "4")),
        dry_run=os.getenv("LIGHTSPEED_DRY_RUN", "").lower() == "true",
    )
