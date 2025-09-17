"""CSV input/output handling with validation and normalization."""

import csv
from pathlib import Path
from typing import Dict, List, Any, Optional
import pandas as pd
from rich.console import Console


class CSVProcessor:
    """Handles CSV reading, validation, and normalization."""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
    
    def read_csv(self, file_path: Path, limit: Optional[int] = None) -> pd.DataFrame:
        """Read and validate CSV file."""
        if not file_path.exists():
            raise FileNotFoundError(f"CSV file not found: {file_path}")
        
        try:
            # Read CSV with UTF-8 encoding
            df = pd.read_csv(file_path, encoding='utf-8')
            
            if limit:
                df = df.head(limit)
                self.console.print(f"[yellow]Limited to first {limit} rows for processing[/yellow]")
            
            self.console.print(f"[green]Loaded {len(df)} rows from {file_path}[/green]")
            
            return df
            
        except Exception as e:
            raise ValueError(f"Failed to read CSV file: {e}")
    
    def validate_required_columns(self, df: pd.DataFrame, required_columns: List[str]) -> None:
        """Validate that required columns exist."""
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            available_cols = list(df.columns)
            raise ValueError(
                f"Missing required columns: {missing_columns}. "
                f"Available columns: {available_cols}"
            )
    
    def normalize_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize and clean CSV data."""
        df_clean = df.copy()
        
        # Clean string columns - strip whitespace
        for col in df_clean.columns:
            if df_clean[col].dtype == 'object':
                df_clean[col] = df_clean[col].astype(str).str.strip()
                # Replace 'nan' strings with actual NaN
                df_clean[col] = df_clean[col].replace('nan', pd.NA)
        
        return df_clean
    
    def extract_product_data(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Extract and structure product data from DataFrame."""
        products = []
        skipped_count = 0
        
        for idx, row in df.iterrows():
            # Check for SKU
            sku = self._clean_string(row.get('SKU', ''))
            if not sku:
                skipped_count += 1
                self.console.print(f"[yellow]Row {idx + 2}: Missing SKU - skipped[/yellow]")
                continue
            
            # Extract all relevant fields
            product_data = {
                'sku': sku,
                'short_description': self._clean_string(row.get('US_Description_Short', '')),
                'long_description': self._clean_string(row.get('US_Description_Long', '')),
                'title_short': self._clean_string(row.get('US_Title_Short', '')),
                'meta_title': self._clean_string(row.get('US_Meta_Title', '')),
                'images': self._clean_string(row.get('Images', '')),
                'weight_value': self._parse_weight(row.get('Weight_Value', '')),
                'row_number': idx + 2  # Excel-style row numbering
            }
            
            products.append(product_data)
        
        if skipped_count > 0:
            self.console.print(f"[yellow]Skipped {skipped_count} rows due to missing SKU[/yellow]")
        
        self.console.print(f"[green]Extracted {len(products)} valid product records[/green]")
        
        return products
    
    def _clean_string(self, value: Any) -> str:
        """Clean and normalize string values."""
        if pd.isna(value) or value == 'nan':
            return ''
        
        # Convert to string and strip whitespace
        cleaned = str(value).strip()
        
        # Normalize line endings but preserve line breaks
        cleaned = cleaned.replace('\r\n', '\n').replace('\r', '\n')
        
        return cleaned
    
    def _parse_weight(self, weight_value: Any) -> Optional[float]:
        """Parse and validate weight value."""
        if pd.isna(weight_value) or weight_value == '' or weight_value == 'nan':
            return None
        
        try:
            weight = float(str(weight_value).strip())
            return weight if weight >= 0 else None
        except (ValueError, TypeError):
            return None
    
    def write_failures_csv(self, failures: List[Dict[str, Any]], output_path: Path) -> None:
        """Write failures to CSV file."""
        if not failures:
            return
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['sku', 'error', 'stage', 'service', 'operation']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for failure in failures:
                writer.writerow({
                    'sku': failure.get('sku', ''),
                    'error': failure.get('error', ''),
                    'stage': failure.get('stage', ''),
                    'service': failure.get('service', ''),
                    'operation': failure.get('operation', '')
                })
        
        self.console.print(f"[yellow]Wrote {len(failures)} failures to {output_path}[/yellow]")
    
    def get_column_info(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Get information about DataFrame columns."""
        return {
            'total_columns': len(df.columns),
            'column_names': list(df.columns),
            'required_columns_present': [
                col for col in ['SKU', 'US_Description_Short', 'US_Description_Long', 
                               'US_Title_Short', 'US_Meta_Title', 'Images', 'Weight_Value']
                if col in df.columns
            ],
            'missing_columns': [
                col for col in ['SKU', 'US_Description_Short', 'US_Description_Long', 
                               'US_Title_Short', 'US_Meta_Title', 'Images', 'Weight_Value']
                if col not in df.columns
            ]
        }
