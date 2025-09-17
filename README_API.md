# Lightspeed API Sync Tool

A robust CLI tool that reads Google-Sheet-exported CSV files and updates existing products via Lightspeed APIs:

- **Retail (R-Series) API**: Updates Custom Fields and Weight
- **eCom (C-Series) API**: Updates Web Store Descriptions and Product Images

**🔒 Safe Operation**: Only updates existing products matched by SKU - never creates new products.

## Features

- ✅ **Dual API Integration**: Works with both Retail and eCom APIs simultaneously
- 🔐 **OAuth 2.0 Authentication**: Secure token-based authentication with automatic refresh
- 💾 **Intelligent Caching**: SKU-to-ID mapping cache to avoid repeated API lookups
- 🚀 **Concurrent Processing**: Configurable concurrency with rate limiting and backoff
- 🛡️ **Error Resilience**: Comprehensive error handling with detailed failure reporting
- 📊 **Rich Reporting**: Console output with progress bars and detailed markdown reports
- 🧪 **Dry Run Mode**: Preview changes before making actual updates
- ⚡ **Idempotent**: Safe to re-run - skips unchanged values unless forced

## Quick Start

### 1. Installation

```bash
# Clone or download the project
cd lightspeed-sync

# Install dependencies
pip install -e .

# Or install from requirements
pip install -r requirements.txt
```

### 2. OAuth App Setup

You need to create OAuth applications in both Lightspeed services:

#### **Retail (R-Series) OAuth Setup**

1. **Login to Lightspeed Retail Back Office**
   - Go to your Retail Back Office (e.g., `https://cloud.lightspeedapp.com`)
   - Navigate to **Settings** → **API** → **OAuth Apps**

2. **Create New OAuth App**
   - Click **"Create App"**
   - Fill in details:
     - **App Name**: `Product Sync Tool`
     - **Description**: `CSV to API product updater`
     - **Redirect URI**: `http://localhost:8080/callback`
     - **Scopes**: Select `employee:all` (or minimum required for product access)

3. **Save Credentials**
   - Copy the **Client ID** and **Client Secret**
   - Set environment variables:
     ```bash
     export LIGHTSPEED_RETAIL_CLIENT_ID="your_retail_client_id"
     export LIGHTSPEED_RETAIL_CLIENT_SECRET="your_retail_client_secret"
     ```

#### **eCom (C-Series) OAuth Setup**

1. **Login to Lightspeed eCom Admin**
   - Go to your eCom admin panel
   - Navigate to **Apps** → **Private Apps** or **API**

2. **Create New Private App**
   - Click **"Create Private App"**
   - Fill in details:
     - **App Name**: `Product Sync Tool`
     - **Redirect URI**: `http://localhost:8080/callback`
     - **Permissions**: Enable `products` (read/write)

3. **Save Credentials**
   - Copy the **Client ID** and **Client Secret**
   - Set environment variables:
     ```bash
     export LIGHTSPEED_ECOM_CLIENT_ID="your_ecom_client_id"
     export LIGHTSPEED_ECOM_CLIENT_SECRET="your_ecom_client_secret"
     ```

### 3. Authentication

```bash
# Authenticate with both services
lightspeed-sync auth --service both

# Or authenticate individually
lightspeed-sync auth --service retail
lightspeed-sync auth --service ecom

# Force re-authentication
lightspeed-sync auth --service both --reauth
```

The tool will:
1. Open your browser for OAuth authorization
2. Save tokens securely in `~/.lightspeed/credentials/`
3. Test the connection to confirm authentication

### 4. Prepare Your CSV

Export your Google Sheet with these columns:

| Column | Required | Description |
|--------|----------|-------------|
| `SKU` | ✅ | Product identifier for matching |
| `US_Description_Short` | ❌ | Short product description (eCom) |
| `US_Description_Long` | ❌ | Long description with HTML (eCom) |
| `US_Title_Short` | ❌ | Custom field: Title Short (Retail) |
| `US_Meta_Title` | ❌ | Custom field: Meta Title (Retail) |
| `Images` | ❌ | Image URLs, comma-separated (eCom) |
| `Weight_Value` | ❌ | Numeric weight value (Retail) |

### 5. Run Sync

```bash
# Test with dry run first
lightspeed-sync sync --input products.csv --dry-run --limit 10

# Sync all data
lightspeed-sync sync --input products.csv

# Sync only eCom (descriptions and images)
lightspeed-sync sync --input products.csv --update ecom

# Sync only Retail with weight updates
lightspeed-sync sync --input products.csv --update retail --set-weight

# Replace all product images instead of appending
lightspeed-sync sync --input products.csv --images replace
```

## Command Reference

### Main Sync Command

```bash
lightspeed-sync sync [OPTIONS]
```

**Options:**
- `--input PATH` - CSV file path (required)
- `--map-cache PATH` - SKU mapping cache file (default: `.cache/sku_map.json`)
- `--out-dir PATH` - Output directory (default: `./out`)
- `--dry-run` - Preview changes without making updates
- `--limit N` - Process only first N rows
- `--force` - Force updates even if values are unchanged
- `--update {all,ecom,retail}` - Which services to update (default: all)
- `--set-weight` - Update product weights in Retail
- `--images {append,replace,skip}` - Image update mode (default: append)
- `--concurrency N` - Concurrent API requests (default: 4)

### Authentication Command

```bash
lightspeed-sync auth [OPTIONS]
```

**Options:**
- `--service {retail,ecom,both}` - Which service to authenticate (default: both)
- `--reauth` - Force re-authentication

