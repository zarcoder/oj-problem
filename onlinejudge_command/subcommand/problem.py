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
    
    # Create test directory
    test_dir = args.dir / 'test'
    if not test_dir.exists():
        os.makedirs(test_dir)
        logger.info('created directory: %s', test_dir)
    
    # Create std file
    std_path = args.dir / _get_filename_for_language('std', language)
    if not std_path.exists():
        template_path = args.template_std
        if template_path is None:
            template_path = config.get_template_path('std', language, cfg)
        
        if template_path and template_path.exists():
            with open(template_path, 'r') as f:
                template_content = f.read()
            with open(std_path, 'w') as f:
                f.write(template_content)
        else:
            with open(std_path, 'w') as f:
                f.write(_get_default_template('std', language))
        logger.info('created file: %s', std_path)
    
    # Create force file
    force_path = args.dir / _get_filename_for_language('force', language)
    if not force_path.exists():
        template_path = args.template_force
        if template_path is None:
            template_path = config.get_template_path('force', language, cfg)
        
        if template_path and template_path.exists():
            with open(template_path, 'r') as f:
                template_content = f.read()
            with open(force_path, 'w') as f:
                f.write(template_content)
        else:
            with open(force_path, 'w') as f:
                f.write(_get_default_template('force', language))
        logger.info('created file: %s', force_path)
    
    # Create problem.md
    md_path = args.dir / 'problem.md'
    if not md_path.exists():
        template_path = args.template_md
        if template_path is None:
            template_path = config.get_template_path('md', language, cfg)
        
        if template_path and template_path.exists():
            with open(template_path, 'r') as f:
                template_content = f.read()
            with open(md_path, 'w') as f:
                f.write(template_content)
        else:
            with open(md_path, 'w') as f:
                f.write(_get_default_template('md', language))
        logger.info('created file: %s', md_path)
    
    # Create validator file
    validator_path = args.dir / 'validator.py'  # Always Python for validator
    if not validator_path.exists():
        template_path = args.template_validator
        if template_path is None:
            template_path = config.get_template_path('validator', language, cfg)
        
        if template_path and template_path.exists():
            with open(template_path, 'r') as f:
                template_content = f.read()
            with open(validator_path, 'w') as f:
                f.write(template_content)
        else:
            with open(validator_path, 'w') as f:
                f.write(_get_default_template('validator', language))
        logger.info('created file: %s', validator_path)
        # Make validator.py executable
        os.chmod(validator_path, 0o755)
    
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
    
    return "" 