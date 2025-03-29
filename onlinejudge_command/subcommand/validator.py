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

def add_subparser(subparsers: argparse.Action) -> None:
    subparser = subparsers.add_parser(
        'validator',
        aliases=['v'],
        help='validate test cases using input validators',
        formatter_class=argparse.RawTextHelpFormatter,
        epilog='''\
example:
    $ np v                     # validate all test cases in data/sample and data/secret directories
    $ np v --only-sample       # validate only test cases in data/sample
    $ np v --only-secret       # validate only test cases in data/secret
    $ np v --test=sample1.in   # validate a specific test case
''',
    )
    subparser.add_argument('--dir', '-d', type=pathlib.Path, default=pathlib.Path('.'), help='specify the problem directory')
    subparser.add_argument('--test', '-t', type=str, help='specify a specific test file to validate (provide filename only)')
    subparser.add_argument('--validator', '-v', type=pathlib.Path, help='specify a specific validator script (default: all scripts in input_validators directory)')
    subparser.add_argument('--only-sample', action='store_true', help='validate only sample test cases')
    subparser.add_argument('--only-secret', action='store_true', help='validate only secret test cases')


def run(args: argparse.Namespace) -> bool:
    # Get the base problem directory
    problem_dir = args.dir
    
    # Find validators
    validator_dir = problem_dir / 'input_validators'
    if not validator_dir.exists() and not args.validator:
        # Try old directory structure
        old_validator = problem_dir / 'validator.py'
        if old_validator.exists():
            logger.warning('Using old-style validator: %s', old_validator)
            validator_scripts = [old_validator]
        else:
            logger.error('No validators found in input_validators directory: %s', validator_dir)
            return False
    else:
        if args.validator:
            # Use specified validator
            validator_scripts = [args.validator]
        else:
            # Use all validators in the directory
            validator_scripts = list(validator_dir.glob('*.py'))
            if not validator_scripts:
                logger.warning('No Python validators found in: %s', validator_dir)
                # Look for other executables
                validator_scripts = [f for f in validator_dir.iterdir() 
                                    if f.is_file() and os.access(f, os.X_OK)]
                if not validator_scripts:
                    logger.error('No executable validators found in: %s', validator_dir)
                    return False
        
    # Make sure all validators are executable
    for validator in validator_scripts:
        if not os.access(validator, os.X_OK):
            logger.warning('Validator script is not executable, making it executable: %s', validator)
            os.chmod(validator, 0o755)
    
    # Find test directories
    test_dirs = []
    if not args.only_secret:
        sample_dir = problem_dir / 'data' / 'sample'
        if sample_dir.exists():
            test_dirs.append(('sample', sample_dir))
    
    if not args.only_sample:
        secret_dir = problem_dir / 'data' / 'secret'
        if secret_dir.exists():
            test_dirs.append(('secret', secret_dir))
    
    # If no new-style directories found, try old directory structure
    if not test_dirs:
        old_test_dir = problem_dir / 'test'
        if old_test_dir.exists():
            logger.warning('Using old-style test directory: %s', old_test_dir)
            test_dirs.append(('test', old_test_dir))
        else:
            logger.error('No test directories found')
            return False
    
    # Get the list of test files to validate
    test_files = []
    if args.test:
        # Find specific test file in all test directories
        found = False
        for test_type, test_dir in test_dirs:
            test_path = test_dir / args.test
            if test_path.exists():
                test_files.append((test_type, test_path))
                found = True
        
        if not found:
            logger.error('Test file not found: %s', args.test)
            logger.info('Looked in: %s', ', '.join(str(d[1]) for d in test_dirs))
            return False
    else:
        # Collect all test files from each directory
        for test_type, test_dir in test_dirs:
            dir_files = sorted(test_dir.glob('*.in'))
            for f in dir_files:
                test_files.append((test_type, f))
        
        if not test_files:
            logger.warning('No test files found in any directory')
            return True
    
    # Validate each test file with each validator
    all_success = True
    total_tests = len(test_files) * len(validator_scripts)
    success_count = 0
    failure_count = 0
    
    for validator in validator_scripts:
        logger.info('Using validator: %s', validator)
        
        for test_type, test_file in test_files:
            logger.info('Validating %s: %s', test_type, test_file.name)
            
            try:
                # Run the validator on the test file
                with open(test_file, 'r') as f:
                    input_data = f.read()
                    
                process = subprocess.run(
                    [str(validator)],
                    input=input_data,
                    text=True,
                    capture_output=True,
                    check=False
                )
                
                if process.returncode == 0:
                    logger.info('[SUCCESS] %s/%s is valid', test_type, test_file.name)
                    success_count += 1
                else:
                    logger.error('[FAILURE] %s/%s is invalid', test_type, test_file.name)
                    if process.stderr:
                        logger.error('Error message: %s', process.stderr.strip())
                    failure_count += 1
                    all_success = False
            
            except Exception as e:
                logger.error('[ERROR] Failed to validate %s/%s: %s', test_type, test_file.name, str(e))
                failure_count += 1
                all_success = False
    
    # Print summary
    logger.info('')
    logger.info('Validation summary:')
    logger.info('  %d test files validated with %d validators', len(test_files), len(validator_scripts))
    logger.info('  %d validations passed, %d validations failed', success_count, failure_count)
    
    return all_success 
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
