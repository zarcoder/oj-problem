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