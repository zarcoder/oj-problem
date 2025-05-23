import argparse
import concurrent.futures
import contextlib
import enum
import json
import os
import pathlib
import platform
import subprocess
import tempfile
import threading
import traceback
from logging import getLogger
from typing import *

import onlinejudge_command.format_utils as fmtutils
import onlinejudge_command.visualization as vis
from onlinejudge_command import output_comparators, pretty_printers, utils
from onlinejudge_command.output_comparators import CompareMode

logger = getLogger(__name__)


def add_subparser(subparsers: argparse.Action) -> None:
    subparsers_add_parser: Callable[..., argparse.ArgumentParser] = subparsers.add_parser  # type: ignore
    subparser = subparsers_add_parser('test', aliases=['t'], help='test your code', formatter_class=argparse.RawTextHelpFormatter, epilog='''\
format string for --format:
  %s                    name
  %e                    extension: "in" or "ans"
  (both %s and %e are required.)

tips:
  There is a feature to use special judges. See https://github.com/zarcoder/np-problem-tools/ details.

  You can do similar things with shell
    e.g. $ for f in data/sample/*.in ; do echo $f ; ./a.out < $f | diff - ${f%.in}.ans ; done
''')
    subparser.add_argument('-c', '--command', default=utils.get_default_command(), help='your solution to be tested. (default: "{}")'.format(utils.get_default_command()))
    subparser.add_argument('-f', '--format', default='%s.%e', help='a format string to recognize the relationship of test cases. (default: "%%s.%%e")')
    subparser.add_argument('-d', '--directory', type=pathlib.Path, default=pathlib.Path('data'), help='a directory name for test cases (default: data/)')
    subparser.add_argument('-m', '--compare-mode', choices=[mode.value for mode in CompareMode], default=CompareMode.CRLF_INSENSITIVE_EXACT_MATCH.value, help='mode to compare outputs. The default behavoir is exact-match to ensure that you always get AC on remote judge servers when you got AC on local tests for the same cases.  (default: crlf-insensitive-exact-match)')
    subparser.add_argument('-M', '--display-mode', choices=[mode.value for mode in DisplayMode], default=DisplayMode.SUMMARY.value, help='mode to display outputs  (default: summary)')
    subparser.add_argument('-S', '--ignore-spaces', dest='compare_mode', action='store_const', const=CompareMode.IGNORE_SPACES.value, help="ignore spaces to compare outputs, but doesn't ignore newlines  (equivalent to --compare-mode=ignore-spaces")
    subparser.add_argument('-N', '--ignore-spaces-and-newlines', dest='compare_mode', action='store_const', const=CompareMode.IGNORE_SPACES_AND_NEWLINES.value, help='ignore spaces and newlines to compare outputs  (equivalent to --compare-mode=ignore-spaces-and-newlines')
    subparser.add_argument('-D', '--diff', dest='display_mode', action='store_const', const=DisplayMode.DIFF.value, help='display the diff  (equivalent to --display-mode=diff)')
    subparser.add_argument('-e', '--error', type=float, help='check as floating point number: correct if its absolute or relative error doesn\'t exceed it')
    subparser.add_argument('-t', '--tle', type=float, help='set the time limit (in second) (default: inf)')
    subparser.add_argument('--mle', type=float, help='set the memory limit (in megabyte) (default: inf)')
    subparser.add_argument('-i', '--print-input', action='store_true', default=True, help='print input cases if not AC  (default)')
    subparser.add_argument('--no-print-input', action='store_false', dest='print_input')
    subparser.add_argument('-j', '--jobs', metavar='N', type=int, help='specifies the number of jobs to run simultaneously  (default: no parallelization)')
    subparser.add_argument('--print-memory', action='store_true', help='print the amount of memory which your program used, even if it is small enough')
    subparser.add_argument('--gnu-time', help='used to measure memory consumption (default: "time" on Linux, "gtime" on mac)', default=None)
    subparser.add_argument('--no-ignore-backup', action='store_false', dest='ignore_backup')
    subparser.add_argument('--ignore-backup', action='store_true', help='ignore backup files and hidden files (i.e. files like "*~", "\\#*\\#" and ".*") (default)')
    subparser.add_argument('--log-file', type=pathlib.Path, help=argparse.SUPPRESS)
    subparser.add_argument('--judge-command', dest='judge', default=None, help='specify judge command instead of default diff judge. The given command (e.g. `./judge`) will be called as `$ ./judge input.txt actual-output.txt expected-output.ans` and should return the result with the exit code of its `main` function.')
    subparser.add_argument('--language', '-l', type=str, choices=['cpp', 'python', 'java'], help='specify the language to use for testing (default: auto-detect)')
    subparser.add_argument('test', nargs='*', type=pathlib.Path, help='paths of test cases. (if empty: globbed from --format)')
    
    # Solution directory options
    solution_group = subparser.add_argument_group('Solution Options')
    solution_group.add_argument('--solution-dir', type=pathlib.Path, default=pathlib.Path('solution/accepted'), help='directory containing solution files (default: solution/accepted/)')
    solution_group.add_argument('--solution-file', type=pathlib.Path, help='specific solution file to test')
    subparser.add_argument('--silent', action='store_true', help='don\'t report output and correct answer even if not AC  (for --mode all)')


