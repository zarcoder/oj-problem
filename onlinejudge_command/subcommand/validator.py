import argparse
import glob
import os
import pathlib
import subprocess
import sys
from logging import getLogger
from typing import *

import onlinejudge_command.utils as utils

logger = getLogger(__name__)


def add_subparser(subparsers: argparse.Action) -> None:
    subparser = subparsers.add_parser(
        'validator',
        aliases=['v'],
        help='validate test cases using validator.py',
        formatter_class=argparse.RawTextHelpFormatter,
        epilog='''\
example:
    $ np v                  # validate all test cases in the test directory
    $ np v --test=test1.in  # validate a specific test case
''',
    )
    subparser.add_argument('--dir', '-d', type=pathlib.Path, default=pathlib.Path('.'), help='specify the directory containing validator.py and test directory')
    subparser.add_argument('--test', '-t', type=str, help='specify a specific test file to validate (relative to test directory)')
    subparser.add_argument('--validator', '-v', type=pathlib.Path, help='specify the validator script (default: validator.py in the current directory)')


def run(args: argparse.Namespace) -> bool:
    # Determine the validator path
    validator_path = args.validator if args.validator else args.dir / 'validator.py'
    
    # Convert to absolute path for better error messages
    validator_path = validator_path.resolve()
    
    if not validator_path.exists():
        logger.error('validator script not found: %s', validator_path)
        return False
    
    # Make sure the validator is executable
    if not os.access(validator_path, os.X_OK):
        logger.warning('validator script is not executable, making it executable: %s', validator_path)
        os.chmod(validator_path, 0o755)
    
    # Determine the test directory
    test_dir = args.dir / 'test'
    if not test_dir.exists():
        logger.error('test directory not found: %s', test_dir)
        return False
    
    # Get the list of test files to validate
    if args.test:
        test_path = test_dir / args.test
        if not test_path.exists():
            logger.error('test file not found: %s', test_path)
            return False
        test_files = [test_path]
    else:
        test_files = sorted(test_dir.glob('*.in'))
        if not test_files:
            logger.warning('no test files found in: %s', test_dir)
            return True
    
    # Validate each test file
    success_count = 0
    failure_count = 0
    
    for test_file in test_files:
        logger.info('validating: %s', test_file)
        
        try:
            # Run the validator on the test file
            with open(test_file, 'r') as f:
                input_data = f.read()
                
            process = subprocess.run(
                [str(validator_path)],
                input=input_data,
                text=True,
                capture_output=True,
                check=False
            )
            
            if process.returncode == 0:
                logger.info('[SUCCESS] %s is valid', test_file)
                success_count += 1
            else:
                logger.error('[FAILURE] %s is invalid', test_file)
                if process.stderr:
                    logger.error('Error message: %s', process.stderr.strip())
                failure_count += 1
        
        except Exception as e:
            logger.error('[ERROR] Failed to validate %s: %s', test_file, str(e))
            failure_count += 1
    
    # Print summary
    logger.info('Validation complete: %d valid, %d invalid', success_count, failure_count)
    
    return failure_count == 0 