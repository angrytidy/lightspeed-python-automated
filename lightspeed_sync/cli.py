"""Main CLI interface for Lightspeed API sync tool."""

import asyncio
from pathlib import Path
from typing import Optional, List
import typer
from rich.console import Console
from rich.panel import Panel

from .config import Config, load_config_from_env
from .auth import RetailAuth, EcomAuth, AuthError
from .clients import RetailClient, EcomClient
from .matchers import SKUMatcher
from .csv_io import CSVProcessor
from .reporting import Reporter
from .updaters import (
    RetailCustomFieldsUpdater,
    RetailWeightUpdater,
    EcomDescriptionsUpdater,
    EcomImagesUpdater
)

app = typer.Typer(
    name="lightspeed-sync",
    help="Lightspeed Retail (R-Series) + eCom (C-Series) API Updater",
    rich_markup_mode="rich"
)

console = Console()


@app.command()
def sync(
    input_file: Path = typer.Option(..., "--input", help="Path to CSV file from Google Sheets"),
    map_cache: Path = typer.Option(".cache/sku_map.json", "--map-cache", help="SKU mapping cache file"),
    out_dir: Path = typer.Option("./out", "--out-dir", help="Output directory"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview changes without making updates"),
    limit: Optional[int] = typer.Option(None, "--limit", help="Process only first N rows"),
    force: bool = typer.Option(False, "--force", help="Force updates even if values are unchanged"),
    update: str = typer.Option("all", "--update", help="Which services to update (all, ecom, retail)"),
    set_weight: bool = typer.Option(False, "--set-weight", help="Update product weights in Retail"),
    images: str = typer.Option("append", "--images", help="Image update mode (append, replace, skip)"),
    concurrency: int = typer.Option(4, "--concurrency", help="Number of concurrent API requests"),
    use_manufacturer_sku: bool = typer.Option(False, "--use-manufacturer-sku", help="Use manufacturer SKU for Retail API lookup instead of custom SKU"),
    duplicate_strategy: str = typer.Option("first_found", "--duplicate-strategy", help="Strategy for handling duplicate manufacturer SKUs (first_found, skip, error)"),
):
    """Sync product data from CSV to Lightspeed APIs."""
    # Validate choices
    if update not in ["all", "ecom", "retail"]:
        raise typer.BadParameter(f"Invalid update choice: {update}. Must be one of: all, ecom, retail")
    if images not in ["append", "replace", "skip"]:
        raise typer.BadParameter(f"Invalid images choice: {images}. Must be one of: append, replace, skip")
    if duplicate_strategy not in ["first_found", "skip", "error"]:
        raise typer.BadParameter(f"Invalid duplicate strategy: {duplicate_strategy}. Must be one of: first_found, skip, error")
    
    try:
        asyncio.run(_sync_main(
            input_file, map_cache, out_dir, dry_run, limit, force,
            update, set_weight, images, concurrency, use_manufacturer_sku, duplicate_strategy
        ))
    except KeyboardInterrupt:
        console.print("\n[yellow]Sync cancelled by user[/yellow]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Sync failed: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def auth(
    service: str = typer.Option("both", "--service", help="Which service to authenticate (retail, ecom, both)"),
    reauth: bool = typer.Option(False, "--reauth", help="Force re-authentication"),
):
    """Authenticate with Lightspeed APIs."""
    # Validate choices
    if service not in ["retail", "ecom", "both"]:
        raise typer.BadParameter(f"Invalid service choice: {service}. Must be one of: retail, ecom, both")
    
    try:
        asyncio.run(_auth_main(service, reauth))
    except KeyboardInterrupt:
        console.print("\n[yellow]Authentication cancelled by user[/yellow]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Authentication failed: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def cache(
    action: str = typer.Option("info", "--action", help="Cache action to perform (info, clear)"),
    map_cache: Path = typer.Option(".cache/sku_map.json", "--map-cache", help="SKU mapping cache file"),
):
    """Manage SKU mapping cache."""
    # Validate choices
    if action not in ["info", "clear"]:
        raise typer.BadParameter(f"Invalid action choice: {action}. Must be one of: info, clear")
    
    matcher = SKUMatcher(map_cache, console)
    
    if action == "info":
        stats = matcher.get_cache_stats()
        
        info_panel = Panel.fit(
            f"[bold]Cache Statistics[/bold]\n\n"
            f"Total SKUs: {stats['total']}\n"
            f"Retail matches: {stats['retail_matches']}\n"
            f"eCom matches: {stats['ecom_matches']}\n"
            f"Both services: {stats['both_matches']}\n"
            f"Retail only: {stats['retail_only']}\n"
            f"eCom only: {stats['ecom_only']}\n"
            f"No matches: {stats['no_matches']}\n\n"
            f"Cache file: {map_cache}",
            title="SKU Cache Info",
            border_style="blue"
        )
        console.print(info_panel)
        
    elif action == "clear":
        matcher.clear_cache()
        console.print("[green]Cache cleared successfully[/green]")


@app.command()
def test_manufacturer_sku(
    sku: str = typer.Option(..., "--sku", help="Manufacturer SKU to test"),
    map_cache: Path = typer.Option(".cache/sku_map.json", "--map-cache", help="SKU mapping cache file"),
):
    """Test manufacturer SKU resolution for a single SKU."""
    try:
        asyncio.run(_test_manufacturer_sku_main(sku, map_cache))
    except KeyboardInterrupt:
        console.print("\n[yellow]Test cancelled by user[/yellow]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Test failed: {e}[/red]")
        raise typer.Exit(1)


async def _auth_main(service: str, reauth: bool) -> None:
    """Main authentication logic."""
    config = load_config_from_env()
    
    console.print("[bold cyan]Lightspeed API Authentication[/bold cyan]\n")
    
    if service in ["retail", "both"]:
        console.print("[bold]Retail (R-Series) Authentication[/bold]")
        
        if not config.retail.client_id or not config.retail.client_secret:
            console.print("[red]Error: LIGHTSPEED_RETAIL_CLIENT_ID and LIGHTSPEED_RETAIL_CLIENT_SECRET environment variables required[/red]")
            return
        
        retail_auth = RetailAuth(
            config.retail.client_id,
            config.retail.client_secret,
            config.credentials_dir
        )
        
        if reauth or not retail_auth.load_tokens():
            retail_auth.start_interactive_auth()
        else:
            # Test existing tokens
            tokens = await retail_auth.get_valid_tokens()
            if await retail_auth.test_connection(tokens):
                console.print("[green]✓ Retail authentication valid[/green]")
            else:
                console.print("[yellow]Retail tokens invalid, re-authenticating...[/yellow]")
                retail_auth.start_interactive_auth()
    
    if service in ["ecom", "both"]:
        console.print("\n[bold]eCom (C-Series) Authentication[/bold]")
        
        if not config.ecom.client_id or not config.ecom.client_secret:
            console.print("[red]Error: LIGHTSPEED_ECOM_CLIENT_ID and LIGHTSPEED_ECOM_CLIENT_SECRET environment variables required[/red]")
            return
        
        ecom_auth = EcomAuth(
            config.ecom.client_id,
            config.ecom.client_secret,
            config.credentials_dir
        )
        
        if reauth or not ecom_auth.load_tokens():
            ecom_auth.start_interactive_auth()
        else:
            # Test existing tokens
            tokens = await ecom_auth.get_valid_tokens()
            if await ecom_auth.test_connection(tokens):
                console.print("[green]✓ eCom authentication valid[/green]")
            else:
                console.print("[yellow]eCom tokens invalid, re-authenticating...[/yellow]")
                ecom_auth.start_interactive_auth()
    
    console.print("\n[green]Authentication complete![/green]")


async def _test_manufacturer_sku_main(sku: str, map_cache: Path) -> None:
    """Test manufacturer SKU resolution for a single SKU."""
    config = load_config_from_env()
    matcher = SKUMatcher(map_cache, console)
    
    console.print(f"[bold cyan]Testing Manufacturer SKU Resolution[/bold cyan]")
    console.print(f"Testing SKU: {sku}\n")
    
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
        return
    
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
        return
    
    # Test manufacturer SKU resolution
    console.print(f"\n[bold]Testing Manufacturer SKU Resolution[/bold]")
    matches = await matcher.resolve_by_manufacturer_sku(
        [sku], retail_tokens, ecom_tokens
    )
    
    match = matches.get(sku)
    if match:
        console.print(f"[green]Resolution Results:[/green]")
        console.print(f"  SKU: {sku}")
        console.print(f"  Retail Item ID: {match.retail_item_id or 'Not found'}")
        console.print(f"  eCom Product ID: {match.ecom_product_id or 'Not found'}")
        console.print(f"  Has Retail Match: {match.has_retail_match}")
        console.print(f"  Has eCom Match: {match.has_ecom_match}")
    else:
        console.print(f"[red]No match found for SKU: {sku}[/red]")


async def _sync_main(
    input_file: Path,
    map_cache: Path,
    out_dir: Path,
    dry_run: bool,
    limit: Optional[int],
    force: bool,
    update: str,
    set_weight: bool,
    images: str,
    concurrency: int,
    use_manufacturer_sku: bool,
    duplicate_strategy: str,
) -> None:
    """Main sync logic."""
    
    # Initialize components
    config = load_config_from_env()
    config.concurrency = concurrency
    config.dry_run = dry_run
    config.force_update = force
    config.output_dir = out_dir
    
    csv_processor = CSVProcessor(console)
    reporter = Reporter(console)
    matcher = SKUMatcher(map_cache, console)
    
    console.print("[bold cyan]Lightspeed API Sync Tool[/bold cyan]\n")
    
    # Validate input file
    if not input_file.exists():
        raise typer.BadParameter(f"Input file not found: {input_file}")
    
    # Load and validate CSV
    console.print("[bold]Step 1: Loading CSV Data[/bold]")
    df = csv_processor.read_csv(input_file, limit)
    csv_processor.validate_required_columns(df, ["SKU"])
    df_clean = csv_processor.normalize_data(df)
    
    # Extract product data
    products = csv_processor.extract_product_data(df_clean)
    column_info = csv_processor.get_column_info(df_clean)
    
    reporter.print_pre_processing_info(len(products), column_info)
    
    if not products:
        console.print("[red]No valid products found in CSV[/red]")
        return
    
    # Load authentication tokens
    console.print("\n[bold]Step 2: Loading Authentication[/bold]")
    retail_tokens = None
    ecom_tokens = None
    
    if update in ["retail", "all"]:
        retail_auth = RetailAuth(
            config.retail.client_id,
            config.retail.client_secret,
            config.credentials_dir
        )
        try:
            retail_tokens = await retail_auth.get_valid_tokens()
            console.print("[green]✓ Retail authentication loaded[/green]")
        except AuthError as e:
            console.print(f"[red]Retail authentication failed: {e}[/red]")
            if update == "retail":
                return
    
    if update in ["ecom", "all"]:
        ecom_auth = EcomAuth(
            config.ecom.client_id,
            config.ecom.client_secret,
            config.credentials_dir
        )
        try:
            ecom_tokens = await ecom_auth.get_valid_tokens()
            console.print("[green]✓ eCom authentication loaded[/green]")
        except AuthError as e:
            console.print(f"[red]eCom authentication failed: {e}[/red]")
            if update == "ecom":
                return
    
    # Resolve SKUs to API IDs
    console.print("\n[bold]Step 3: Resolving SKUs[/bold]")
    skus = [p["sku"] for p in products]
    
    if use_manufacturer_sku:
        console.print("[yellow]Using manufacturer SKU resolution for Retail API[/yellow]")
        matches = await matcher.resolve_manufacturer_sku_with_duplicate_handling(
            skus, retail_tokens, ecom_tokens, concurrency, duplicate_strategy
        )
    else:
        matches = await matcher.resolve_sku_batch(
            skus, retail_tokens, ecom_tokens, concurrency
        )
    
    reporter.print_sku_resolution_summary(matches, len(skus))
    
    # Filter products based on available matches
    valid_products = []
    for product in products:
        match = matches.get(product["sku"])
        if not match:
            continue
        
        # Check if we have the required service matches
        has_required_match = False
        if update == "retail" and match.has_retail_match:
            has_required_match = True
        elif update == "ecom" and match.has_ecom_match:
            has_required_match = True
        elif update == "all" and (match.has_retail_match or match.has_ecom_match):
            has_required_match = True
        
        if has_required_match:
            product["match"] = match
            valid_products.append(product)
    
    console.print(f"[green]Found {len(valid_products)} products with valid matches[/green]")
    
    if not valid_products:
        console.print("[yellow]No products can be updated with current matches[/yellow]")
        reporter.generate_markdown_report(out_dir / "sync_report.md", dry_run)
        return
    
    reporter.update_processed_count(len(valid_products))
    reporter.update_skipped_count(len(products) - len(valid_products))
    
    # Perform updates
    console.print(f"\n[bold]Step 4: {'Previewing' if dry_run else 'Performing'} Updates[/bold]")
    
    all_results = []
    
    # Retail updates
    if update in ["retail", "all"] and retail_tokens:
        console.print("[cyan]Updating Retail (R-Series)...[/cyan]")
        
        # Custom fields
        custom_fields_updater = RetailCustomFieldsUpdater(retail_tokens, console)
        await custom_fields_updater.discover_custom_fields()
        
        custom_field_updates = []
        for product in valid_products:
            if product["match"].has_retail_match:
                custom_field_updates.append({
                    "match": product["match"],
                    "title_short": product["title_short"],
                    "meta_title": product["meta_title"]
                })
        
        if custom_field_updates:
            results = await custom_fields_updater.bulk_update_custom_fields(
                custom_field_updates, force, dry_run
            )
            all_results.extend(results)
        
        # Weight updates
        if set_weight:
            weight_updater = RetailWeightUpdater(retail_tokens, console)
            
            weight_updates = []
            for product in valid_products:
                if product["match"].has_retail_match and product["weight_value"]:
                    weight_updates.append({
                        "match": product["match"],
                        "weight": product["weight_value"]
                    })
            
            if weight_updates:
                results = await weight_updater.bulk_update_weights(
                    weight_updates, force, dry_run
                )
                all_results.extend(results)
    
    # eCom updates
    if update in ["ecom", "all"] and ecom_tokens:
        console.print("[cyan]Updating eCom (C-Series)...[/cyan]")
        
        # Descriptions
        descriptions_updater = EcomDescriptionsUpdater(ecom_tokens, console)
        
        description_updates = []
        for product in valid_products:
            if product["match"].has_ecom_match:
                description_updates.append({
                    "match": product["match"],
                    "short_description": product["short_description"],
                    "long_description": product["long_description"]
                })
        
        if description_updates:
            results = await descriptions_updater.bulk_update_descriptions(
                description_updates, force, dry_run
            )
            all_results.extend(results)
        
        # Images
        if images != "skip":
            images_updater = EcomImagesUpdater(ecom_tokens, console)
            
            image_updates = []
            for product in valid_products:
                if product["match"].has_ecom_match and product["images"]:
                    image_updates.append({
                        "match": product["match"],
                        "image_urls": product["images"]
                    })
            
            if image_updates:
                results = await images_updater.bulk_update_images(
                    image_updates, images, force, dry_run
                )
                all_results.extend(results)
    
    # Process results
    for result in all_results:
        reporter.add_result(result)
    
    # Generate outputs
    console.print(f"\n[bold]Step 5: Generating Reports[/bold]")
    
    # Write failures CSV
    if reporter.failures:
        csv_processor.write_failures_csv(reporter.failures, out_dir / "failures.csv")
    
    # Generate report
    reporter.generate_markdown_report(out_dir / "sync_report.md", dry_run)
    
    # Print final summary
    console.print(f"\n{'='*60}")
    reporter.print_summary(dry_run)
    console.print(f"{'='*60}")


if __name__ == "__main__":
    app()