### Cache Management

```bash
lightspeed-sync cache [OPTIONS]
```

**Options:**
- `--action {info,clear}` - Cache action (default: info)
- `--map-cache PATH` - Cache file path

## Data Processing Details

### SKU Resolution

The tool maintains a local cache (`.cache/sku_map.json`) that maps SKUs to:
- **Retail Item ID** - For custom fields and weight updates
- **eCom Product ID** - For descriptions and images

**Cache Benefits:**
- Avoids repeated API lookups on re-runs
- Handles large product catalogs efficiently
- 24-hour cache expiry for data freshness

### Update Operations

#### **Retail (R-Series) Updates**
1. **Custom Fields Discovery**: Automatically discovers custom field mappings
2. **Custom Fields Update**: Maps `US_Title_Short` → "Title Short", `US_Meta_Title` → "Meta Title"
3. **Weight Update**: Updates product weight from `Weight_Value` (optional with `--set-weight`)

#### **eCom (C-Series) Updates**
1. **Descriptions**: Updates short and long descriptions (HTML preserved)
2. **Images**: 
   - **Append Mode**: Adds new images, keeps existing ones
   - **Replace Mode**: Removes all images, adds new ones
   - **Skip Mode**: Doesn't touch images

### Error Handling

- **Rate Limiting**: Automatic backoff and retry for 429 responses
- **Authentication**: Auto-refresh expired tokens
- **Per-Row Errors**: Individual failures don't stop the entire process
- **Detailed Logging**: All errors captured in `failures.csv`

## Output Files

After running, check the `./out` directory:

- **`sync_report.md`** - Detailed processing report with statistics
- **`failures.csv`** - CSV of failed operations for easy review
- **`.cache/sku_map.json`** - SKU to ID mappings (cached for performance)

## Advanced Usage

### Environment Configuration

```bash
# API Credentials (required)
export LIGHTSPEED_RETAIL_CLIENT_ID="your_retail_client_id"
export LIGHTSPEED_RETAIL_CLIENT_SECRET="your_retail_client_secret"
export LIGHTSPEED_ECOM_CLIENT_ID="your_ecom_client_id"
export LIGHTSPEED_ECOM_CLIENT_SECRET="your_ecom_client_secret"

# Optional Settings
export LIGHTSPEED_CONCURRENCY="6"        # Concurrent requests
export LIGHTSPEED_DRY_RUN="true"        # Default to dry-run mode
```

### Batch Processing Workflow

```bash
# 1. Test with small sample
lightspeed-sync sync --input products.csv --dry-run --limit 50

# 2. Process descriptions only first
lightspeed-sync sync --input products.csv --update ecom --images skip

# 3. Then process images separately
lightspeed-sync sync --input products.csv --update ecom --images replace

# 4. Finally update retail custom fields
lightspeed-sync sync --input products.csv --update retail --set-weight
```

### Large Dataset Handling

For large product catalogs (10,000+ products):

```bash
# Use higher concurrency (but respect rate limits)
lightspeed-sync sync --input large_products.csv --concurrency 8

# Process in batches using --limit
lightspeed-sync sync --input products.csv --limit 1000
# Edit CSV to remove processed rows, repeat
```

## Troubleshooting

### Authentication Issues

**Problem**: "Authentication failed - token may be expired"
```bash
# Re-authenticate
lightspeed-sync auth --service both --reauth

# Check token status
lightspeed-sync cache --action info
```

**Problem**: "No retail/ecom tokens found"
```bash
# Ensure environment variables are set
echo $LIGHTSPEED_RETAIL_CLIENT_ID
echo $LIGHTSPEED_ECOM_CLIENT_ID

# Run authentication
lightspeed-sync auth --service both
```

### SKU Resolution Issues

**Problem**: "No retail/ecom matches found"
```bash
# Check cache status
lightspeed-sync cache --action info

# Clear cache and retry
lightspeed-sync cache --action clear
lightspeed-sync sync --input products.csv --dry-run --limit 10
```

**Problem**: SKUs not matching
- Verify SKU format in CSV matches Lightspeed exactly
- Check for leading/trailing spaces
- Confirm SKU field name in both systems

### API Rate Limiting

**Problem**: "Rate limit exceeded" errors
```bash
# Reduce concurrency
lightspeed-sync sync --input products.csv --concurrency 2

# Add delays between requests (modify rate_limit_delay in config)
```

### Performance Optimization

**Slow processing**:
1. Increase `--concurrency` (but watch for rate limits)
2. Use `--limit` to process in smaller batches
3. Run updates separately by service (`--update retail` then `--update ecom`)

## API Documentation References

- **Retail API**: [retail-support.lightspeedhq.com](https://retail-support.lightspeedhq.com)
- **eCom API**: [Lightspeed eCom API Docs](https://developers.lightspeedhq.com/ecom/)
- **OAuth Setup**: Check respective admin panels for latest OAuth configuration steps

## Security Notes

- **Token Storage**: Tokens stored in `~/.lightspeed/credentials/` with restricted permissions (600)
- **No Hardcoded Credentials**: All secrets via environment variables
- **Local Processing**: No data sent to third parties
- **HTTPS Only**: All API communications over HTTPS

## Support

For issues related to:
- **OAuth Setup**: Check Lightspeed documentation and admin panels
- **API Limits**: Refer to your Lightspeed plan's API quotas
- **Tool Usage**: Review this README and check `--help` for any command

---

**Version**: 1.0.0  
**Python**: 3.11+  
**License**: MIT
