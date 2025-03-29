#!/usr/bin/env python3
import random
import sys
import os

def generate_test_case(m, n, max_value, randomness_level=0.8):
    """
    生成一个测试用例
    
    参数:
    - m: 序列中整数的个数
    - n: 查询的个数
    - max_value: 整数的最大值
    - randomness_level: 随机性级别 (0-1), 决定生成的测试用例的随机程度
    
    返回:
    - 测试用例的输入和期望输出
    """
    # 生成m个互不相同的整数序列
    numbers = random.sample(range(-max_value, max_value + 1), m)
    
    # 根据随机性级别决定查询
    in_sequence_queries = []
    out_sequence_queries = []
    
    # 收集序列中的数字作为查询
    for num in numbers:
        in_sequence_queries.append(num)
    
    # 生成不在序列中的数字作为查询
    available_values = list(set(range(-max_value, max_value + 1)) - set(numbers))
    out_sequence_queries = random.sample(available_values, min(len(available_values), n))
    
    # 合并并随机排序所有查询
    all_queries = in_sequence_queries + out_sequence_queries
    random.shuffle(all_queries)
    
    # 如果查询数不够n个，添加随机查询
    while len(all_queries) < n:
        query_value = random.randint(-max_value, max_value)
        all_queries.append(query_value)
    
    # 只保留n个查询
    queries = all_queries[:n]
    
    # 计算预期输出
    sorted_numbers = sorted(numbers, reverse=True)  # 从大到小排序
    
    expected_output = []
    for query in queries:
        if query in numbers:
            position = sorted_numbers.index(query) + 1  # 位置从1开始计数
            expected_output.append(str(position))
        else:
            expected_output.append("-1")  # 查询的整数不在原序列中
    
    # 生成输入字符串
    input_lines = [
        str(m),
        " ".join(map(str, numbers)),
        str(n),
    ] + list(map(str, queries))
    
    input_str = "\n".join(input_lines)
    output_str = "\n".join(expected_output)
    
    return input_str, output_str

def main():
    """
    主函数，根据参数生成测试数据
    """
    if len(sys.argv) < 3:
        print("用法: python generate_test_data.py <输出目录> <文件前缀> [测试用例数量]")
        sys.exit(1)
    
    output_dir = sys.argv[1]
    file_prefix = sys.argv[2]
    num_cases = int(sys.argv[3]) if len(sys.argv) > 3 else 20
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 生成样例测试用例
    input_sample, output_sample = generate_test_case(m=5, n=3, max_value=6)
    
    # 保存样例测试用例
    with open(os.path.join(output_dir, f"{file_prefix}1.in"), 'w') as f:
        f.write(input_sample)
    
    with open(os.path.join(output_dir, f"{file_prefix}1.ans"), 'w') as f:
        f.write(output_sample)
    
    # 生成额外的测试用例
    test_configs = [
        # (m, n, max_value, randomness_level)
        (10, 5, 100, 0.8),                  # 小型测试用例
        (100, 50, 1000, 0.8),               # 中型测试用例
        (1000, 500, 10000, 0.8),            # 大型测试用例
        (10000, 1000, 100000, 0.8),         # 更大型测试用例
        (100000, 100000, 1000000, 0.8),     # 最大测试用例
        (100, 100, 100, 0.5),               # 密集查询
        (10000, 100, 1000, 0.3),            # 大量重复查询
        (10, 100000, 10, 0.9),              # 大量针对小序列的查询
        (50000, 50000, 100000, 0.7),        # 大型均衡测试用例
        (100000, 1, 1000000, 1.0),          # 只有一个查询的极端情况
        (2, 100000, 10, 0.9),               # 最小序列，大量查询
        (100000, 100000, 2147483647, 0.8),  # 使用INT_MAX
        (100000, 100000, 1000, 0.8),        # 高度重复的值范围
        (10000, 10000, 5000, 0.5),          # 约一半查询在序列中
        (10000, 10000, 500000, 0.9),        # 几乎所有查询都不在序列中
        (50000, 50000, 25000, 0.9),         # 序列几乎包含整个值范围
        (10000, 10000, 100000, 0.1),        # 低随机性，更有结构化的测试
        (10000, 10000, 100000, 0.9),        # 高随机性，更无结构的测试
        (10000, 10000, 10000, 0.5),         # 均衡的测试用例
    ]
    
    # 确保不超过请求的测试用例数
    test_configs = test_configs[:min(len(test_configs), num_cases - 1)]
    
    for i, config in enumerate(test_configs, start=2):
        m, n, max_value, randomness = config
        input_str, output_str = generate_test_case(m, n, max_value, randomness)
        
        # 保存测试用例
        with open(os.path.join(output_dir, f"{file_prefix}{i}.in"), 'w') as f:
            f.write(input_str)
        
        with open(os.path.join(output_dir, f"{file_prefix}{i}.ans"), 'w') as f:
            f.write(output_str)
        
        print(f"生成测试用例 {i}: m={m}, n={n}, max_value={max_value}")
    
    print(f"成功生成 {min(len(test_configs) + 1, num_cases)} 个测试用例在 {output_dir} 目录中")

if __name__ == "__main__":
    main() 