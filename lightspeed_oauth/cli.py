"""Command-line interface for Lightspeed OAuth helper."""

import os
import sys
import webbrowser
from pathlib import Path
from typing import Optional
import asyncio

import typer
from rich.console import Console
from rich.table import Table
from rich.json import JSON
from rich.panel import Panel
from rich import print as rprint
from dotenv import load_dotenv

from .models import OAuthConfig
from .storage import TokenStorage
from .auth import OAuthClient
from .http import LightspeedAPIClient


# Load environment variables
load_dotenv()

app = typer.Typer(
    name="lsr-auth",
    help="Lightspeed Retail OAuth helper and API client",
    no_args_is_help=True
)

console = Console()


def load_config() -> OAuthConfig:
    """Load OAuth configuration from environment variables."""
    try:
        return OAuthConfig()
    except Exception as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        console.print("\n[yellow]Please set the following environment variables:[/yellow]")
        console.print("  LIGHTSPEED_RETAIL_CLIENT_ID")
        console.print("  LIGHTSPEED_RETAIL_CLIENT_SECRET")
        console.print("  LIGHTSPEED_RETAIL_REDIRECT_URI")
        console.print("  LIGHTSPEED_RETAIL_SCOPE (optional, defaults to 'employee:all')")
        console.print("\nYou can also create a .env file with these variables.")
        raise typer.Exit(1)


@app.command()
def init(
    manual: bool = typer.Option(
        False, 
        "--manual", 
        help="Use manual code entry instead of local server"
    )
):
    """Initialize OAuth authentication and get tokens."""
    config = load_config()
    storage = TokenStorage()
    oauth_client = OAuthClient(config)
    
    try:
        # Generate state for security
        state = oauth_client.generate_state()
        
        if manual:
            # Manual flow
            console.print("[blue]Starting manual authentication flow...[/blue]")
            code, error = oauth_client.manual_auth_flow(state)
            
            if error:
                console.print(f"[red]Error: {error}[/red]")
                raise typer.Exit(1)
        else:
            # Automatic flow with local server
            console.print("[blue]Starting automatic authentication flow...[/blue]")
            console.print("Opening browser for authentication...")
            
            # Open browser
            auth_url = oauth_client.build_authorize_url(state)
            try:
                webbrowser.open(auth_url)
            except Exception:
                console.print(f"[yellow]Could not open browser automatically.[/yellow]")
                console.print(f"Please visit: {auth_url}")
            
            # Start callback server
            console.print("Starting local callback server...")
            code, error = asyncio.run(oauth_client.start_callback_server(state))
            
            if error:
                console.print(f"[red]Error: {error}[/red]")
                raise typer.Exit(1)
        
        if not code:
            console.print("[red]No authorization code received[/red]")
            raise typer.Exit(1)
        
        # Exchange code for tokens
        console.print("Exchanging authorization code for tokens...")
        tokens = oauth_client.exchange_code_for_tokens(code)
        
        # Save tokens
        storage.save_tokens(tokens)
        
        # Display success message
        console.print("\n[green]✓ Authentication successful![/green]")
        
        # Show token info
        info_table = Table(title="Token Information")
        info_table.add_column("Property", style="cyan")
        info_table.add_column("Value", style="white")
        
        info_table.add_row("Access Token", tokens.get_masked_access_token())
        info_table.add_row("Refresh Token", tokens.get_masked_refresh_token())
        info_table.add_row("Expires At", tokens.expires_at.strftime("%Y-%m-%d %H:%M:%S UTC"))
        info_table.add_row("Scope", tokens.scope)
        info_table.add_row("Storage Path", str(storage.credentials_file))
        
        console.print(info_table)
        
    except Exception as e:
        console.print(f"[red]Authentication failed: {e}[/red]")
        raise typer.Exit(1)
    finally:
        oauth_client.close()


