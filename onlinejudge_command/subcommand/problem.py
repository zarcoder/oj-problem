import argparse
import os
import pathlib
import sys
import yaml
import re
from datetime import datetime
from logging import getLogger
from typing import *

import onlinejudge_command.config as config
import onlinejudge_command.utils as utils

logger = getLogger(__name__)

# 问题文件夹结构定义
PROBLEM_STRUCTURE = {
    'problem.yaml': {
        'required': True,
        'description': 'Problem Metadata',
        'type': 'file',
        'content': {
            'problem_format_version': 'legacy',
            'name': '',
            'uuid': '',
            'author': '',
            'source': '',
            'source_url': '',
            'license': 'unknown',
            'rights_owner': '',
            'limits': {
                'time_multiplier': 5.0,
                'time_safety_margin': 2.0,
                'memory': 2048,          # MiB
                'output': 8,             # MiB
                'code': 128,             # KiB
                'compilation_time': 60,  # seconds
                'compilation_memory': 2048,  # MiB
                'validation_time': 60,   # seconds
                'validation_memory': 2048,  # MiB
                'validation_output': 8,  # MiB
            },
            'validation': 'default',
            'validator_flags': '',
            'keywords': '',
            'created_at': '',           # 自动填充当前日期
        }
    },
    'statement/': {
        'required': True,
        'description': 'Problem Statements',
        'type': 'directory',
        'subdirs': {
            'problem.md': {
                'type': 'file',
                'content': '# Problem Title\n\n## Description\n\n## Input\n\n## Output\n\n## Examples\n\n## Notes\n'
            }
        }
    },
    'attachments/': {
        'required': False,
        'description': 'Attachments',
        'type': 'directory'
    },
    'solution/': {
        'required': False,
        'description': 'Solution Description',
        'type': 'directory',
        'subdirs': {
            'solution.md': {
                'type': 'file',
                'content': '# Solution\n\n## Approach\n\n## Complexity\n\n- Time Complexity: \n- Space Complexity: \n'
            },
            'accepted/': {
                'type': 'directory'
            }
        }
    },
    'data/': {
        'required': True,
        'description': 'Test Data',
        'type': 'directory',
        'subdirs': {
            'sample/': {
                'required': False,
                'type': 'directory'
            },
            'secret/': {
                'required': True,
                'type': 'directory'
            },
            'invalid_input/': {
                'required': False,
                'type': 'directory'
            },
            'invalid_output/': {
                'required': False,
                'type': 'directory'
            },
            'valid_output/': {
                'required': False,
                'type': 'directory'
            }
        }
    },
    'generators/': {
        'required': False,
        'description': 'Generators',
        'type': 'directory'
    },
    'include/': {
        'required': False,
        'description': 'Included Files',
        'type': 'directory'
    },
    'submissions/': {
        'required': True,
        'description': 'Example Submissions',
        'type': 'directory',
        'subdirs': {
            'accepted/': {
                'type': 'directory'
            }
        }
    },
    'input_validators/': {
        'required': True,
        'description': 'Input Validators',
        'type': 'directory'
    },
    'static_validator/': {
        'required': False,
        'description': 'Static Validator',
        'type': 'directory'
    },
    'output_validator/': {
        'required': False,
        'description': 'Output Validator',
        'type': 'directory'
    },
    'input_visualizer/': {
        'required': False,
        'description': 'Input Visualizer',
        'type': 'directory'
    },
    'output_visualizer/': {
        'required': False,
        'description': 'Output Visualizer',
        'type': 'directory'
    }
}

