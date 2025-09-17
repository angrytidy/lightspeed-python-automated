"""eCom (C-Series) API authentication."""

import httpx
from typing import Dict

from .base import AuthBase, AuthError
from ..config import AuthTokens


class EcomAuth(AuthBase):
    """Authentication for Lightspeed eCom (C-Series) API."""
    
    @property
    def service_name(self) -> str:
        return "ecom"
    
    @property
    def auth_base_url(self) -> str:
        return "https://api.webshopapp.com/oauth/authorize"
    
    @property
    def token_url(self) -> str:
        return "https://api.webshopapp.com/oauth/token"
    
    @property
    def scopes(self) -> str:
        # Standard scopes for product management
        return "products"
    
    async def _enrich_tokens(self, tokens: AuthTokens, token_data: Dict) -> None:
        """Add shop_id to tokens by making a test API call."""
        # The eCom API may require a shop ID for some calls
        # We can get this from the shop info endpoint
        
        headers = {
            "Authorization": f"Bearer {tokens.access_token}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                # Get shop information
                response = await client.get(
                    "https://api.webshopapp.com/en/shop.json",
                    headers=headers
                )
                response.raise_for_status()
                shop_data = response.json()
                
                # Extract shop ID from response
                if "shop" in shop_data:
                    shop_info = shop_data["shop"]
                    if "id" in shop_info:
                        tokens.shop_id = str(shop_info["id"])
                        self.console.print(f"[green]Retrieved eCom shop ID: {tokens.shop_id}[/green]")
                    elif "shop_id" in shop_info:
                        tokens.shop_id = str(shop_info["shop_id"])
                        self.console.print(f"[green]Retrieved eCom shop ID: {tokens.shop_id}[/green]")
                    else:
                        # Shop ID might not be required for all operations
                        self.console.print("[yellow]No shop ID found, but may not be required[/yellow]")
                else:
                    self.console.print("[yellow]No shop information found[/yellow]")
                    
            except httpx.HTTPStatusError as e:
                # Shop ID might not be required, so don't fail
                self.console.print(f"[yellow]Warning: Could not retrieve shop information: {e.response.text}[/yellow]")
    
    async def test_connection(self, tokens: AuthTokens) -> bool:
        """Test the API connection with current tokens."""
        headers = {
            "Authorization": f"Bearer {tokens.access_token}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                # Test with a simple API call
                response = await client.get(
                    "https://api.webshopapp.com/en/shop.json",
                    headers=headers
                )
                response.raise_for_status()
                return True
            except:
                return False
    
    async def get_product_fields_info(self, tokens: AuthTokens) -> Dict[str, str]:
        """Get information about available product fields."""
        headers = {
            "Authorization": f"Bearer {tokens.access_token}",
            "Content-Type": "application/json"
        }
        
        field_info = {
            "description": "Short description field",
            "content": "Long description/content field (HTML supported)",
            "title": "Product title",
            "fulltitle": "Full product title"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                # Get a sample product to inspect field structure
                response = await client.get(
                    "https://api.webshopapp.com/en/products.json",
                    headers=headers,
                    params={"limit": 1}
                )
                response.raise_for_status()
                products_data = response.json()
                
                if "products" in products_data and products_data["products"]:
                    product = products_data["products"][0]
                    available_fields = list(product.keys())
                    self.console.print(f"[green]Available product fields: {available_fields[:10]}...[/green]")
                
                return field_info
                
            except httpx.HTTPStatusError as e:
                self.console.print(f"[yellow]Warning: Could not retrieve product field info: {e.response.text}[/yellow]")
                return field_info
    
    def _sync_enrich_tokens(self, tokens, token_data):
        """Synchronous version of token enrichment."""
        import requests
        
        headers = {
            "Authorization": f"Bearer {tokens.access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.get(
                "https://api.webshopapp.com/en/shop.json",
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            shop_data = response.json()
            
            if "shop" in shop_data:
                shop_info = shop_data["shop"]
                if "id" in shop_info:
                    tokens.shop_id = str(shop_info["id"])
                    self.console.print(f"[green]Retrieved eCom shop ID: {tokens.shop_id}[/green]")
                elif "shop_id" in shop_info:
                    tokens.shop_id = str(shop_info["shop_id"])
                    self.console.print(f"[green]Retrieved eCom shop ID: {tokens.shop_id}[/green]")
                else:
                    self.console.print("[yellow]No shop ID found, but may not be required[/yellow]")
            else:
                self.console.print("[yellow]No shop information found[/yellow]")
                
        except requests.RequestException as e:
            self.console.print(f"[yellow]Warning: Could not retrieve shop information: {str(e)}[/yellow]")
