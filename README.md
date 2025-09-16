# Google Sheet to Lightspeed Retail CSV Converter

A reliable Python tool to transform Google Sheet exports into Lightspeed Retail import CSVs for updating existing products. This tool handles web store descriptions, custom fields, images, and weight updates without creating new products.

## Features

- ✅ **Safe Updates Only**: Updates existing products by SKU - never creates new products
- 🔄 **Three Output CSVs**: Items, Custom Fields, and Images with proper formatting
- 🛡️ **Data Validation**: Handles missing data, duplicates, and invalid formats gracefully  
- 📝 **HTML Preservation**: Maintains HTML formatting in long descriptions
- 📊 **Detailed Reporting**: Generates summary reports with warnings and previews
- 🔍 **Testing Support**: Dry-run mode and row limiting for safe testing

## Quick Start

### 1. Export Google Sheet to CSV

1. Open your Google Sheet
2. Go to **File** → **Download** → **Comma Separated Values (.csv)**
3. Save the file (e.g., `client_products.csv`)

*Screenshot placeholder: [Google Sheets export dialog]*

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the Converter

```bash
# Basic conversion
python sheet_to_lightspeed.py --input client_products.csv

# Test with first 50 rows and URL validation
python sheet_to_lightspeed.py --input client_products.csv --validate-images --limit 50

# Dry run to preview without creating files
python sheet_to_lightspeed.py --input client_products.csv --dry-run
```

## Input Requirements

Your Google Sheet CSV must contain these columns:

| Column | Required | Description |
|--------|----------|-------------|
| `SKU` | ✅ | Unique product identifier (used for matching) |
| `US_Description_Short` | ❌ | Short product description |
| `US_Description_Long` | ❌ | Long description (HTML preserved) |
| `US_Title_Short` | ❌ | Custom field: Title Short |
| `US_Meta_Title` | ❌ | Custom field: Meta Title |
| `Images` | ❌ | Image URLs (comma-separated) |
| `Weight_Value` | ❌ | Numeric weight value |

**Note**: Additional columns are ignored. Missing optional columns result in empty values in output.

## Output Files

The tool generates three CSV files in the `./out` directory:

### 1. Items_Update.csv
Updates product descriptions and weight:
```csv
systemSku,shortDescription,longDescription,weight
ABC123,"Short desc","<p>Long HTML description</p>",1.5
```

### 2. CustomFields_Update.csv  
Updates custom fields (Title Short, Meta Title):
```csv
systemSku,customField1,customField2
ABC123,"Custom Title","Meta Title Text"
```

### 3. Images_Update.csv
Updates product images with sort order:
```csv
systemSku,imageUrl,sortOrder
ABC123,"https://example.com/image1.jpg",1
ABC123,"https://example.com/image2.jpg",2
```

## Lightspeed Import Process

### 1. Access Lightspeed Back Office
1. Log into your Lightspeed Retail Back Office
2. Navigate to **Inventory** → **Import**

*Screenshot placeholder: [Lightspeed import screen]*

### 2. Import Each CSV File

**Items Update:**
1. Select **Items_Update.csv**
2. Choose **Update existing items**
3. Map columns: `systemSku` → SKU, others as labeled
4. Run import

**Custom Fields Update:**
1. Select **CustomFields_Update.csv**  
2. Choose **Update existing items**
3. Map `customField1` → "Title Short" (configure in admin)
4. Map `customField2` → "Meta Title" (configure in admin)
5. Run import

**Images Update:**
1. Select **Images_Update.csv**
2. Choose **Update existing items**
3. Map columns as labeled
4. Run import

*Screenshot placeholder: [Lightspeed column mapping]*

### 3. Verify Results
1. Check a few products manually in Lightspeed
2. Verify descriptions, custom fields, and images updated correctly
3. Review the `run_report.md` for any warnings or issues

## Command Line Options

