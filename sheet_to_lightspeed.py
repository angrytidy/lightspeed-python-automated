#!/usr/bin/env python3
"""
Google Sheet to Lightspeed Retail CSV Converter

Transforms a Google Sheet export (CSV) into three Lightspeed import CSVs:
- Items_Update.csv (descriptions, weight)
- CustomFields_Update.csv (title short, meta title)  
- Images_Update.csv (image URLs with sort order)

Only updates existing products by SKU - no new product creation.
"""

import argparse
import csv
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
import pandas as pd


class LightspeedConverter:
    """Converts Google Sheet CSV to Lightspeed import CSVs"""
    
    def __init__(self, validate_images: bool = False, dry_run: bool = False):
        self.validate_images = validate_images
        self.dry_run = dry_run
        self.stats = {
            'total_rows': 0,
            'skipped_rows': 0,
            'duplicate_skus': 0,
            'items_written': 0,
            'custom_fields_written': 0,
            'image_rows_written': 0,
            'invalid_urls': 0,
            'invalid_weights': 0,
            'warnings': []
        }
        
        # URL validation regex
        self.url_pattern = re.compile(r'^https?://.+', re.IGNORECASE)
    
    def log_warning(self, message: str) -> None:
        """Log a warning message"""
        self.stats['warnings'].append(message)
        print(f"WARNING: {message}")
    
    def validate_url(self, url: str) -> bool:
        """Validate URL format (no network calls)"""
        if not url or not url.strip():
            return False
        return bool(self.url_pattern.match(url.strip()))
    
    def parse_weight(self, weight_str: Any) -> Optional[str]:
        """Parse and validate weight value"""
        if pd.isna(weight_str) or weight_str == '':
            return None
            
        # Convert to string and clean
        weight_clean = str(weight_str).strip()
        if not weight_clean:
            return None
            
        try:
            # Try to convert to float first, then check if it's a whole number
            weight_float = float(weight_clean)
            if weight_float < 0:
                self.stats['invalid_weights'] += 1
                self.log_warning(f"Negative weight value: {weight_clean}")
                return None
            
            # Convert to int if it's a whole number, otherwise keep as float
            if weight_float.is_integer():
                return str(int(weight_float))
            else:
                return str(weight_float)
                
        except (ValueError, TypeError):
            self.stats['invalid_weights'] += 1
            self.log_warning(f"Invalid weight value: {weight_clean}")
            return None
    
    def clean_string(self, value: Any) -> str:
        """Clean string value - strip whitespace but preserve HTML"""
        if pd.isna(value) or value == '':
            return ''
        
        # Convert to string and strip leading/trailing whitespace
        cleaned = str(value).strip()
        
        # Normalize line endings but preserve line breaks
        cleaned = cleaned.replace('\r\n', '\n').replace('\r', '\n')
        
        return cleaned
    
    def parse_images(self, images_str: Any, sku: str) -> List[Tuple[str, int]]:
        """Parse comma-separated image URLs and return with sort order"""
        if pd.isna(images_str) or images_str == '':
            return []
        
        images_clean = str(images_str).strip()
        if not images_clean:
            return []
        
        # Split on commas and clean each URL
        urls = [url.strip() for url in images_clean.split(',')]
        valid_images = []
        
        for i, url in enumerate(urls, 1):
            if not url:  # Skip empty strings
                continue
                
            if self.validate_images and not self.validate_url(url):
                self.stats['invalid_urls'] += 1
                self.log_warning(f"Invalid URL for SKU {sku}: {url}")
                continue
                
            valid_images.append((url, i))
        
        return valid_images
    
    def load_and_validate_data(self, input_path: Path, limit: Optional[int] = None) -> pd.DataFrame:
        """Load CSV data and perform basic validation"""
        try:
            # Read CSV with UTF-8 encoding
            df = pd.read_csv(input_path, encoding='utf-8')
            
            if limit:
                df = df.head(limit)
                print(f"Limited to first {limit} rows for testing")
            
            print(f"Loaded {len(df)} rows from {input_path}")
            
            # Check for required columns
            required_cols = ['SKU']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                raise ValueError(f"Missing required columns: {missing_cols}")
            
            # Show available columns
            print(f"Available columns: {list(df.columns)}")
            
            return df
            
        except Exception as e:
            print(f"ERROR: Failed to load input file: {e}")
            sys.exit(1)
    
    def process_data(self, df: pd.DataFrame) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """Process input data and generate output records"""
        items_data = []
        custom_fields_data = []
        images_data = []
        
        # Track SKUs to detect duplicates
        seen_skus = set()
        sku_images = defaultdict(list)  # Aggregate images from duplicate SKUs
        
        self.stats['total_rows'] = len(df)
        
        for idx, row in df.iterrows():
            # Check for SKU
            sku = self.clean_string(row.get('SKU', ''))
            if not sku:
                self.stats['skipped_rows'] += 1
                self.log_warning(f"Row {idx + 2} missing SKU - skipped")
                continue
            
            # Handle duplicate SKUs
            is_duplicate = sku in seen_skus
            if is_duplicate:
                self.stats['duplicate_skus'] += 1
                self.log_warning(f"Duplicate SKU found: {sku} (row {idx + 2})")
            else:
                seen_skus.add(sku)
                
                # Process Items data (only for first occurrence)
                items_record = {
                    'systemSku': sku,
                    'shortDescription': self.clean_string(row.get('US_Description_Short', '')),
                    'longDescription': self.clean_string(row.get('US_Description_Long', '')),
                    'weight': self.parse_weight(row.get('Weight_Value', '')) or ''
                }
                items_data.append(items_record)
                
                # Process Custom Fields data (only for first occurrence)
                custom_fields_record = {
                    'systemSku': sku,
                    'customField1': self.clean_string(row.get('US_Title_Short', '')),
                    'customField2': self.clean_string(row.get('US_Meta_Title', ''))
                }
                custom_fields_data.append(custom_fields_record)
            
            # Always aggregate images (from all occurrences of SKU)
            images = self.parse_images(row.get('Images', ''), sku)
            sku_images[sku].extend(images)
        
        # Process aggregated images with proper sort order per SKU
        for sku, image_list in sku_images.items():
            # Re-number sort order for aggregated images
            for sort_order, (url, _) in enumerate(image_list, 1):
                images_record = {
                    'systemSku': sku,
                    'imageUrl': url,
                    'sortOrder': sort_order
                }
                images_data.append(images_record)
        
        # Update stats
        self.stats['items_written'] = len(items_data)
        self.stats['custom_fields_written'] = len(custom_fields_data)
        self.stats['image_rows_written'] = len(images_data)
        
        return items_data, custom_fields_data, images_data
    
    def write_csv(self, data: List[Dict], output_path: Path, fieldnames: List[str]) -> None:
        """Write data to CSV file with proper encoding and quoting"""
        if self.dry_run:
            print(f"DRY RUN: Would write {len(data)} rows to {output_path}")
            return
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            writer.writerows(data)
        
        print(f"Written {len(data)} rows to {output_path}")
    
    def generate_report(self, output_dir: Path, items_data: List[Dict], 
                       custom_fields_data: List[Dict], images_data: List[Dict]) -> None:
        """Generate markdown report with summary and previews"""
        if self.dry_run:
            print("DRY RUN: Would generate run_report.md")
            return
        
        report_path = output_dir / 'run_report.md'
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# Lightspeed CSV Conversion Report\n\n")
            f.write(f"**Generated:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Summary statistics
            f.write("## Summary\n\n")
            f.write(f"- **Total rows processed:** {self.stats['total_rows']}\n")
            f.write(f"- **Rows skipped (missing SKU):** {self.stats['skipped_rows']}\n")
            f.write(f"- **Duplicate SKUs found:** {self.stats['duplicate_skus']}\n")
            f.write(f"- **Items written:** {self.stats['items_written']}\n")
            f.write(f"- **Custom fields written:** {self.stats['custom_fields_written']}\n")
            f.write(f"- **Image rows written:** {self.stats['image_rows_written']}\n")
            f.write(f"- **Invalid URLs:** {self.stats['invalid_urls']}\n")
            f.write(f"- **Invalid weights:** {self.stats['invalid_weights']}\n\n")
            
            # Warnings
            if self.stats['warnings']:
                f.write("## Warnings\n\n")
                for warning in self.stats['warnings'][:10]:  # Limit to first 10
                    f.write(f"- {warning}\n")
                if len(self.stats['warnings']) > 10:
                    f.write(f"- ... and {len(self.stats['warnings']) - 10} more warnings\n")
                f.write("\n")
            
            # Preview samples
            self._write_preview_table(f, "Items_Update.csv Preview", items_data[:5], 
                                    ['systemSku', 'shortDescription', 'longDescription', 'weight'])
            
            self._write_preview_table(f, "CustomFields_Update.csv Preview", custom_fields_data[:5],
                                    ['systemSku', 'customField1', 'customField2'])
            
            self._write_preview_table(f, "Images_Update.csv Preview", images_data[:5],
                                    ['systemSku', 'imageUrl', 'sortOrder'])
        
        print(f"Report written to {report_path}")
    
    def _write_preview_table(self, f, title: str, data: List[Dict], columns: List[str]) -> None:
        """Write a preview table in markdown format"""
        f.write(f"## {title}\n\n")
        
        if not data:
            f.write("*No data to preview*\n\n")
            return
        
        # Header
        f.write("| " + " | ".join(columns) + " |\n")
        f.write("| " + " | ".join(["---"] * len(columns)) + " |\n")
        
        # Rows
        for row in data:
            values = []
            for col in columns:
                value = str(row.get(col, ''))
                # Truncate long values and escape pipes
                if len(value) > 50:
                    value = value[:47] + "..."
                value = value.replace('|', '\\|').replace('\n', ' ')
                values.append(value)
            f.write("| " + " | ".join(values) + " |\n")
        
        f.write("\n")
    
    def convert(self, input_path: Path, output_dir: Path, limit: Optional[int] = None) -> None:
        """Main conversion process"""
        print(f"Converting {input_path} to Lightspeed CSVs...")
        print(f"Output directory: {output_dir}")
        print(f"Validate images: {self.validate_images}")
        print(f"Dry run: {self.dry_run}")
        print()
        
        # Load and validate input data
        df = self.load_and_validate_data(input_path, limit)
        
        # Process data
        items_data, custom_fields_data, images_data = self.process_data(df)
        
        # Write output files
        self.write_csv(items_data, output_dir / 'Items_Update.csv',
                      ['systemSku', 'shortDescription', 'longDescription', 'weight'])
        
        self.write_csv(custom_fields_data, output_dir / 'CustomFields_Update.csv',
                      ['systemSku', 'customField1', 'customField2'])
        
        self.write_csv(images_data, output_dir / 'Images_Update.csv',
                      ['systemSku', 'imageUrl', 'sortOrder'])
        
        print()  # Add spacing before report generation
        
        # Generate report
        self.generate_report(output_dir, items_data, custom_fields_data, images_data)
        
        # Print final summary
        print("\n" + "="*50)
        print("CONVERSION COMPLETE")
        print("="*50)
        print(f"Total rows processed: {self.stats['total_rows']}")
        print(f"Rows skipped (missing SKU): {self.stats['skipped_rows']}")
        print(f"Duplicate SKUs found: {self.stats['duplicate_skus']}")
        print(f"Files generated:")
        print(f"  - Items: {self.stats['items_written']} rows")
        print(f"  - Custom Fields: {self.stats['custom_fields_written']} rows")
        print(f"  - Images: {self.stats['image_rows_written']} rows")
        
        if self.stats['warnings']:
            print(f"\nWarnings: {len(self.stats['warnings'])} (see report for details)")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Convert Google Sheet CSV to Lightspeed Retail import CSVs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python sheet_to_lightspeed.py --input client.csv
  python sheet_to_lightspeed.py --input client.csv --validate-images --limit 50
  python sheet_to_lightspeed.py --input client.csv --dry-run
        """
    )
    
    parser.add_argument('--input', required=True, type=Path,
                       help='Path to input CSV file from Google Sheets')
    parser.add_argument('--out-dir', type=Path, default=Path('./out'),
                       help='Output directory (default: ./out)')
    parser.add_argument('--validate-images', action='store_true',
                       help='Validate image URL syntax (no network calls)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Print summary without writing files')
    parser.add_argument('--limit', type=int,
                       help='Process only first N rows for testing')
    
    args = parser.parse_args()
    
    # Validate input file exists
    if not args.input.exists():
        print(f"ERROR: Input file not found: {args.input}")
        sys.exit(1)
    
    # Create converter and run
    converter = LightspeedConverter(
        validate_images=args.validate_images,
        dry_run=args.dry_run
    )
    
    try:
        converter.convert(args.input, args.out_dir, args.limit)
    except KeyboardInterrupt:
        print("\nConversion cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Conversion failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
