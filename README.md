# np-problem-tools

[中文版文档](./README_zh.md)

`np-problem-tools` is a command-line tool for competitive programming problem setting. It helps you create problem files, validate test cases, and test your solutions.

## Features

- Create problem files (std.cpp, force.cpp, problem.md, validator.py)
- Validate test cases with custom validators
- Test your code
- Test your code for interactive problems
- Generate input files from generators
- Generate output files from inputs and reference implementations
- **NEW** Support for configuration files to customize defaults
- **NEW** Support for template management for different programming languages
- **NEW** Compare solutions with random test cases
- **NEW** Beautiful test result visualization

## Installation

```console
$ pip3 install np-problem-tools
```

For enhanced visualization, install optional dependencies:

```console
$ pip3 install np-problem-tools[rich]
```

## Usage

```console
$ np problem [-l LANGUAGE]   # Create problem files with specified language
$ np validator               # Validate test cases
$ np test [-c COMMAND]       # Test your code
$ np test-reactive [-c COMMAND] JUDGE_COMMAND  # Test interactive problems
$ np generate-input GENERATOR_COMMAND  # Generate input files
$ np generate-output [-c COMMAND] [TEST...]  # Generate output files
$ np template list           # List available templates
$ np template set TYPE PATH  # Set a template
$ np compare                 # Compare standard and brute-force solutions
$ np qa                      # Run full quality assurance check
```

See `$ np --help` for more details.

## Configuration

You can create a `.np-config.json` file in your home directory to customize defaults:

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

## Example: Creating a Problem

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

## Example: Validating Test Cases

```console
$ echo "3\n1 2 3" > test/sample-1.in
$ np v
[INFO] np-problem-tools 1.1.1
[INFO] validating: test/sample-1.in
[INFO] [SUCCESS] test/sample-1.in is valid
[INFO] Validation complete: 1 valid, 0 invalid
```

## Example: Testing Your Solution

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

## Example: Managing Templates

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

## Example: Comparing Solutions

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

## Example: Quality Assurance Check

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

## License

MIT License
