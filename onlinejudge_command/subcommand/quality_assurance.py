import argparse
import os
import pathlib
import subprocess
import sys
from logging import getLogger
from typing import *

import onlinejudge_command.config as config
import onlinejudge_command.format_utils as fmtutils
import onlinejudge_command.utils as utils
import onlinejudge_command.visualization as vis
from onlinejudge_command.subcommand import validator, test, compare
from onlinejudge_command.output_comparators import CompareMode
from onlinejudge_command.subcommand.test import DisplayMode

logger = getLogger(__name__)


def add_subparser(subparsers: argparse.Action) -> None:
    subparser = subparsers.add_parser(
        'quality-assurance',
        aliases=['qa'],
        help='run a complete quality assurance check on the problem',
        formatter_class=argparse.RawTextHelpFormatter,
        epilog='''\
example:
    $ np qa                  # run all quality assurance checks
    $ np qa --skip-validator # skip validator check
    $ np qa --skip-test      # skip test check
    $ np qa --skip-compare   # skip compare check
''',
    )
    subparser.add_argument('--dir', '-d', type=pathlib.Path, default=pathlib.Path('.'), help='specify the directory containing the problem')
    subparser.add_argument('--test-dir', type=pathlib.Path, default=pathlib.Path('test'), help='directory containing test files (default: test/)')
    subparser.add_argument('--format', '-f', default='%s.%e', help='a format string to recognize the relationship of test cases. (default: "%%s.%%e")')
    subparser.add_argument('--language', '-l', type=str, help='specify the language (cpp, python, java)')
    subparser.add_argument('--timeout', '-t', type=float, help='timeout for each test in seconds')
    subparser.add_argument('--skip-validator', action='store_true', help='skip validator check')
    subparser.add_argument('--skip-test', action='store_true', help='skip test check')
    subparser.add_argument('--skip-compare', action='store_true', help='skip compare check')
    subparser.add_argument('--verbose', '-v', action='store_true', help='show details of each test')


def run(args: argparse.Namespace) -> bool:
    # Load config
    cfg = config.load_config()
    
    # Determine language
    language = args.language
    if language is None:
        language = cfg.get('default_language', 'cpp')
    
    # Check if test directory exists
    test_dir = args.dir / args.test_dir
    if not test_dir.exists():
        vis.print_error(f'Test directory not found: {test_dir}')
        return False
    
    # Find test files
    tests = fmtutils.glob_with_format(test_dir, args.format)
    if not tests:
        vis.print_error(f'No test files found in {test_dir}')
        return False
    
    vis.print_header(f"Quality Assurance Check")
    vis.print_info(f"Found {len(tests)} test cases")
    
    # Step 1: Run validator check
    validator_success = True
    if not args.skip_validator:
        vis.print_header("Step 1: Validator Check")
        
        # Create validator args
        validator_args = argparse.Namespace()
        validator_args.dir = args.dir
        validator_args.test = None
        validator_args.validator = './input_validators/validate.py'
        validator_args.only_sample = False
        validator_args.only_secret = False
        validator_args.silent = False
        
        # Run validator
        validator_success = validator.run(validator_args)
        
        if validator_success:
            vis.print_success("Validator check passed")
        else:
            vis.print_error("Validator check failed")
    else:
        vis.print_info("Validator check skipped")
    
    # Step 2: Run test check
    test_success = True
    if not args.skip_test and validator_success:
        vis.print_header("Step 2: Test Check")
        
        # Determine std path
        std_path = args.dir / _get_filename_for_language('std', language)
        if not std_path.exists():
            vis.print_error(f'std solution not found: {std_path}')
            return False
        
        # Create test args
        test_args = argparse.Namespace()
        test_args.command = f"./std" if language == "cpp" else f"python3 std.py" if language == "python" else f"java Std"
        test_args.format = args.format
        test_args.directory = args.test_dir
        test_args.timeout = args.timeout
        test_args.verbose = args.verbose
        test_args.jobs = None
        test_args.ignore_backup = True
        test_args.judge = None
        test_args.compare_mode = CompareMode.CRLF_INSENSITIVE_EXACT_MATCH.value
        test_args.display_mode = DisplayMode.SUMMARY.value
        test_args.error = None
        test_args.test = []
        test_args.tle = args.timeout
        test_args.mle = None
        test_args.print_input = True
        test_args.silent = False
        test_args.gnu_time = None
        test_args.judge_command = None
        test_args.select = None
        test_args.language = language
        
        # Prepare std solution
        vis.print_info(f"Preparing std solution")
        std_executable = _prepare_solution(std_path, language, cfg)
        if std_executable is None:
            return False
        
        # Run test
        test_result = test.run(test_args)
        test_success = test_result == 0
        
        if test_success:
            vis.print_success("Test check passed")
        else:
            vis.print_error("Test check failed")
    else:
        if not validator_success:
            vis.print_warning("Test check skipped due to validator failure")
        else:
            vis.print_info("Test check skipped")
    
    # Step 3: Run compare check
    compare_success = True
    if not args.skip_compare and validator_success and test_success:
        vis.print_header("Step 3: Compare Check")
        
        # Create compare args
        compare_args = argparse.Namespace()
        compare_args.dir = args.dir
        compare_args.std = None
        compare_args.force = None
        compare_args.random = False
        compare_args.count = None
        compare_args.seed = None
        compare_args.generator = None
        compare_args.language = language
        compare_args.timeout = args.timeout
        compare_args.verbose = args.verbose
        compare_args.test_dir = args.test_dir
        compare_args.format = args.format
        
        # Run compare
        compare_success = compare.run(compare_args)
        
        if compare_success:
            vis.print_success("Compare check passed")
        else:
            vis.print_error("Compare check failed")
    else:
        if not validator_success or not test_success:
            vis.print_warning("Compare check skipped due to previous failures")
        else:
            vis.print_info("Compare check skipped")
    
    # Final result
    vis.print_header("Quality Assurance Summary")
    
    if validator_success and test_success and compare_success:
        vis.print_success("All checks passed!")
        return True
    else:
        vis.print_error("Some checks failed")
        if not validator_success:
            vis.print_error("- Validator check failed")
        if not test_success:
            vis.print_error("- Test check failed")
        if not compare_success:
            vis.print_error("- Compare check failed")
        return False


