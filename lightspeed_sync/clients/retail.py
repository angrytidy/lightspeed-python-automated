"""Retail (R-Series) API client."""

from typing import Dict, Any, Optional, List
from .base import BaseClient, NotFoundError


class RetailClient(BaseClient):
    """HTTP client for Lightspeed Retail (R-Series) API."""
    
    @property
    def base_url(self) -> str:
        return "https://api.lightspeedapp.com/API/V3"
    
    @property
    def account_id(self) -> str:
        """Get account ID from tokens."""
        if not self.tokens.account_id:
            raise ValueError("No account ID available in tokens")
        return self.tokens.account_id
    
    async def find_item_by_sku(self, sku: str) -> Optional[Dict[str, Any]]:
        """Find an item by SKU."""
        try:
            # Try different SKU field names that might be used
            sku_fields = ["customSku", "sku", "manufacturerSku", "defaultAlias"]
            
            for field in sku_fields:
                try:
                    response = await self.get(
                        f"Account/{self.account_id}/Item.json",
                        params={field: sku, "limit": 1}
                    )
                    
                    if "Item" in response and response["Item"]:
                        items = response["Item"] if isinstance(response["Item"], list) else [response["Item"]]
                        if items:
                            return items[0]
                except NotFoundError:
                    continue
            
            return None
            
        except Exception:
            return None
    
    async def get_item(self, item_id: str) -> Dict[str, Any]:
        """Get item details by ID."""
        response = await self.get(f"Account/{self.account_id}/Item/{item_id}.json")
        
        if "Item" in response:
            return response["Item"]
        
        raise NotFoundError(f"Item {item_id} not found")
    
    async def update_item(self, item_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update an item."""
        response = await self.put(
            f"Account/{self.account_id}/Item/{item_id}.json",
            json_data=updates
        )
        
        if "Item" in response:
            return response["Item"]
        
        return response
    
    async def update_custom_fields(
        self,
        item_id: str,
        field_mapping: Dict[str, str],
        values: Dict[str, str]
    ) -> Dict[str, Any]:
        """Update custom fields for an item."""
        # Build update payload based on field mapping
        updates = {}
        
        for field_name, field_value in values.items():
            if field_name in field_mapping:
                api_field = field_mapping[field_name]
                updates[api_field] = field_value
        
        if not updates:
            return {"success": True, "message": "No custom fields to update"}
        
        return await self.update_item(item_id, updates)
    
    async def update_weight(self, item_id: str, weight: float) -> Dict[str, Any]:
        """Update item weight."""
        updates = {"weight": weight}
        return await self.update_item(item_id, updates)
    
    async def search_items(
        self,
        params: Optional[Dict[str, Any]] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Search for items with given parameters."""
        search_params = {"limit": limit}
        if params:
            search_params.update(params)
        
        response = await self.get(f"Account/{self.account_id}/Item.json", params=search_params)
        
        if "Item" in response:
            items = response["Item"]
            return items if isinstance(items, list) else [items]
        
        return []
    
    async def get_custom_field_info(self) -> Dict[str, str]:
        """Discover custom field mappings by inspecting an item."""
        try:
            # Get a sample item to inspect custom field structure
            items = await self.search_items(limit=1)
            
            if not items:
                return {}
            
            item = items[0]
            custom_field_mapping = {}
            
            # Look for custom fields in the item structure
            for key, value in item.items():
                if key.startswith("customField") and isinstance(value, str):
                    # Try to match common field names
                    value_lower = value.lower()
                    if "title" in value_lower and "short" in value_lower:
                        custom_field_mapping["Title Short"] = key
                    elif "meta" in value_lower and "title" in value_lower:
                        custom_field_mapping["Meta Title"] = key
            
            return custom_field_mapping
            
        except Exception:
            return {}
