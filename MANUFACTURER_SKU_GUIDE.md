# Manufacturer SKU Resolution Guide

This guide explains the new manufacturer SKU functionality added to the Lightspeed API sync tool.

## Overview

The manufacturer SKU resolution feature allows you to look up products in Lightspeed Retail using the manufacturer SKU field instead of the custom SKU field. This is particularly useful when your CSV data contains manufacturer SKUs rather than custom SKUs.

## New Features

### 1. Manufacturer SKU Lookup Methods

#### RetailClient Methods

- `find_item_by_manufacturer_sku(manufacturer_sku: str)` - Find a single item by manufacturer SKU
- `find_items_by_manufacturer_sku_batch(manufacturer_skus: List[str])` - Find multiple items by manufacturer SKU

#### SKUMatcher Methods

- `resolve_by_manufacturer_sku(skus, retail_tokens, ecom_tokens)` - Resolve SKUs using manufacturer SKU lookup
- `resolve_manufacturer_sku_with_duplicate_handling(skus, retail_tokens, ecom_tokens, duplicate_strategy)` - Handle duplicate manufacturer SKUs
- `find_duplicate_manufacturer_skus(skus)` - Identify duplicate SKUs in a list

### 2. Command Line Options

#### New Sync Options

```bash
lightspeed-sync sync --input products.csv \
  --use-manufacturer-sku \
  --duplicate-strategy first_found
```

- `--use-manufacturer-sku` - Use manufacturer SKU for Retail API lookup
- `--duplicate-strategy` - Strategy for handling duplicates (first_found, skip, error)

#### New Test Command

```bash
lightspeed-sync test-manufacturer-sku --sku "MANUFACTURER-SKU-123"
```

## Usage Examples

### 1. Basic Manufacturer SKU Sync

```bash
# Sync using manufacturer SKU resolution
lightspeed-sync sync --input products.csv --use-manufacturer-sku --update retail
```

### 2. Handle Duplicate Manufacturer SKUs

```bash
# Use first found strategy for duplicates
lightspeed-sync sync --input products.csv \
  --use-manufacturer-sku \
  --duplicate-strategy first_found

# Skip products with duplicate manufacturer SKUs
lightspeed-sync sync --input products.csv \
  --use-manufacturer-sku \
  --duplicate-strategy skip

# Error if duplicate manufacturer SKUs found
lightspeed-sync sync --input products.csv \
  --use-manufacturer-sku \
  --duplicate-strategy error
```

### 3. Test Single Manufacturer SKU

```bash
# Test resolution for a specific manufacturer SKU
lightspeed-sync test-manufacturer-sku --sku "YOUR-MANUFACTURER-SKU"
```

### 4. Programmatic Usage

```python
from lightspeed_sync.matchers import SKUMatcher
from lightspeed_sync.clients import RetailClient

# Initialize matcher
matcher = SKUMatcher(Path(".cache/sku_map.json"))

# Resolve manufacturer SKUs
matches = await matcher.resolve_by_manufacturer_sku(
    ["SKU-001", "SKU-002"], 
    retail_tokens, 
    ecom_tokens
)

# Handle duplicates
matches = await matcher.resolve_manufacturer_sku_with_duplicate_handling(
    ["SKU-001", "SKU-001", "SKU-002"],  # Note duplicate
    retail_tokens, 
    ecom_tokens,
    duplicate_strategy="first_found"
)
```

## Duplicate Handling Strategies

### 1. `first_found` (Default)
- Uses the first found result for all occurrences of a duplicate SKU
- Recommended for most use cases
- Ensures consistent behavior

### 2. `skip`
- Skips products with duplicate manufacturer SKUs
- Useful when you want to avoid ambiguous updates
- Logs warnings for skipped products

### 3. `error`
- Raises an error if duplicate manufacturer SKUs are found
- Useful for data validation
- Stops processing immediately

## API Differences

### Regular SKU Lookup
- Searches multiple fields: `customSku`, `sku`, `manufacturerSku`, `defaultAlias`
- Returns first match found
- More flexible but potentially slower

### Manufacturer SKU Lookup
- Searches only `manufacturerSku` field
- More specific and faster
- Better for data that specifically contains manufacturer SKUs

## Error Handling

The manufacturer SKU functionality includes comprehensive error handling:

- **Authentication errors** - Clear messages when tokens are invalid
- **API errors** - Graceful handling of API failures
- **Duplicate detection** - Warnings and strategies for handling duplicates
- **Cache management** - Automatic caching with 24-hour TTL

## Testing

### Test Script
Use the provided test script to verify functionality:

```bash
python test_manufacturer_sku.py
```

### Manual Testing
Test individual manufacturer SKUs:

```bash
lightspeed-sync test-manufacturer-sku --sku "YOUR-TEST-SKU"
```

## Best Practices

1. **Use manufacturer SKU resolution** when your CSV data contains manufacturer SKUs
2. **Test with small batches** first (use `--limit 20`)
3. **Handle duplicates appropriately** based on your data quality
4. **Monitor logs** for warnings about duplicate SKUs
5. **Use dry-run mode** to preview changes before applying

## Troubleshooting

### Common Issues

1. **No matches found**
   - Verify manufacturer SKUs exist in Lightspeed Retail
   - Check that the `manufacturerSku` field is populated
   - Use the test command to verify individual SKUs

2. **Duplicate SKU warnings**
   - Review your CSV data for duplicate manufacturer SKUs
   - Choose appropriate duplicate strategy
   - Consider data cleanup if duplicates are unexpected

3. **Authentication errors**
   - Run `lightspeed-sync auth` to refresh tokens
   - Verify environment variables are set correctly
   - Check token expiration

### Debug Mode

Enable verbose logging by setting the log level:

```bash
export LIGHTSPEED_LOG_LEVEL=DEBUG
lightspeed-sync sync --input products.csv --use-manufacturer-sku
```

## Migration from Custom SKU

If you're migrating from custom SKU to manufacturer SKU resolution:

1. **Test with small batch** using `--limit 20`
2. **Compare results** between custom and manufacturer SKU lookups
3. **Update your CSV data** to ensure manufacturer SKUs are consistent
4. **Use dry-run mode** to verify changes before applying

## Performance Considerations

- Manufacturer SKU lookup is typically faster than multi-field lookup
- Caching reduces API calls for repeated SKUs
- Concurrent processing improves performance for large datasets
- Rate limiting prevents API throttling

## Support

For issues or questions about manufacturer SKU functionality:

1. Check the troubleshooting section above
2. Review logs for error messages
3. Test with individual SKUs using the test command
4. Verify your Lightspeed Retail data structure
