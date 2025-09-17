"""Retail weight updater."""

from typing import Optional, List, Dict, Any
from rich.console import Console

from ..config import ProductMatch, UpdateResult, AuthTokens
from ..clients import RetailClient, APIError


class RetailWeightUpdater:
    """Updates weight in Lightspeed Retail."""
    
    def __init__(self, tokens: AuthTokens, console: Optional[Console] = None):
        self.tokens = tokens
        self.console = console or Console()
    
    async def update_weight(
        self,
        match: ProductMatch,
        weight: float,
        force: bool = False,
        dry_run: bool = False
    ) -> UpdateResult:
        """Update weight for a product."""
        result = UpdateResult(
            sku=match.sku,
            service="retail",
            operation="weight",
            success=False
        )
        
        if not match.has_retail_match:
            result.error = "No retail item ID found"
            return result
        
        if weight < 0:
            result.error = "Weight cannot be negative"
            return result
        
        if dry_run:
            result.success = True
            result.changes_made = {"weight": str(weight)}
            return result
        
        try:
            async with RetailClient(self.tokens) as client:
                # Get current item to check for changes
                if not force:
                    current_item = await client.get_item(match.retail_item_id)
                    current_weight = current_item.get("weight", 0)
                    
                    # Convert to float for comparison
                    try:
                        current_weight = float(current_weight)
                    except (ValueError, TypeError):
                        current_weight = 0.0
                    
                    # Check if weight is already set (with small tolerance for float comparison)
                    if abs(current_weight - weight) < 0.001:
                        result.success = True
                        result.error = "Weight already up to date"
                        return result
                
                # Update the weight
                await client.update_weight(match.retail_item_id, weight)
                
                result.success = True
                result.changes_made = {"weight": str(weight)}
                
        except APIError as e:
            result.error = f"API error: {str(e)}"
        except Exception as e:
            result.error = f"Unexpected error: {str(e)}"
        
        return result
    
    async def bulk_update_weights(
        self,
        updates: List[Dict[str, Any]],
        force: bool = False,
        dry_run: bool = False
    ) -> List[UpdateResult]:
        """Update weights for multiple products."""
        results = []
        
        for update_data in updates:
            match = update_data["match"]
            weight = update_data.get("weight")
            
            if weight is None:
                result = UpdateResult(
                    sku=match.sku,
                    service="retail",
                    operation="weight",
                    success=True,
                    error="No weight specified"
                )
                results.append(result)
                continue
            
            try:
                weight_value = float(weight)
            except (ValueError, TypeError):
                result = UpdateResult(
                    sku=match.sku,
                    service="retail",
                    operation="weight",
                    success=False,
                    error=f"Invalid weight value: {weight}"
                )
                results.append(result)
                continue
            
            result = await self.update_weight(match, weight_value, force, dry_run)
            results.append(result)
            
            # Log result
            if result.success:
                if result.changes_made:
                    self.console.print(f"[green]✓ {match.sku}: Updated weight to {weight_value}[/green]")
                else:
                    self.console.print(f"[dim]- {match.sku}: {result.error}[/dim]")
            else:
                self.console.print(f"[red]✗ {match.sku}: {result.error}[/red]")
        
        return results
