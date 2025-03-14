# 如何安装 `np` 命令

[English version of this document](./INSTALL.md)

请按照以下步骤操作：

1.  如果您使用 Windows 环境，请使用 [Windows Subsystem for Linux (WSL)](https://docs.microsoft.com/en-us/windows/wsl/about)。对于初学者来说，Linux（尤其是 Ubuntu）通常比 Windows 更容易使用。
    -   另外，如果您使用 Visual Studio Code（或其他 IDE），请暂时关闭它并不要使用。不要使用 IDE 中的控制台。
    -   当然，如果您是专业人士，也可以在原生 Windows 环境中使用 `np` 命令。
1.  :snake: 安装 [Python](https://www.python.org/)。如果您使用 Ubuntu（包括 WSL 中的 Ubuntu），请运行 `$ sudo apt install python3`。
1.  通过运行 `$ python3 --version` 检查您的 Python。如果显示类似 `Python 3.x.y` 的内容，则表示正常。
    -   如果显示类似 `Command 'python3' not found` 的内容，则表示您未能安装 Python。
    -   如果 Python 版本太旧，则不正常。`x` 必须大于或等于 `6`。如果 `x` 小于 `6`，请升级您的 Python。
1.  :package: 安装 [pip](https://pip.pypa.io/en/stable/)。如果您使用 Ubuntu（包括 WSL 中的 Ubuntu），请运行 `$ sudo apt install python3-pip`。
1.  通过运行 `$ pip3 --version` 检查您的 pip。如果显示类似 `pip x.y.z ...` 的内容，则表示正常。
    -   如果显示类似 `Command 'pip3' not found` 的内容，则表示您未能安装 pip。
    -   即使找不到 `pip3`，您也可能可以使用 `python3 -m pip` 代替 `pip3`。尝试运行 `$ python3 -m pip --version`。如果显示 `pip x.y.z ...`，则表示正常。
    -   不要使用 `pip` 或 `pip2`。请使用 `pip3`。
1.  :dart: 运行 `$ pip3 install np-problem-tools` 安装 `np` 命令。如果显示 `Successfully installed np-problem-tools-x.y.z`（或 `Requirement already satisfied: np-problem-tools`），则表示正常。
    -   如果显示 `Permission denied`，请运行 `$ pip3 install --user np-problem-tools` 或 `$ sudo pip3 install np-problem-tools`。
1.  通过 `$ np --version` 检查 `np` 命令。如果显示类似 `np-problem-tools x.y.z` 的内容，则表示正常。
    -   如果显示类似 `Command 'np' not found` 的内容，则需要设置 [`PATH`](https://en.wikipedia.org/wiki/PATH_%28variable%29)。请按照以下步骤操作：
        1.  通过运行 `$ find / -name np 2> /dev/null` 查找 `np` 文件的路径。该文件通常位于 `/home/ubuntu/.local/bin/np` 或 `/usr/local/bin/np`。
        1.  通过运行 `$ /home/ubuntu/.local/bin/np --version` 检查找到的 `np` 文件是否确实是 `np`。
        1.  将包含 `np` 的目录添加到您的 `PATH` 中。例如，如果 `np` 位于 `/home/ubuntu/.local/bin/np`，请在 `~/.bashrc` 的末尾写入 `export PATH="/home/ubuntu/.local/bin:$PATH"`。
            -   不要写 `export PATH="/home/ubuntu/.local/bin/np:$PATH"`。这不是一个目录。
            -   如果您不使用 bash，请根据您的 shell 将正确的设置写入正确的文件。例如，如果您使用 macOS，您的 shell 可能是 zsh。对于 zsh，请将相同的命令写入 `~/.zshrc`。
        1.  通过 `source ~/.bashrc` 重新加载配置。
            -   如果您不使用 bash，请使用适合您的 shell 的方式。
        1.  通过 `$ echo $PATH` 检查您的 `PATH`。如果显示您指定的内容（例如 `/home/ubuntu/.local/bin:...`），则表示正常。
    -   如果显示类似 `ModuleNotFoundError: No module named 'onlinejudge'` 的内容，则表示您的 Python 环境已损坏，并且未能安装 `np` 命令。运行 `$ pip3 install --force-reinstall np-problem-tools` 以忽略旧版本并重新安装。
    -   如果显示类似 `SyntaxError: invalid syntax` 的内容，则表示您错误地使用了 `pip2`。运行 `$ pip2 uninstall np-problem-tools`，然后重试安装。
1.  完成。

如果您无法理解上述说明中的许多句子（例如，如果您不知道"运行 `$ python3 --version`"是什么意思），请向您的朋友寻求帮助。 