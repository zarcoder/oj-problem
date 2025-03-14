import argparse
import os
import pathlib
import random
import subprocess
import sys
import tempfile
import time
from logging import getLogger
from typing import *

import onlinejudge_command.config as config
import onlinejudge_command.format_utils as fmtutils
import onlinejudge_command.utils as utils
import onlinejudge_command.visualization as vis

logger = getLogger(__name__)


def add_subparser(subparsers: argparse.Action) -> None:
    subparser = subparsers.add_parser(
        'compare',
        aliases=['c'],
        help='compare std and force solutions with tests',
        formatter_class=argparse.RawTextHelpFormatter,
        epilog='''\
example:
    $ np compare                  # compare std and force solutions with existing test files
    $ np compare --random         # compare with random tests
    $ np compare --count=100      # run 100 random tests (with --random)
    $ np compare --seed=42        # use seed 42 for random tests (with --random)
    $ np compare --std=./std --force=./force  # specify solution paths
''',
    )
    subparser.add_argument('--dir', '-d', type=pathlib.Path, default=pathlib.Path('.'), help='specify the directory containing solutions')
    subparser.add_argument('--std', type=pathlib.Path, help='specify the path to std solution')
    subparser.add_argument('--force', type=pathlib.Path, help='specify the path to force solution')
    subparser.add_argument('--random', '-r', action='store_true', help='use random tests instead of existing test files')
    subparser.add_argument('--count', '-n', type=int, help='number of random tests to run (with --random)')
    subparser.add_argument('--seed', '-s', type=int, help='random seed (with --random)')
    subparser.add_argument('--generator', '-g', type=pathlib.Path, help='path to custom test generator (with --random)')
    subparser.add_argument('--language', '-l', type=str, help='specify the language (cpp, python, java)')
    subparser.add_argument('--timeout', '-t', type=float, help='timeout for each test in seconds')
    subparser.add_argument('--verbose', '-v', action='store_true', help='show details of each test')
    subparser.add_argument('--test-dir', type=pathlib.Path, default=pathlib.Path('test'), help='directory containing test files (default: test/)')
    subparser.add_argument('--format', '-f', default='%s.%e', help='a format string to recognize the relationship of test cases. (default: "%%s.%%e")')


def run(args: argparse.Namespace) -> bool:
    # Load config
    cfg = config.load_config()
    
    # Determine language
    language = args.language
    if language is None:
        language = cfg.get('default_language', 'cpp')
    
    # Determine paths
    if args.std:
        std_path = args.std
    else:
        std_path = args.dir / _get_filename_for_language('std', language)
    
    if args.force:
        force_path = args.force
    else:
        force_path = args.dir / _get_filename_for_language('force', language)
    
    # Check if files exist
    if not std_path.exists():
        vis.print_error(f'std solution not found: {std_path}')
        return False
    
    if not force_path.exists():
        vis.print_error(f'force solution not found: {force_path}')
        return False
    
    # Determine timeout
    timeout = args.timeout
    if timeout is None:
        timeout = cfg.get('test', {}).get('timeout', 5.0)
    
    # Prepare solutions
    vis.print_header(f"Preparing solutions")
    std_executable = _prepare_solution(std_path, language, cfg)
    force_executable = _prepare_solution(force_path, language, cfg)
    
    if std_executable is None or force_executable is None:
        return False
    
    # Check if we should use random tests
    if args.random:
        return _run_random_tests(args, std_executable, force_executable, language, timeout, cfg)
    else:
        return _run_existing_tests(args, std_executable, force_executable, language, timeout, cfg)