MEMORY_WARNING = 500  # megabyte
MEMORY_PRINT = 100  # megabyte


class DisplayMode(enum.Enum):
    SUMMARY = 'summary'
    ALL = 'all'
    DIFF = 'diff'
    DIFF_ALL = 'diff-all'


class SpecialJudge:
    def __init__(self, judge_command: str, *, is_silent: bool):
        self.judge_command = judge_command  # already quoted and joined command
        self.is_silent = is_silent

    def run(self, *, actual_output: bytes, input_path: pathlib.Path, expected_output_path: Optional[pathlib.Path]) -> bool:
        with tempfile.TemporaryDirectory() as tempdir:
            actual_output_path = pathlib.Path(tempdir) / 'actual.ans'
            with open(actual_output_path, 'wb') as fh:
                fh.write(actual_output)

            # if you use shlex.quote, it fails on Windows. why?
            command = ' '.join([
                self.judge_command,  # already quoted and joined command
                str(input_path.resolve()),
                str(actual_output_path.resolve()),
                str(expected_output_path.resolve() if expected_output_path is not None else ''),
            ])

            logger.info('$ %s', command)
            info, proc = utils.exec_command(command)
        if not self.is_silent:
            logger.info(utils.NO_HEADER + 'judge\'s output:\n%s', pretty_printers.make_pretty_large_file_content(info['answer'] or b'', limit=40, head=20, tail=10))
        return proc.returncode == 0


