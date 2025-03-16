import argparse
import os
import pathlib
import sys
from logging import getLogger
from typing import *

import onlinejudge_command.config as config
import onlinejudge_command.utils as utils

logger = getLogger(__name__)


def add_subparser(subparsers: argparse.Action) -> None:
    subparser = subparsers.add_parser(
        'problem',
        aliases=['p'],
        help='create problem files for problem setting',
        formatter_class=argparse.RawTextHelpFormatter,
        epilog='''\
example:
    $ np p                  # create problem files in the current directory
    $ np p --dir=problem1   # create problem files in the problem1 directory
    $ np p --language=python  # create problem files using Python templates
''',
    )
    subparser.add_argument('--dir', '-d', type=pathlib.Path, default=pathlib.Path('.'), help='specify the directory to create problem files')
    subparser.add_argument('--template-std', type=pathlib.Path, help='specify the template file for std.cpp')
    subparser.add_argument('--template-force', type=pathlib.Path, help='specify the template file for force.cpp')
    subparser.add_argument('--template-validator', type=pathlib.Path, help='specify the template file for validator.py')
    subparser.add_argument('--template-md', type=pathlib.Path, help='specify the template file for problem.md')
    subparser.add_argument('--language', '-l', type=str, help='specify the language (cpp, python, java)')


def run(args: argparse.Namespace) -> bool:
    # Load config
    cfg = config.load_config()
    
    # Determine language
    language = args.language
    if language is None:
        language = cfg.get('default_language', 'cpp')
    
    # Create the directory if it doesn't exist
    if not args.dir.exists():
        os.makedirs(args.dir)
        logger.info('created directory: %s', args.dir)
    
    # Create problem with new format (now the default)
    return _create_problem(args, cfg, language)


def _create_problem(args: argparse.Namespace, cfg: Dict[str, Any], language: str) -> bool:
    """Create problem files using the standard directory structure."""
    # Create problem.yaml
    problem_yaml_path = args.dir / 'problem.yaml'
    if not problem_yaml_path.exists():
        with open(problem_yaml_path, 'w') as f:
            f.write(_get_default_template('problem_yaml', language))
        logger.info('created file: %s', problem_yaml_path)
    
    # Create statement directory and files
    statement_dir = args.dir / 'statement'
    if not statement_dir.exists():
        os.makedirs(statement_dir)
        logger.info('created directory: %s', statement_dir)
    
    # Create problem statement files
    problem_tex_path = statement_dir / 'problem.en.tex'
    if not problem_tex_path.exists():
        with open(problem_tex_path, 'w') as f:
            f.write(_get_default_template('problem_tex', language))
        logger.info('created file: %s', problem_tex_path)
    
    # Create attachments directory
    attachments_dir = args.dir / 'attachments'
    if not attachments_dir.exists():
        os.makedirs(attachments_dir)
        logger.info('created directory: %s', attachments_dir)
    
    # Create solution directory and files
    solution_dir = args.dir / 'solution'
    if not solution_dir.exists():
        os.makedirs(solution_dir)
        logger.info('created directory: %s', solution_dir)
    
    # Create solution file
    solution_tex_path = solution_dir / 'solution.en.tex'
    if not solution_tex_path.exists():
        with open(solution_tex_path, 'w') as f:
            f.write(_get_default_template('solution_tex', language))
        logger.info('created file: %s', solution_tex_path)
    
    # Create data directory and subdirectories
    data_dir = args.dir / 'data'
    if not data_dir.exists():
        os.makedirs(data_dir)
        logger.info('created directory: %s', data_dir)
    
    # Create sample directory
    sample_dir = data_dir / 'sample'
    if not sample_dir.exists():
        os.makedirs(sample_dir)
        logger.info('created directory: %s', sample_dir)
    
    # Create sample test files
    sample_in_path = sample_dir / '1.in'
    sample_ans_path = sample_dir / '1.ans'
    if not sample_in_path.exists():
        with open(sample_in_path, 'w') as f:
            f.write('Sample input 1\n')
        logger.info('created file: %s', sample_in_path)
    if not sample_ans_path.exists():
        with open(sample_ans_path, 'w') as f:
            f.write('Sample output 1\n')
        logger.info('created file: %s', sample_ans_path)
    
    # Create secret directory
    secret_dir = data_dir / 'secret'
    if not secret_dir.exists():
        os.makedirs(secret_dir)
        logger.info('created directory: %s', secret_dir)
    
    # Create generators directory
    generators_dir = args.dir / 'generators'
    if not generators_dir.exists():
        os.makedirs(generators_dir)
        logger.info('created directory: %s', generators_dir)
    
    # Create include directory and subdirectories
    include_dir = args.dir / 'include'
    if not include_dir.exists():
        os.makedirs(include_dir)
        logger.info('created directory: %s', include_dir)
    
    # Create default include directory
    default_include_dir = include_dir / 'default'
    if not default_include_dir.exists():
        os.makedirs(default_include_dir)
        logger.info('created directory: %s', default_include_dir)
    
    # Create submissions directory and subdirectories
    submissions_dir = args.dir / 'submissions'
    if not submissions_dir.exists():
        os.makedirs(submissions_dir)
        logger.info('created directory: %s', submissions_dir)
    
    # Create submissions.yaml
    submissions_yaml_path = submissions_dir / 'submissions.yaml'
    if not submissions_yaml_path.exists():
        with open(submissions_yaml_path, 'w') as f:
            f.write(_get_default_template('submissions_yaml', language))
        logger.info('created file: %s', submissions_yaml_path)
    
    # Create accepted directory
    accepted_dir = submissions_dir / 'accepted'
    if not accepted_dir.exists():
        os.makedirs(accepted_dir)
        logger.info('created directory: %s', accepted_dir)
    
    # Create accepted solution
    accepted_solution_path = accepted_dir / _get_filename_for_language('solution', language)
    if not accepted_solution_path.exists():
        with open(accepted_solution_path, 'w') as f:
            f.write(_get_default_template('std', language))
        logger.info('created file: %s', accepted_solution_path)
    
    # Create other submission directories
    for subdir in ['rejected', 'wrong_answer', 'time_limit_exceeded', 'run_time_error', 'brute_force']:
        subdir_path = submissions_dir / subdir
        if not subdir_path.exists():
            os.makedirs(subdir_path)
            logger.info('created directory: %s', subdir_path)
    
    # Create input_validators directory
    input_validators_dir = args.dir / 'input_validators'
    if not input_validators_dir.exists():
        os.makedirs(input_validators_dir)
        logger.info('created directory: %s', input_validators_dir)
    
    # Create input validator
    input_validator_path = input_validators_dir / 'validate.py'
    if not input_validator_path.exists():
        with open(input_validator_path, 'w') as f:
            f.write(_get_default_template('validator', language))
        logger.info('created file: %s', input_validator_path)
        # Make validator.py executable
        os.chmod(input_validator_path, 0o755)
    
    # Create output_validator directory
    output_validator_dir = args.dir / 'output_validator'
    if not output_validator_dir.exists():
        os.makedirs(output_validator_dir)
        logger.info('created directory: %s', output_validator_dir)
    
    logger.info('problem files created successfully')
    return True


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


