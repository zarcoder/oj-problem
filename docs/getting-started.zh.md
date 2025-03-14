# `np` 命令入门指南

`np` 命令是一个用于自动化竞赛编程中常见任务的命令行工具。

## 如何安装

如果您已经安装了 Python，可以使用以下命令进行安装：

```console
$ pip3 install --user np-problem-tools
```

推荐使用 Linux（包括 Windows Subsystem for Linux）或 macOS 作为操作系统，但在 Windows 上也可以运行。

有关详细说明，请阅读 [docs/INSTALL_zh.md](./INSTALL_zh.md)。

## 使用样例测试

在提交解答前，您是否会使用样例进行测试？您是否曾经觉得这很麻烦而省略了测试？您应该始终在提交前进行测试，因为提交一个连样例都无法通过的解答只会导致罚时。测试对于调试也很有用，所以每次重写程序时都应该使用样例测试您的程序。

然而，"打开问题页面、复制样例输入、运行程序、将输入粘贴到 shell 中，然后比较输出结果与样例输出"是一项繁琐的任务。对每个样例和每次提交都这样做相当麻烦。手动执行这些繁琐的任务容易被省略或出错。这个问题可以通过自动化来解决。

使用 `np` 命令，您可以自动化样例测试。具体来说，它会自动执行以下操作：

1. 打开问题页面并获取样例
2. 运行程序并提供样例输入
3. 比较程序输出与样例输出

您可以通过 `np d URL` 下载样例，然后通过 `np t` 使用下载的样例测试您的解答。例如：

```console
$ np d https://atcoder.jp/contests/agc001/tasks/agc001_a
[x] problem recognized: AtCoderProblem.from_url('https://atcoder.jp/contests/agc001/tasks/agc001_a')
[x] load cookie from: /home/ubuntu/.local/share/online-judge-tools/cookie.jar
[x] GET: https://atcoder.jp/contests/agc001/tasks/agc001_a
[x] 200 OK
[x] save cookie to: /home/ubuntu/.local/share/online-judge-tools/cookie.jar
[x] append history to: /home/ubuntu/.cache/online-judge-tools/download-history.jsonl

[*] sample 0
[x] input: Input example 1
2
1 3 1 2
[+] saved to: test/sample-1.in
[x] output: Input example 1
3
[+] saved to: test/sample-1.out

[*] sample 1
[x] input: Input example 2
5
100 1 2 3 14 15 58 58 58 29
[+] saved to: test/sample-2.in
[x] output: Sample output 2
135
[+] saved to: test/sample-2.out

$ g++ main.cpp

$ np t
[*] 2 cases found

[*] sample-1
[x] time: 0.003978 sec
[+] AC

[*] sample-2
[x] time: 0.004634 sec
[-] WA
output:
3

expected:
135


[x] slowest: 0.004634 sec  (for sample-2)
[x] max memory: 2.344000 MB  (for sample-1)
[-] test failed: 1 AC / 2 cases
```

`np t` 的基本功能几乎等同于准备 `test/sample-1.in`、`test/sample-1.out` 等文件，然后运行 `for f in test/*.in ; do diff <(./a.out < $f) ${f/.in/.out} ; done`。如果您想测试 `./a.out` 以外的命令（例如 `python3 main.py`），请使用 `-c` 选项（例如 `np t -c "python3 main.py"`）。如果您想获取用于系统测试而非样例的测试用例，请使用 `--system` 选项。运行 `np d --help` 或 `np t --help` 查看其他功能。

## 提交

提交解答时，您必须用鼠标选择"要提交的问题"和"解答的语言"，将源代码复制粘贴到文本框中，然后点击发送按钮。这一系列操作很繁琐。您是否曾经因为在提交时选错了"问题"或"语言"而受到罚时？如果您有任何这样的经历，我们建议自动化提交过程。

使用 `np` 命令，您可以自动化提交过程。例如，如果您想将文件 `main.cpp` 提交到问题 <https://codeforces.com/contest/1200/problem/F>，您可以执行 `np s https://codeforces.com/contest/1200/problem/F`。实际输出如下：