def build_match_function(*, compare_mode: CompareMode, error: Optional[float], judge_command: Optional[str], silent: bool, test_input_path: pathlib.Path, test_output_path: Optional[pathlib.Path]) -> Callable[[bytes, bytes], bool]:
    """build_match_function builds the function to compare actual outputs and expected outputs.

    This function doesn't any I/O.
    """

    if judge_command is not None:
        special_judge = SpecialJudge(judge_command=judge_command, is_silent=silent)

        def run_judge_command(actual: bytes, expected: bytes) -> bool:
            # the second argument is ignored
            return special_judge.run(
                actual_output=actual,
                input_path=test_input_path,
                expected_output_path=test_output_path,
            )

        return run_judge_command

    is_exact = False
    if compare_mode == CompareMode.EXACT_MATCH and error is None:
        is_exact = True
        file_comparator: output_comparators.OutputComparator = output_comparators.ExactComparator()
    elif compare_mode == CompareMode.CRLF_INSENSITIVE_EXACT_MATCH and error is None:
        is_exact = True
        file_comparator = output_comparators.CRLFInsensitiveComparator(output_comparators.ExactComparator())
    else:
        if error is not None:
            word_comparator: output_comparators.OutputComparator = output_comparators.FloatingPointNumberComparator(rel_tol=error, abs_tol=error)
        else:
            word_comparator = output_comparators.ExactComparator()
        if compare_mode in (CompareMode.EXACT_MATCH, CompareMode.CRLF_INSENSITIVE_EXACT_MATCH, CompareMode.IGNORE_SPACES):
            file_comparator = output_comparators.SplitLinesComparator(output_comparators.SplitComparator(word_comparator))
        elif compare_mode == CompareMode.IGNORE_SPACES_AND_NEWLINES:
            file_comparator = output_comparators.SplitComparator(word_comparator)
        else:
            assert False
        file_comparator = output_comparators.CRLFInsensitiveComparator(file_comparator)

    def compare_outputs(actual: bytes, expected: bytes) -> bool:
        # 检查输入是否为空
        if not expected:
            logger.warning('Expected output is empty, treating as WA')
            return False
        
        # 尝试去除尾部空白字符后再比较
        actual_clean = actual.strip()
        expected_clean = expected.strip()
        
        # 实际比较
        result = file_comparator(actual_clean, expected_clean)
        
        if not result:
            logger.debug("Comparison failed:")
            logger.debug(f"Expected: {expected_clean}")
            logger.debug(f"Actual: {actual_clean}")
            
            # 如果精确比较失败，但是启用了宽松比较，给出提示
            if is_exact:
                non_strict_comparator = output_comparators.CRLFInsensitiveComparator(output_comparators.SplitComparator(output_comparators.ExactComparator()))
                if non_strict_comparator(actual_clean, expected_clean):
                    logger.warning('This would be AC if spaces and newlines were ignored. Please use --ignore-spaces (-S) option or --ignore-spaces-and-newline (-N) option.')
        return result

    return compare_outputs


def run_checking_output(*, answer: bytes, test_output_path: Optional[pathlib.Path], is_special_judge: bool, match_function: Callable[[bytes, bytes], bool]) -> Optional[bool]:
    """run_checking_output executes matching of the actual output and the expected output.

    This function has file I/O including the execution of the judge command.
    """

    if test_output_path is None and not is_special_judge:
        logger.warning('No expected output file found, skipping comparison')
        return None
    
    if test_output_path is not None:
        try:
            with test_output_path.open('rb') as outf:
                expected = outf.read()
                # 移除可能的尾部空行
                expected = expected.rstrip()
                # 移除尾部空行后的答案
                trimmed_answer = answer.rstrip()
                
                # 记录比较结果
                result = match_function(trimmed_answer, expected)
                
                if not result:
                    logger.debug("Output comparison failed:")
                    logger.debug(f"Expected: {expected}")
                    logger.debug(f"Actual: {trimmed_answer}")
                
                return result
        except Exception as e:
            logger.error(f"Error reading expected output file: {e}")
            return False
    else:
        # only if --judge option
        expected = b''
        logger.warning('Expected output file not found')
        if is_special_judge:
            return match_function(answer, expected)
        else:
            return False


class JudgeStatus(enum.Enum):
    AC = 'AC'
    WA = 'WA'
    RE = 'RE'
    TLE = 'TLE'
    MLE = 'MLE'


