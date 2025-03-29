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
    $ np compare                  # compare std solution with all other solutions using all test data
    $ np compare --no-all         # compare only std and brute_force solutions (like original behavior)
    $ np compare --random         # compare with random tests
    $ np compare --count=100      # run 100 random tests (with --random)
    $ np compare --seed=42        # use seed 42 for random tests (with --random)
    $ np compare --std=./std --force=./force  # specify solution paths
    $ np compare --language=cpp   # specify language for solutions
    $ np compare --test-dir=data/sample  # use only sample tests instead of all tests

note:
    By default, the command will:
    - Use all test files in data/ directory (both sample and secret)
    - Compare standard solution with all other solutions in solution/ directory
    - Look for standard solution in solution/accepted/*.{language}
    
    If a specific language is not specified or a file with the specified language is not found,
    the command will try to find any solution file with supported languages (cpp, py, java).
    
    If no solution files are found in the solution directories, it will fall back to
    std.cpp and force.cpp in the current directory.
''',
    )
    subparser.add_argument('--dir', '-d', type=pathlib.Path, default=pathlib.Path('.'), help='specify the directory containing solutions')
    subparser.add_argument('--std', type=pathlib.Path, help='specify the path to std solution')
    subparser.add_argument('--force', type=pathlib.Path, help='specify the path to force solution')
    subparser.add_argument('--all', action='store_true', default=True, help='compare std solution with all other solutions (default: True)')
    subparser.add_argument('--no-all', action='store_false', dest='all', help='only compare std and brute_force solutions (disable --all)')
    subparser.add_argument('--random', '-r', action='store_true', help='use random tests instead of existing test files')
    subparser.add_argument('--count', '-n', type=int, help='number of random tests to run (with --random)')
    subparser.add_argument('--seed', '-s', type=int, help='random seed (with --random)')
    subparser.add_argument('--generator', '-g', type=pathlib.Path, help='path to custom test generator (with --random)')
    subparser.add_argument('--language', '-l', type=str, help='specify the language (cpp, python, java)')
    subparser.add_argument('--timeout', '-t', type=float, help='timeout for each test in seconds')
    subparser.add_argument('--verbose', '-v', action='store_true', help='show details of each test')
    subparser.add_argument('--test-dir', type=pathlib.Path, default=None, help='directory containing test files (default: data/)')
    subparser.add_argument('--format', '-f', default='%s.%e', help='a format string to recognize the relationship of test cases. (default: "%%s.%%e")')


def run(args: argparse.Namespace) -> bool:
    # Load config
    cfg = config.load_config()
    
    # Determine language
    language = args.language
    if language is None:
        language = cfg.get('default_language', 'cpp')
    
    # Map language aliases
    language_map = {
        'python': 'py',
        'python3': 'py',
        'c++': 'cpp',
    }
    language = language_map.get(language.lower(), language) if language else language
    
    # Find standard solution
    if args.std:
        std_path = args.std
    else:
        solution_found = False
        
        # First try to find in solution/accepted directory
        solution_dir = args.dir / 'solution' / 'accepted'
        if solution_dir.exists():
            # Try to find file with specified language first
            found = False
            if language:
                for file in solution_dir.glob(f'*.{language}'):
                    std_path = file
                    found = True
                    solution_found = True
                    vis.print_info(f'Using standard solution: {std_path}')
                    break
            
            # If not found with specified language, try any supported language
            if not found:
                for lang in ['cpp', 'py', 'java']:
                    if found:
                        break
                    for file in solution_dir.glob(f'*.{lang}'):
                        std_path = file
                        language = lang  # Update language to match found file
                        found = True
                        solution_found = True
                        vis.print_info(f'Using standard solution: {std_path} (language: {language})')
                        break
        
        # If no solution found in accepted/, search entire solution/ directory
        if not solution_found:
            solution_root = args.dir / 'solution'
            if solution_root.exists():
                vis.print_info(f'No solution found in accepted/, searching in solution/ directory')
                # Try to find any *.cpp, *.py, or *.java files in solution/ directory (recursive)
                solution_files = []
                for ext in ['cpp', 'py', 'java']:
                    solution_files.extend(list(solution_root.glob(f'**/*.{ext}')))
                
                if solution_files:
                    # Use the first solution found
                    std_path = solution_files[0]
                    language = std_path.suffix[1:]  # Update language to match found file
                    solution_found = True
                    vis.print_info(f'Using solution: {std_path.relative_to(args.dir)} (language: {language})')
            
            # If still not found, use default
            if not solution_found:
                std_path = args.dir / _get_filename_for_language('std', language)
                vis.print_info(f'No solution files found in solution/ directory, trying {std_path}')
        
    # Check if std exists
    if not std_path.exists():
        vis.print_error(f'std solution not found: {std_path}')
        return False
    
    # Prepare standard solution
    vis.print_header(f"Preparing standard solution")
    std_executable = _prepare_solution(std_path, language, cfg)
    if std_executable is None:
        return False
    
    # If --all option is used (default), find all solutions in solution/ directory
    if args.all:
        return _compare_all_solutions(args, std_path, std_executable, language, cfg)
    
    # Regular compare flow with single force solution
    if args.force:
        force_path = args.force
    else:
        force_found = False
        
        # First try to find in solution/brute_force directory
        solution_dir = args.dir / 'solution' / 'brute_force'
        if solution_dir.exists():
            # Try to find file with specified language first
            found = False
            if language:
                for file in solution_dir.glob(f'*.{language}'):
                    force_path = file
                    found = True
                    force_found = True
                    vis.print_info(f'Using brute force solution: {force_path}')
                    break
            
            # If not found with specified language, try any supported language
            if not found:
                for lang in ['cpp', 'py', 'java']:
                    if found:
                        break
                    for file in solution_dir.glob(f'*.{lang}'):
                        force_path = file
                        found = True
                        force_found = True
                        vis.print_info(f'Using brute force solution: {force_path}')
                        break
        
        # If no dedicated force solution is found, try to find any other solution in solution/ directory
        if not force_found:
            solution_root = args.dir / 'solution'
            if solution_root.exists():
                # Look for solutions in other subdirectories (not accepted or the directory containing std)
                std_dir = std_path.parent
                other_dirs = [d for d in solution_root.iterdir() 
                             if d.is_dir() and d.name != 'accepted' and d != std_dir]
                
                if other_dirs:
                    vis.print_info(f'No dedicated brute_force solution found, using --all mode')
                    # Use implicit --all mode instead of single comparison
                    return _compare_all_solutions(args, std_path, std_executable, language, cfg)
            
            # If still no alternatives, use default
            force_path = args.dir / _get_filename_for_language('force', language)
            vis.print_info(f'No alternative solutions found, trying {force_path}')
    
    # Check if force exists
    if not force_path.exists():
        vis.print_error(f'Force solution not found: {force_path}')
        vis.print_info(f'You can try using --all to compare with all available solutions')
        return False
    
    # Prepare force solution
    vis.print_header(f"Preparing force solution")
    force_executable = _prepare_solution(force_path, language, cfg)
    if force_executable is None:
        return False
    
    # Determine timeout
    timeout = args.timeout
    if timeout is None:
        timeout = cfg.get('test', {}).get('timeout', 5.0)
    
    # Check if we should use random tests
    if args.random:
        return _run_random_tests(args, std_executable, force_executable, language, timeout, cfg)
    else:
        return _run_existing_tests(args, std_executable, force_executable, language, timeout, cfg)