def _get_filename_for_language(file_type: str, language: str) -> str:
    """
    Get filename for the given file type and language.
    
    Args:
        file_type: Type of file (std, force)
        language: Language (cpp, python, java)
        
    Returns:
        Filename with appropriate extension
    """
    if language == 'cpp':
        return f"{file_type}.cpp"
    elif language == 'python':
        return f"{file_type}.py"
    elif language == 'java':
        return f"{file_type.capitalize()}.java"
    else:
        return f"{file_type}.{language}"


def _prepare_solution(path: pathlib.Path, language: str, cfg: Dict[str, Any]) -> Optional[pathlib.Path]:
    """
    Prepare solution for execution (compile if needed).
    
    Args:
        path: Path to solution file
        language: Language (cpp, python, java)
        cfg: Configuration
        
    Returns:
        Path to executable, or None if preparation failed
    """
    if language == 'cpp':
        # Compile C++ solution
        executable = path.with_suffix('')
        compile_cmd = cfg.get('commands', {}).get('cpp_compile', 'g++ -std=c++17 -O2 -o {output} {input}')
        compile_cmd = compile_cmd.format(input=path, output=executable)
        
        vis.print_info(f'Compiling {path}...')
        try:
            subprocess.run(compile_cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            vis.print_success('Compilation successful')
            return executable
        except subprocess.CalledProcessError as e:
            vis.print_error(f'Compilation failed: {e.stderr.decode()}')
            return None
    
    elif language == 'java':
        # Compile Java solution
        compile_cmd = cfg.get('commands', {}).get('java_compile', 'javac {input}')
        compile_cmd = compile_cmd.format(input=path)
        
        vis.print_info(f'Compiling {path}...')
        try:
            subprocess.run(compile_cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            vis.print_success('Compilation successful')
            return path
        except subprocess.CalledProcessError as e:
            vis.print_error(f'Compilation failed: {e.stderr.decode()}')
            return None
    
    else:
        # No compilation needed for Python and other interpreted languages
        return path 