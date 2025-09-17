"""eCom (C-Series) API client."""

from typing import Dict, Any, Optional, List
from .base import BaseClient, NotFoundError


class EcomClient(BaseClient):
    """HTTP client for Lightspeed eCom (C-Series) API."""
    
    @property
    def base_url(self) -> str:
        return "https://api.webshopapp.com/en"
    
    async def find_product_by_sku(self, sku: str) -> Optional[Dict[str, Any]]:
        """Find a product by SKU."""
        try:
            # Search for product by SKU
            response = await self.get(
                "products.json",
                params={"sku": sku, "limit": 1}
            )
            
            if "products" in response and response["products"]:
                products = response["products"]
                if isinstance(products, list) and products:
                    return products[0]
                elif isinstance(products, dict):
                    return products
            
            return None
            
        except NotFoundError:
            return None
    
    async def get_product(self, product_id: str) -> Dict[str, Any]:
        """Get product details by ID."""
        response = await self.get(f"products/{product_id}.json")
        
        if "product" in response:
            return response["product"]
        
        raise NotFoundError(f"Product {product_id} not found")
    
    async def update_product(self, product_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update a product."""
        # Wrap updates in product object if not already wrapped
        if "product" not in updates:
            payload = {"product": updates}
        else:
            payload = updates
        
        response = await self.put(f"products/{product_id}.json", json_data=payload)
        
        if "product" in response:
            return response["product"]
        
        return response
    
    async def update_descriptions(
        self,
        product_id: str,
        short_description: Optional[str] = None,
        long_description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update product descriptions."""
        updates = {}
        
        if short_description is not None:
            updates["description"] = short_description
        
        if long_description is not None:
            updates["content"] = long_description
        
        if not updates:
            return {"success": True, "message": "No descriptions to update"}
        
        return await self.update_product(product_id, updates)
    
    async def get_product_images(self, product_id: str) -> List[Dict[str, Any]]:
        """Get all images for a product."""
        try:
            response = await self.get(f"products/{product_id}/images.json")
            
            if "images" in response:
                images = response["images"]
                return images if isinstance(images, list) else [images]
            
            return []
            
        except NotFoundError:
            return []
    
    async def add_product_image(
        self,
        product_id: str,
        image_url: str,
        sort_order: int = 1
    ) -> Dict[str, Any]:
        """Add an image to a product from URL."""
        image_data = {
            "image": {
                "src": image_url,
                "sortOrder": sort_order
            }
        }
        
        response = await self.post(f"products/{product_id}/images.json", json_data=image_data)
        return response
    
    async def update_product_image(
        self,
        product_id: str,
        image_id: str,
        sort_order: int
    ) -> Dict[str, Any]:
        """Update image sort order."""
        image_data = {
            "image": {
                "sortOrder": sort_order
            }
        }
        
        response = await self.put(
            f"products/{product_id}/images/{image_id}.json",
            json_data=image_data
        )
        return response
    
    async def delete_product_image(self, product_id: str, image_id: str) -> Dict[str, Any]:
        """Delete a product image."""
        return await self.delete(f"products/{product_id}/images/{image_id}.json")
    
    async def replace_product_images(
        self,
        product_id: str,
        image_urls: List[str]
    ) -> List[Dict[str, Any]]:
        """Replace all product images with new ones."""
        results = []
        
        # First, get existing images
        existing_images = await self.get_product_images(product_id)
        
        # Delete existing images
        for image in existing_images:
            try:
                await self.delete_product_image(product_id, str(image["id"]))
            except:
                pass  # Continue even if deletion fails
        
        # Add new images
        for i, url in enumerate(image_urls, 1):
            try:
                result = await self.add_product_image(product_id, url, i)
                results.append(result)
            except Exception as e:
                results.append({"error": str(e), "url": url})
        
        return results
    
    async def append_product_images(
        self,
        product_id: str,
        image_urls: List[str]
    ) -> List[Dict[str, Any]]:
        """Append images to existing product images."""
        results = []
        
        # Get existing images to determine starting sort order
        existing_images = await self.get_product_images(product_id)
        start_order = len(existing_images) + 1
        
        # Add new images
        for i, url in enumerate(image_urls):
            try:
                result = await self.add_product_image(product_id, url, start_order + i)
                results.append(result)
            except Exception as e:
                results.append({"error": str(e), "url": url})
        
        return results
    
    async def search_products(
        self,
        params: Optional[Dict[str, Any]] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Search for products with given parameters."""
        search_params = {"limit": limit}
        if params:
            search_params.update(params)
        
        response = await self.get("products.json", params=search_params)
        
        if "products" in response:
            products = response["products"]
            return products if isinstance(products, list) else [products]
        
        return []
