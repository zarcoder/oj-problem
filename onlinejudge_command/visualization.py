import os
import sys
import time
from typing import Dict, List, Optional, Tuple, Any

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    from rich.syntax import Syntax
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Fallback functions for when rich is not available
def _print_header(text: str) -> None:
    """Print a header without rich."""
    print("\n" + "=" * 80)
    print(f" {text}")
    print("=" * 80)

def _print_success(text: str) -> None:
    """Print a success message without rich."""
    print(f"✓ {text}")

def _print_error(text: str) -> None:
    """Print an error message without rich."""
    print(f"✗ {text}")

def _print_info(text: str) -> None:
    """Print an info message without rich."""
    print(f"ℹ {text}")

def _print_table(headers: List[str], rows: List[List[str]]) -> None:
    """Print a table without rich."""
    # Calculate column widths
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))
    
    # Print headers
    header_row = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    print(header_row)
    print("-" * len(header_row))
    
    # Print rows
    for row in rows:
        print(" | ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row)))

def _print_code(code: str, language: str) -> None:
    """Print code without rich."""
    print(f"\n--- {language} ---")
    print(code)
    print("---")

# Rich-enabled functions
console = Console() if RICH_AVAILABLE else None

def print_header(text: str) -> None:
    """Print a styled header."""
    if RICH_AVAILABLE:
        console.print(Panel(text, style="bold blue"))
    else:
        _print_header(text)

def print_success(text: str) -> None:
    """Print a success message."""
    if RICH_AVAILABLE:
        console.print(f"[bold green]✓[/bold green] {text}")
    else:
        _print_success(text)

def print_error(text: str) -> None:
    """Print an error message."""
    if RICH_AVAILABLE:
        console.print(f"[bold red]✗[/bold red] {text}")
    else:
        _print_error(text)

def print_info(text: str) -> None:
    """Print an info message."""
    if RICH_AVAILABLE:
        console.print(f"[bold blue]ℹ[/bold blue] {text}")
    else:
        _print_info(text)

def print_warning(text: str) -> None:
    """Print a warning message."""
    if RICH_AVAILABLE:
        console.print(f"[bold yellow]⚠[/bold yellow] {text}")
    else:
        print(f"⚠ {text}")

def print_table(headers: List[str], rows: List[List[Any]]) -> None:
    """Print a styled table."""
    if RICH_AVAILABLE:
        table = Table(show_header=True, header_style="bold")
        for header in headers:
            table.add_column(header)
        
        for row in rows:
            table.add_row(*[str(cell) for cell in row])
        
        console.print(table)
    else:
        _print_table(headers, rows)

def print_code(code: str, language: str = "python") -> None:
    """Print syntax-highlighted code."""
    if RICH_AVAILABLE:
        syntax = Syntax(code, language, theme="monokai", line_numbers=True)
        console.print(syntax)
    else:
        _print_code(code, language)

def create_progress() -> Any:
    """Create a progress bar."""
    if RICH_AVAILABLE:
        return Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TextColumn("[bold]{task.completed}/{task.total}"),
            TimeElapsedColumn(),
        )
    else:
        return None

def print_test_results(test_results: List[Dict[str, Any]]) -> None:
    """
    Print test results in a nice table.
    
    Args:
        test_results: List of test result dictionaries with keys:
            - test_name: Name of the test
            - status: 'AC', 'WA', 'TLE', 'RE', etc.
            - time: Execution time in seconds
            - memory: Memory usage in MB (optional)
    """
    if not test_results:
        print_warning("No test results to display")
        return
    
    headers = ["Test", "Status", "Time (s)", "Memory (MB)"]
    rows = []
    
    for result in test_results:
        status = result.get('status', 'N/A')
        status_str = status
        
        # Format row data
        row = [
            result.get('test_name', 'Unknown'),
            status_str,
            f"{result.get('time', 0):.6f}",
            f"{result.get('memory', 'N/A')}" if result.get('memory') is not None else 'N/A'
        ]
        rows.append(row)
    
    if RICH_AVAILABLE:
        table = Table(show_header=True, header_style="bold")
        for header in headers:
            table.add_column(header)
        
        for i, row in enumerate(rows):
            status = test_results[i].get('status', 'N/A')
            
            # Style based on status
            if status == 'AC':
                status_style = "bold green"
            elif status in ['WA', 'TLE', 'RE']:
                status_style = "bold red"
            else:
                status_style = "bold yellow"
            
            styled_row = [
                row[0],
                f"[{status_style}]{row[1]}[/{status_style}]",
                row[2],
                row[3]
            ]
            
            table.add_row(*styled_row)
        
        console.print(table)
    else:
        _print_table(headers, rows)
    
    # Print summary
    ac_count = sum(1 for r in test_results if r.get('status') == 'AC')
    total_count = len(test_results)
    
    if RICH_AVAILABLE:
        if ac_count == total_count:
            console.print(f"\n[bold green]All tests passed! {ac_count}/{total_count}[/bold green]")
        else:
            console.print(f"\n[bold yellow]Tests passed: {ac_count}/{total_count}[/bold yellow]")
    else:
        if ac_count == total_count:
            print(f"\nAll tests passed! {ac_count}/{total_count}")
        else:
            print(f"\nTests passed: {ac_count}/{total_count}")