def extract_examples_from_md(md_file_path):
    """从markdown文件中提取样例输入和输出"""
    examples = []
    
    try:
        with open(md_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找Examples部分
        examples_section = re.search(r'## Examples\s+(.+?)(?=\n##|\Z)', content, re.DOTALL)
        if not examples_section:
            logger.warning("没有找到Examples部分")
            return []
        
        examples_text = examples_section.group(1)
        
        # 查找所有输入和输出块
        input_blocks = re.findall(r'```(?:input)?\s*\n(.*?)\n```', examples_text, re.DOTALL)
        output_blocks = re.findall(r'```(?:output)?\s*\n(.*?)\n```', examples_text, re.DOTALL)
        
        # 如果没有找到明确标记的输入输出块，尝试使用一般的代码块
        if not input_blocks or not output_blocks:
            code_blocks = re.findall(r'```\s*\n(.*?)\n```', examples_text, re.DOTALL)
            if len(code_blocks) >= 2 and len(code_blocks) % 2 == 0:
                # 假设偶数块是输入，奇数块是输出
                input_blocks = code_blocks[::2]
                output_blocks = code_blocks[1::2]
        
        # 确保输入和输出块数量相同
        if len(input_blocks) != len(output_blocks):
            logger.warning(f"输入块和输出块数量不匹配: {len(input_blocks)} 输入, {len(output_blocks)} 输出")
            return []
        
        # 创建样例列表
        for i, (inp, out) in enumerate(zip(input_blocks, output_blocks)):
            examples.append({
                'input': inp.strip(),
                'output': out.strip(),
                'index': i + 1
            })
        
    except Exception as e:
        logger.error(f"提取样例时出错: {str(e)}")
    
    return examples

def generate_sample_files(problem_dir):
    """根据problem.md生成样例文件"""
    # 找到problem.md文件
    problem_md_path = problem_dir / 'statement' / 'problem.md'
    if not problem_md_path.exists():
        logger.error(f"找不到 {problem_md_path}")
        return False
    
    # 提取样例
    examples = extract_examples_from_md(problem_md_path)
    if not examples:
        logger.warning("无法从problem.md提取样例")
        return False
    
    # 确保sample目录存在
    sample_dir = problem_dir / 'data' / 'sample'
    sample_dir.mkdir(parents=True, exist_ok=True)
    
    # 写入样例文件
    sample_count = 0
    for example in examples:
        input_file = sample_dir / f"sample{example['index']}.in"
        output_file = sample_dir / f"sample{example['index']}.ans"
        
        with open(input_file, 'w', encoding='utf-8') as f:
            f.write(example['input'])
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(example['output'])
        
        sample_count += 1
        logger.info(f"创建样例 {sample_count}: {input_file.name} 和 {output_file.name}")
    
    logger.info(f"成功从problem.md创建了 {sample_count} 个样例")
    return True

def generate_validator(problem_dir):
    """生成输入验证器"""
    validator_dir = problem_dir / 'input_validators'
    validator_dir.mkdir(parents=True, exist_ok=True)
    
    validator_path = validator_dir / 'validate.py'
    
    # 如果验证器已存在，则不替换
    if validator_path.exists():
        logger.info(f"验证器已存在: {validator_path}")
        return
    
    # 创建一个简单的通用验证器
    with open(validator_path, 'w', encoding='utf-8') as f:
        f.write('''#!/usr/bin/env python3
import sys
import re

def main():
    """
    基本输入验证器
    每行检查长度，总行数和非打印字符
    可根据问题要求修改
    """
    line_count = 0
    max_line_length = 100000  # 可配置
    max_lines = 100000  # 可配置
    
    for line in sys.stdin:
        line_count += 1
        
        # 检查行数是否过多
        if line_count > max_lines:
            print(f"错误: 行数超过限制 {max_lines}", file=sys.stderr)
            return 1
        
        # 检查行长度
        if len(line) > max_line_length:
            print(f"错误: 第 {line_count} 行长度 ({len(line)}) 超过限制 {max_line_length}", file=sys.stderr)
            return 1
        
        # 检查非法字符
        if re.search(r'[^\x20-\x7E\n]', line):
            print(f"错误: 第 {line_count} 行包含非法字符", file=sys.stderr)
            return 1
    
    # 检查是否有输入
    if line_count == 0:
        print("错误: 没有输入", file=sys.stderr)
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
''')
    
    # 设置为可执行文件
    os.chmod(validator_path, 0o755)
    logger.info(f"创建基本验证器: {validator_path}")

def generate_solution(problem_dir):
    """生成解决方案模板"""
    solution_dir = problem_dir / 'solution' / 'accepted'
    solution_dir.mkdir(parents=True, exist_ok=True)
    
    cpp_solution_path = solution_dir / 'solution.cpp'
    py_solution_path = solution_dir / 'solution.py'
    
    # 如果解决方案已存在，则不替换
    if cpp_solution_path.exists() or py_solution_path.exists():
        logger.info(f"解决方案已存在")
        return
    
    # 创建C++解决方案模板
    with open(cpp_solution_path, 'w', encoding='utf-8') as f:
        f.write('''#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
using namespace std;

void solve() {
    // 在此实现解决方案
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    // 取消注释以处理多个测试用例
    // int t;
    // cin >> t;
    // while (t--) {
        solve();
    // }
    
    return 0;
}
''')
    
    # 创建Python解决方案模板
    with open(py_solution_path, 'w', encoding='utf-8') as f:
        f.write('''#!/usr/bin/env python3

def solve():
    # 在此实现解决方案
    pass

if __name__ == "__main__":
    # 取消注释以处理多个测试用例
    # t = int(input())
    # for _ in range(t):
    #     solve()
    solve()
''')
    
    logger.info(f"创建解决方案模板: {cpp_solution_path} 和 {py_solution_path}")

def create_structure(base_path, structure, problem_name=""):
    """递归创建问题结构"""
    for name, info in structure.items():
        path = os.path.join(base_path, name)
        
        if info.get('type') == 'directory':
            os.makedirs(path, exist_ok=True)
            logger.info(f"Created directory: {path}")
            
            # 创建子目录或子文件
            if 'subdirs' in info:
                create_structure(path, info['subdirs'], problem_name)
                
        elif info.get('type') == 'file':
            if name == 'problem.yaml':
                # 特殊处理 problem.yaml
                content = info.get('content', {}).copy()
                content['name'] = problem_name
                content['created_at'] = datetime.now().strftime("%Y-%m-%d")
                
                with open(path, 'w', encoding='utf-8') as f:
                    # 使用多行字符串格式化YAML
                    f.write("# Problem configuration\n")
                    f.write(f"problem_format_version: {content.get('problem_format_version', 'legacy')}\n")
                    f.write(f"name: {content['name']}\n")
                    f.write(f"uuid: {content.get('uuid', '')}\n")
                    f.write(f"author: {content.get('author', '')}\n")
                    f.write(f"source: {content.get('source', '')}\n")
                    f.write(f"source_url: {content.get('source_url', '')}\n")
                    f.write(f"license: {content.get('license', 'unknown')}\n")
                    f.write(f"rights_owner: {content.get('rights_owner', '')}\n")
                    f.write("\n# Limits\n")
                    f.write("limits:\n")
                    
                    # 处理limits部分
                    limits = content.get('limits', {})
                    f.write(f"  time_multiplier: {limits.get('time_multiplier', 5.0)}\n")
                    f.write(f"  time_safety_margin: {limits.get('time_safety_margin', 2.0)}\n")
                    f.write(f"  memory: {limits.get('memory', 2048)}\n")
                    f.write(f"  output: {limits.get('output', 8)}\n")
                    f.write(f"  code: {limits.get('code', 128)}\n")
                    f.write(f"  compilation_time: {limits.get('compilation_time', 60)}\n")
                    f.write(f"  compilation_memory: {limits.get('compilation_memory', 2048)}\n")
                    f.write(f"  validation_time: {limits.get('validation_time', 60)}\n")
                    f.write(f"  validation_memory: {limits.get('validation_memory', 2048)}\n")
                    f.write(f"  validation_output: {limits.get('validation_output', 8)}\n")
                    
                    f.write("\n# Validation\n")
                    f.write(f"validation: {content.get('validation', 'default')}\n")
                    f.write(f"validator_flags: {content.get('validator_flags', '')}\n")
                    f.write(f"keywords: {content.get('keywords', '')}\n")
            else:
                # 处理其他文件
                with open(path, 'w', encoding='utf-8') as f:
                    content = info.get('content', '')
                    if isinstance(content, str) and name == 'problem.md':
                        # 替换标题为问题名称
                        content = content.replace('Problem Title', problem_name)
                    f.write(content)
            
            logger.info(f"Created file: {path}")


def run(args: argparse.Namespace) -> bool:
    """创建问题结构的主函数"""
    # 检查是否使用新方式创建问题结构
    if hasattr(args, 'name') and args.name:
        # 新的标准目录结构方式
        problem_name = args.name
        
        # 创建问题目录
        if hasattr(args, 'dir') and args.dir:
            if isinstance(args.dir, pathlib.Path):
                problem_dir = args.dir
            else:
                problem_dir = pathlib.Path(args.dir)
        else:
            problem_dir = pathlib.Path('.')
        
        # 如果不是直接在指定目录创建，创建一个包含问题名的子目录
        if not hasattr(args, 'direct') or not args.direct:
            problem_dir = problem_dir / problem_name
        
        os.makedirs(problem_dir, exist_ok=True)
        logger.info(f"Creating problem structure for: {problem_name}")
        
        # 创建问题文件夹结构
        create_structure(problem_dir, PROBLEM_STRUCTURE, problem_name)
        
        logger.info(f"\nProblem structure created successfully at: {problem_dir}")
        logger.info("\nRequired directories/files are:")
        for name, info in PROBLEM_STRUCTURE.items():
            if info.get('required', False):
                logger.info(f"  - {name}: {info.get('description', '')}")
        
        # 生成额外的文件
        if not args.no_init:
            # 生成样例文件
            generate_sample_files(problem_dir)
            
            # 生成验证器
            generate_validator(problem_dir)
            
            # 生成解决方案模板
            generate_solution(problem_dir)
            
            logger.info("\n问题初始化完成，已生成必要文件结构")
            
        else:
            # 仅创建最基本的样例文件
            samples_dir = problem_dir / 'data' / 'sample'
            with open(samples_dir / 'sample1.in', 'w', encoding='utf-8') as f:
                f.write('# Sample 1 input\n')
            with open(samples_dir / 'sample1.ans', 'w', encoding='utf-8') as f:
                f.write('# Sample 1 output\n')
            
            logger.info("\nAdded basic sample test files in data/sample/")
        
        logger.info("\nNow you can start working on your problem!")
        
        return True
    else:
        # 旧的方式
        # Load config
        cfg = config.load_config()
        
        # Determine language
        language = args.language
        if language is None:
            language = cfg.get('default_language', 'cpp')
        
        # Create the directory if it doesn't exist
        if not args.dir.exists():
            os.makedirs(args.dir)
            logger.info('created directory: %s', args.dir)
        
        # Create problem with new format (now the default)
        return _create_problem(args, cfg, language)


def add_subparser(subparsers: argparse.Action) -> None:
    subparser = subparsers.add_parser(
        'problem',
        aliases=['p'],
        help='create problem directory structure',
        formatter_class=argparse.RawTextHelpFormatter,
        epilog='''\
example:
    $ np p problem1                  # create problem files with name problem1
    $ np p problem1 --dir=contests/abc123   # create problem1 files in the contests/abc123 directory
    $ np p problem1 --direct         # create problem files directly in the specified directory
    $ np p problem1 --no-init        # create basic structure without generating files from problem.md
    $ np p --dir=problem1 --language=python  # create old-style problem files using Python templates
''',
    )
    group = subparser.add_argument_group('Standard Problem Structure Options')
    group.add_argument('name', nargs='?', help='name of the problem')
    group.add_argument('--dir', '-d', help='directory to create problem in (default: current directory)')
    group.add_argument('--direct', action='store_true', help='create files directly in the specified directory without a subdirectory')
    group.add_argument('--no-init', action='store_true', help='do not initialize problem files (samples from problem.md, validator, solutions)')
    
    legacy_group = subparser.add_argument_group('Legacy Options')
    legacy_group.add_argument('--template-std', type=pathlib.Path, help='specify the template file for std.cpp')
    legacy_group.add_argument('--template-force', type=pathlib.Path, help='specify the template file for force.cpp')
    legacy_group.add_argument('--template-validator', type=pathlib.Path, help='specify the template file for validator.py')
    legacy_group.add_argument('--template-md', type=pathlib.Path, help='specify the template file for problem.md')
    legacy_group.add_argument('--language', '-l', type=str, help='specify the language (cpp, python, java)')


def _create_problem(args: argparse.Namespace, cfg: Dict[str, Any], language: str) -> bool:
    """Create problem files using the standard directory structure."""
    # Create problem.yaml
    problem_yaml_path = args.dir / 'problem.yaml'
    if not problem_yaml_path.exists():
        with open(problem_yaml_path, 'w') as f:
            f.write(_get_default_template('problem_yaml', language))
        logger.info('created file: %s', problem_yaml_path)
    
    # Create statement directory and files
    statement_dir = args.dir / 'statement'
    if not statement_dir.exists():
        os.makedirs(statement_dir)
        logger.info('created directory: %s', statement_dir)
    
    # Create problem statement files
    problem_tex_path = statement_dir / 'problem.en.tex'
    if not problem_tex_path.exists():
        with open(problem_tex_path, 'w') as f:
            f.write(_get_default_template('problem_tex', language))
        logger.info('created file: %s', problem_tex_path)
    
    # Create attachments directory
    attachments_dir = args.dir / 'attachments'
    if not attachments_dir.exists():
        os.makedirs(attachments_dir)
        logger.info('created directory: %s', attachments_dir)
    
    # Create solution directory and files
    solution_dir = args.dir / 'solution'
    if not solution_dir.exists():
        os.makedirs(solution_dir)
        logger.info('created directory: %s', solution_dir)
    
    # Create solution file
    solution_tex_path = solution_dir / 'solution.en.tex'
    if not solution_tex_path.exists():
        with open(solution_tex_path, 'w') as f:
            f.write(_get_default_template('solution_tex', language))
        logger.info('created file: %s', solution_tex_path)
    
    # Create data directory and subdirectories
    data_dir = args.dir / 'data'
    if not data_dir.exists():
        os.makedirs(data_dir)
        logger.info('created directory: %s', data_dir)
    
    # Create sample directory
    sample_dir = data_dir / 'sample'
    if not sample_dir.exists():
        os.makedirs(sample_dir)
        logger.info('created directory: %s', sample_dir)
    
    # Create sample test files
    sample_in_path = sample_dir / '1.in'
    sample_ans_path = sample_dir / '1.ans'
    if not sample_in_path.exists():
        with open(sample_in_path, 'w') as f:
            f.write('Sample input 1\n')
        logger.info('created file: %s', sample_in_path)
    if not sample_ans_path.exists():
        with open(sample_ans_path, 'w') as f:
            f.write('Sample output 1\n')
        logger.info('created file: %s', sample_ans_path)
    
    # Create secret directory
    secret_dir = data_dir / 'secret'
    if not secret_dir.exists():
        os.makedirs(secret_dir)
        logger.info('created directory: %s', secret_dir)
    
    # Create generators directory
    generators_dir = args.dir / 'generators'
    if not generators_dir.exists():
        os.makedirs(generators_dir)
        logger.info('created directory: %s', generators_dir)
    
    # Create include directory and subdirectories
    include_dir = args.dir / 'include'
    if not include_dir.exists():
        os.makedirs(include_dir)
        logger.info('created directory: %s', include_dir)
    
    # Create default include directory
    default_include_dir = include_dir / 'default'
    if not default_include_dir.exists():
        os.makedirs(default_include_dir)
        logger.info('created directory: %s', default_include_dir)
    
    # Create submissions directory and subdirectories
    submissions_dir = args.dir / 'submissions'
    if not submissions_dir.exists():
        os.makedirs(submissions_dir)
        logger.info('created directory: %s', submissions_dir)
    
    # Create submissions.yaml
    submissions_yaml_path = submissions_dir / 'submissions.yaml'
    if not submissions_yaml_path.exists():
        with open(submissions_yaml_path, 'w') as f:
            f.write(_get_default_template('submissions_yaml', language))
        logger.info('created file: %s', submissions_yaml_path)
    
    # Create accepted directory
    accepted_dir = submissions_dir / 'accepted'
    if not accepted_dir.exists():
        os.makedirs(accepted_dir)
        logger.info('created directory: %s', accepted_dir)
    
    # Create accepted solution
    accepted_solution_path = accepted_dir / _get_filename_for_language('solution', language)
    if not accepted_solution_path.exists():
        with open(accepted_solution_path, 'w') as f:
            f.write(_get_default_template('std', language))
        logger.info('created file: %s', accepted_solution_path)
    
    # Create other submission directories
    for subdir in ['rejected', 'wrong_answer', 'time_limit_exceeded', 'run_time_error', 'brute_force']:
        subdir_path = submissions_dir / subdir
        if not subdir_path.exists():
            os.makedirs(subdir_path)
            logger.info('created directory: %s', subdir_path)
    
    # Create input_validators directory
    input_validators_dir = args.dir / 'input_validators'
    if not input_validators_dir.exists():
        os.makedirs(input_validators_dir)
        logger.info('created directory: %s', input_validators_dir)
    
    # Create input validator
    input_validator_path = input_validators_dir / 'validate.py'
    if not input_validator_path.exists():
        with open(input_validator_path, 'w') as f:
            f.write(_get_default_template('validator', language))
        logger.info('created file: %s', input_validator_path)
        # Make validator.py executable
        os.chmod(input_validator_path, 0o755)
    
    # Create output_validator directory
    output_validator_dir = args.dir / 'output_validator'
    if not output_validator_dir.exists():
        os.makedirs(output_validator_dir)
        logger.info('created directory: %s', output_validator_dir)
    
    logger.info('problem files created successfully')
    return True


def _get_filename_for_language(file_type: str, language: str) -> str:
    """
    Get filename for the given file type and language.
    
    Args:
        file_type: Type of file (std, force)
        language: Language (cpp, python, java)
        
    Returns:
        Filename with appropriate extension
    """
    if language == 'cpp':
        return f"{file_type}.cpp"
    elif language == 'python':
        return f"{file_type}.py"
    elif language == 'java':
        return f"{file_type.capitalize()}.java"
    else:
        return f"{file_type}.{language}"


def _get_default_template(template_type: str, language: str) -> str:
    """
    Get default template for the given template type and language.
    
    Args:
        template_type: Type of template (std, force, validator, md)
        language: Language (cpp, python, java)
        
    Returns:
        Default template content
    """
    if template_type == 'std':
        if language == 'cpp':
            return '''\
#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

using namespace std;

int main() {
    // Your solution code here
    
    return 0;
}
'''
        elif language == 'python':
            return '''\
#!/usr/bin/env python3

def solve():
    // Your solution code here
    pass

if __name__ == "__main__":
    solve()
'''
        elif language == 'java':
            return '''\
import java.util.*;

public class Std {
    public static void main(String[] args) {
        Scanner scanner = new Scanner(System.in);
        // Your solution code here
    }
}
'''
    
    elif template_type == 'force':
        if language == 'cpp':
            return '''\
#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

using namespace std;

// This is a brute force solution for verification purposes
int main() {
    // Your brute force solution code here
    
    return 0;
}
'''
        elif language == 'python':
            return '''\
#!/usr/bin/env python3

def solve_brute_force():
    // Your brute force solution code here
    pass

if __name__ == "__main__":
    solve_brute_force()
'''
        elif language == 'java':
            return '''\
import java.util.*;

public class Force {
    public static void main(String[] args) {
        Scanner scanner = new Scanner(System.in);
        // Your brute force solution code here
    }
}
'''
    
    elif template_type == 'validator':
        return '''\
#!/usr/bin/env python3

import sys
import re

def validate_input(input_data):
    """
    Validate the input according to the problem constraints.
    Return True if the input is valid, False otherwise.
    """
    lines = input_data.strip().split('\\n')
    
    // Add your validation logic here
    // Example:
    // if len(lines) < 1:
    //     return False
    // try:
    //     n = int(lines[0])
    //     if not (1 <= n <= 100000):
    //         return False
    // except ValueError:
    //     return False
    
    return True

if __name__ == '__main__':
    input_data = sys.stdin.read()
    if validate_input(input_data):
        print("Input is valid")
        sys.exit(0)
    else:
        print("Input is invalid", file=sys.stderr)
        sys.exit(1)
'''
    
    elif template_type == 'md':
        return '''\
# Problem Title

## Description

Problem description goes here.

## Input

Input format description goes here.

## Output

Output format description goes here.

## Constraints

Constraints go here.

## Sample Input 1

```
Sample input 1 goes here
```

## Sample Output 1

```
Sample output 1 goes here
```

## Notes

Additional notes go here.
'''
    
    elif template_type == 'problem_yaml':
        return '''\
# Problem configuration
problem_format_version: legacy
name: Problem Name
uuid: 
author: Author Name
source: Source of the problem
source_url: 
license: unknown
rights_owner: 

# Limits
limits:
  time_multiplier: 5.0
  time_safety_margin: 2.0
  memory: 2048
  output: 8
  code: 128
  compilation_time: 60
  compilation_memory: 2048
  validation_time: 60
  validation_memory: 2048
  validation_output: 8

# Validation
validation: default
validator_flags: 
keywords: 
'''

    elif template_type == 'problem_tex':
        return '''\
\\problemname{Problem Name}

\\begin{problemstatement}
Problem description goes here.
\\end{problemstatement}

\\begin{inputformat}
Input format description goes here.
\\end{inputformat}

\\begin{outputformat}
Output format description goes here.
\\end{outputformat}

\\begin{constraints}
Constraints go here.
\\end{constraints}

\\begin{sampleinput}
Sample input 1 goes here
\\end{sampleinput}

\\begin{sampleoutput}
Sample output 1 goes here
\\end{sampleoutput}

\\begin{notes}
Additional notes go here.
\\end{notes}
'''

    elif template_type == 'solution_tex':
        return '''\
\\problemname{Problem Name}

\\begin{solutionstatement}
Solution description goes here.
\\end{solutionstatement}

\\begin{complexity}
Time complexity: O(?)
Space complexity: O(?)
\\end{complexity}
'''

    elif template_type == 'submissions_yaml':
        return '''\
# Submissions configuration
submissions:
  accepted:
    - file: solution.cpp
      description: Main solution
  wrong_answer:
    - file: wrong.cpp
      description: Solution with wrong algorithm
  time_limit_exceeded:
    - file: slow.cpp
      description: Slow solution
'''
    
    return "" 