def _run_existing_tests(args: argparse.Namespace, std_executable: pathlib.Path, force_executable: pathlib.Path, language: str, timeout: float, cfg: Dict[str, Any]) -> bool:
    """Run comparison tests using existing test files."""
    # Check if test directory exists
    if not args.test_dir.exists():
        vis.print_error(f'Test directory not found: {args.test_dir}')
        return False
    
    # Find test files
    tests = fmtutils.glob_with_format(args.test_dir, args.format)
    if not tests:
        vis.print_error(f'No test files found in {args.test_dir}')
        vis.print_info(f'You can use --random to run random tests instead')
        return False
    
    vis.print_header(f"Running {len(tests)} existing tests")
    
    # Create progress bar if rich is available
    progress = vis.create_progress()
    compare_results = []
    
    if progress:
        with progress:
            task = progress.add_task("Running tests...", total=len(tests))
            for i, (name, paths) in enumerate(tests):
                # Only use .in files
                if len(paths) >= 1:
                    input_path = paths[0]
                    with open(input_path, 'r') as f:
                        input_data = f.read()
                    
                    result = _run_comparison_test(i, name, input_data, std_executable, force_executable, language, timeout, cfg, args)
                    compare_results.append(result)
                progress.update(task, advance=1)
    else:
        for i, (name, paths) in enumerate(tests):
            vis.print_info(f'Test {i + 1}/{len(tests)}: {name}')
            # Only use .in files
            if len(paths) >= 1:
                input_path = paths[0]
                with open(input_path, 'r') as f:
                    input_data = f.read()
                
                result = _run_comparison_test(i, name, input_data, std_executable, force_executable, language, timeout, cfg, args)
                compare_results.append(result)
    
    # Print results
    vis.print_header("Comparison Results")
    vis.print_compare_results(compare_results)
    
    # Check if all tests passed
    all_match = all(result.get('match', False) for result in compare_results)
    return all_match


def _run_random_tests(args: argparse.Namespace, std_executable: pathlib.Path, force_executable: pathlib.Path, language: str, timeout: float, cfg: Dict[str, Any]) -> bool:
    """Run comparison tests using random test data."""
    # Determine test count
    count = args.count
    if count is None:
        count = cfg.get('compare', {}).get('num_random_tests', 20)
    
    # Set random seed
    seed = args.seed
    if seed is None:
        seed = random.randint(0, 10**9)
    random.seed(seed)
    vis.print_info(f'Using random seed: {seed}')
    
    vis.print_header(f"Running {count} random tests")
    
    # Create progress bar if rich is available
    progress = vis.create_progress()
    compare_results = []
    
    if progress:
        with progress:
            task = progress.add_task("Running tests...", total=count)
            for i in range(count):
                # Generate random input
                if args.generator:
                    input_data = _generate_input_from_generator(args.generator)
                else:
                    input_data = _generate_random_input(cfg)
                
                result = _run_comparison_test(i, f"random-{i+1}", input_data, std_executable, force_executable, language, timeout, cfg, args)
                compare_results.append(result)
                progress.update(task, advance=1)
    else:
        for i in range(count):
            vis.print_info(f'Test {i + 1}/{count}')
            # Generate random input
            if args.generator:
                input_data = _generate_input_from_generator(args.generator)
            else:
                input_data = _generate_random_input(cfg)
            
            result = _run_comparison_test(i, f"random-{i+1}", input_data, std_executable, force_executable, language, timeout, cfg, args)
            compare_results.append(result)
    
    # Print results
    vis.print_header("Comparison Results")
    vis.print_compare_results(compare_results)
    
    # Check if all tests passed
    all_match = all(result.get('match', False) for result in compare_results)
    return all_match