```console
$ np d https://atcoder.jp/contests/agc001/tasks/agc001_a
[x] problem recognized: AtCoderProblem.from_url('https://atcoder.jp/contests/agc001/tasks/agc001_a')
[x] load cookie from: /home/ubuntu/.local/share/online-judge-tools/cookie.jar
[x] GET: https://atcoder.jp/contests/agc001/tasks/agc001_a
[x] 200 OK
[x] save cookie to: /home/ubuntu/.local/share/online-judge-tools/cookie.jar
[x] append history to: /home/ubuntu/.cache/online-judge-tools/download-history.jsonl

[*] sample 0
[x] input: Input example 1
2
1 3 1 2
[+] saved to: test/sample-1.in
[x] output: Input example 1
3
[+] saved to: test/sample-1.out

[*] sample 1
[x] input: Input example 2
5
100 1 2 3 14 15 58 58 58 29
[+] saved to: test/sample-2.in
[x] output: Sample output 2
135
[+] saved to: test/sample-2.out

$ g++ main.cpp

$ np t
[*] 2 cases found

[*] sample-1
[x] time: 0.003978 sec
[+] AC

[*] sample-2
[x] time: 0.004634 sec
[-] WA
output:
3

expected:
135


[x] slowest: 0.004634 sec  (for sample-2)
[x] max memory: 2.344000 MB  (for sample-1)
[-] test failed: 1 AC / 2 cases
$ np s https://codeforces.com/contest/1200/problem/F main.cpp
[x] read history from: /home/ubuntu/.cache/online-judge-tools/download-history.jsonl
[x] found urls in history:
https://codeforces.com/contest/1200/problem/F
[x] problem recognized: CodeforcesProblem.from_url('https://codeforces.com/contest/1200/problem/F'): https://codeforces.com/contest/1200/problem/F
[*] code (2341 byte):
#include <bits/stdc++.h>
#define REP(i, n) for (int i = 0; (i) < (int)(n); ++ (i))
using namespace std;


constexpr int MAX_M = 10;
constexpr int MOD = 2520;  // lcm of { 1, 2, 3, ..., 10 }
int main() {
    // config
    int n; scanf("%d", &n);
... (62 lines) ...

    // query
    int q; scanf("%d", &q);
    while (q --) {
        int x, c; scanf("%d%d", &x, &c);
        -- x;
        printf("%d\n", solve1(x, c));
        }
    return 0;
}

[x] load cookie from: /home/ubuntu/.local/share/online-judge-tools/cookie.jar
[x] GET: https://codeforces.com/contest/1200/problem/F
[x] 200 OK
[x] both GCC and Clang are available for C++ compiler
[x] use: GCC
[*] chosen language: 54 (GNU G++17 7.3.0)
[x] sleep(3.00)
Are you sure? [y/N] y
[x] GET: https://codeforces.com/contest/1200/problem/F
[x] 200 OK
[x] POST: https://codeforces.com/contest/1200/problem/F
[x] redirected: https://codeforces.com/contest/1200/my
[x] 200 OK
[+] success: result: https://codeforces.com/contest/1200/my
[x] open the submission page with: sensible-browser
[1513:1536:0910/223148.485554:ERROR:browser_process_sub_thread.cc(221)] Waited 5 ms for network service
Opening in existing browser session.
[x] save cookie to: /home/ubuntu/.local/share/online-judge-tools/cookie.jar
```

（但是，由于提交需要登录，请提前执行 `np login https://atcoder.jp/`。如果安装了 [Selenium](https://www.seleniumhq.org/)（执行了 `apt install python3-selenium firefox-geckodriver` 等），GUI 浏览器将启动，请在其中正常登录。如果您没有 Selenium，系统将直接在 CUI 上要求您输入用户名和密码。）

如果您已经在同一目录中执行了 `np d URL`，`np s main.cpp` 将猜测 URL 并提交。为了防止 URL 指定错误，我们建议使用这种省力的形式。语言会被自动识别并适当设置。

## 随机测试

当您实现了解答并提交，因为它通过了样例但得到了 WA 或 RE，而您完全不知道原因时，应该怎么办？在这种情况下，您可以使用随机生成的用例进行调试。具体来说：

1. 实现一个程序，随机生成满足约束条件的测试输入
2. 使用 (1.) 中的程序准备多个测试输入
3. （如果可能，实现一个直接的解决方案，您可以相信它总是输出正确的答案，并为输入准备测试输出）
4. 使用 (2.) 和 (3.) 中生成的测试用例测试您的解答
5. 分析 (4.) 中发现的破解用例，找出错误

`np` 命令也有帮助实现这一点的功能。您可以使用 `np g/i` 命令生成随机输入，使用 `np g/o` 命令生成输出。

例如，如果您想生成 100 个随机测试用例，可以执行：

```console
$ np g/i -c ./correct_solution ./random_generator 100
```

这将使用 `./random_generator` 生成 100 个随机输入，并使用 `./correct_solution` 生成相应的输出。

如果您想找出您的解答与正确解答之间的差异，可以使用：

```console
$ np g/i --hack-actual ./your_solution --hack-expected ./correct_solution ./random_generator
```

这将生成随机输入，并比较 `./your_solution` 和 `./correct_solution` 的输出。如果发现差异，它将保存导致差异的输入。

## 比较解决方案

在竞赛编程中，通常会实现两种解决方案：一种是标准解（可能更高效但复杂），另一种是暴力解（简单但可能较慢）。比较这两种解决方案的输出是确保正确性的好方法。

使用 `np compare` 命令，您可以轻松比较两种解决方案：

```console
$ np compare --count 10
```

这将生成 10 个随机测试用例，并比较 `std.cpp` 和 `force.cpp` 的输出。如果所有输出都匹配，则表明您的标准解可能是正确的。

如果您已经有测试用例，可以使用 `--use-existing` 选项：

```console
$ np compare --use-existing
```

这将使用 `test` 目录中的现有测试用例进行比较。

## 质量保证

为了确保您的问题设置质量良好，您可以使用 `np qa` 命令运行完整的质量保证检查：

```console
$ np qa
```

这将执行以下检查：
1. 验证器检查：确保所有测试用例都符合问题约束
2. 测试检查：确保标准解能通过所有测试用例
3. 比较检查：确保标准解和暴力解的输出匹配

如果所有检查都通过，您的问题设置可能是高质量的。

## 模板管理

`np` 命令支持管理不同编程语言的模板。您可以使用 `np template` 命令列出和设置模板：

```console
$ np template list
$ np template set std ~/templates/fast_io.cpp -l cpp
```

这使您可以快速开始新问题，而无需从头编写常用代码。

## 配置

您可以在主目录中创建 `.np-config.json` 文件来自定义默认设置。有关详细信息，请参阅 README 文件。 