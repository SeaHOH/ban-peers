"""
Simple monkey patches for argparse's help format displaying compatibility of
Unicode Basic Multilingual Plane
"""
import re
import textwrap
import argparse


_origin_funcs = {
    'textwrap.TextWrapper._split': textwrap.TextWrapper._split,
    'argparse.HelpFormatter._join_parts': argparse.HelpFormatter._join_parts
}

# U+2000 - Start of General Punctuation
wordsep_unicode_simple = re.compile('[\u0000-\u1FFF]+|[\u2000-\uFFFF]')


# Action help
def _split(self, text):
    _split = _origin_funcs['textwrap.TextWrapper._split']
    chunks = []
    for chunk in _split(self, text):
        cl = wordsep_unicode_simple.findall(chunk)
        if cl:
            chunks.extend(cl)
        else:
            chunks.append(chunk)
    return chunks


# Action header
def _join_parts(self, part_strings):
    _join_parts = _origin_funcs['argparse.HelpFormatter._join_parts']
    action_header = part_strings[0]
    if not action_header.endswith('\n'):
        p = _len(action_header) - self._max_help_position
        if p > 0:
            part_strings[0] = action_header[:-p]
    return _join_parts(self, part_strings)


# String displaying lenght
def _len(o):
    if isinstance(o, str):
        l = 0
        for c in o:
            if ord(c) > 0x036F:  # End of Combining Diacritics Marks
                l += 2
            else:
                l += 1
    else:
        l = len(o)
    return l


def patch():
    textwrap.TextWrapper._split = _split
    argparse.HelpFormatter._join_parts = _join_parts
    argparse.len = textwrap.len = _len


def unpatch():
    textwrap.TextWrapper._split = _origin_funcs['textwrap.TextWrapper._split']
    argparse.HelpFormatter._join_parts = _origin_funcs['argparse.HelpFormatter._join_parts']
    argparse.len = textwrap.len = len