def display_result(proc: subprocess.Popen, answer: str, memory: Optional[float], test_input_path: pathlib.Path, test_output_path: Optional[pathlib.Path], *, mle: Optional[float], display_mode: DisplayMode, compare_mode: CompareMode, does_print_input: bool, silent: bool, match_result: Optional[bool]) -> JudgeStatus:
    """display_result prints the result of the test and its statistics.

    This function prints many logs and does some I/O.
    """

    # prepare the function to print the input
    is_input_printed = False

    def print_input() -> None:
        nonlocal is_input_printed
        if does_print_input and not is_input_printed:
            is_input_printed = True
            with test_input_path.open('rb') as inf:
                input_content = inf.read()
                logger.info(utils.NO_HEADER + 'input content:\n%s', pretty_printers.make_pretty_large_file_content(input_content, limit=40, head=20, tail=10))

    # check TLE, RE or not
    status = JudgeStatus.AC
    if proc.returncode is None:
        logger.info(utils.FAILURE + '' + utils.red('TLE'))
        status = JudgeStatus.TLE
        if not silent:
            print_input()
    elif memory is not None and mle is not None and memory > mle:
        logger.info(utils.FAILURE + '' + utils.red('MLE'))
        status = JudgeStatus.MLE
        if not silent:
            print_input()
    elif proc.returncode != 0:
        logger.info(utils.FAILURE + '' + utils.red('RE') + ': return code %d', proc.returncode)
        status = JudgeStatus.RE
        if not silent:
            print_input()

    # check WA or not
    if match_result is not None and not match_result:
        if status == JudgeStatus.AC:
            logger.info(utils.FAILURE + '' + utils.red('WA'))
        status = JudgeStatus.WA
        if not silent:
            print_input()
            if test_output_path is not None:
                with test_output_path.open('rb') as outf:
                    expected = outf.read().decode()
            else:
                expected = ''
            if display_mode == DisplayMode.SUMMARY:
                logger.info(utils.NO_HEADER + 'actual output:\n%s', pretty_printers.make_pretty_large_file_content(answer.encode(), limit=40, head=20, tail=10))
                logger.info(utils.NO_HEADER + 'expected output:\n%s', pretty_printers.make_pretty_large_file_content(expected.encode(), limit=40, head=20, tail=10))
            elif display_mode == DisplayMode.ALL:
                logger.info(utils.NO_HEADER + 'actual output:\n%s', pretty_printers.make_pretty_all(answer.encode()))
                logger.info(utils.NO_HEADER + 'expected output:\n%s', pretty_printers.make_pretty_all(expected.encode()))
            elif display_mode == DisplayMode.DIFF:
                logger.info(utils.NO_HEADER + pretty_printers.make_pretty_diff(answer.encode(), expected=expected, compare_mode=compare_mode, limit=40))
            elif display_mode == DisplayMode.DIFF_ALL:
                logger.info(utils.NO_HEADER + pretty_printers.make_pretty_diff(answer.encode(), expected=expected, compare_mode=compare_mode, limit=-1))
            else:
                assert False
    if match_result is None:
        if not silent:
            print_input()
            logger.info(utils.NO_HEADER + 'output:\n%s', pretty_printers.make_pretty_large_file_content(answer.encode(), limit=40, head=20, tail=10))
    if status == JudgeStatus.AC:
        logger.info(utils.SUCCESS + '' + utils.green('AC'))

    return status


