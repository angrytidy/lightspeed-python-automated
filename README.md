# Lightspeed OAuth Helper

A simple, reliable OAuth helper and CLI for the Lightspeed Retail API. This tool handles the complete OAuth 2.0 flow including authorization code exchange, token refresh, and authenticated API calls.

## Features

- 🔐 **Complete OAuth 2.0 Flow**: Authorization code → access token → refresh token
- 🌐 **Automatic Browser Flow**: Opens browser and captures callback automatically
- 🔄 **Auto Token Refresh**: Automatically refreshes expired tokens
- 💾 **Secure Token Storage**: Stores tokens locally with proper security
- 🖥️ **Simple CLI**: Easy-to-use command-line interface
- 🔒 **HTTPS Callback Server**: Self-signed certificate for local development
- 📊 **Rich Output**: Beautiful console output with tables and JSON formatting

## Installation

```bash
pip install -e .
```

## Configuration

Create a `.env` file in your project root with your Lightspeed Retail API credentials:

```env
LIGHTSPEED_RETAIL_CLIENT_ID=your_client_id_here
LIGHTSPEED_RETAIL_CLIENT_SECRET=your_client_secret_here
LIGHTSPEED_RETAIL_REDIRECT_URI=https://localhost:8080/callback
LIGHTSPEED_RETAIL_SCOPE=employee:all
```

### Required Environment Variables

- `LIGHTSPEED_RETAIL_CLIENT_ID`: Your Lightspeed Retail API client ID
- `LIGHTSPEED_RETAIL_CLIENT_SECRET`: Your Lightspeed Retail API client secret
- `LIGHTSPEED_RETAIL_REDIRECT_URI`: OAuth redirect URI (must match registered URI)
- `LIGHTSPEED_RETAIL_SCOPE`: OAuth scope (defaults to `employee:all`)

## Usage

### Initialize Authentication

Start the OAuth flow to get your first access token:

```bash
# Automatic flow (opens browser)
lsr-auth init

# Manual flow (paste code manually)
lsr-auth init --manual
```

This will:
1. Open your browser to the Lightspeed authorization page
2. Capture the authorization code via local HTTPS server
3. Exchange the code for access and refresh tokens
4. Store tokens securely in `~/.lightspeed/credentials/retail.json`

### Refresh Tokens

Refresh your access token using the stored refresh token:

```bash
lsr-auth refresh
```

### Make API Calls

Make authenticated API calls to the Lightspeed Retail API:

```bash
# Get account information
lsr-auth call /API/V3/Account.json

# Get items
lsr-auth call /API/V3/Item.json

# Use different HTTP methods
lsr-auth call /API/V3/Item.json --method POST
```

### View Token Information

Check your stored tokens and configuration:

```bash
lsr-auth info
```

### Clear Tokens

Remove all stored tokens:

```bash
lsr-auth clear
```

## API Endpoints

The tool uses the official Lightspeed Retail API endpoints:

- **Authorization**: `https://cloud.lightspeedapp.com/auth/oauth/authorize`
- **Token Exchange**: `https://cloud.lightspeedapp.com/auth/oauth/token`
- **API Base**: `https://api.lightspeedapp.com`

## Token Storage

Tokens are stored securely in:
- **Location**: `~/.lightspeed/credentials/retail.json`
- **Format**: JSON with masked display
- **Security**: Local file permissions only

Example stored token structure:
```json
{
  "access_token": "your_access_token",
  "refresh_token": "your_refresh_token",
  "expires_at": "2025-09-17T12:34:56Z",
  "scope": "employee:all",
  "token_type": "Bearer"
}
```

## Error Handling

The tool handles common OAuth errors gracefully:

- **Invalid credentials**: Clear error messages with setup instructions
- **Expired tokens**: Automatic refresh with fallback to re-authentication
- **Network errors**: Retry logic with helpful error messages
- **State mismatch**: Security validation for OAuth flow

## Development

### Project Structure

```
lightspeed_oauth/
├── __init__.py          # Package initialization
├── cli.py              # Typer CLI interface
├── auth.py             # OAuth flow implementation
├── models.py           # Pydantic data models
├── storage.py          # Token storage and retrieval
└── http.py             # HTTP client with auto-refresh
```

### Dependencies

- **httpx**: Modern HTTP client
- **typer**: CLI framework
- **pydantic**: Data validation
- **rich**: Beautiful console output
- **python-dotenv**: Environment variable loading
- **fastapi**: Local callback server
- **uvicorn**: ASGI server
- **cryptography**: Self-signed certificates

## Security Notes

- Tokens are stored locally with file system permissions
- Self-signed certificates are used for local HTTPS callback
- State parameter validation prevents CSRF attacks
- Tokens are masked in all output except the first/last 4 characters
- Refresh tokens are used to minimize access token exposure

## Troubleshooting

### Common Issues

1. **"Configuration error"**: Check your `.env` file and environment variables
2. **"No valid tokens available"**: Run `lsr-auth init` to authenticate
3. **"Token refresh failed"**: Run `lsr-auth init` to re-authenticate
4. **"State mismatch"**: This is a security feature; try the auth flow again
5. **"Could not open browser"**: Use `lsr-auth init --manual` for manual flow

### Browser Security Warnings

The local HTTPS server uses a self-signed certificate. Your browser will show a security warning. This is normal for local development. Click "Advanced" and "Proceed to localhost" to continue.

## License

MIT License - see LICENSE file for details.