@app.command()
def refresh():
    """Refresh the access token using the stored refresh token."""
    config = load_config()
    storage = TokenStorage()
    oauth_client = OAuthClient(config)
    
    try:
        # Load current tokens
        tokens = storage.load_tokens()
        if not tokens:
            console.print("[red]No tokens found. Run 'lsr-auth init' first.[/red]")
            raise typer.Exit(1)
        
        if not tokens.refresh_token:
            console.print("[red]No refresh token available. Run 'lsr-auth init' to re-authenticate.[/red]")
            raise typer.Exit(1)
        
        console.print("Refreshing access token...")
        new_tokens = oauth_client.refresh_tokens(tokens.refresh_token)
        
        # Save new tokens
        storage.save_tokens(new_tokens)
        
        console.print("[green]✓ Token refresh successful![/green]")
        
        # Show updated token info
        info_table = Table(title="Updated Token Information")
        info_table.add_column("Property", style="cyan")
        info_table.add_column("Value", style="white")
        
        info_table.add_row("Access Token", new_tokens.get_masked_access_token())
        info_table.add_row("Refresh Token", new_tokens.get_masked_refresh_token())
        info_table.add_row("Expires At", new_tokens.expires_at.strftime("%Y-%m-%d %H:%M:%S UTC"))
        info_table.add_row("Scope", new_tokens.scope)
        
        console.print(info_table)
        
    except Exception as e:
        console.print(f"[red]Token refresh failed: {e}[/red]")
        console.print("[yellow]You may need to run 'lsr-auth init' to re-authenticate.[/yellow]")
        raise typer.Exit(1)
    finally:
        oauth_client.close()


@app.command()
def call(
    path: str = typer.Argument(..., help="API endpoint path (e.g., /API/V3/Account.json)"),
    method: str = typer.Option("GET", "--method", "-m", help="HTTP method"),
    pretty: bool = typer.Option(True, "--pretty/--no-pretty", help="Pretty print JSON response")
):
    """Make an authenticated API call to Lightspeed."""
    config = load_config()
    storage = TokenStorage()
    api_client = LightspeedAPIClient(config, storage)
    
    try:
        # Check if tokens exist
        if not storage.has_tokens():
            console.print("[red]No tokens found. Run 'lsr-auth init' first.[/red]")
            raise typer.Exit(1)
        
        console.print(f"[blue]Making {method} request to {path}...[/blue]")
        
        # Make the API call
        if method.upper() == "GET":
            response = api_client.get(path)
        elif method.upper() == "POST":
            response = api_client.post(path)
        elif method.upper() == "PUT":
            response = api_client.put(path)
        elif method.upper() == "DELETE":
            response = api_client.delete(path)
        else:
            console.print(f"[red]Unsupported HTTP method: {method}[/red]")
            raise typer.Exit(1)
        
        # Display response
        console.print(f"[green]✓ Request successful![/green]")
        
        if pretty and isinstance(response, dict):
            console.print(JSON.from_data(response, indent=2))
        else:
            console.print(response)
            
    except Exception as e:
        console.print(f"[red]API call failed: {e}[/red]")
        raise typer.Exit(1)
    finally:
        api_client.close()


@app.command()
def info():
    """Show information about stored tokens and configuration."""
    config = load_config()
    storage = TokenStorage()
    
    # Show configuration
    config_table = Table(title="Configuration")
    config_table.add_column("Setting", style="cyan")
    config_table.add_column("Value", style="white")
    
    config_table.add_row("Client ID", config.client_id[:8] + "..." if len(config.client_id) > 8 else config.client_id)
    config_table.add_row("Redirect URI", config.redirect_uri)
    config_table.add_row("Scope", config.scope)
    
    console.print(config_table)
    console.print()
    
    # Show token information
    info = storage.get_storage_info()
    
    token_table = Table(title="Token Storage")
    token_table.add_column("Property", style="cyan")
    token_table.add_column("Value", style="white")
    
    token_table.add_row("Storage Path", info["storage_path"])
    token_table.add_row("Has Tokens", "Yes" if info["has_tokens"] else "No")
    
    if info["has_tokens"]:
        token_table.add_row("Access Token", info["access_token"])
        token_table.add_row("Refresh Token", info["refresh_token"])
        token_table.add_row("Expires At", info["expires_at"])
        token_table.add_row("Is Expired", "Yes" if info["is_expired"] else "No")
        token_table.add_row("Scope", info["scope"])
    
    console.print(token_table)


@app.command()
def clear():
    """Clear stored tokens."""
    storage = TokenStorage()
    
    if not storage.has_tokens():
        console.print("[yellow]No tokens to clear.[/yellow]")
        return
    
    if typer.confirm("Are you sure you want to clear all stored tokens?"):
        storage.clear_tokens()
        console.print("[green]✓ Tokens cleared successfully![/green]")
    else:
        console.print("Operation cancelled.")


if __name__ == "__main__":
    app()
