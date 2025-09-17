"""Reporting and logging functionality."""

from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from .config import ProcessingStats, UpdateResult


class Reporter:
    """Handles reporting and logging for sync operations."""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.stats = ProcessingStats()
        self.failures: List[Dict[str, Any]] = []
    
    def add_result(self, result: UpdateResult) -> None:
        """Add an update result to statistics and failures tracking."""
        self.stats.add_result(result)
        
        if not result.success:
            self.failures.append({
                'sku': result.sku,
                'error': result.error,
                'stage': 'update',
                'service': result.service,
                'operation': result.operation
            })
    
    def add_failure(self, sku: str, error: str, stage: str, service: str = '', operation: str = '') -> None:
        """Add a failure manually."""
        self.stats.errors += 1
        self.failures.append({
            'sku': sku,
            'error': error,
            'stage': stage,
            'service': service,
            'operation': operation
        })
    
    def print_summary(self, dry_run: bool = False) -> None:
        """Print a summary of the processing results."""
        title = "DRY RUN SUMMARY" if dry_run else "PROCESSING SUMMARY"
        
        # Create summary table
        table = Table(title=title, show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Count", justify="right", style="green")
        
        table.add_row("Total Rows", str(self.stats.total_rows))
        table.add_row("Processed", str(self.stats.processed_rows))
        table.add_row("Skipped", str(self.stats.skipped_rows))
        table.add_row("Retail Updates", str(self.stats.retail_updates))
        table.add_row("eCom Updates", str(self.stats.ecom_updates))
        table.add_row("Errors", str(self.stats.errors))
        table.add_row("Warnings", str(self.stats.warnings))
        
        self.console.print(table)
        
        # Show errors if any
        if self.failures:
            self.console.print(f"\n[red]Found {len(self.failures)} errors:[/red]")
            error_table = Table(show_header=True, header_style="bold red")
            error_table.add_column("SKU", style="yellow")
            error_table.add_column("Service", style="cyan")
            error_table.add_column("Error", style="red")
            
            for failure in self.failures[:10]:  # Show first 10 errors
                error_table.add_row(
                    failure['sku'],
                    failure['service'],
                    failure['error'][:80] + "..." if len(failure['error']) > 80 else failure['error']
                )
            
            if len(self.failures) > 10:
                error_table.add_row("...", "...", f"and {len(self.failures) - 10} more errors")
            
            self.console.print(error_table)
    
    def print_pre_processing_info(self, total_rows: int, column_info: Dict[str, Any]) -> None:
        """Print information before processing starts."""
        self.stats.total_rows = total_rows
        
        # Column information
        info_panel = Panel.fit(
            f"[bold]Input Data Analysis[/bold]\n\n"
            f"Total rows: {total_rows}\n"
            f"Total columns: {column_info['total_columns']}\n\n"
            f"[green]Required columns present:[/green]\n"
            f"{', '.join(column_info['required_columns_present'])}\n\n"
            f"[yellow]Missing optional columns:[/yellow]\n"
            f"{', '.join(column_info['missing_columns']) if column_info['missing_columns'] else 'None'}",
            title="CSV Analysis",
            border_style="blue"
        )
        self.console.print(info_panel)
    
    def print_sku_resolution_summary(self, matches: Dict[str, Any], total_skus: int) -> None:
        """Print SKU resolution summary."""
        retail_matches = sum(1 for m in matches.values() if m.has_retail_match)
        ecom_matches = sum(1 for m in matches.values() if m.has_ecom_match)
        both_matches = sum(1 for m in matches.values() if m.has_retail_match and m.has_ecom_match)
        no_matches = sum(1 for m in matches.values() if not m.has_retail_match and not m.has_ecom_match)
        
        resolution_table = Table(title="SKU Resolution Results", show_header=True, header_style="bold blue")
        resolution_table.add_column("Category", style="cyan")
        resolution_table.add_column("Count", justify="right", style="green")
        resolution_table.add_column("Percentage", justify="right", style="yellow")
        
        resolution_table.add_row("Total SKUs", str(total_skus), "100%")
        resolution_table.add_row("Retail Matches", str(retail_matches), f"{retail_matches/total_skus*100:.1f}%")
        resolution_table.add_row("eCom Matches", str(ecom_matches), f"{ecom_matches/total_skus*100:.1f}%")
        resolution_table.add_row("Both Services", str(both_matches), f"{both_matches/total_skus*100:.1f}%")
        resolution_table.add_row("No Matches", str(no_matches), f"{no_matches/total_skus*100:.1f}%")
        
        self.console.print(resolution_table)
    
    def generate_markdown_report(self, output_path: Path, dry_run: bool = False) -> None:
        """Generate detailed markdown report."""
        report_content = self._build_markdown_report(dry_run)
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        self.console.print(f"[green]Report written to {output_path}[/green]")
    
    def _build_markdown_report(self, dry_run: bool = False) -> str:
        """Build the markdown report content."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        title = "Lightspeed API Sync Report (DRY RUN)" if dry_run else "Lightspeed API Sync Report"
        
        content = f"""# {title}

**Generated:** {timestamp}

## Summary Statistics

| Metric | Count |
|--------|--------|
| Total Rows | {self.stats.total_rows} |
| Processed Rows | {self.stats.processed_rows} |
| Skipped Rows | {self.stats.skipped_rows} |
| Retail Updates | {self.stats.retail_updates} |
| eCom Updates | {self.stats.ecom_updates} |
| Errors | {self.stats.errors} |
| Warnings | {self.stats.warnings} |

## Processing Results

### Success Rate
- **Overall Success:** {((self.stats.retail_updates + self.stats.ecom_updates) / max(1, self.stats.processed_rows * 2) * 100):.1f}%
- **Retail Success:** {(self.stats.retail_updates / max(1, self.stats.processed_rows) * 100):.1f}%
- **eCom Success:** {(self.stats.ecom_updates / max(1, self.stats.processed_rows) * 100):.1f}%

"""
        
        # Add errors section if there are failures
        if self.failures:
            content += "## Errors and Failures\n\n"
            content += "| SKU | Service | Operation | Error |\n"
            content += "|-----|---------|-----------|-------|\n"
            
            for failure in self.failures[:20]:  # Limit to first 20 errors
                error_text = failure['error'].replace('|', '\\|').replace('\n', ' ')[:100]
                content += f"| {failure['sku']} | {failure['service']} | {failure['operation']} | {error_text} |\n"
            
            if len(self.failures) > 20:
                content += f"\n*... and {len(self.failures) - 20} more errors*\n"
        
        content += f"""
## Recommendations

"""
        
        if self.stats.errors > 0:
            content += f"- **Review Errors:** {self.stats.errors} operations failed. Check the errors table above for details.\n"
        
        if self.stats.skipped_rows > 0:
            content += f"- **Missing SKUs:** {self.stats.skipped_rows} rows were skipped due to missing SKU values.\n"
        
        if self.stats.retail_updates == 0 and self.stats.ecom_updates == 0:
            content += "- **No Updates:** No successful updates were made. Check authentication and SKU resolution.\n"
        
        content += f"""
---
*Report generated by Lightspeed Sync Tool v1.0.0*
"""
        
        return content
    
    def update_processed_count(self, count: int) -> None:
        """Update the processed rows count."""
        self.stats.processed_rows = count
    
    def update_skipped_count(self, count: int) -> None:
        """Update the skipped rows count."""
        self.stats.skipped_rows = count
    
    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.stats.warnings += 1
        self.console.print(f"[yellow]Warning: {message}[/yellow]")