```bash
python sheet_to_lightspeed.py [OPTIONS]

Required:
  --input PATH              Path to input CSV from Google Sheets

Optional:
  --out-dir PATH           Output directory (default: ./out)
  --validate-images        Validate image URL syntax (no network calls)
  --dry-run               Print summary without writing files  
  --limit N               Process only first N rows for testing
  --help                  Show help message
```

## Data Processing Rules

### SKU Handling
- **Required**: Rows without SKU are skipped and logged
- **Duplicates**: First occurrence kept, images aggregated from all occurrences
- **Matching**: SKU maps to `systemSku` in all output files

### Descriptions  
- **HTML Preserved**: Long descriptions maintain HTML formatting
- **Empty Values**: Blank descriptions allowed (not synthesized)
- **Whitespace**: Leading/trailing spaces trimmed

### Images
- **Multiple URLs**: Comma-separated URLs split into separate rows
- **Sort Order**: Sequential numbering (1, 2, 3...) per SKU
- **Validation**: Basic URL format checking (optional)
- **Aggregation**: Images from duplicate SKUs combined

### Weight
- **Source**: Uses `Weight_Value` column only
- **Validation**: Must be numeric and non-negative
- **Invalid Data**: Left blank with warning logged

## Error Handling & Logging

The tool provides comprehensive error handling:

- **Missing SKUs**: Rows skipped with warning
- **Duplicate SKUs**: Logged but processed (images aggregated)
- **Invalid URLs**: Skipped with warning (when validation enabled)
- **Invalid Weights**: Set to blank with warning
- **File Errors**: Clear error messages with exit codes

### Sample Report Output

```markdown
# Lightspeed CSV Conversion Report

**Generated:** 2024-01-15 14:30:22

## Summary
- **Total rows processed:** 1,250
- **Rows skipped (missing SKU):** 3
- **Duplicate SKUs found:** 5
- **Items written:** 1,247
- **Custom fields written:** 1,247  
- **Image rows written:** 2,891
- **Invalid URLs:** 2
- **Invalid weights:** 1

## Items_Update.csv Preview
| systemSku | shortDescription | longDescription | weight |
|-----------|------------------|-----------------|--------|
| ABC123    | Short desc       | <p>Long...</p>  | 1.5    |
```

## Troubleshooting

### Common Issues

**"Missing required columns: ['SKU']"**
- Ensure your CSV has a column named exactly `SKU`
- Check for extra spaces or different casing

**"Invalid weight value: XYZ"**  
- Weight must be numeric (integer or decimal)
- Negative weights are rejected
- Empty weights are allowed

**"Invalid URL for SKU ABC123: badurl"**
- Only appears when `--validate-images` is used
- URLs must start with `http://` or `https://`
- Invalid URLs are skipped, not the entire row

**No output files created**
- Check if `--dry-run` flag was used
- Verify input file exists and is readable
- Check for permission issues in output directory

### Getting Help

1. Run with `--dry-run` first to preview results
2. Use `--limit 10` to test with small data samples
3. Check `run_report.md` for detailed warnings and statistics
4. Verify your Google Sheet has the expected column names

## File Structure

```
/project
├── sheet_to_lightspeed.py    # Main conversion script
├── requirements.txt          # Python dependencies  
├── README.md                # This file
└── out/                     # Generated output (created on run)
    ├── Items_Update.csv
    ├── CustomFields_Update.csv  
    ├── Images_Update.csv
    └── run_report.md
```

## Technical Details

- **Python Version**: 3.10+
- **Dependencies**: pandas, python-slugify
- **Encoding**: UTF-8 with proper CSV quoting
- **Memory**: Processes entire CSV in memory (suitable for typical product catalogs)
- **Performance**: Handles thousands of products efficiently

## Safety Features

- ✅ No network calls (offline processing)
- ✅ No credential storage or transmission  
- ✅ Preserves original data (read-only input)
- ✅ Deterministic output ordering
- ✅ Comprehensive validation and logging
- ✅ Dry-run mode for safe testing

---

*For support or feature requests, please refer to your development team.*
