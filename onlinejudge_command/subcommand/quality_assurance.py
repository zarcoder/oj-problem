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
            test_dir_path = pathlib.Path('data')  # 使用主 data 目录，让子命令扫描子目录
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
                test_dir_path = pathlib.Path('test')
                vis.print_warning(f'data/ not found, using legacy test/ directory instead')
            else:
                # 尝试查找 solution/accepted 目录中的解决方案
                solution_dir = args.dir / 'solution' / 'accepted'
                if solution_dir.exists() and any(solution_dir.iterdir()):
                    vis.print_warning(f'No test directory found, but solutions exist in solution/accepted/')
                    vis.print_warning(f'Please create test cases in data/ directory first')
                else:
                    vis.print_error(f'Test directory not found: {test_dir}')
                return False
        else:
            # 尝试使用新格式
            new_test_dir = args.dir / 'data'
            if new_test_dir.exists():
                test_dir = new_test_dir
                test_dir_path = pathlib.Path('data')
                vis.print_warning(f'test/ not found, using data/ directory instead')
            else:
                vis.print_error(f'Test directory not found: {test_dir}')
                return False
    
    # 确定解决方案目录
    solution_dir = args.dir / 'solution' / 'accepted'
    
    vis.print_header(f"Quality Assurance Check")
    
    # 步骤 1: 验证器检查 - 直接调用 validator.run
    validator_success = True
    if not args.skip_validator:
        vis.print_header("Step 1: Validator Check")
        
        # 创建验证器参数对象
        validator_args = argparse.Namespace()
        # 使用在 validator.py 中定义的参数
        validator_args.validator = None  # 让 validator.py 使用默认验证器
        validator_args.silent = False
        validator_args.only_sample = False
        validator_args.only_secret = False
        
        # 运行验证器
        validator_success = validator.run(validator_args)
        
        if validator_success:
            vis.print_success("Validator check passed")
        else:
            vis.print_error("Validator check failed")
    else:
        vis.print_info("Validator check skipped")
    
    # 步骤 2: 测试检查 - 直接调用 test.run
    test_success = True
    if not args.skip_test and validator_success:
        vis.print_header("Step 2: Test Check")
        
        # 创建测试参数对象
        test_args = argparse.Namespace()
        # 使用 test.py 中定义的参数
        test_args.command = None  # 让 test.py 自动选择命令
        test_args.format = args.format
        test_args.directory = test_dir_path  # 使用相对路径
        test_args.compare_mode = 'crlf-insensitive-exact-match'
        test_args.display_mode = 'summary'
        test_args.error = None
        test_args.tle = args.timeout
        test_args.mle = None
        test_args.print_input = True
        test_args.no_print_input = False
        test_args.jobs = None
        test_args.print_memory = True
        test_args.gnu_time = None
        test_args.ignore_backup = True
        test_args.no_ignore_backup = False
        test_args.log_file = None
        test_args.judge = None
        test_args.language = language
        test_args.test = []
        test_args.solution_dir = solution_dir
        test_args.solution_file = None
        test_args.silent = False
        
        # 运行测试
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
    
    # 步骤 3: 比较检查 - 直接调用 compare.run
    compare_success = True
    if not args.skip_compare and validator_success and test_success:
        vis.print_header("Step 3: Compare Check")
        
        # 创建比较参数对象
        compare_args = argparse.Namespace()
        # 使用 compare.py 中定义的参数
        compare_args.dir = args.dir
        compare_args.directory = test_dir_path
        compare_args.format = args.format
        compare_args.command = None
        compare_args.error = None
        compare_args.silent = False
        compare_args.ignore_backup = True
        compare_args.no_ignore_backup = False
        compare_args.tle = args.timeout
        compare_args.compare_mode = 'crlf-insensitive-exact-match'
        compare_args.jobs = None
        compare_args.judge = None
        compare_args.language = language
        compare_args.all = True  # 默认比较所有解决方案
        compare_args.no_all = False  # 不禁用全部比较
        compare_args.random = False
        compare_args.count = None
        compare_args.seed = None
        compare_args.generator = None
        compare_args.verbose = False
        compare_args.test_dir = test_dir_path
        compare_args.std = None  # compare.py 需要这个参数
        compare_args.force = None
        compare_args.timeout = args.timeout
        
        # 运行比较
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
    
    # 最终结果
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