def _compare_all_solutions(args: argparse.Namespace, std_path: pathlib.Path, std_executable: pathlib.Path, language: str, cfg: Dict[str, Any]) -> bool:
    """Compare standard solution with all other solutions found in solution/ directory."""
    solution_root = args.dir / 'solution'
    if not solution_root.exists():
        vis.print_error(f'Solution directory not found: {solution_root}')
        return False
    
    # Get all subdirectories in solution/ except accepted/
    solution_dirs = [d for d in solution_root.iterdir() if d.is_dir() and d.name != 'accepted']
    
    if not solution_dirs:
        vis.print_error(f'No solution directories found in {solution_root} (except accepted/)')
        return False
    
    vis.print_info(f'Found {len(solution_dirs)} solution directories to compare with standard solution')
    
    # Determine timeout
    timeout = args.timeout
    if timeout is None:
        timeout = cfg.get('test', {}).get('timeout', 5.0)
    
    all_passed = True
    solutions_found = False
    
    # Compare with each solution directory
    for solution_dir in solution_dirs:
        # Find all solution files in this directory
        solution_files = []
        
        # First specifically look for files named "solution.*"
        for ext in ['cpp', 'py', 'java']:
            solution_files.extend(list(solution_dir.glob(f'solution.{ext}')))
            
        # If no "solution.*" files found, try all files with supported extensions
        if not solution_files:
            for ext in ['cpp', 'py', 'java']:
                solution_files.extend(list(solution_dir.glob(f'*.{ext}')))
        
        # Skip empty directories silently (no warning)
        if not solution_files:
            continue
            
        # Show header only if there are files to compare
        vis.print_header(f"Checking solutions in {solution_dir.name}/")
        solutions_found = True
        
        # Compare each solution with std
        for force_path in solution_files:
            vis.print_info(f'Comparing with {force_path.relative_to(args.dir)}')
            
            # Prepare force solution
            force_executable = _prepare_solution(force_path, force_path.suffix[1:], cfg)
            if force_executable is None:
                all_passed = False
                continue
            
            # Run comparison
            if args.random:
                result = _run_random_tests(args, std_executable, force_executable, language, timeout, cfg)
            else:
                result = _run_existing_tests(args, std_executable, force_executable, language, timeout, cfg)
            
            if not result:
                all_passed = False
    
    if not solutions_found:
        vis.print_warning(f"No solution files found in any subdirectories of {solution_root}")
        return True  # Return success if no solutions to compare
        
    return all_passed


