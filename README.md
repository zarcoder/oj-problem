# oj-problem-tools

`oj-problem-tools` is a command-line tool for competitive programming problem setting. This tool helps you create problem files, validate test cases, and test your solutions.

## Features

- Create problem files (std.cpp, force.cpp, problem.md, validator.py)
- Validate test cases using custom validators
- Test your code
- Test your code for reactive problems
- Generate input files from generators
- Generate output files from input and reference implementation
- **NEW** Configuration file support for customizing default settings
- **NEW** Template management for different programming languages
- **NEW** Compare solutions with random test cases
- **NEW** Beautiful visualization of test results

## How to install

```console
$ pip3 install oj-problem-tools
```

For enhanced visualization, install with optional dependencies:

```console
$ pip3 install oj-problem-tools[rich]
```

## How to use

```console
$ oj problem [-l LANGUAGE]   # Create problem files with specified language
$ oj validator               # Validate test cases
$ oj test [-c COMMAND]       # Test your code
$ oj test-reactive [-c COMMAND] JUDGE_COMMAND
$ oj generate-input GENERATOR_COMMAND
$ oj generate-output [-c COMMAND] [TEST...]
$ oj template list           # List available templates
$ oj template set TYPE PATH  # Set a template
$ oj compare                 # Compare std and force solutions
```

For details, see `$ oj --help`.

## Configuration

You can create a `.oj-config.json` file in your home directory to customize default settings:

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
$ oj p -l cpp
[INFO] oj-problem-tools 1.0.1
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
$ oj v
[INFO] oj-problem-tools 1.0.1
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
$ oj t -c "./solution"
[INFO] oj-problem-tools 1.0.1
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
$ oj template list
[INFO] oj-problem-tools 1.0.1
[INFO] Default language: cpp
[INFO] Templates for cpp:
[INFO]   std: /path/to/std.cpp
[INFO]   force: /path/to/force.cpp

$ oj template set std ~/templates/fast_io.cpp -l cpp
[INFO] oj-problem-tools 1.0.1
[INFO] Template set: std for cpp -> /home/user/templates/fast_io.cpp
```

## Example: Comparing Solutions

```console
$ oj compare --count 10
[INFO] oj-problem-tools 1.0.1
[INFO] Using random seed: 123456789
[INFO] Compiling std.cpp...
[INFO] Compilation successful
[INFO] Compiling force.cpp...
[INFO] Compilation successful
[INFO] Running 10 random tests...
[INFO] All outputs match! 10/10
```

## License

MIT License
