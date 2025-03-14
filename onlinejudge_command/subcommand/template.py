import argparse
import os
import pathlib
import sys
from logging import getLogger
from typing import *

import onlinejudge_command.config as config
import onlinejudge_command.utils as utils

logger = getLogger(__name__)


def add_subparser(subparsers: argparse.Action) -> None:
    subparser = subparsers.add_parser(
        'template',
        aliases=['tpl'],
        help='manage templates for problem files',
        formatter_class=argparse.RawTextHelpFormatter,
        epilog='''\
example:
    $ np template list                      # list all templates
    $ np template set std path/to/std.cpp   # set template for std.cpp
    $ np template set --language=python std path/to/std.py  # set Python template
    $ np template get std                   # get path to std template
    $ np template delete std                # delete std template
''',
    )
    
    subparser.add_argument('--language', '-l', type=str, help='specify the language (cpp, python, java)')
    
    # Create subcommands for template management
    template_subparsers = subparser.add_subparsers(dest='template_subcommand', help='template subcommand')
    
    # List templates
    list_parser = template_subparsers.add_parser('list', help='list all templates')
    
    # Set template
    set_parser = template_subparsers.add_parser('set', help='set template')
    set_parser.add_argument('template_type', type=str, help='template type (std, force, validator, md)')
    set_parser.add_argument('path', type=pathlib.Path, help='path to template file')
    
    # Get template
    get_parser = template_subparsers.add_parser('get', help='get template path')
    get_parser.add_argument('template_type', type=str, help='template type (std, force, validator, md)')
    
    # Delete template
    delete_parser = template_subparsers.add_parser('delete', help='delete template')
    delete_parser.add_argument('template_type', type=str, help='template type (std, force, validator, md)')
    
    # Set default language
    default_parser = template_subparsers.add_parser('default', help='set default language')
    default_parser.add_argument('language', type=str, help='language (cpp, python, java)')


def run(args: argparse.Namespace) -> bool:
    """
    Run the template subcommand.
    
    Args:
        args: Command line arguments
        
    Returns:
        True if successful, False otherwise
    """
    if args.template_subcommand == 'list':
        return _list_templates(args.language)
    elif args.template_subcommand == 'set':
        return _set_template(args.template_type, args.path, args.language)
    elif args.template_subcommand == 'get':
        return _get_template(args.template_type, args.language)
    elif args.template_subcommand == 'delete':
        return _delete_template(args.template_type, args.language)
    elif args.template_subcommand == 'default':
        return _set_default_language(args.language)
    else:
        logger.error('No template subcommand specified')
        return False


def _list_templates(language: Optional[str] = None) -> bool:
    """
    List all templates.
    
    Args:
        language: Language to list templates for. If None, list for all languages.
        
    Returns:
        True if successful, False otherwise
    """
    cfg = config.load_config()
    templates = cfg.get('templates', {})
    
    if language is not None:
        if language not in templates:
            logger.error('Language %s not found in templates', language)
            return False
        
        languages = {language: templates[language]}
    else:
        languages = templates
    
    default_language = cfg.get('default_language', 'cpp')
    logger.info('Default language: %s', default_language)
    
    for lang, lang_templates in languages.items():
        logger.info('Templates for %s:', lang)
        for template_type, path in lang_templates.items():
            if path is not None:
                logger.info('  %s: %s', template_type, path)
            else:
                logger.info('  %s: <not set>', template_type)
    
    return True


def _set_template(template_type: str, path: pathlib.Path, language: Optional[str] = None) -> bool:
    """
    Set template.
    
    Args:
        template_type: Template type (std, force, validator, md)
        path: Path to template file
        language: Language to set template for. If None, use default language.
        
    Returns:
        True if successful, False otherwise
    """
    if not path.exists():
        logger.error('Template file %s does not exist', path)
        return False
    
    cfg = config.load_config()
    
    if language is None:
        language = cfg.get('default_language', 'cpp')
    
    success = config.set_template_path(template_type, path, language, cfg)
    
    if success:
        logger.info('Set %s template for %s to %s', template_type, language, path)
    
    return success


def _get_template(template_type: str, language: Optional[str] = None) -> bool:
    """
    Get template path.
    
    Args:
        template_type: Template type (std, force, validator, md)
        language: Language to get template for. If None, use default language.
        
    Returns:
        True if successful, False otherwise
    """
    cfg = config.load_config()
    
    if language is None:
        language = cfg.get('default_language', 'cpp')
    
    path = config.get_template_path(template_type, language, cfg)
    
    if path is not None:
        logger.info('%s template for %s: %s', template_type, language, path)
        return True
    else:
        logger.info('%s template for %s is not set', template_type, language)
        return False


def _delete_template(template_type: str, language: Optional[str] = None) -> bool:
    """
    Delete template.
    
    Args:
        template_type: Template type (std, force, validator, md)
        language: Language to delete template for. If None, use default language.
        
    Returns:
        True if successful, False otherwise
    """
    cfg = config.load_config()
    
    if language is None:
        language = cfg.get('default_language', 'cpp')
    
    if 'templates' not in cfg or language not in cfg['templates'] or template_type not in cfg['templates'][language]:
        logger.error('%s template for %s is not set', template_type, language)
        return False
    
    cfg['templates'][language][template_type] = None
    success = config.save_config(cfg)
    
    if success:
        logger.info('Deleted %s template for %s', template_type, language)
    
    return success


def _set_default_language(language: str) -> bool:
    """
    Set default language.
    
    Args:
        language: Language to set as default
        
    Returns:
        True if successful, False otherwise
    """
    cfg = config.load_config()
    
    if language not in cfg.get('templates', {}):
        logger.warning('Language %s not found in templates. Adding it.', language)
        if 'templates' not in cfg:
            cfg['templates'] = {}
        cfg['templates'][language] = {
            'std': None,
            'force': None,
            'validator': None,
        }
    
    cfg['default_language'] = language
    success = config.save_config(cfg)
    
    if success:
        logger.info('Set default language to %s', language)
    
    return success 