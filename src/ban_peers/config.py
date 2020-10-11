"""utils for read/write config file"""

import os
import re
import argparse
from .appdirs import user_config_dir  # type: ignore


filename = 'ban_peers'
_default_config_dir = user_config_dir('BanPeers')
_default_config_file = os.path.join(_default_config_dir, f'{filename}.conf')

_skip_settings = {'remove_ads', 'config', 'help', 'version'}
_bool_settings = {'resolve_country', 'no_xunlei_reprieve',
                  'no_fake_progress_check', 'no_serious_leech_check',
                  'no_refused_upload_check', 'private_check',
                  'log_unknown', 'no_close_pairing'}
_s2b = {
    '0': False, 'false': False,  'no': False,
    '1': True,   'true': True,  'yes': True
}


class FileType(argparse.FileType):
    def __call__(self, string):
        if 'w' in self._mode and string != '-':
            dir = os.path.dirname(os.path.abspath(string))
            if not os.path.exists(dir):
                os.makedirs(dir, exist_ok=True)
        return super().__call__(string)


def current_dir_config_file():
    for ext in ['conf', 'ini', 'cfg']:
        if os.path.exists(f'{filename}.{ext}'):
            return f'{filename}.{ext}'


def save(config, file, log=None):
    for name, value in config.items():
        if value and name not in _skip_settings:
            file.write(f'{name} = {value}\n')
            if log:
                log(name, value)


def load(config, file, log=None):
    for l in file.readlines():
        try:
            name, value = re.split('\s*=\s*', l.strip(), 1)
        except ValueError:
            continue
        if name in _skip_settings or name not in config or config[name]:
            continue
        if name in _bool_settings:
            value = _s2b[value.lower()]
        elif value.isdecimal():
            value = int(value)
        if not value:
            continue
        config[name] = value
        if log:
            log(name, value)
