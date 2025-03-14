import json
import os
import pathlib
from logging import getLogger
from typing import Any, Dict, Optional

logger = getLogger(__name__)

# 默认配置文件路径
DEFAULT_CONFIG_PATH = pathlib.Path.home() / '.oj-config.json'

# 默认配置
DEFAULT_CONFIG = {
    'templates': {
        'cpp': {
            'std': None,
            'force': None,
            'validator': None,
        },
        'python': {
            'std': None,
            'force': None,
            'validator': None,
        },
        'java': {
            'std': None,
            'force': None,
            'validator': None,
        }
    },
    'default_language': 'cpp',
    'commands': {
        'cpp_compile': 'g++ -std=c++17 -O2 -o {output} {input}',
        'cpp_run': './{executable}',
        'python_run': 'python3 {input}',
        'java_compile': 'javac {input}',
        'java_run': 'java -cp {dir} {classname}'
    },
    'test': {
        'timeout': 5.0,  # seconds
        'compare_method': 'exact',  # exact, float, etc.
    },
    'compare': {
        'num_random_tests': 20,
        'max_random_size': 100,
    }
}


def load_config(config_path: Optional[pathlib.Path] = None) -> Dict[str, Any]:
    """
    Load configuration from file. If file doesn't exist, create it with default values.
    
    Args:
        config_path: Path to config file. If None, use default path.
        
    Returns:
        Dict containing configuration.
    """
    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH
    
    if not config_path.exists():
        logger.info('Config file not found. Creating default config at %s', config_path)
        save_config(DEFAULT_CONFIG, config_path)
        return DEFAULT_CONFIG.copy()
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Merge with default config to ensure all keys exist
        merged_config = DEFAULT_CONFIG.copy()
        _deep_update(merged_config, config)
        return merged_config
    
    except Exception as e:
        logger.error('Failed to load config: %s', e)
        logger.info('Using default config')
        return DEFAULT_CONFIG.copy()


def save_config(config: Dict[str, Any], config_path: Optional[pathlib.Path] = None) -> bool:
    """
    Save configuration to file.
    
    Args:
        config: Configuration dict to save
        config_path: Path to save config to. If None, use default path.
        
    Returns:
        True if successful, False otherwise.
    """
    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH
    
    try:
        # Ensure directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
        
        logger.info('Config saved to %s', config_path)
        return True
    
    except Exception as e:
        logger.error('Failed to save config: %s', e)
        return False


def get_template_path(template_type: str, language: Optional[str] = None, config: Optional[Dict[str, Any]] = None) -> Optional[pathlib.Path]:
    """
    Get path to template file.
    
    Args:
        template_type: Type of template (std, force, validator)
        language: Language of template. If None, use default language from config.
        config: Configuration dict. If None, load from default path.
        
    Returns:
        Path to template file, or None if not set.
    """
    if config is None:
        config = load_config()
    
    if language is None:
        language = config.get('default_language', 'cpp')
    
    template_path = config.get('templates', {}).get(language, {}).get(template_type)
    
    if template_path is not None:
        return pathlib.Path(template_path)
    
    return None


def set_template_path(template_type: str, path: pathlib.Path, language: Optional[str] = None, config: Optional[Dict[str, Any]] = None) -> bool:
    """
    Set path to template file.
    
    Args:
        template_type: Type of template (std, force, validator)
        path: Path to template file
        language: Language of template. If None, use default language from config.
        config: Configuration dict. If None, load from default path.
        
    Returns:
        True if successful, False otherwise.
    """
    if config is None:
        config = load_config()
    
    if language is None:
        language = config.get('default_language', 'cpp')
    
    if 'templates' not in config:
        config['templates'] = {}
    
    if language not in config['templates']:
        config['templates'][language] = {}
    
    config['templates'][language][template_type] = str(path)
    
    return save_config(config)


def get_command(command_type: str, config: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """
    Get command from config.
    
    Args:
        command_type: Type of command (cpp_compile, cpp_run, etc.)
        config: Configuration dict. If None, load from default path.
        
    Returns:
        Command string, or None if not set.
    """
    if config is None:
        config = load_config()
    
    return config.get('commands', {}).get(command_type)


def set_command(command_type: str, command: str, config: Optional[Dict[str, Any]] = None) -> bool:
    """
    Set command in config.
    
    Args:
        command_type: Type of command (cpp_compile, cpp_run, etc.)
        command: Command string
        config: Configuration dict. If None, load from default path.
        
    Returns:
        True if successful, False otherwise.
    """
    if config is None:
        config = load_config()
    
    if 'commands' not in config:
        config['commands'] = {}
    
    config['commands'][command_type] = command
    
    return save_config(config)


def _deep_update(d: Dict[str, Any], u: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively update a dict.
    
    Args:
        d: Dict to update
        u: Dict with updates
        
    Returns:
        Updated dict
    """
    for k, v in u.items():
        if isinstance(v, dict) and k in d and isinstance(d[k], dict):
            _deep_update(d[k], v)
        else:
            d[k] = v
    return d 