def _get_default_template(template_type: str, language: str) -> str:
    """
    Get default template for the given template type and language.
    
    Args:
        template_type: Type of template (std, force, validator, md)
        language: Language (cpp, python, java)
        
    Returns:
        Default template content
    """
    if template_type == 'std':
        if language == 'cpp':
            return '''\
#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

using namespace std;

int main() {
    // Your solution code here
    
    return 0;
}
'''
        elif language == 'python':
            return '''\
#!/usr/bin/env python3

def solve():
    # Your solution code here
    pass

if __name__ == "__main__":
    solve()
'''
        elif language == 'java':
            return '''\
import java.util.*;

public class Std {
    public static void main(String[] args) {
        Scanner scanner = new Scanner(System.in);
        // Your solution code here
    }
}
'''
    
    elif template_type == 'force':
        if language == 'cpp':
            return '''\
#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

using namespace std;

// This is a brute force solution for verification purposes
int main() {
    // Your brute force solution code here
    
    return 0;
}
'''
        elif language == 'python':
            return '''\
#!/usr/bin/env python3

def solve_brute_force():
    # Your brute force solution code here
    pass

if __name__ == "__main__":
    solve_brute_force()
'''
        elif language == 'java':
            return '''\
import java.util.*;

public class Force {
    public static void main(String[] args) {
        Scanner scanner = new Scanner(System.in);
        // Your brute force solution code here
    }
}
'''
    
    elif template_type == 'validator':
        return '''\
#!/usr/bin/env python3

import sys
import re

def validate_input(input_data):
    """
    Validate the input according to the problem constraints.
    Return True if the input is valid, False otherwise.
    """
    lines = input_data.strip().split('\\n')
    
    # Add your validation logic here
    # Example:
    # if len(lines) < 1:
    #     return False
    # try:
    #     n = int(lines[0])
    #     if not (1 <= n <= 100000):
    #         return False
    # except ValueError:
    #     return False
    
    return True

if __name__ == '__main__':
    input_data = sys.stdin.read()
    if validate_input(input_data):
        print("Input is valid")
        sys.exit(0)
    else:
        print("Input is invalid", file=sys.stderr)
        sys.exit(1)
'''
    
    elif template_type == 'md':
        return '''\
# Problem Title

## Description

Problem description goes here.

## Input

Input format description goes here.

## Output

Output format description goes here.

## Constraints

Constraints go here.

## Sample Input 1

```
Sample input 1 goes here
```

## Sample Output 1

```
Sample output 1 goes here
```

## Notes

Additional notes go here.
'''
    
    elif template_type == 'problem_yaml':
        return '''\
# Problem configuration
name: Problem Name
author: Author Name
source: Source of the problem
license: License information
rights_owner: Rights owner

# Limits
limits:
  time_multiplier: 1
  time_safety_margin: 2
  memory: 1024
  output: 16
  compilation_time: 60
  validation_time: 60
  validation_memory: 1024
  validation_output: 16

# Validation
validation: custom
'''

    elif template_type == 'problem_tex':
        return '''\
\\problemname{Problem Name}

\\begin{problemstatement}
Problem description goes here.
\\end{problemstatement}

\\begin{inputformat}
Input format description goes here.
\\end{inputformat}

\\begin{outputformat}
Output format description goes here.
\\end{outputformat}

\\begin{constraints}
Constraints go here.
\\end{constraints}

\\begin{sampleinput}
Sample input 1 goes here
\\end{sampleinput}

\\begin{sampleoutput}
Sample output 1 goes here
\\end{sampleoutput}

\\begin{notes}
Additional notes go here.
\\end{notes}
'''

    elif template_type == 'solution_tex':
        return '''\
\\problemname{Problem Name}

\\begin{solutionstatement}
Solution description goes here.
\\end{solutionstatement}

\\begin{complexity}
Time complexity: O(?)
Space complexity: O(?)
\\end{complexity}
'''

    elif template_type == 'submissions_yaml':
        return '''\
# Submissions configuration
submissions:
  accepted:
    - file: solution.cpp
      description: Main solution
  wrong_answer:
    - file: wrong.cpp
      description: Solution with wrong algorithm
  time_limit_exceeded:
    - file: slow.cpp
      description: Slow solution
'''
    
    return "" 