def print_compare_results(compare_results: List[Dict[str, Any]]) -> None:
    """
    Print comparison test results in a nice table.
    
    Args:
        compare_results: List of comparison result dictionaries with keys:
            - test_id: ID of the test
            - match: Whether outputs match (True/False)
            - std_time: Execution time for std solution
            - force_time: Execution time for force solution
            - std_status: Status of std solution (AC, RE, TLE, RJ)
            - force_status: Status of force solution (AC, RE, TLE, RJ)
    """
    if not compare_results:
        print_warning("No comparison results to display")
        return
    
    headers = ["Test", "Result", "Std Time (s)", "Force Time (s)", "Speedup"]
    
    # Check if we have status information
    has_status = any('std_status' in result for result in compare_results)
    if has_status:
        headers = ["Test", "Result", "Std Status", "Force Status", "Std Time (s)", "Force Time (s)", "Speedup"]
    
    rows = []
    
    for result in compare_results:
        match = result.get('match', False)
        std_time = result.get('std_time', 0)
        force_time = result.get('force_time', 0)
        
        # Calculate speedup
        if force_time > 0 and std_time > 0:
            speedup = std_time / force_time
            speedup_str = f"{speedup:.2f}x"
        else:
            speedup_str = "N/A"
        
        # Format row data
        if has_status:
            std_status = result.get('std_status', 'N/A')
            force_status = result.get('force_status', 'N/A')
            row = [
                result.get('test_id', 'Unknown'),
                "Match" if match else "Mismatch",
                std_status,
                force_status,
                f"{std_time:.6f}",
                f"{force_time:.6f}",
                speedup_str
            ]
        else:
            row = [
                result.get('test_id', 'Unknown'),
                "Match" if match else "Mismatch",
                f"{std_time:.6f}",
                f"{force_time:.6f}",
                speedup_str
            ]
        rows.append(row)
    
    if RICH_AVAILABLE:
        table = Table(show_header=True, header_style="bold")
        for header in headers:
            table.add_column(header)
        
        for i, row in enumerate(rows):
            match = compare_results[i].get('match', False)
            
            # Style based on match status
            result_style = "bold green" if match else "bold red"
            result_text = f"[{result_style}]{row[1]}[/{result_style}]"
            
            # Style status if available
            if has_status:
                std_status = compare_results[i].get('std_status', 'N/A')
                force_status = compare_results[i].get('force_status', 'N/A')
                
                std_status_style = "bold green" if std_status == 'AC' else "bold red"
                force_status_style = "bold green" if force_status == 'AC' else "bold red"
                
                std_status_text = f"[{std_status_style}]{row[2]}[/{std_status_style}]"
                force_status_text = f"[{force_status_style}]{row[3]}[/{force_status_style}]"
                
                # Style speedup
                std_time = compare_results[i].get('std_time', 0)
                force_time = compare_results[i].get('force_time', 0)
                if force_time > 0 and std_time > 0:
                    speedup = std_time / force_time
                    if speedup > 1:
                        speedup_style = "bold green"
                    elif speedup < 1:
                        speedup_style = "bold red"
                    else:
                        speedup_style = "bold white"
                    speedup_text = f"[{speedup_style}]{row[6]}[/{speedup_style}]"
                else:
                    speedup_text = row[6]
                
                styled_row = [
                    row[0],
                    result_text,
                    std_status_text,
                    force_status_text,
                    row[4],
                    row[5],
                    speedup_text
                ]
            else:
                # Style speedup
                std_time = compare_results[i].get('std_time', 0)
                force_time = compare_results[i].get('force_time', 0)
                if force_time > 0 and std_time > 0:
                    speedup = std_time / force_time
                    if speedup > 1:
                        speedup_style = "bold green"
                    elif speedup < 1:
                        speedup_style = "bold red"
                    else:
                        speedup_style = "bold white"
                    speedup_text = f"[{speedup_style}]{row[4]}[/{speedup_style}]"
                else:
                    speedup_text = row[4]
                
                styled_row = [
                    row[0],
                    result_text,
                    row[2],
                    row[3],
                    speedup_text
                ]
            
            table.add_row(*styled_row)
        
        console.print(table)
    else:
        _print_table(headers, rows)
    
    # Print summary
    match_count = sum(1 for r in compare_results if r.get('match', False))
    total_count = len(compare_results)
    
    if RICH_AVAILABLE:
        if match_count == total_count:
            console.print(f"\n[bold green]All outputs match! {match_count}/{total_count}[/bold green]")
        else:
            console.print(f"\n[bold red]Outputs match: {match_count}/{total_count}[/bold red]")
    else:
        if match_count == total_count:
            print(f"\nAll outputs match! {match_count}/{total_count}")
        else:
            print(f"\nOutputs match: {match_count}/{total_count}") 