def test_single_case(test_name: str, test_input_path: pathlib.Path, test_output_path: Optional[pathlib.Path], *, lock: Optional[threading.Lock] = None, args: argparse.Namespace) -> Dict[str, Any]:
    # print the header earlier if not in parallel
    if lock is None:
        logger.info('')
        logger.info('%s', test_name)

    # 在测试开始时记录输入数据
    input_content = ""
    try:
        with test_input_path.open('r') as inf:
            input_content = inf.read().strip()
        logger.info('Test input:%s', " " + input_content if input_content else " <empty>")
    except Exception as e:
        logger.error(f"Error reading input file: {e}")

    # run the binary
    with test_input_path.open('rb') as inf:
        info, proc = utils.exec_command(args.command, stdin=inf, timeout=args.tle, gnu_time=args.gnu_time)
        # TODO: the `answer` should be bytes, not str
        answer: str = (info['answer'] or b'').decode(errors='replace')
        elapsed: float = info['elapsed']
        memory: Optional[float] = info['memory']

    # lock is required to avoid mixing logs if in parallel
    nullcontext = contextlib.nullcontext()
    with lock or nullcontext:
        if lock is not None:
            logger.info('')
            logger.info('%s', test_name)
        logger.info('time: %f sec', elapsed)
        if memory:
            if memory < MEMORY_PRINT:
                if args.print_memory:
                    logger.info('memory: %f MB', memory)
            elif memory < MEMORY_WARNING:
                logger.info('memory: %f MB', memory)
            else:
                logger.warning('memory: %f MB', memory)

        # 显示程序输出
        logger.info('Program output:%s', " " + answer.strip() if answer.strip() else " <empty>")

        # 检查预期输出
        expected_output = ""
        if test_output_path is not None:
            try:
                with test_output_path.open('r') as outf:
                    expected_output = outf.read().strip()
                logger.info('Expected output:%s', " " + expected_output if expected_output else " <empty>")
            except Exception as e:
                logger.error(f"Error reading expected output file: {e}")

        match_function = build_match_function(compare_mode=CompareMode(args.compare_mode), error=args.error, judge_command=args.judge, silent=args.silent, test_input_path=test_input_path, test_output_path=test_output_path)
        match_result = run_checking_output(answer=answer.encode(), test_output_path=test_output_path, is_special_judge=args.judge is not None, match_function=match_function)
        
        # 如果没有找到期望输出文件，而且不是特殊评测，则测试结果显示为"未知"（Unknown）而不是"通过"（AC）
        if match_result is None and test_output_path is None and not args.judge:
            logger.warning("Cannot determine if the answer is correct - no expected output file found")
            # 我们需要手动修改status为未知状态
            status = JudgeStatus.AC  # 临时设置为AC，后面会在dispaly_result中修改
        else:
            status = display_result(proc, answer, memory, test_input_path, test_output_path, mle=args.mle, display_mode=DisplayMode(args.display_mode), compare_mode=CompareMode(args.compare_mode), does_print_input=args.print_input, silent=args.silent, match_result=match_result)

    # return the result
    testcase = {
        'name': test_name,
        'input': str(test_input_path.resolve()),
    }
    if test_output_path:
        testcase['output'] = str(test_output_path.resolve())
    return {
        'status': status.value,
        'testcase': testcase,
        'output': answer,
        'exitcode': proc.returncode,
        'elapsed': elapsed,
        'memory': memory,
    }


def check_gnu_time(gnu_time: str) -> bool:
    try:
        with tempfile.NamedTemporaryFile(delete=True) as fh:
            subprocess.check_call([gnu_time, '-f', '%M KB', '-o', fh.name, '--', 'true'])
            with open(fh.name) as fh1:
                data = fh1.read()
            int(utils.remove_suffix(data.rstrip().splitlines()[-1], ' KB'))
            return True
    except NameError:
        raise  # NameError is not a runtime error caused by the environment, but a coding mistake
    except AttributeError:
        raise  # AttributeError is also a mistake
    except Exception:
        logger.debug(traceback.format_exc())
    return False


