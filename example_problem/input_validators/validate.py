#!/usr/bin/env python3

import sys
import re

def validate_input(input_data):
    """
    Validate the input according to the problem constraints.
    Return True if the input is valid, False otherwise.
    """
    lines = input_data.strip().split('\n')
    
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
