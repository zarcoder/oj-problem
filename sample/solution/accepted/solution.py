#!/usr/bin/env python3

def solve():
    # 读取输入数据
    m = int(input())
    numbers = list(map(int, input().split()))
    
    # 对数组进行排序（从大到小）
    sorted_numbers = sorted(numbers, reverse=True)
    
    # 创建一个字典，存储每个数字在排序后的位置（1开始计数）
    positions = {num: idx + 1 for idx, num in enumerate(sorted_numbers)}
    
    # 处理查询
    n = int(input())
    for _ in range(n):
        query = int(input())
        
        # 查找位置并输出
        if query in positions:
            print(positions[query])
        else:
            print("-1")

if __name__ == "__main__":
    solve() 