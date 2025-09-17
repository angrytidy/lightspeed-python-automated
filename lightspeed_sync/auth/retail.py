"""Retail (R-Series) API authentication."""

import httpx
from typing import Dict

from .base import AuthBase, AuthError
from ..config import AuthTokens


class RetailAuth(AuthBase):
    """Authentication for Lightspeed Retail (R-Series) API."""
    
    @property
    def service_name(self) -> str:
        return "retail"
    
    @property
    def auth_base_url(self) -> str:
        return "https://cloud.lightspeedapp.com/auth/oauth/authorize"
    
    @property
    def token_url(self) -> str:
        return "https://cloud.lightspeedapp.com/auth/oauth/token"
    
    @property
    def scopes(self) -> str:
        # Get scope from config if available
        from ..config import load_config_from_env
        config = load_config_from_env()
        return config.retail.scope
    
    async def _enrich_tokens(self, tokens: AuthTokens, token_data: Dict) -> None:
        """Add account_id to tokens by making a test API call."""
        # The Retail API requires an account ID for all calls
        # We can get this from the /Account endpoint
        
        headers = {
            "Authorization": f"Bearer {tokens.access_token}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                # Get account information
                response = await client.get(
                    "https://api.lightspeedapp.com/API/V3/Account.json",
                    headers=headers
                )
                response.raise_for_status()
                account_data = response.json()
                
                # Extract account ID from response
                if "Account" in account_data:
                    if isinstance(account_data["Account"], list):
                        # Multiple accounts - use first one
                        account_id = str(account_data["Account"][0]["accountID"])
                    else:
                        # Single account
                        account_id = str(account_data["Account"]["accountID"])
                    
                    tokens.account_id = account_id
                    self.console.print(f"[green]Retrieved Retail account ID: {account_id}[/green]")
                else:
                    raise AuthError("Could not retrieve account information")
                    
            except httpx.HTTPStatusError as e:
                raise AuthError(f"Failed to retrieve account information: {e.response.text}")
    
    async def discover_custom_fields(self, tokens: AuthTokens) -> Dict[str, str]:
        """Discover custom field mappings for the account."""
        if not tokens.account_id:
            raise AuthError("No account ID available")
        
        headers = {
            "Authorization": f"Bearer {tokens.access_token}",
            "Content-Type": "application/json"
        }
        
        custom_field_mapping = {}
        
        async with httpx.AsyncClient() as client:
            try:
                # Get a sample item to inspect custom field structure
                response = await client.get(
                    f"https://api.lightspeedapp.com/API/V3/Account/{tokens.account_id}/Item.json",
                    headers=headers,
                    params={"limit": 1}
                )
                response.raise_for_status()
                items_data = response.json()
                
                if "Item" in items_data and items_data["Item"]:
                    item = items_data["Item"][0] if isinstance(items_data["Item"], list) else items_data["Item"]
                    
                    # Look for custom fields in the item structure
                    # Lightspeed typically uses customFieldN format
                    for key, value in item.items():
                        if key.startswith("customField") and isinstance(value, str):
                            # Try to match common field names
                            if "title" in value.lower() and "short" in value.lower():
                                custom_field_mapping["Title Short"] = key
                            elif "meta" in value.lower() and "title" in value.lower():
                                custom_field_mapping["Meta Title"] = key
                
                self.console.print(f"[green]Discovered custom fields: {custom_field_mapping}[/green]")
                return custom_field_mapping
                
            except httpx.HTTPStatusError as e:
                self.console.print(f"[yellow]Warning: Could not discover custom fields: {e.response.text}[/yellow]")
                return {}
    
    def _sync_enrich_tokens(self, tokens, token_data):
        """Synchronous version of token enrichment."""
        import requests
        
        headers = {
            "Authorization": f"Bearer {tokens.access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.get(
                "https://api.lightspeedapp.com/API/V3/Account.json",
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            account_data = response.json()
            
            if "Account" in account_data:
                if isinstance(account_data["Account"], list):
                    account_id = str(account_data["Account"][0]["accountID"])
                else:
                    account_id = str(account_data["Account"]["accountID"])
                
                tokens.account_id = account_id
                self.console.print(f"[green]Retrieved Retail account ID: {account_id}[/green]")
            else:
                raise AuthError("Could not retrieve account information")
                
        except requests.RequestException as e:
            raise AuthError(f"Failed to retrieve account information: {str(e)}")
    
    async def test_connection(self, tokens: AuthTokens) -> bool:
        """Test the API connection with current tokens."""
        if not tokens.account_id:
            return False
        
        headers = {
            "Authorization": f"Bearer {tokens.access_token}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"https://api.lightspeedapp.com/API/V3/Account/{tokens.account_id}.json",
                    headers=headers
                )
                response.raise_for_status()
                return True
            except:
                return False
