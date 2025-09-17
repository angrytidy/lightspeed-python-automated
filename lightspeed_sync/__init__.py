"""
Lightspeed Retail (R-Series) + eCom (C-Series) API Updater

A robust CLI tool that reads Google-Sheet-exported CSV files and updates
existing products via Lightspeed APIs:
- Retail (R-Series) API: Custom Fields and Weight
- eCom (C-Series) API: Web Store Descriptions and Product Images

No new products are created; only updates to existing items matched by SKU.
"""

__version__ = "1.0.0"
__author__ = "Lightspeed Sync Tool"

from .config import Config, RetailConfig, EcomConfig

__all__ = ["Config", "RetailConfig", "EcomConfig"]
