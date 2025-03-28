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
    $ np qa                      # run all quality assurance checks
    $ np qa --skip-validator     # skip validator check
    $ np qa --skip-test          # skip test check
    $ np qa --skip-compare       # skip compare check
    $ np qa --use-legacy-format  # use old directory format (test/ instead of data/sample/)
''',
    )
    subparser.add_argument('--dir', '-d', type=pathlib.Path, default=pathlib.Path('.'), help='specify the directory containing the problem')
    subparser.add_argument('--test-dir', type=pathlib.Path, default=None, help='directory containing test files (default: data/sample/ or test/)')
    subparser.add_argument('--format', '-f', default='%s.%e', help='a format string to recognize the relationship of test cases. (default: "%%s.%%e")')
    subparser.add_argument('--language', '-l', type=str, help='specify the language (cpp, python, java)')
    subparser.add_argument('--timeout', '-t', type=float, help='timeout for each test in seconds')
    subparser.add_argument('--skip-validator', action='store_true', help='skip validator check')
    subparser.add_argument('--skip-test', action='store_true', help='skip test check')
    subparser.add_argument('--skip-compare', action='store_true', help='skip compare check')
    subparser.add_argument('--verbose', '-v', action='store_true', help='show details of each test')
    subparser.add_argument('--use-legacy-format', action='store_true', help='use old directory format (test/ instead of data/sample/)')


def run(args: argparse.Namespace) -> bool:
    # Load config
    cfg = config.load_config()
    
    # Determine language
    language = args.language
    if language is None:
        language = cfg.get('default_language', 'cpp')
    
    # 确定测试目录
    # 如果没有明确指定 test_dir，则根据是否使用旧格式来决定目录
    if args.test_dir is None:
        if args.use_legacy_format:
            test_dir_path = pathlib.Path('test')
        else:
            test_dir_path = pathlib.Path('data/sample')
    else:
        test_dir_path = args.test_dir
    
    # 构建完整路径
    test_dir = args.dir / test_dir_path
    
    # 如果指定的目录不存在，尝试使用其他格式
    if not test_dir.exists():
        # 如果当前使用新格式但目录不存在，尝试旧格式
        if not args.use_legacy_format:
            legacy_test_dir = args.dir / 'test'
            if legacy_test_dir.exists():
                test_dir = legacy_test_dir
                vis.print_warning(f'data/sample/ not found, using legacy test/ directory instead')
            else:
                # 尝试查找 solution/accepted 目录中的解决方案
                solution_dir = args.dir / 'solution' / 'accepted'
                if solution_dir.exists() and any(solution_dir.iterdir()):
                    vis.print_warning(f'No test directory found, but solutions exist in solution/accepted/')
                    vis.print_warning(f'Please create test cases in data/sample/ directory first')
                else:
                    vis.print_error(f'Test directory not found: {test_dir}')
                return False
        else:
            # 尝试使用新格式
            new_test_dir = args.dir / 'data' / 'sample'
            if new_test_dir.exists():
                test_dir = new_test_dir
                vis.print_warning(f'test/ not found, using data/sample/ directory instead')
            else:
                vis.print_error(f'Test directory not found: {test_dir}')
                return False
    
    # 确定解决方案路径
    # 首先检查新结构中是否有解决方案
    solution_dir = args.dir / 'solution' / 'accepted'
    has_solution_in_new_structure = False
    solution_path = None
    
    if solution_dir.exists():
        # 查找解决方案文件
        for extension in ['.cpp', '.py', '.java']:
            potential_solution = solution_dir / f"solution{extension}"
            if potential_solution.exists():
                solution_path = potential_solution
                has_solution_in_new_structure = True
                break
    
    # 如果在新结构中没有找到解决方案，使用旧的std文件
    if not has_solution_in_new_structure:
        solution_path = args.dir / _get_filename_for_language('std', language)
    
    # Find test files
    tests = fmtutils.glob_with_format(test_dir, args.format)
    if not tests:
        vis.print_error(f'No test files found in {test_dir}')
        return False
    
    vis.print_header(f"Quality Assurance Check")
    vis.print_info(f"Found {len(tests)} test cases in {test_dir}")
    
    # Step 1: Run validator check
    validator_success = True
    if not args.skip_validator:
        vis.print_header("Step 1: Validator Check")
        
        # Create validator args
        validator_args = argparse.Namespace()
        validator_args.dir = args.dir
        validator_args.test = None
<<<<<<< HEAD
        validator_args.validator = None
        validator_args.test_dir = None  # 让validator子命令自行决定目录
        validator_args.only_sample = False
        validator_args.only_secret = False
=======
        validator_args.validator = './input_validators/validate.py'
        validator_args.only_sample = False
        validator_args.only_secret = False
        validator_args.silent = False
>>>>>>> 6e8c1fd8e1ff6025d18e041f2ca1efd0e44d2228
        
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
        
        # 检查解决方案文件是否存在
        if not solution_path or not solution_path.exists():
            # 尝试在 solution/accepted/ 目录下查找解决方案
            solution_dir = args.dir / 'solution' / 'accepted'
            if solution_dir.exists():
                for ext in ['.cpp', '.py', '.java']:
                    potential_solution = solution_dir / f"solution{ext}"
                    if potential_solution.exists():
                        solution_path = potential_solution
                        has_solution_in_new_structure = True
                        break
            
            # 如果仍然找不到解决方案
            if not solution_path or not solution_path.exists():
                vis.print_error(f'Solution not found: {solution_path}')
                return False
        
        # 确定运行命令
        if has_solution_in_new_structure:
            if solution_path.suffix == '.cpp':
                command = f"./solution" if os.name != 'nt' else "solution.exe"
            elif solution_path.suffix == '.py':
                command = f"python3 {solution_path}"
            elif solution_path.suffix == '.java':
                command = f"java -cp {solution_dir} Solution"
            else:
                vis.print_error(f'Unsupported file type: {solution_path}')
                return False
        else:
            # 使用旧格式的命令
            command = f"./std" if language == "cpp" and os.name != 'nt' else f"std.exe" if language == "cpp" else f"python3 std.py" if language == "python" else f"java Std"
        
        # Create test args
        test_args = argparse.Namespace()
        test_args.command = command
        test_args.format = args.format
        test_args.directory = str(test_dir_path)  # 使用相对路径
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
<<<<<<< HEAD
        test_args.language = language if not has_solution_in_new_structure else solution_path.suffix[1:]
        test_args.solution_file = None  # 对新版本的支持
        test_args.solution_dir = None   # 对新版本的支持
=======
        test_args.language = language
>>>>>>> 6e8c1fd8e1ff6025d18e041f2ca1efd0e44d2228
        
        # 准备解决方案
        vis.print_info(f"Preparing solution: {solution_path}")
        solution_executable = _prepare_solution(solution_path, 
                                               language if not has_solution_in_new_structure else solution_path.suffix[1:], 
                                               cfg)
        if solution_executable is None:
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
        
        # 检查是否有force解决方案
        force_path = None
        if has_solution_in_new_structure:
            # 在solution/accepted目录中查找其他解决方案
            for file in solution_dir.iterdir():
                if file.is_file() and file.name != solution_path.name:
                    force_path = file
                    break
        
        # 如果在新结构中没有找到其他解决方案，使用旧的force文件
        if not force_path:
            force_path = args.dir / _get_filename_for_language('force', language)
            if not force_path.exists():
                vis.print_warning(f"No alternative solution found for comparison (tried {force_path})")
                vis.print_info("Compare check skipped")
                return True
        
        # Create compare args
        compare_args = argparse.Namespace()
        compare_args.dir = args.dir
        compare_args.std = solution_path if has_solution_in_new_structure else None
        compare_args.force = force_path if force_path and force_path.exists() else None
        compare_args.random = False
        compare_args.count = None
        compare_args.seed = None
        compare_args.generator = None
        compare_args.language = language if not has_solution_in_new_structure else None
        compare_args.timeout = args.timeout
        compare_args.verbose = args.verbose
        compare_args.test_dir = str(test_dir_path)
        compare_args.format = args.format
        
        # 如果没有可比较的解决方案，跳过比较
        if not compare_args.force:
            vis.print_warning("No alternative solution found for comparison")
            vis.print_info("Compare check skipped")
            return True
        
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