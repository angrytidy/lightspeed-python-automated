"""eCom images updater."""

import re
from typing import List, Dict, Any, Optional, Literal
from rich.console import Console

from ..config import ProductMatch, UpdateResult, AuthTokens
from ..clients import EcomClient, APIError


class EcomImagesUpdater:
    """Updates images in Lightspeed eCom."""
    
    def __init__(self, tokens: AuthTokens, console: Optional[Console] = None):
        self.tokens = tokens
        self.console = console or Console()
        
        # URL validation regex
        self.url_pattern = re.compile(r'^https?://.+', re.IGNORECASE)
    
    def validate_image_urls(self, urls: List[str]) -> List[str]:
        """Validate and filter image URLs."""
        valid_urls = []
        
        for url in urls:
            url = url.strip()
            if not url:
                continue
            
            if self.url_pattern.match(url):
                valid_urls.append(url)
            else:
                self.console.print(f"[yellow]Warning: Invalid image URL: {url}[/yellow]")
        
        return valid_urls
    
    async def update_images(
        self,
        match: ProductMatch,
        image_urls: List[str],
        mode: Literal["append", "replace", "skip"] = "append",
        force: bool = False,
        dry_run: bool = False
    ) -> UpdateResult:
        """Update images for a product."""
        result = UpdateResult(
            sku=match.sku,
            service="ecom",
            operation="images",
            success=False
        )
        
        if not match.has_ecom_match:
            result.error = "No eCom product ID found"
            return result
        
        if mode == "skip":
            result.success = True
            result.error = "Images update skipped by mode setting"
            return result
        
        # Validate URLs
        valid_urls = self.validate_image_urls(image_urls)
        
        if not valid_urls:
            result.success = True
            result.error = "No valid image URLs to process"
            return result
        
        if dry_run:
            result.success = True
            result.changes_made = {
                "mode": mode,
                "urls": valid_urls,
                "count": len(valid_urls)
            }
            return result
        
        try:
            async with EcomClient(self.tokens) as client:
                if mode == "replace":
                    # Replace all images
                    image_results = await client.replace_product_images(
                        match.ecom_product_id, valid_urls
                    )
                else:
                    # Append images
                    if not force:
                        # Check if images already exist
                        existing_images = await client.get_product_images(match.ecom_product_id)
                        existing_urls = {img.get("src", "") for img in existing_images}
                        
                        # Filter out URLs that already exist
                        new_urls = [url for url in valid_urls if url not in existing_urls]
                        
                        if not new_urls:
                            result.success = True
                            result.error = "All images already exist"
                            return result
                        
                        valid_urls = new_urls
                    
                    image_results = await client.append_product_images(
                        match.ecom_product_id, valid_urls
                    )
                
                # Count successful uploads
                successful_uploads = sum(1 for r in image_results if "error" not in r)
                failed_uploads = len(image_results) - successful_uploads
                
                result.success = True
                result.changes_made = {
                    "mode": mode,
                    "successful": successful_uploads,
                    "failed": failed_uploads,
                    "total": len(valid_urls)
                }
                
                if failed_uploads > 0:
                    result.error = f"{failed_uploads} image uploads failed"
                
        except APIError as e:
            result.error = f"API error: {str(e)}"
        except Exception as e:
            result.error = f"Unexpected error: {str(e)}"
        
        return result
    
    async def bulk_update_images(
        self,
        updates: List[Dict[str, Any]],
        mode: Literal["append", "replace", "skip"] = "append",
        force: bool = False,
        dry_run: bool = False
    ) -> List[UpdateResult]:
        """Update images for multiple products."""
        results = []
        
        for update_data in updates:
            match = update_data["match"]
            image_urls = update_data.get("image_urls", [])
            
            # Handle comma-separated URLs in a single string
            if isinstance(image_urls, str):
                image_urls = [url.strip() for url in image_urls.split(",") if url.strip()]
            elif not isinstance(image_urls, list):
                image_urls = []
            
            result = await self.update_images(
                match, image_urls, mode, force, dry_run
            )
            results.append(result)
            
            # Log result
            if result.success:
                if result.changes_made and "total" in result.changes_made:
                    changes = result.changes_made
                    if changes.get("successful", 0) > 0:
                        self.console.print(f"[green]✓ {match.sku}: {changes['mode']} {changes['successful']} images[/green]")
                        if changes.get("failed", 0) > 0:
                            self.console.print(f"[yellow]  Warning: {changes['failed']} images failed[/yellow]")
                    else:
                        self.console.print(f"[dim]- {match.sku}: {result.error}[/dim]")
                else:
                    self.console.print(f"[dim]- {match.sku}: {result.error}[/dim]")
            else:
                self.console.print(f"[red]✗ {match.sku}: {result.error}[/red]")
        
        return results
    
    def parse_image_string(self, images_str: str) -> List[str]:
        """Parse comma-separated image URLs from string."""
        if not images_str or not images_str.strip():
            return []
        
        # Split on commas and clean each URL
        urls = []
        for url in images_str.split(","):
            url = url.strip()
            if url:
                urls.append(url)
        
        return urls
