import argparse
import glob
import os
import pathlib
import sys
from typing import *

import onlinejudge_command.utils as utils

# 尝试导入rich库，如果不可用则使用基本输出
try:
    from rich.console import Console
    from rich.table import Table
    from rich import box
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


def add_subparser(subparsers: argparse.ArgumentParser) -> None:
    subparser = subparsers.add_parser('validator', aliases=['v'], help='validate input files', formatter_class=argparse.RawTextHelpFormatter, epilog='''\
validate input files using the specified validator

example:
    $ np validator
    $ np validator --validator ./input_validators/validate.py
    $ np validator --only-sample  # 只检测data/sample目录
    $ np validator --only-secret  # 只检测data/secret目录
''')
    subparser.add_argument('--validator', default='./input_validators/validate.py', help='validator program (default: "./input_validators/validate.py")')
    subparser.add_argument('--silent', action='store_true', help='silent mode')
    subparser.add_argument('--only-sample', action='store_true', help='only validate files in the data/sample directory')
    subparser.add_argument('--only-secret', action='store_true', help='only validate files in the data/secret directory')
    subparser.set_defaults(func=run)


def run(args: argparse.Namespace) -> bool:
    # find input files
    input_paths: List[pathlib.Path] = []
    
    # Check data/sample directory if not --only-secret
    if not args.only_secret:
        sample_dir = pathlib.Path('data/sample')
        if sample_dir.exists() and sample_dir.is_dir():
            sample_files = sorted(sample_dir.glob('*.in'))
            input_paths.extend(sample_files)
            utils.logger.info('Found {} test files in data/sample directory'.format(len(sample_files)))
        else:
            utils.logger.warning('data/sample directory doesn\'t exist')
    
    # Check data/secret directory if not --only-sample
    if not args.only_sample:
        secret_dir = pathlib.Path('data/secret')
        if secret_dir.exists() and secret_dir.is_dir():
            secret_files = sorted(secret_dir.glob('*.in'))
            input_paths.extend(secret_files)
            utils.logger.info('Found {} test files in data/secret directory'.format(len(secret_files)))
        else:
            utils.logger.warning('data/secret directory doesn\'t exist')
    
    if not input_paths:
        utils.logger.error('no input files found')
        return False
    
    # validate input files
    validator = pathlib.Path(args.validator)
    if not validator.exists():
        utils.logger.error('validator: {} doesn\'t exist'.format(validator))
        return False
    
    # Make sure the validator is executable
    if not os.access(validator, os.X_OK):
        utils.logger.warning('validator script is not executable, making it executable: {}'.format(validator))
        os.chmod(validator, 0o755)
    
    valid_count = 0
    invalid_count = 0
    
    # Store validation results for table display
    validation_results = []
    
    for path in input_paths:
        utils.logger.info('validating: {}'.format(path))
        
        # Run the validator with python interpreter
        command = ["python3", str(validator)]
        with open(str(path)) as inf:
            result = utils.subprocess.run(command, stdin=inf, capture_output=True, text=True, check=False)
        
        is_valid = result.returncode == 0
        error_message = ""
        
        if is_valid:
            utils.logger.info('valid: {}'.format(path))
            valid_count += 1
        else:
            # 收集错误信息
            if result.stderr:
                error_message = result.stderr.strip()
                utils.logger.error(error_message)
            elif result.stdout:
                error_message = result.stdout.strip()
                utils.logger.error(error_message)
            
            utils.logger.error('invalid: {}'.format(path))
            invalid_count += 1
        
        validation_results.append({
            "file": str(path),
            "is_valid": is_valid,
            "error": error_message
        })
    
    # Print summary
    utils.logger.info('validation summary: {} valid file(s) and {} invalid file(s)'.format(valid_count, invalid_count))
    
    # Print table visualization
    if validation_results:
        if HAS_RICH:
            print_rich_table(validation_results)
        else:
            print_basic_table(validation_results)
    
    return invalid_count == 0


def print_rich_table(results: List[Dict[str, Any]]) -> None:
    """Print validation results in a rich table format."""
    console = Console()
    
    table = Table(title="Validation Results", box=box.ROUNDED)
    
    # Add columns
    table.add_column("File", style="cyan")
    table.add_column("Status", style="cyan")
    table.add_column("Error Message", style="cyan")
    
    # Add rows
    for result in results:
        file_name = result["file"]
        status = "✓ Valid" if result["is_valid"] else "✗ Invalid"
        status_style = "green" if result["is_valid"] else "red"
        error = result.get("error", "")
        
        # Truncate error message if too long
        if len(error) > 50:
            error = error[:47] + "..."
        
        table.add_row(
            file_name,
            status,
            error,
            style=None if result["is_valid"] else "red"
        )
    
    # Print the table
    console.print(table)


def print_basic_table(results: List[Dict[str, Any]]) -> None:
    """Print validation results in a basic table format."""
    # Find the maximum width for each column
    max_file_width = max(len(result["file"]) for result in results)
    max_file_width = max(max_file_width, len("File"))
    max_status_width = max(len("✓ Valid"), len("✗ Invalid"))
    
    # 计算错误消息的最大宽度，但限制在合理范围内
    error_messages = [result.get("error", "") for result in results]
    max_error_width = max(len(msg) for msg in error_messages) if error_messages else 0
    max_error_width = max(max_error_width, len("Error Message"))
    max_error_width = min(max_error_width, 50)  # 限制错误消息宽度
    
    # Calculate total table width
    total_width = max_file_width + max_status_width + max_error_width + 10  # 10 for padding and separators
    
    # Print table header
    utils.logger.info("╭" + "─" * total_width + "╮")
    utils.logger.info("│ Validation Results" + " " * (total_width - 19) + "│")
    utils.logger.info("├" + "─" * max_file_width + "┬" + "─" * max_status_width + "┬" + "─" * max_error_width + "┤")
    utils.logger.info("│ " + "File".ljust(max_file_width - 1) + "│ " + "Status".ljust(max_status_width - 1) + "│ " + "Error Message".ljust(max_error_width - 1) + "│")
    utils.logger.info("├" + "─" * max_file_width + "┼" + "─" * max_status_width + "┼" + "─" * max_error_width + "┤")
    
    # Print table rows
    for result in results:
        file_name = result["file"]
        status = "✓ Valid" if result["is_valid"] else "✗ Invalid"
        error = result.get("error", "")
        
        # Truncate error message if too long
        if len(error) > max_error_width - 1:
            error = error[:max_error_width - 4] + "..."
        
        utils.logger.info("│ " + file_name.ljust(max_file_width - 1) + "│ " + status.ljust(max_status_width - 1) + "│ " + error.ljust(max_error_width - 1) + "│")
    
    # Print table footer
    utils.logger.info("╰" + "─" * max_file_width + "┴" + "─" * max_status_width + "┴" + "─" * max_error_width + "╯") 