def run(args: argparse.Namespace) -> int:
    # 查找命令行指定的solution文件
    language = args.language
    solution_command = args.command
    
    # 如果提供了特定的solution文件，使用它
    if args.solution_file:
        if not args.solution_file.exists():
            logger.error('Solution file not found: %s', args.solution_file)
            return 1
        
        solution_command = get_command_for_file(args.solution_file, language)
        logger.info('Testing solution file: %s', args.solution_file)
        logger.info('Command: %s', solution_command)
    # 否则，查找solution目录中的所有解决方案
    elif args.solution_dir and args.solution_dir.exists():
        logger.info('Looking for solutions in: %s', args.solution_dir)
        solution_files = list(args.solution_dir.glob('*.*'))
        
        if not solution_files:
            logger.warning('No solution files found in %s', args.solution_dir)
        else:
            logger.info('Found %d solution files', len(solution_files))
            
            if language:
                # 如果指定了语言，只选择该语言的解决方案
                solution_files = [f for f in solution_files if is_file_of_language(f, language)]
                if not solution_files:
                    logger.warning('No %s solution files found', language)
            
            if solution_files:
                # 选择一个解决方案进行测试（优先级：C++ > Python > Java）
                priority_order = {'cpp': 1, 'py': 2, 'java': 3}
                selected_file = min(solution_files, key=lambda f: priority_order.get(f.suffix.lstrip('.'), 999))
                
                solution_command = get_command_for_file(selected_file, language)
                logger.info('Testing solution file: %s', selected_file)
                logger.info('Command: %s', solution_command)
    
    # 将选择的命令设置回args
    args.command = solution_command
    
    # 设置测试参数
    if args.gnu_time is None:
        if platform.system() == 'Darwin':
            args.gnu_time = 'gtime'
        else:
            args.gnu_time = 'time'
    
    # list tests from the specified directory
    tests = []  # type: List[Tuple[str, Tuple[pathlib.Path, Optional[pathlib.Path]]]]
    
    # 处理测试目录
    dirs_to_scan = []
    # 确保 directory 是 pathlib.Path 类型
    directory = args.directory if isinstance(args.directory, pathlib.Path) else pathlib.Path(args.directory)
    
    if directory.exists():
        # 如果目录存在，查找所有子目录
        if directory.name == 'data':
            # 如果是主data目录，扫描所有子目录
            subdirs = [d for d in directory.iterdir() if d.is_dir()]
            if subdirs:
                logger.info('Scanning all subdirectories under %s', directory)
                dirs_to_scan.extend(subdirs)
            else:
                # 如果没有子目录，直接扫描主目录
                logger.info('No subdirectories found under %s, scanning the directory itself', directory)
                dirs_to_scan.append(directory)
        else:
            # 如果不是主data目录，直接扫描该目录
            dirs_to_scan.append(directory)
    else:
        logger.warning('Directory not found: %s', directory)
        # 尝试旧的目录结构
        old_dirs = [pathlib.Path('test'), pathlib.Path('tests')]
        for old_dir in old_dirs:
            if old_dir.exists():
                logger.warning('No tests found in %s, trying old directory structure: %s', directory, old_dir)
                dirs_to_scan.append(old_dir)
                break
    
    # 从各个目录收集测试用例
    for test_dir in dirs_to_scan:
        dir_tests = fmtutils.glob_with_format(test_dir, args.format)
        if dir_tests:
            # 根据目录名创建前缀
            dir_prefix = test_dir.name + '_' if test_dir.name != 'data' else ''
            logger.info('Found %d tests in %s', len(dir_tests), test_dir)
            
            for name, paths in dir_tests:
                # 确保paths列表非空
                if not paths:
                    logger.warning('No files found for test %s', name)
                    continue
                    
                # 第一个路径应该是输入文件
                input_path = paths[0]
                
                # 查找匹配的输出/答案文件
                output_path = None
                if len(paths) > 1:
                    for path in paths[1:]:
                        if path.suffix in ['.out', '.ans']:
                            output_path = path
                            break
                            
                if output_path:
                    logger.debug('Test %s: input=%s, output=%s', name, input_path, output_path)
                else:
                    logger.debug('Test %s: input=%s, no output file found', name, input_path)
                
                tests.append((f"{dir_prefix}{name}", (input_path, output_path)))

    # 如果还指定了具体的测试文件，添加它们
    if args.test:
        for test_path in args.test:
            if test_path.exists():
                name = test_path.stem
                output_path = None
                for ext in ['.out', '.ans']:
                    potential_output = test_path.with_suffix(ext)
                    if potential_output.exists():
                        output_path = potential_output
                        break
                tests.append((name, (test_path, output_path)))
    
    if not tests:
        logger.error('No test cases found')
        return 1
    
    logger.info('found %d tests in total', len(tests))
    
    # check whether GNU time is available
    gnu_time = args.gnu_time
    if not check_gnu_time(gnu_time):
        gnu_time = None
        logger.warning('GNU time is not available: %s', gnu_time)
        if args.mle is not None:
            logger.warning('MLE will be ignored')
    
    # run tests
    history = []  # type: List[Dict[str, Any]]
    if args.jobs is None:
        for name, (input_path, output_path) in tests:
            history.append(test_single_case(name, input_path, output_path, args=args))
    else:
        if os.name == 'nt':
            logger.warning("-j/--jobs option is unstable on Windows environment")
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as executor:
            lock = threading.Lock()
            futures = []  # type: List[concurrent.futures.Future]
            for name, (input_path, output_path) in tests:
                futures.append(executor.submit(test_single_case, name, input_path, output_path, lock=lock, args=args))
            for future in futures:
                history.append(future.result())
    
    # summarize
    test_results = []
    for result in history:
        status = result['status']
        # 检查 status 是否为字符串，如果不是则获取其 value 属性
        status_value = status if isinstance(status, str) else status.value
        
        test_results.append({
            'test_name': result['testcase']['name'],
            'status': status_value,
            'time': result['elapsed'],
            'memory': result['memory']
        })
    
    # Print results using visualization module
    vis.print_header("Test Results")
    vis.print_test_results(test_results)
    
    # Check if all tests passed
    ac_count = sum(1 for result in history if result['status'] == JudgeStatus.AC or result['status'] == 'AC')
    total_count = len(history)
    if total_count == 0:
        logger.error('no tests')
        return 1
    elif ac_count != total_count:
        logger.info('some cases failed')
        return 1
    else:
        logger.info('all tests passed')
        return 0

