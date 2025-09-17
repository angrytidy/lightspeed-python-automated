# Testing Guide for Lightspeed Sync Tools

This guide covers testing both tools: the **CSV Generator** and the **API Integration Tool**.

## 🧪 Test Data

We've created `test_products.csv` with various test scenarios:
- Valid products with complete data
- Missing SKUs (should be skipped)
- Duplicate SKUs (should be handled)
- Invalid weights and URLs (should generate warnings)
- HTML content preservation
- Multiple images per product

## 📋 Testing the CSV Generator

### **Quick Test (Recommended Start)**

```bash
# Test with dry run first
python sheet_to_lightspeed.py --input test_products.csv --dry-run --validate-images

# Generate actual files
python sheet_to_lightspeed.py --input test_products.csv --validate-images --out-dir test_output
```

### **Expected Results**
- ✅ 9 rows processed, 1 skipped (missing SKU)
- ✅ 1 duplicate SKU detected and handled
- ✅ 7 unique products in output
- ✅ 11 image rows (multiple images per product)
- ✅ 4 warnings logged (missing SKU, duplicate, invalid weight, invalid URL)

### **Generated Files**
```
test_output/
├── Items_Update.csv         # Product descriptions and weights
├── CustomFields_Update.csv  # Custom fields (Title Short, Meta Title)
├── Images_Update.csv        # Product images with sort order
└── run_report.md           # Detailed processing report
```

### **Validation Checks**

1. **Items_Update.csv**:
   ```bash
   # Check HTML preservation
   head -3 test_output/Items_Update.csv
   ```
   Should show HTML tags intact in longDescription.

2. **Images_Update.csv**:
   ```bash
   # Check image sort order
   head -8 test_output/Images_Update.csv
   ```
   Should show sequential sortOrder (1,2,3) per SKU.

3. **Report**:
   ```bash
   # Check processing summary
   cat test_output/run_report.md
   ```

## 🔗 Testing the API Integration Tool

### **1. Test CLI Installation**

```bash
# Verify installation
lightspeed-sync --help
lightspeed-sync sync --help
lightspeed-sync auth --help
lightspeed-sync cache --help
```

### **2. Test Without Authentication**

```bash
# This should show helpful error messages
lightspeed-sync sync --input test_products.csv --dry-run --limit 3
```

**Expected Output**:
- ✅ CSV loads successfully
- ✅ Shows authentication errors (expected)
- ✅ Shows 0 API matches (expected without auth)
- ✅ Generates report despite no matches

### **3. Test Cache Management**

```bash
# View cache info
lightspeed-sync cache --action info

# Clear cache
lightspeed-sync cache --action clear

# Check cache is empty
lightspeed-sync cache --action info
```

### **4. Test with Mock Authentication (Advanced)**

If you want to test API functionality without real Lightspeed accounts:

```bash
# Set dummy environment variables
export LIGHTSPEED_RETAIL_CLIENT_ID="test_retail_id"
export LIGHTSPEED_RETAIL_CLIENT_SECRET="test_retail_secret"
export LIGHTSPEED_ECOM_CLIENT_ID="test_ecom_id"
export LIGHTSPEED_ECOM_CLIENT_SECRET="test_ecom_secret"

# Try authentication (will fail but show proper flow)
lightspeed-sync auth --service both
```

## 🎯 Production Testing Workflow

### **Phase 1: CSV Generator Testing**

1. **Test with your real data**:
   ```bash
   python sheet_to_lightspeed.py --input your_real_data.csv --dry-run --limit 10
   ```

2. **Validate output**:
   - Check HTML preservation
   - Verify image URLs are split correctly
   - Confirm custom field mapping
   - Review warnings in report

3. **Generate full output**:
   ```bash
   python sheet_to_lightspeed.py --input your_real_data.csv --validate-images
   ```

4. **Import to Lightspeed** (manual):
   - Upload Items_Update.csv to Lightspeed Back Office
   - Upload CustomFields_Update.csv
   - Upload Images_Update.csv
   - Verify a few products manually

### **Phase 2: API Integration Testing**

1. **Set up OAuth Apps** (see README_API.md):
   - Create Retail OAuth app
   - Create eCom OAuth app
   - Set environment variables

2. **Authenticate**:
   ```bash
   lightspeed-sync auth --service both
   ```

3. **Test with small dataset**:
   ```bash
   lightspeed-sync sync --input your_real_data.csv --dry-run --limit 5
   ```

4. **Check SKU resolution**:
   ```bash
   lightspeed-sync cache --action info
   ```

5. **Perform actual updates**:
   ```bash
   # Start with eCom only
   lightspeed-sync sync --input your_real_data.csv --update ecom --limit 10

   # Then Retail
   lightspeed-sync sync --input your_real_data.csv --update retail --limit 10
   ```

## 🔍 Test Scenarios Covered

### **Data Quality Tests**
- ✅ Missing SKUs (skipped with warning)
- ✅ Duplicate SKUs (first kept, images aggregated)
- ✅ Invalid weights (set to blank with warning)
- ✅ Invalid image URLs (skipped with warning)
- ✅ HTML content preservation
- ✅ Empty optional fields (handled gracefully)

### **Processing Tests**
- ✅ Dry run mode (no files written)
- ✅ Row limiting (for testing large datasets)
- ✅ Output directory creation
- ✅ UTF-8 encoding handling
- ✅ CSV quoting for HTML content

### **API Integration Tests**
- ✅ Authentication error handling
- ✅ SKU resolution and caching
- ✅ Service-specific updates
- ✅ Concurrent processing
- ✅ Rate limiting and retries
- ✅ Comprehensive error reporting

## 🚨 Troubleshooting Test Issues

### **CSV Generator Issues**

**Problem**: "Missing required columns"
```bash
# Check your CSV columns
head -1 your_file.csv
```
Ensure you have at least `SKU` column.

**Problem**: No output files generated
```bash
# Check if dry-run was used
python sheet_to_lightspeed.py --input test_products.csv --dry-run
```
Remove `--dry-run` to generate files.

### **API Tool Issues**

**Problem**: "Type not yet supported" error
- This was fixed - ensure you have the latest version
- Run `pip install -e .` again if needed

**Problem**: Authentication failures
- Check environment variables are set
- Verify OAuth app configuration in Lightspeed
- Check network connectivity

**Problem**: No SKU matches found
- Verify SKUs in CSV match exactly those in Lightspeed
- Check for extra spaces or formatting differences
- Try with known working SKUs first

## 📊 Success Metrics

### **CSV Generator Success**
- All valid rows processed
- HTML preserved in output
- Images split correctly with sort order
- Warnings logged for data issues
- Clean CSV files generated

### **API Tool Success**
- Authentication completes successfully
- SKU resolution finds matches
- Updates applied without errors
- Detailed reports generated
- Cache populated for performance

## 🎉 Next Steps After Testing

1. **CSV Approach**: Import generated CSVs to Lightspeed manually
2. **API Approach**: Run full sync with your complete dataset
3. **Hybrid Approach**: Use CSV for initial bulk updates, API for ongoing sync

Both tools are production-ready and can handle your real data safely!