def _run_existing_tests(args: argparse.Namespace, std_executable: pathlib.Path, force_executable: pathlib.Path, language: str, timeout: float, cfg: Dict[str, Any]) -> bool:
    """Run comparison tests using existing test files."""
    # Determine test directory - if not specified, use data/ directory
    if args.test_dir is None:
        data_dir = args.dir / 'data'
        if data_dir.exists():
            test_dirs = []
            
            # Check if sample and secret directories exist
            sample_dir = data_dir / 'sample'
            secret_dir = data_dir / 'secret'
            
            found_dirs = False
            if sample_dir.exists():
                test_dirs.append(sample_dir)
                found_dirs = True
                
            if secret_dir.exists():
                test_dirs.append(secret_dir)
                found_dirs = True
                
            if not found_dirs:
                # If no sample/secret subdirectories, just use data/ itself
                test_dirs.append(data_dir)
                vis.print_info(f'Using tests from {data_dir} directory')
        else:
            # If data/ doesn't exist, try old directory structure
            test_dir = args.dir / 'test'
            if test_dir.exists():
                test_dirs = [test_dir]
                vis.print_info(f'Using tests from {test_dir} directory')
            else:
                vis.print_error(f'Test directory not found: {data_dir} or {test_dir}')
                vis.print_info(f'You can use --random to run random tests instead')
                return False
    else:
        # Use specified test directory
        test_dirs = [args.test_dir]
        if not args.test_dir.exists():
            vis.print_error(f'Test directory not found: {args.test_dir}')
            vis.print_info(f'You can use --random to run random tests instead')
            return False
    
    # Find test files from all test directories
    all_tests = []
    for test_dir in test_dirs:
        tests = fmtutils.glob_with_format(test_dir, args.format)
        if tests:
            vis.print_info(f'Found {len(tests)} tests in {test_dir}')
            all_tests.extend(tests)
    
    if not all_tests:
        vis.print_error(f'No test files found in specified directories')
        vis.print_info(f'You can use --random to run random tests instead')
        return False
    
    vis.print_header(f"Running {len(all_tests)} existing tests")
    
    # Create progress bar if rich is available
    progress = vis.create_progress()
    compare_results = []
    
    if progress:
        with progress:
            task = progress.add_task("Running tests...", total=len(all_tests))
            for i, (name, paths) in enumerate(all_tests):
                # Only use .in files
                if len(paths) >= 1:
                    input_path = paths[0]
                    with open(input_path, 'r') as f:
                        input_data = f.read()
                    
                    result = _run_comparison_test(i, name, input_data, std_executable, force_executable, language, timeout, cfg, args)
                    compare_results.append(result)
                progress.update(task, advance=1)
    else:
        for i, (name, paths) in enumerate(all_tests):
            vis.print_info(f'Test {i + 1}/{len(all_tests)}: {name}')
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
    std_output, std_time, std_status = _run_solution(std_executable, input_data, language, timeout, cfg)
    
    if std_status != 'AC':
        vis.print_error(f'std solution failed with status: {std_status}')
        return {
            'test_id': test_name,
            'match': False,
            'std_time': std_time,
            'force_time': 0,
            'std_status': std_status,
            'force_status': 'N/A',
            'error': f'std solution {std_status}'
        }
    
    # Run force solution
    force_output, force_time, force_status = _run_solution(force_executable, input_data, language, timeout, cfg)
    
    if force_status != 'AC':
        vis.print_error(f'force solution failed with status: {force_status}')
        return {
            'test_id': test_name,
            'match': False,
            'std_time': std_time,
            'force_time': force_time,
            'std_status': std_status,
            'force_status': force_status,
            'error': f'force solution {force_status}'
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
        test_dir = args.dir / 'data' / 'sample'
        if not test_dir.exists():
            # Try old directory structure if new one doesn't exist
            old_test_dir = args.dir / 'test'
            if old_test_dir.exists():
                test_dir = old_test_dir
            else:
                os.makedirs(test_dir)
        
        fail_in_path = test_dir / f'{test_name}.in'
        fail_std_path = test_dir / f'{test_name}.std.ans'
        fail_force_path = test_dir / f'{test_name}.force.ans'
        
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
        'force_time': force_time,
        'std_status': std_status,
        'force_status': force_status
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


def _run_solution(executable: pathlib.Path, input_data: str, language: str, timeout: float, cfg: Dict[str, Any]) -> Tuple[Optional[str], float, str]:
    """
    Run solution with the given input.
    
    Args:
        executable: Path to executable
        input_data: Input data
        language: Language (cpp, python, java)
        timeout: Timeout in seconds
        cfg: Configuration
        
    Returns:
        Tuple of (output, time, status) where status is one of:
        - 'AC': Accepted (successful execution)
        - 'RE': Runtime Error
        - 'TLE': Time Limit Exceeded
        - 'RJ': Rejected (other error)
    """
    if language == 'cpp':
        run_cmd = cfg.get('commands', {}).get('cpp_run', './{executable}')
        run_cmd = run_cmd.format(executable=executable)
    elif language in ['python', 'py']:
        run_cmd = cfg.get('commands', {}).get('python_run', 'python3 {input}')
        run_cmd = run_cmd.format(input=executable)
    elif language == 'java':
        classname = executable.stem
        run_cmd = cfg.get('commands', {}).get('java_run', 'java -cp {dir} {classname}')
        run_cmd = run_cmd.format(dir=executable.parent, classname=classname)
    else:
        vis.print_error(f'Unsupported language: {language}')
        return None, 0, 'RJ'
    
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
            return None, 0, 'RE'
        
        return process.stdout, end_time - start_time, 'AC'
    
    except subprocess.TimeoutExpired:
        vis.print_error(f'Execution timed out after {timeout:.1f} seconds')
        return None, timeout, 'TLE'
    
    except Exception as e:
        vis.print_error(f'Execution failed: {e}')
        return None, 0, 'RJ'


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