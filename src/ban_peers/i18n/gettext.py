#! /usr/bin/env python3

"""Internationalization and localization support.

This module provides extension of find/read mo files from zip archive
(same zipimporter with the module) for CPython buildin gettext module.
"""

import os
import io
import sys
import gettext


# try get default locale code
try:
    # check if it's supported by the _locale._getdefaultlocale function
    from _locale import _getdefaultlocale  # type: ignore
    from locale import windows_locale
except ImportError:
    _defaultlocalecode = None
else:
    _defaultlocalecode = _getdefaultlocale()[0]
    # make sure the code values are valid
    if _defaultlocalecode:
        if sys.platform == "win32" and _defaultlocalecode[:2] == "0x":
            # map windows language identifier to language name
            _defaultlocalecode = windows_locale.get(int(_defaultlocalecode, 0))
        # ...add other platform-specific processing here, if necessary...


_current_dir = os.path.abspath(os.path.dirname(__file__))
_default_localedir = os.path.join(_current_dir, 'locale')


def path_exists(path):
    if hasattr(__loader__, 'archive') and path.startswith(__loader__.archive):
        return path[len(__loader__.archive)+1:] in __loader__._files
    else:
        return os.path.exists(path)


def find(domain, localedir=None, languages=None, all=False):
    # Get some reasonable defaults for arguments that were not supplied
    if localedir is None:
        localedirs = _default_localedir, gettext._default_localedir
    else:
        localedirs = localedir,
    if languages is None:
        languages = []
        if _defaultlocalecode:
            languages.append(_defaultlocalecode)
        else:
            for envar in ('LANGUAGE', 'LC_ALL', 'LC_MESSAGES', 'LANG'):
                val = os.environ.get(envar)
                if val:
                    languages = val.split(':')
                    break
        if 'C' not in languages:
            languages.append('C')
    # now normalize and expand the languages
    nelangs = []
    for lang in languages:
        for nelang in gettext._expand_lang(lang):
            if nelang not in nelangs:
                nelangs.append(nelang)
    # select a language
    if all:
        result = []
    else:
        result = None
    for dir in localedirs:
        for lang in nelangs:
            if lang == 'C':
                break
            mofile = os.path.join(dir, lang, 'LC_MESSAGES', domain + '.mo')
            if path_exists(mofile):
                if all:
                    result.append(mofile)
                else:
                    return mofile
    return result


def translation(domain, localedir=None, languages=None,
                class_=None, fallback=False, codeset=gettext._unspecified):
    if class_ is None:
        class_ = gettext.GNUTranslations
    mofiles = find(domain, localedir, languages, all=True)
    if not mofiles:
        if fallback:
            return gettext.NullTranslations()
        from errno import ENOENT
        raise FileNotFoundError(ENOENT,
                                'No translation file found for domain', domain)
    # Avoid opening, reading, and parsing the .mo file after it's been done
    # once.
    result = None
    for mofile in mofiles:
        key = (class_, os.path.abspath(mofile))
        t = gettext._translations.get(key)
        if t is None:
            if hasattr(__loader__, 'archive') and \
                    mofile.startswith(__loader__.archive):
                modata = __loader__.get_data(mofile)
                fp = io.BytesIO(modata)
                fp.name = mofile
                t = gettext._translations.setdefault(key, class_(fp))
            else:
                with open(mofile, 'rb') as fp:
                    t = gettext._translations.setdefault(key, class_(fp))
        # Copy the translation object to allow setting fallbacks and
        # output charset. All other instance data is shared with the
        # cached object.
        # Delay copy import for speeding up gettext import when .mo files
        # are not used.
        import copy
        t = copy.copy(t)
        if codeset is not gettext._unspecified:
            import warnings
            warnings.warn('parameter codeset is deprecated',
                          DeprecationWarning, 2)
            if codeset:
                with warnings.catch_warnings():
                    warnings.filterwarnings('ignore', r'.*\bset_output_charset\b.*',
                                            DeprecationWarning)
                    t.set_output_charset(codeset)
        if result is None:
            result = t
        else:
            result.add_fallback(t)
    return result
