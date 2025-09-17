"""eCom descriptions updater."""

from typing import Optional, List, Dict, Any
from rich.console import Console

from ..config import ProductMatch, UpdateResult, AuthTokens
from ..clients import EcomClient, APIError


class EcomDescriptionsUpdater:
    """Updates descriptions in Lightspeed eCom."""
    
    def __init__(self, tokens: AuthTokens, console: Optional[Console] = None):
        self.tokens = tokens
        self.console = console or Console()
    
    async def update_descriptions(
        self,
        match: ProductMatch,
        short_description: Optional[str] = None,
        long_description: Optional[str] = None,
        force: bool = False,
        dry_run: bool = False
    ) -> UpdateResult:
        """Update descriptions for a product."""
        result = UpdateResult(
            sku=match.sku,
            service="ecom",
            operation="descriptions",
            success=False
        )
        
        if not match.has_ecom_match:
            result.error = "No eCom product ID found"
            return result
        
        # Prepare updates
        updates = {}
        if short_description is not None:
            updates["short"] = short_description
        if long_description is not None:
            updates["long"] = long_description
        
        if not updates:
            result.success = True
            result.error = "No descriptions to update"
            return result
        
        if dry_run:
            result.success = True
            result.changes_made = updates
            return result
        
        try:
            async with EcomClient(self.tokens) as client:
                # Get current product to check for changes
                if not force:
                    current_product = await client.get_product(match.ecom_product_id)
                    
                    # Check if values are already set
                    changes_needed = {}
                    
                    if short_description is not None:
                        current_short = current_product.get("description", "")
                        if current_short != short_description:
                            changes_needed["short"] = short_description
                    
                    if long_description is not None:
                        current_long = current_product.get("content", "")
                        if current_long != long_description:
                            changes_needed["long"] = long_description
                    
                    if not changes_needed:
                        result.success = True
                        result.error = "Descriptions already up to date"
                        return result
                    
                    updates = changes_needed
                
                # Update the product
                update_data = {}
                if "short" in updates:
                    update_data["description"] = updates["short"]
                if "long" in updates:
                    update_data["content"] = updates["long"]
                
                await client.update_descriptions(
                    match.ecom_product_id,
                    update_data.get("description"),
                    update_data.get("content")
                )
                
                result.success = True
                result.changes_made = updates
                
        except APIError as e:
            result.error = f"API error: {str(e)}"
        except Exception as e:
            result.error = f"Unexpected error: {str(e)}"
        
        return result
    
    async def bulk_update_descriptions(
        self,
        updates: List[Dict[str, Any]],
        force: bool = False,
        dry_run: bool = False
    ) -> List[UpdateResult]:
        """Update descriptions for multiple products."""
        results = []
        
        for update_data in updates:
            match = update_data["match"]
            short_desc = update_data.get("short_description")
            long_desc = update_data.get("long_description")
            
            result = await self.update_descriptions(
                match, short_desc, long_desc, force, dry_run
            )
            results.append(result)
            
            # Log result
            if result.success:
                if result.changes_made:
                    changed_fields = []
                    if "short" in result.changes_made:
                        changed_fields.append("short description")
                    if "long" in result.changes_made:
                        changed_fields.append("long description")
                    self.console.print(f"[green]✓ {match.sku}: Updated {', '.join(changed_fields)}[/green]")
                else:
                    self.console.print(f"[dim]- {match.sku}: {result.error}[/dim]")
            else:
                self.console.print(f"[red]✗ {match.sku}: {result.error}[/red]")
        
        return results
