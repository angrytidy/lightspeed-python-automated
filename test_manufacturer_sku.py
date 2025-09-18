#!/usr/bin/env python3
"""
Test script for manufacturer SKU functionality.
This script demonstrates how to use the new manufacturer SKU resolution features.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from lightspeed_sync.config import load_config_from_env
from lightspeed_sync.auth import RetailAuth, EcomAuth, AuthError
from lightspeed_sync.matchers import SKUMatcher
from lightspeed_sync.clients import RetailClient, EcomClient
from rich.console import Console

console = Console()


async def test_manufacturer_sku_resolution():
    """Test the manufacturer SKU resolution functionality."""
    
    console.print("[bold cyan]Manufacturer SKU Resolution Test[/bold cyan]\n")
    
    # Load configuration
    config = load_config_from_env()
    matcher = SKUMatcher(Path(".cache/test_sku_map.json"), console)
    
    # Test SKUs (replace with actual manufacturer SKUs from your system)
    test_skus = [
        "TEST-SKU-001",
        "TEST-SKU-002", 
        "TEST-SKU-003"
    ]
    
    console.print(f"Testing manufacturer SKU resolution for: {test_skus}\n")
    
    # Load authentication tokens
    retail_tokens = None
    ecom_tokens = None
    
    try:
        retail_auth = RetailAuth(
            config.retail.client_id,
            config.retail.client_secret,
            config.credentials_dir
        )
        retail_tokens = await retail_auth.get_valid_tokens()
        console.print("[green]✓ Retail authentication loaded[/green]")
    except AuthError as e:
        console.print(f"[red]Retail authentication failed: {e}[/red]")
        console.print("[yellow]Skipping Retail API tests[/yellow]")
    
    try:
        ecom_auth = EcomAuth(
            config.ecom.client_id,
            config.ecom.client_secret,
            config.credentials_dir
        )
        ecom_tokens = await ecom_auth.get_valid_tokens()
        console.print("[green]✓ eCom authentication loaded[/green]")
    except AuthError as e:
        console.print(f"[red]eCom authentication failed: {e}[/red]")
        console.print("[yellow]Skipping eCom API tests[/yellow]")
    
    if not retail_tokens and not ecom_tokens:
        console.print("[red]No authentication available. Please run 'lightspeed-sync auth' first.[/red]")
        return
    
    # Test manufacturer SKU resolution
    console.print(f"\n[bold]Testing Manufacturer SKU Resolution[/bold]")
    matches = await matcher.resolve_by_manufacturer_sku(
        test_skus, retail_tokens, ecom_tokens
    )
    
    # Display results
    console.print(f"\n[bold]Resolution Results:[/bold]")
    for sku, match in matches.items():
        console.print(f"  SKU: {sku}")
        console.print(f"    Retail Item ID: {match.retail_item_id or 'Not found'}")
        console.print(f"    eCom Product ID: {match.ecom_product_id or 'Not found'}")
        console.print(f"    Has Retail Match: {match.has_retail_match}")
        console.print(f"    Has eCom Match: {match.has_ecom_match}")
        console.print()
    
    # Test duplicate handling
    console.print(f"\n[bold]Testing Duplicate SKU Handling[/bold]")
    duplicate_skus = test_skus + test_skus[:2]  # Add some duplicates
    console.print(f"Testing with duplicates: {duplicate_skus}")
    
    duplicates = matcher.find_duplicate_manufacturer_skus(duplicate_skus)
    if duplicates:
        console.print(f"[yellow]Found duplicate SKUs: {duplicates}[/yellow]")
    
    # Test individual SKU lookup
    if retail_tokens:
        console.print(f"\n[bold]Testing Individual SKU Lookup[/bold]")
        test_sku = test_skus[0]
        
        async with RetailClient(retail_tokens) as retail_client:
            item = await retail_client.find_item_by_manufacturer_sku(test_sku)
            if item:
                console.print(f"[green]Found item for {test_sku}:[/green]")
                console.print(f"  Item ID: {item.get('itemID', 'N/A')}")
                console.print(f"  Description: {item.get('description', 'N/A')}")
                console.print(f"  Manufacturer SKU: {item.get('manufacturerSku', 'N/A')}")
            else:
                console.print(f"[yellow]No item found for manufacturer SKU: {test_sku}[/yellow]")
    
    console.print(f"\n[green]Test completed![/green]")


if __name__ == "__main__":
    try:
        asyncio.run(test_manufacturer_sku_resolution())
    except KeyboardInterrupt:
        console.print("\n[yellow]Test cancelled by user[/yellow]")
    except Exception as e:
        console.print(f"[red]Test failed: {e}[/red]")
        import traceback
        traceback.print_exc()