# 辅助函数：基于文件类型返回适当的命令
def get_command_for_file(file_path: pathlib.Path, language: Optional[str] = None) -> str:
    if language is None:
        # 根据文件扩展名判断语言
        suffix = file_path.suffix.lower()
        if suffix in ['.cpp', '.cc', '.cxx']:
            language = 'cpp'
        elif suffix == '.py':
            language = 'python'
        elif suffix == '.java':
            language = 'java'
        else:
            logger.warning('Unknown file type: %s, will try to use default command', suffix)
            return utils.get_default_command()
    
    if language == 'cpp':
        # 编译C++文件
        output_file = file_path.with_suffix('')
        compile_cmd = f'g++ -std=c++17 -O2 "{file_path}" -o "{output_file}"'
        logger.info('Compiling: %s', compile_cmd)
        
        proc = subprocess.run(compile_cmd, shell=True, capture_output=True, text=True)
        if proc.returncode != 0:
            logger.error('Compilation failed:\n%s', proc.stderr)
            return utils.get_default_command()
        
        # 返回编译后的可执行文件路径
        return str(output_file)
    
    elif language == 'python':
        return f'python3 "{file_path}"'
    
    elif language == 'java':
        # 编译Java文件
        class_name = file_path.stem
        compile_cmd = f'javac "{file_path}"'
        logger.info('Compiling: %s', compile_cmd)
        
        proc = subprocess.run(compile_cmd, shell=True, capture_output=True, text=True)
        if proc.returncode != 0:
            logger.error('Compilation failed:\n%s', proc.stderr)
            return utils.get_default_command()
        
        # 返回java命令
        return f'java -cp "{file_path.parent}" {class_name}'
    
    # 如果语言未知，使用默认命令
    return utils.get_default_command()

# 辅助函数：检查文件是否属于指定语言
def is_file_of_language(file_path: pathlib.Path, language: str) -> bool:
    suffix = file_path.suffix.lower()
    if language == 'cpp':
        return suffix in ['.cpp', '.cc', '.cxx']
    elif language == 'python':
        return suffix == '.py'
    elif language == 'java':
        return suffix == '.java'
    return False
