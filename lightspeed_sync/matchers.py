"""SKU to API ID resolution with caching."""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import asyncio
from rich.console import Console
from rich.progress import Progress, TaskID

from .config import ProductMatch, AuthTokens
from .clients import RetailClient, EcomClient, NotFoundError


class SKUMatcher:
    """Resolves SKUs to Retail Item IDs and eCom Product IDs with caching."""
    
    def __init__(self, cache_file: Path, console: Optional[Console] = None):
        self.cache_file = cache_file
        self.console = console or Console()
        self.cache: Dict[str, ProductMatch] = {}
        self.cache_dirty = False
        
        # Ensure cache directory exists
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing cache
        self._load_cache()
    
    def _load_cache(self) -> None:
        """Load SKU mappings from cache file."""
        if not self.cache_file.exists():
            return
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            for sku, data in cache_data.items():
                self.cache[sku] = ProductMatch(**data)
            
            self.console.print(f"[green]Loaded {len(self.cache)} SKU mappings from cache[/green]")
            
        except (json.JSONDecodeError, ValueError) as e:
            self.console.print(f"[yellow]Warning: Could not load cache file: {e}[/yellow]")
            self.cache = {}
    
    def _save_cache(self) -> None:
        """Save SKU mappings to cache file."""
        if not self.cache_dirty:
            return
        
        try:
            cache_data = {}
            for sku, match in self.cache.items():
                cache_data[sku] = match.model_dump()
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2)
            
            self.cache_dirty = False
            self.console.print(f"[green]Saved {len(self.cache)} SKU mappings to cache[/green]")
            
        except Exception as e:
            self.console.print(f"[red]Error saving cache: {e}[/red]")
    
    def get_cached_match(self, sku: str) -> Optional[ProductMatch]:
        """Get cached match for SKU if it exists and is recent."""
        if sku not in self.cache:
            return None
        
        match = self.cache[sku]
        
        # Check if cache is stale (older than 24 hours)
        if match.last_updated:
            age_hours = (time.time() - match.last_updated) / 3600
            if age_hours > 24:
                return None
        
        return match
    
    def cache_match(self, match: ProductMatch) -> None:
        """Cache a SKU match."""
        match.last_updated = int(time.time())
        self.cache[match.sku] = match
        self.cache_dirty = True
    
    async def resolve_sku_batch(
        self,
        skus: List[str],
        retail_tokens: Optional[AuthTokens] = None,
        ecom_tokens: Optional[AuthTokens] = None,
        max_concurrent: int = 5
    ) -> Dict[str, ProductMatch]:
        """Resolve multiple SKUs to their API IDs."""
        results = {}
        
        # Check cache first
        uncached_skus = []
        for sku in skus:
            cached = self.get_cached_match(sku)
            if cached:
                results[sku] = cached
            else:
                uncached_skus.append(sku)
        
        if not uncached_skus:
            self.console.print(f"[green]All {len(skus)} SKUs found in cache[/green]")
            return results
        
        self.console.print(f"[yellow]Resolving {len(uncached_skus)} SKUs via APIs...[/yellow]")
        
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(max_concurrent)
        
        # Create progress bar
        with Progress() as progress:
            task = progress.add_task("[cyan]Resolving SKUs...", total=len(uncached_skus))
            
            async def resolve_single_sku(sku: str) -> ProductMatch:
                async with semaphore:
                    match = ProductMatch(sku=sku)
                    
                    # Resolve retail ID
                    if retail_tokens:
                        try:
                            async with RetailClient(retail_tokens) as retail_client:
                                item = await retail_client.find_item_by_sku(sku)
                                if item:
                                    match.retail_item_id = str(item.get("itemID", ""))
                        except Exception as e:
                            self.console.print(f"[yellow]Retail lookup failed for {sku}: {e}[/yellow]")
                    
                    # Resolve eCom ID
                    if ecom_tokens:
                        try:
                            async with EcomClient(ecom_tokens) as ecom_client:
                                product = await ecom_client.find_product_by_sku(sku)
                                if product:
                                    match.ecom_product_id = str(product.get("id", ""))
                        except Exception as e:
                            self.console.print(f"[yellow]eCom lookup failed for {sku}: {e}[/yellow]")
                    
                    # Cache the result
                    self.cache_match(match)
                    progress.advance(task)
                    
                    return match
            
            # Execute all resolutions concurrently
            tasks = [resolve_single_sku(sku) for sku in uncached_skus]
            resolved_matches = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for sku, result in zip(uncached_skus, resolved_matches):
                if isinstance(result, Exception):
                    self.console.print(f"[red]Error resolving {sku}: {result}[/red]")
                    results[sku] = ProductMatch(sku=sku)
                else:
                    results[sku] = result
        
        # Save cache
        self._save_cache()
        
        # Print summary
        retail_matches = sum(1 for m in results.values() if m.has_retail_match)
        ecom_matches = sum(1 for m in results.values() if m.has_ecom_match)
        
        self.console.print(f"[green]SKU Resolution Summary:[/green]")
        self.console.print(f"  Total SKUs: {len(results)}")
        self.console.print(f"  Retail matches: {retail_matches}")
        self.console.print(f"  eCom matches: {ecom_matches}")
        self.console.print(f"  Both services: {sum(1 for m in results.values() if m.has_retail_match and m.has_ecom_match)}")
        
        return results
    
    async def resolve_single_sku(
        self,
        sku: str,
        retail_tokens: Optional[AuthTokens] = None,
        ecom_tokens: Optional[AuthTokens] = None
    ) -> ProductMatch:
        """Resolve a single SKU to its API IDs."""
        results = await self.resolve_sku_batch([sku], retail_tokens, ecom_tokens)
        return results[sku]
    
    def get_unmatched_skus(
        self,
        matches: Dict[str, ProductMatch],
        require_retail: bool = True,
        require_ecom: bool = True
    ) -> List[str]:
        """Get list of SKUs that don't have required matches."""
        unmatched = []
        
        for sku, match in matches.items():
            missing_retail = require_retail and not match.has_retail_match
            missing_ecom = require_ecom and not match.has_ecom_match
            
            if missing_retail or missing_ecom:
                unmatched.append(sku)
        
        return unmatched
    
    def filter_matches(
        self,
        matches: Dict[str, ProductMatch],
        require_retail: bool = False,
        require_ecom: bool = False
    ) -> Dict[str, ProductMatch]:
        """Filter matches to only include those with required service matches."""
        filtered = {}
        
        for sku, match in matches.items():
            has_retail = match.has_retail_match
            has_ecom = match.has_ecom_match
            
            # Include if it has the required matches
            if (not require_retail or has_retail) and (not require_ecom or has_ecom):
                filtered[sku] = match
        
        return filtered
    
    def clear_cache(self) -> None:
        """Clear the entire cache."""
        self.cache = {}
        self.cache_dirty = True
        if self.cache_file.exists():
            self.cache_file.unlink()
        self.console.print("[yellow]Cache cleared[/yellow]")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get statistics about the current cache."""
        total = len(self.cache)
        retail_matches = sum(1 for m in self.cache.values() if m.has_retail_match)
        ecom_matches = sum(1 for m in self.cache.values() if m.has_ecom_match)
        both_matches = sum(1 for m in self.cache.values() if m.has_retail_match and m.has_ecom_match)
        
        return {
            "total": total,
            "retail_matches": retail_matches,
            "ecom_matches": ecom_matches,
            "both_matches": both_matches,
            "retail_only": retail_matches - both_matches,
            "ecom_only": ecom_matches - both_matches,
            "no_matches": total - retail_matches - ecom_matches + both_matches
        }
