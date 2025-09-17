"""Retail custom fields updater."""

from typing import Dict, Any, Optional, List
from rich.console import Console

from ..config import ProductMatch, UpdateResult, AuthTokens
from ..clients import RetailClient, APIError


class RetailCustomFieldsUpdater:
    """Updates custom fields in Lightspeed Retail."""
    
    def __init__(self, tokens: AuthTokens, console: Optional[Console] = None):
        self.tokens = tokens
        self.console = console or Console()
        self.field_mapping: Dict[str, str] = {}
    
    async def discover_custom_fields(self) -> Dict[str, str]:
        """Discover custom field mappings for the account."""
        async with RetailClient(self.tokens) as client:
            self.field_mapping = await client.get_custom_field_info()
        
        if self.field_mapping:
            self.console.print(f"[green]Custom field mapping discovered: {self.field_mapping}[/green]")
        else:
            self.console.print("[yellow]No custom field mapping found - using default field names[/yellow]")
            # Use common default field names
            self.field_mapping = {
                "Title Short": "customField1",
                "Meta Title": "customField2"
            }
        
        return self.field_mapping
    
    async def update_custom_fields(
        self,
        match: ProductMatch,
        title_short: Optional[str] = None,
        meta_title: Optional[str] = None,
        force: bool = False,
        dry_run: bool = False
    ) -> UpdateResult:
        """Update custom fields for a product."""
        result = UpdateResult(
            sku=match.sku,
            service="retail",
            operation="custom_fields",
            success=False
        )
        
        if not match.has_retail_match:
            result.error = "No retail item ID found"
            return result
        
        # Prepare field values
        field_values = {}
        if title_short is not None:
            field_values["Title Short"] = title_short
        if meta_title is not None:
            field_values["Meta Title"] = meta_title
        
        if not field_values:
            result.success = True
            result.error = "No custom fields to update"
            return result
        
        if dry_run:
            result.success = True
            result.changes_made = field_values
            return result
        
        try:
            async with RetailClient(self.tokens) as client:
                # Get current item to check for changes
                if not force:
                    current_item = await client.get_item(match.retail_item_id)
                    
                    # Check if values are already set
                    changes_needed = {}
                    for field_name, new_value in field_values.items():
                        if field_name in self.field_mapping:
                            api_field = self.field_mapping[field_name]
                            current_value = current_item.get(api_field, "")
                            
                            if current_value != new_value:
                                changes_needed[field_name] = new_value
                    
                    if not changes_needed:
                        result.success = True
                        result.error = "Custom fields already up to date"
                        return result
                    
                    field_values = changes_needed
                
                # Update the item
                await client.update_custom_fields(
                    match.retail_item_id,
                    self.field_mapping,
                    field_values
                )
                
                result.success = True
                result.changes_made = field_values
                
        except APIError as e:
            result.error = f"API error: {str(e)}"
        except Exception as e:
            result.error = f"Unexpected error: {str(e)}"
        
        return result
    
    async def bulk_update_custom_fields(
        self,
        updates: List[Dict[str, Any]],
        force: bool = False,
        dry_run: bool = False
    ) -> List[UpdateResult]:
        """Update custom fields for multiple products."""
        results = []
        
        # Ensure field mapping is discovered
        if not self.field_mapping:
            await self.discover_custom_fields()
        
        for update_data in updates:
            match = update_data["match"]
            title_short = update_data.get("title_short")
            meta_title = update_data.get("meta_title")
            
            result = await self.update_custom_fields(
                match, title_short, meta_title, force, dry_run
            )
            results.append(result)
            
            # Log result
            if result.success:
                if result.changes_made:
                    self.console.print(f"[green]✓ {match.sku}: Updated custom fields {list(result.changes_made.keys())}[/green]")
                else:
                    self.console.print(f"[dim]- {match.sku}: {result.error}[/dim]")
            else:
                self.console.print(f"[red]✗ {match.sku}: {result.error}[/red]")
        
        return results
