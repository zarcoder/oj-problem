#!/usr/bin/env python3
import sys
import re

def main():
    """
    验证输入是否符合题目要求:
    - 第一行: m (2 <= m <= 10^5), 整数个数
    - 第二行: m个互不相同的整数
    - 第三行: n (1 <= n <= 10^5), 查询个数
    - 接下来n行: 每行一个整数查询
    """
    lines = sys.stdin.readlines()
    line_index = 0
    
    # 验证第一行: m
    if line_index >= len(lines):
        print(f"错误: 缺少输入行", file=sys.stderr)
        return 1
    
    line = lines[line_index].strip()
    line_index += 1
    
    if not re.match(r'^[0-9]+$', line):
        print(f"错误: 第一行应该是一个整数m", file=sys.stderr)
        return 1
    
    m = int(line)
    if m < 2 or m > 10**5:
        print(f"错误: m的值应该在2和10^5之间，当前值: {m}", file=sys.stderr)
        return 1
    
    # 验证第二行: m个互不相同的整数
    if line_index >= len(lines):
        print(f"错误: 缺少输入行", file=sys.stderr)
        return 1
    
    line = lines[line_index].strip()
    line_index += 1
    
    numbers = line.split()
    if len(numbers) != m:
        print(f"错误: 第二行应该包含{m}个整数，实际包含{len(numbers)}个", file=sys.stderr)
        return 1
    
    # 检查是否所有元素都是整数
    for num in numbers:
        if not re.match(r'^-?[0-9]+$', num):
            print(f"错误: '{num}'不是一个有效的整数", file=sys.stderr)
            return 1
    
    # 检查是否所有元素都不相同
    num_set = set(map(int, numbers))
    if len(num_set) != m:
        print(f"错误: 第二行的整数应该互不相同", file=sys.stderr)
        return 1
    
    # 验证第三行: n
    if line_index >= len(lines):
        print(f"错误: 缺少输入行", file=sys.stderr)
        return 1
    
    line = lines[line_index].strip()
    line_index += 1
    
    if not re.match(r'^[0-9]+$', line):
        print(f"错误: 第三行应该是一个整数n", file=sys.stderr)
        return 1
    
    n = int(line)
    if n < 1 or n > 10**5:
        print(f"错误: n的值应该在1和10^5之间，当前值: {n}", file=sys.stderr)
        return 1
    
    # 验证接下来的n行，每行一个整数
    for i in range(n):
        if line_index >= len(lines):
            print(f"错误: 缺少查询输入，应有{n}个查询，实际只有{i}个", file=sys.stderr)
            return 1
        
        line = lines[line_index].strip()
        line_index += 1
        
        if not re.match(r'^-?[0-9]+$', line):
            print(f"错误: 查询{i+1}不是一个有效的整数", file=sys.stderr)
            return 1
    
    # 检查是否还有多余的行
    if line_index < len(lines) and lines[line_index].strip():
        print(f"错误: 输入文件包含多余的行", file=sys.stderr)
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 