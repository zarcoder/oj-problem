# np-problem-tools

[English Documentation](./README.md)

`np-problem-tools` 是一个用于竞赛编程题目设置的命令行工具。该工具可帮助您创建题目文件、验证测试用例并测试您的解决方案。

## 功能特点

- 创建题目文件（std.cpp、force.cpp、problem.md、validator.py）
- 使用自定义验证器验证测试用例
- 测试您的代码
- 测试交互式问题的代码
- 从生成器生成输入文件
- 从输入和参考实现生成输出文件
- **新功能** 支持配置文件以自定义默认设置
- **新功能** 支持不同编程语言的模板管理
- **新功能** 使用随机测试用例比较解决方案
- **新功能** 美观的测试结果可视化

## 安装方法

```console
$ pip3 install np-problem-tools
```

要增强可视化效果，请安装可选依赖项：

```console
$ pip3 install np-problem-tools[rich]
```

## 使用方法

```console
$ np problem [-l LANGUAGE]   # 使用指定语言创建题目文件
$ np validator               # 验证测试用例
$ np test [-c COMMAND]       # 测试您的代码
$ np test-reactive [-c COMMAND] JUDGE_COMMAND  # 测试交互式问题
$ np generate-input GENERATOR_COMMAND  # 生成输入文件
$ np generate-output [-c COMMAND] [TEST...]  # 生成输出文件
$ np template list           # 列出可用模板
$ np template set TYPE PATH  # 设置模板
$ np compare                 # 比较标准解和暴力解
$ np qa                      # 运行完整的质量保证检查
```

详细信息请参见 `$ np --help`。

## 配置

您可以在主目录中创建 `.np-config.json` 文件来自定义默认设置：

```json
{
  "default_language": "cpp",
  "templates": {
    "cpp": {
      "std": "/path/to/std.cpp",
      "force": "/path/to/force.cpp"
    },
    "python": {
      "std": "/path/to/std.py",
      "force": "/path/to/force.py"
    }
  },
  "commands": {
    "cpp_compile": "g++ -std=c++17 -O2 -o {output} {input}",
    "cpp_run": "./{executable}",
    "python_run": "python3 {input}"
  },
  "compare": {
    "num_random_tests": 20,
    "max_random_size": 100
  }
}
```

## 示例：创建题目

```console
$ mkdir my-problem && cd my-problem
$ np p -l cpp
[INFO] np-problem-tools 1.1.1
[INFO] created directory: test
[INFO] created file: std.cpp
[INFO] created file: force.cpp
[INFO] created file: problem.md
[INFO] created file: validator.py
[INFO] problem files created successfully
```

## 示例：验证测试用例

```console
$ echo "3\n1 2 3" > test/sample-1.in
$ np v
[INFO] np-problem-tools 1.1.1
[INFO] validating: test/sample-1.in
[INFO] [SUCCESS] test/sample-1.in is valid
[INFO] Validation complete: 1 valid, 0 invalid
```

## 示例：测试您的解决方案

```console
$ cat <<EOF > solution.cpp
#include <iostream>
#include <vector>
using namespace std;

int main() {
    int n;
    cin >> n;
    vector<int> a(n);
    for (int i = 0; i < n; i++) {
        cin >> a[i];
    }
    int sum = 0;
    for (int x : a) {
        sum += x;
    }
    cout << sum << endl;
    return 0;
}
EOF

$ g++ -o solution solution.cpp
$ echo "3\n1 2 3" > test/sample-1.in
$ echo "6" > test/sample-1.out
$ np t -c "./solution"
[INFO] np-problem-tools 1.1.1
[INFO] 1 cases found

[INFO] sample-1
[INFO] time: 0.001234 sec
[SUCCESS] AC

[INFO] slowest: 0.001234 sec  (for sample-1)
[INFO] max memory: 3.456000 MB  (for sample-1)
[SUCCESS] test passed: 1 AC / 1 cases
```

## 示例：管理模板

```console
$ np template list
[INFO] np-problem-tools 1.1.1
[INFO] Default language: cpp
[INFO] Templates for cpp:
[INFO]   std: /path/to/std.cpp
[INFO]   force: /path/to/force.cpp

$ np template set std ~/templates/fast_io.cpp -l cpp
[INFO] np-problem-tools 1.1.1
[INFO] Template set: std for cpp -> /home/user/templates/fast_io.cpp
```

## 示例：比较解决方案

```console
$ np compare --count 10
[INFO] np-problem-tools 1.1.1
[INFO] Using random seed: 123456789
[INFO] Compiling std.cpp...
[INFO] Compilation successful
[INFO] Compiling force.cpp...
[INFO] Compilation successful
[INFO] Running 10 random tests...
[INFO] All outputs match! 10/10
```

## 示例：质量保证检查

```console
$ np qa
[INFO] np-problem-tools 1.1.1
╭──────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ Quality Assurance Check                                                                                  │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────╯
ℹ Found 2 test cases
╭──────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ Step 1: Validator Check                                                                                  │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────╯
[INFO] validating: test/sample-1.in
[INFO] [SUCCESS] test/sample-1.in is valid
[INFO] validating: test/sample-2.in
[INFO] [SUCCESS] test/sample-2.in is valid
[INFO] Validation complete: 2 valid, 0 invalid
✓ Validator check passed
╭──────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ Step 2: Test Check                                                                                       │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────╯
ℹ Preparing std solution
ℹ Compiling std.cpp...
✓ Compilation successful
[INFO] found 2 tests
[INFO] all tests passed
✓ Test check passed
╭──────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ Step 3: Compare Check                                                                                    │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭──────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ Preparing solutions                                                                                      │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────╯
ℹ Compiling std.cpp...
✓ Compilation successful
ℹ Compiling force.cpp...
✓ Compilation successful
╭──────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ Running 2 existing tests                                                                                 │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────╯
All outputs match! 2/2
✓ Compare check passed
╭──────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ Quality Assurance Summary                                                                                │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────╯
✓ All checks passed!
```

## 许可证

MIT 许可证 