#!/usr/bin/env python3

import sys
import re

def validate_input(input_data):
    """
    Validate the input according to the problem constraints.
    Return True if the input is valid, False otherwise.
    """
    lines = input_data.strip().split('\n')
    
    # 要求至少有两行输入
    if len(lines) < 2:
        print("Error: Input must have at least 2 lines", file=sys.stderr)
        return False
    
    # 第一行必须是一个整数
    try:
        n = int(lines[0])
        if not (1 <= n <= 100):
            print(f"Error: First line must be an integer between 1 and 100, got {n}", file=sys.stderr)
            return False
    except ValueError:
        print(f"Error: First line must be an integer, got '{lines[0]}'", file=sys.stderr)
        return False
    
    # 第二行必须包含n个整数
    try:
        values = list(map(int, lines[1].split()))
        if len(values) != n:
            print(f"Error: Second line must contain exactly {n} integers, got {len(values)}", file=sys.stderr)
            return False
    except ValueError:
        print("Error: Second line must contain integers only", file=sys.stderr)
        return False
    
    return True

if __name__ == '__main__':
    input_data = sys.stdin.read()
    if validate_input(input_data):
        print("Input is valid")
        sys.exit(0)
    else:
        sys.exit(1)
