import argparse
import pathlib
import sys
import traceback
from logging import DEBUG, INFO, StreamHandler, basicConfig, getLogger
from typing import *

import onlinejudge_command.__about__ as version
import onlinejudge_command.subcommand.compare as subcommand_compare
import onlinejudge_command.subcommand.generate_input as subcommand_generate_input
import onlinejudge_command.subcommand.generate_output as subcommand_generate_output
import onlinejudge_command.subcommand.problem as subcommand_problem
import onlinejudge_command.subcommand.template as subcommand_template
import onlinejudge_command.subcommand.test as subcommand_test
import onlinejudge_command.subcommand.test_reactive as subcommand_test_reactive
import onlinejudge_command.subcommand.validator as subcommand_validator
import onlinejudge_command.subcommand.quality_assurance as subcommand_quality_assurance
from onlinejudge_command import log_formatter, update_checking, utils

logger = getLogger(__name__)


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Tools for competitive programming problem setting',
        formatter_class=argparse.RawTextHelpFormatter,
        epilog='''\
tips:
  This tool helps you create and validate competitive programming problems.
''',
    )
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('--version', action='store_true', help='print the np-problem-tools version number')
    parser.add_argument('--update-check', action='store_true', help='check for updates (disabled by default)')

    subparsers = parser.add_subparsers(dest='subcommand', help='for details, see "{} COMMAND --help"'.format(sys.argv[0]))
    subcommand_test.add_subparser(subparsers)
    subcommand_generate_output.add_subparser(subparsers)
    subcommand_generate_input.add_subparser(subparsers)
    subcommand_test_reactive.add_subparser(subparsers)
    subcommand_problem.add_subparser(subparsers)
    subcommand_validator.add_subparser(subparsers)
    subcommand_template.add_subparser(subparsers)
    subcommand_compare.add_subparser(subparsers)
    subcommand_quality_assurance.add_subparser(subparsers)

    return parser


def run_program(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if args.version:
        print('np-problem-tools {}'.format(version.__version__))
        return 0
    logger.debug('args: %s', str(args))

    # print the version to use for user-supporting
    logger.info('np-problem-tools %s', version.__version__)

    # TODO: make functions for subcommand take a named tuple instead of the raw result of argparse. Using named tuples make code well-typed.
    if args.subcommand in ['test', 't']:
        if not subcommand_test.run(args):
            return 1
    elif args.subcommand in ['test-reactive', 't/r', 'test-interactive', 't/i']:
        if not subcommand_test_reactive.run(args):
            return 1
    elif args.subcommand in ['generate-output', 'g/o']:
        subcommand_generate_output.run(args)
    elif args.subcommand in ['generate-input', 'g/i']:
        subcommand_generate_input.run(args)
    elif args.subcommand in ['problem', 'p']:
        if not subcommand_problem.run(args):
            return 1
    elif args.subcommand in ['validator', 'v']:
        if not subcommand_validator.run(args):
            return 1
    elif args.subcommand in ['template', 'tpl']:
        if not subcommand_template.run(args):
            return 1
    elif args.subcommand in ['compare', 'c']:
        if not subcommand_compare.run(args):
            return 1
    elif args.subcommand in ['quality-assurance', 'qa']:
        if not subcommand_quality_assurance.run(args):
            return 1
    else:
        parser.print_help(file=sys.stderr)
        return 1
    return 0


def main(args: Optional[List[str]] = None) -> 'NoReturn':
    parser = get_parser()
    parsed = parser.parse_args(args=args)

    # configure the logger
    level = INFO
    if parsed.verbose:
        level = DEBUG
    handler = StreamHandler(sys.stdout)
    handler.setFormatter(log_formatter.LogFormatter())
    basicConfig(level=level, handlers=[handler])

    # check update only if explicitly requested
    is_updated = True
    if parsed.update_check:
        is_updated = update_checking.run()

    try:
        sys.exit(run_program(parsed, parser=parser))
    except NotImplementedError:
        logger.debug('\n' + traceback.format_exc())
        logger.error('NotImplementedError')
        logger.info('The operation you specified is not supported yet. Pull requests are welcome.')
        logger.info('see: https://github.com/zarcoder/np-problem-tools')
        if not is_updated and parsed.update_check:
            logger.info(utils.HINT + 'try updating the version of np-problem-tools: $ pip3 install -U np-problem-tools')
        sys.exit(1)
    except Exception as e:
        logger.debug('\n' + traceback.format_exc())
        logger.exception(str(e))
        if not is_updated and parsed.update_check:
            logger.info(utils.HINT + 'try updating the version of np-problem-tools: $ pip3 install -U np-problem-tools')
        sys.exit(1)


if __name__ == '__main__':
    main()
