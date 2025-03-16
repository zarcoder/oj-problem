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
  There is a feature to use special judges. See https://github.com/zarcoder/np-problem-tools/blob/master/docs/getting-started.md#test-for-problems-with-special-judge for details.

  You can do similar things with shell
    e.g. $ for f in data/sample/*.in ; do echo $f ; ./a.out < $f | diff - ${f%.in}.ans ; done
''')
    subparser.add_argument('-c', '--command', default=utils.get_default_command(), help='your solution to be tested. (default: "{}")'.format(utils.get_default_command()))
    subparser.add_argument('-f', '--format', default='%s.%e', help='a format string to recognize the relationship of test cases. (default: "%%s.%%e")')
    subparser.add_argument('-d', '--directory', type=pathlib.Path, default=pathlib.Path('data/sample'), help='a directory name for test cases (default: data/sample/)')
    subparser.add_argument('-m', '--compare-mode', choices=[mode.value for mode in CompareMode], default=CompareMode.CRLF_INSENSITIVE_EXACT_MATCH.value, help='mode to compare outputs. The default behavoir is exact-match to ensure that you always get AC on remote judge servers when you got AC on local tests for the same cases.  (default: crlf-insensitive-exact-match)')
    subparser.add_argument('-M', '--display-mode', choices=[mode.value for mode in DisplayMode], default=DisplayMode.SUMMARY.value, help='mode to display outputs  (default: summary)')
    subparser.add_argument('-S', '--ignore-spaces', dest='compare_mode', action='store_const', const=CompareMode.IGNORE_SPACES.value, help="ignore spaces to compare outputs, but doesn't ignore newlines  (equivalent to --compare-mode=ignore-spaces")
    subparser.add_argument('-N', '--ignore-spaces-and-newlines', dest='compare_mode', action='store_const', const=CompareMode.IGNORE_SPACES_AND_NEWLINES.value, help='ignore spaces and newlines to compare outputs  (equivalent to --compare-mode=ignore-spaces-and-newlines')
    subparser.add_argument('-D', '--diff', dest='display_mode', action='store_const', const=DisplayMode.DIFF.value, help='display the diff  (equivalent to --display-mode=diff)')
    subparser.add_argument('-s', '--silent', action='store_true', help='don\'t report output and correct answer even if not AC  (for --mode all)')
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
        result = file_comparator(actual, expected)
        if not result and is_exact:
            non_stcict_comparator = output_comparators.CRLFInsensitiveComparator(output_comparators.SplitComparator(output_comparators.ExactComparator()))
            if non_stcict_comparator(actual, expected):
                logger.warning('This was AC if spaces and newlines were ignored. Please use --ignore-spaces (-S) option or --ignore-spaces-and-newline (-N) option.')
        return result

    return compare_outputs


def run_checking_output(*, answer: bytes, test_output_path: Optional[pathlib.Path], is_special_judge: bool, match_function: Callable[[bytes, bytes], bool]) -> Optional[bool]:
    """run_checking_output executes matching of the actual output and the expected output.

    This function has file I/O including the execution of the judge command.
    """

    if test_output_path is None and not is_special_judge:
        return None
    if test_output_path is not None:
        with test_output_path.open('rb') as outf:
            expected = outf.read()
    else:
        # only if --judge option
        expected = b''
        logger.warning('expected output is not found')
    return match_function(answer, expected)


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
                logger.info(utils.NO_HEADER + 'input:\n%s', pretty_printers.make_pretty_large_file_content(inf.read(), limit=40, head=20, tail=10))

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
                logger.info(utils.NO_HEADER + 'output:\n%s', pretty_printers.make_pretty_large_file_content(answer.encode(), limit=40, head=20, tail=10))
                logger.info(utils.NO_HEADER + 'expected:\n%s', pretty_printers.make_pretty_large_file_content(expected.encode(), limit=40, head=20, tail=10))
            elif display_mode == DisplayMode.ALL:
                logger.info(utils.NO_HEADER + 'output:\n%s', pretty_printers.make_pretty_all(answer.encode()))
                logger.info(utils.NO_HEADER + 'expected:\n%s', pretty_printers.make_pretty_all(expected.encode()))
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

        match_function = build_match_function(compare_mode=CompareMode(args.compare_mode), error=args.error, judge_command=args.judge, silent=args.silent, test_input_path=test_input_path, test_output_path=test_output_path)
        match_result = run_checking_output(answer=answer.encode(), test_output_path=test_output_path, is_special_judge=args.judge is not None, match_function=match_function)
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


def run(args: 'argparse.Namespace') -> int:
    # Check if we should use solution/accepted directory
    solution_dir = pathlib.Path('solution/accepted')
    if solution_dir.exists():
        # Find all solution files in the directory
        solution_files = []
        
        # If language is specified, only look for files with that extension
        if args.language:
            ext_map = {'cpp': 'cpp', 'python': 'py', 'java': 'java'}
            ext = ext_map.get(args.language, args.language)
            solution_files.extend(list(solution_dir.glob(f'*.{ext}')))
            if not solution_files:
                logger.error('No solution files found with extension .%s in %s', ext, solution_dir)
                return 1
        else:
            # Otherwise, look for all supported languages
            for ext in ['cpp', 'py', 'java']:
                solution_files.extend(list(solution_dir.glob(f'*.{ext}')))
        
        if solution_files:
            logger.info('Found %d solution files in %s', len(solution_files), solution_dir)
            
            # Compile all solutions that need compilation
            for solution_file in solution_files:
                if solution_file.suffix == '.cpp':
                    # Compile C++ solution
                    output_file = solution_dir / solution_file.stem
                    compile_cmd = f'g++ -std=c++17 -O2 -o {output_file} {solution_file}'
                    logger.info('Compiling %s...', solution_file)
                    try:
                        subprocess.run(compile_cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        logger.info('Compilation successful')
                    except subprocess.CalledProcessError as e:
                        logger.error('Compilation failed: %s', e.stderr.decode())
                        return 1
                elif solution_file.suffix == '.java':
                    # Compile Java solution
                    compile_cmd = f'javac {solution_file}'
                    logger.info('Compiling %s...', solution_file)
                    try:
                        subprocess.run(compile_cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        logger.info('Compilation successful')
                    except subprocess.CalledProcessError as e:
                        logger.error('Compilation failed: %s', e.stderr.decode())
                        return 1
            
            # Use the solution based on the specified language or priority order
            if args.language:
                ext_map = {'cpp': '.cpp', 'python': '.py', 'java': '.java'}
                target_ext = ext_map.get(args.language, f'.{args.language}')
                for solution_file in solution_files:
                    if solution_file.suffix == target_ext:
                        if target_ext == '.cpp':
                            args.command = str(solution_dir / solution_file.stem)
                        elif target_ext == '.py':
                            args.command = f'python3 {solution_file}'
                        elif target_ext == '.java':
                            args.command = f'java -cp {solution_dir} {solution_file.stem}'
                        logger.info('Using %s solution: %s', args.language, args.command)
                        break
            else:
                # Priority: cpp > python > java
                found = False
                # First try C++
                for solution_file in solution_files:
                    if solution_file.suffix == '.cpp':
                        args.command = str(solution_dir / solution_file.stem)
                        logger.info('Using C++ solution: %s', args.command)
                        found = True
                        break
                
                # Then try Python
                if not found:
                    for solution_file in solution_files:
                        if solution_file.suffix == '.py':
                            args.command = f'python3 {solution_file}'
                            logger.info('Using Python solution: %s', args.command)
                            found = True
                            break
                
                # Finally try Java
                if not found:
                    for solution_file in solution_files:
                        if solution_file.suffix == '.java':
                            args.command = f'java -cp {solution_dir} {solution_file.stem}'
                            logger.info('Using Java solution: %s', args.command)
                            found = True
                            break
    
    # list tests
    if not args.directory.exists():
        logger.error('no such directory: %s', args.directory)
        return 1
    tests = fmtutils.glob_with_format(args.directory, args.format)  # type: List[Tuple[pathlib.Path, pathlib.Path]]
    if not tests:
        # Try to find tests in the old directory structure
        old_directory = pathlib.Path('test')
        if old_directory.exists():
            logger.warning('No tests found in %s, trying old directory structure: %s', args.directory, old_directory)
            tests = fmtutils.glob_with_format(old_directory, args.format)
            if tests:
                logger.info('Found tests in old directory structure: %s', old_directory)
                args.directory = old_directory
    
    if not tests:
        logger.error('no tests found')
        return 1
    logger.info('found %d tests', len(tests))

    # Check if the tests use the old .out extension instead of .ans
    has_out_extension = False
    for _, paths in tests:
        if len(paths) >= 2 and paths[1].suffix == '.out':
            has_out_extension = True
            break
    
    if has_out_extension:
        logger.warning('Found tests with .out extension. The new format uses .ans extension.')
        
    # check wheather GNU time is available
    gnu_time = 'time'
    if platform.system() == 'Darwin':
        gnu_time = 'gtime'
    if not check_gnu_time(gnu_time):
        gnu_time = None
        logger.warning('GNU time is not available: %s', gnu_time)
        if args.mle is not None:
            logger.warning('MLE will be ignored')

    # run tests
    history = []  # type: List[Dict[str, Any]]
    if args.jobs is None:
        for name, paths in tests:
            # Find the output file (could be .out or .ans)
            output_path = None
            for path in paths[1:]:
                if path.suffix in ['.out', '.ans']:
                    output_path = path
                    break
            history += [test_single_case(name, paths[0], output_path, args=args)]
    else:
        if os.name == 'nt':
            logger.warning("-j/--jobs option is unstable on Windows environmet")
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as executor:
            lock = threading.Lock()
            futures = []  # type: List[concurrent.futures.Future]
            for name, paths in tests:
                # Find the output file (could be .out or .ans)
                output_path = None
                for path in paths[1:]:
                    if path.suffix in ['.out', '.ans']:
                        output_path = path
                        break
                futures += [executor.submit(test_single_case, name, paths[0], output_path, lock=lock, args=args)]
            for future in futures:
                history += [future.result()]

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