def _run_comparison_test(
    test_index: int,
    test_name: str,
    input_data: str,
    std_executable: pathlib.Path,
    force_executable: pathlib.Path,
    language: str,
    timeout: float,
    cfg: Dict[str, Any],
    args: argparse.Namespace
) -> Dict[str, Any]:
    """Run a single comparison test with the given input data."""
    if args.verbose:
        vis.print_info('Input:')
        print(input_data)
    
    # Run std solution
    std_output, std_time = _run_solution(std_executable, input_data, language, timeout, cfg)
    
    if std_output is None:
        vis.print_error('std solution failed')
        return {
            'test_id': test_name,
            'match': False,
            'std_time': 0,
            'force_time': 0,
            'error': 'std solution failed'
        }
    
    # Run force solution
    force_output, force_time = _run_solution(force_executable, input_data, language, timeout, cfg)
    
    if force_output is None:
        vis.print_error('force solution failed')
        return {
            'test_id': test_name,
            'match': False,
            'std_time': std_time,
            'force_time': 0,
            'error': 'force solution failed'
        }
    
    # Compare outputs
    match = std_output.strip() == force_output.strip()
    
    if args.verbose:
        if match:
            vis.print_success('Outputs match')
            if args.verbose:
                vis.print_info('Output:')
                print(std_output)
        else:
            vis.print_error('Outputs do not match')
            vis.print_info('std output:')
            print(std_output)
            vis.print_info('force output:')
            print(force_output)
    
    # Save failing test case
    if not match:
        test_dir = args.dir / 'test'
        if not test_dir.exists():
            os.makedirs(test_dir)
        
        fail_in_path = test_dir / f'{test_name}.in'
        fail_std_path = test_dir / f'{test_name}.std.out'
        fail_force_path = test_dir / f'{test_name}.force.out'
        
        with open(fail_in_path, 'w') as f:
            f.write(input_data)
        with open(fail_std_path, 'w') as f:
            f.write(std_output)
        with open(fail_force_path, 'w') as f:
            f.write(force_output)
        
        vis.print_info(f'Saved failing test case to {fail_in_path}')
    
    return {
        'test_id': test_name,
        'match': match,
        'std_time': std_time,
        'force_time': force_time
    }


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


def _run_solution(executable: pathlib.Path, input_data: str, language: str, timeout: float, cfg: Dict[str, Any]) -> Tuple[Optional[str], float]:
    """
    Run solution with the given input.
    
    Args:
        executable: Path to executable
        input_data: Input data
        language: Language (cpp, python, java)
        timeout: Timeout in seconds
        cfg: Configuration
        
    Returns:
        Tuple of (output, time) or (None, 0) if execution failed
    """
    if language == 'cpp':
        run_cmd = cfg.get('commands', {}).get('cpp_run', './{executable}')
        run_cmd = run_cmd.format(executable=executable)
    elif language == 'python':
        run_cmd = cfg.get('commands', {}).get('python_run', 'python3 {input}')
        run_cmd = run_cmd.format(input=executable)
    elif language == 'java':
        classname = executable.stem
        run_cmd = cfg.get('commands', {}).get('java_run', 'java -cp {dir} {classname}')
        run_cmd = run_cmd.format(dir=executable.parent, classname=classname)
    else:
        vis.print_error(f'Unsupported language: {language}')
        return None, 0
    
    try:
        start_time = time.time()
        process = subprocess.run(
            run_cmd,
            shell=True,
            input=input_data,
            text=True,
            capture_output=True,
            timeout=timeout
        )
        end_time = time.time()
        
        if process.returncode != 0:
            vis.print_error(f'Execution failed with return code {process.returncode}')
            if process.stderr:
                vis.print_error(f'Error: {process.stderr}')
            return None, 0
        
        return process.stdout, end_time - start_time
    
    except subprocess.TimeoutExpired:
        vis.print_error(f'Execution timed out after {timeout:.1f} seconds')
        return None, 0
    
    except Exception as e:
        vis.print_error(f'Execution failed: {e}')
        return None, 0


def _generate_input_from_generator(generator_path: pathlib.Path) -> str:
    """
    Generate input using a custom generator.
    
    Args:
        generator_path: Path to generator
        
    Returns:
        Generated input
    """
    try:
        process = subprocess.run(
            [str(generator_path)],
            text=True,
            capture_output=True,
            check=True
        )
        return process.stdout
    
    except subprocess.CalledProcessError as e:
        vis.print_error(f'Generator failed: {e.stderr}')
        return ""
    
    except Exception as e:
        vis.print_error(f'Generator failed: {e}')
        return ""


def _generate_random_input(cfg: Dict[str, Any]) -> str:
    """
    Generate random input.
    
    Args:
        cfg: Configuration
        
    Returns:
        Generated input
    """
    max_size = cfg.get('compare', {}).get('max_random_size', 100)
    
    # Generate a random array problem
    n = random.randint(1, max_size)
    
    lines = []
    lines.append(str(n))
    
    # Generate n random integers
    a = [random.randint(1, 1000) for _ in range(n)]
    lines.append(' '.join(map(str, a)))
    
    return '\n'.join(lines) 