#! /usr/bin/env python3
# Written by Martin v. Löwis <loewis@informatik.hu-berlin.de>
#
# Modified by:
#
#    s-ball <s-ball@laposte.net>
#        https://github.com/s-ball/mo_installer  (mo_installer)
#
#    Hanno Schlichting <hanno@hannosch.eu>
#        https://github.com/hannosch/python-gettext  (python-gettext)
#
#    SeaHOH <seahoh@gmail.com>
#        https://github.com/SeaHOH/ban-peers  (Ban-Peers)

"""Generate binary message catalog from textual translation description.

This program converts a textual Uniforum-style message catalog (.po file) into
a binary GNU catalog (.mo file).  This is essentially the same function as the
GNU msgfmt program, however, it is a simpler implementation.  Currently it
handles plural forms and message contexts, but does not generate hashing table.

Usage: msgfmt.py [OPTIONS] filename.po [filename.po ...]

Options:
    -o file
    --output-file=file
        Specify the output file to write to. If the name is omitted, output
        will go to a file named filename.mo (based of the input file name).
        If the option is omitted, and if suitable, will output to a subdir
        named "<LANGUAGE>/LC_MESSAGES" (based of the input file path).

    -h
    --help
        Print this message and exit.

    -V
    --version
        Display version information and exit.

If more than one input file is given, and if an output file is passed with
-o option, then all the input files are merged. If keys are repeated (common
for "" key for the header) the one from last file is used. Please make sure
that all the charset/encoding are same.

If more than one input file is given, and no -o option is present, then
every input file is compiled in its corresponding mo file (same name with mo
replacing po)
"""

import os
import sys
import ast
import getopt
import struct
import array
import encodings

__version__ = "1.2.3"


# All character encodings used for PO files listed below
supported_charset = '''
ASCII
ISO-8859-1
ISO-8859-2
ISO-8859-3
ISO-8859-4
ISO-8859-5
ISO-8859-6
ISO-8859-7
ISO-8859-8
ISO-8859-9
ISO-8859-13
ISO-8859-14
ISO-8859-15
KOI8-R
KOI8-U
KOI8-T
CP850
CP866
CP874
CP932
CP949
CP950
CP1250
CP1251
CP1252
CP1253
CP1254
CP1255
CP1256
CP1257
GB2312
EUC-JP
EUC-KR
EUC-TW
BIG5
BIG5-HKSCS
GBK
GB18030
SHIFT_JIS
JOHAB
TIS-620
VISCII
GEORGIAN-PS
UTF-8
'''.split()
supported_charset = ((encodings.search_function(c.lower()), c)
                     for c in supported_charset)
supported_charset = {ec.name: c
                     for ec, c in supported_charset if ec}
_default_encoding = 'latin-1'  # Don't change!!!
supported_charset[_default_encoding] = 'UNSET'


def usage(code, msg=''):
    print(__doc__, file=sys.stderr)
    if msg:
        print(msg, file=sys.stderr)
    sys.exit(code)


class PoSyntaxError(Exception):
    """Syntax error in a po file."""

    def __init__(self, msg, fname, lno, content=''):
        self.msg = msg
        self.fname = fname
        self.lno = lno
        self.content = content

    def __str__(self):
        return ('PO file syntax error: {}\n'
                '  File "{}", line {}\n'
                '    {}').format(self.msg, self.fname, self.lno, self.content)


def processmetadata(metadata, messages):
    """See whether there is an encoding/language declaration."""
    k, v = metadata.split(':', 1)
    k = k.strip().lower()
    v = v.strip()
    if k == 'content-type':
        charset = v.split('charset=')[1]
        if not charset:
            return
        encoding = encodings.search_function(charset.lower())
        encoding = encoding and encoding.name
        if encoding is None:
            raise RuntimeError('The {} charset does not supported by current '
                               'Python. If you want to go on process, '
                               'please change it to UTF-8.'
                               .format(charset))
        if encoding not in supported_charset:
            raise ValueError('The {} charset does not supported by PO files. '
                             'If you want to go on process, '
                             'please change it to UTF-8.'
                             .format(charset))
        encoding_last = messages['encoding_last']
        if encoding_last and encoding != encoding_last:
            raise ValueError('input files has different charset: {} and {}, '
                             'could not be merged. If you want to go on process'
                             ', please make them same, '
                             'or change both of them to UTF-8.'
                             .format(supported_charset[encoding_last], charset))
        messages['encoding'] = encoding
    elif k == 'language':
        if v:
            messages['language'] = v


def add(ctxt, id, string, fuzzy, messages):
    "Add a non-fuzzy translation to the dictionary."
    if not fuzzy and string:
        if ctxt is None:
            if not id:
                for metadata in string.split('\n'):
                    if ':' in metadata:
                        processmetadata(metadata, messages)
        else:
            id = '{}\x04{}'.format(ctxt, id)
        encoding = messages['encoding']
        messages[id.encode(encoding)] = string.encode(encoding)


def generate(messages):
    "Return the generated output."
    # Delete keys used of metadata
    for mkey in ['encoding', 'encoding_last', 'language']:
        messages.pop(mkey, None)
    # The msgids are sorted in the .mo file
    _mids, _mstrs = zip(*sorted(messages.items()))
    mcount = len(_mids)
    mids = []
    mstrs = []
    # The header is 7 Uint32, and index entries also use Uint32. We don't use
    # hashing table, so the string tables start right after the index tables.
    offsets = array.array('I')
    headerlen = 4 * 7
    idxlen = (4 + 4) * mcount
    offset = offset_hash = headerlen + idxlen * 2
    # For each string, we need size of the string, then the file offset.
    # Each string is NUL terminated; the NUL does not count into the size.
    # The string tables first has the list of msgids
    for mid in _mids:
        mids.extend([mid, b'\0'])
        offsets.extend([len(mid), offset])
        offset += len(mid) + 1
    del _mids
    # and the msgstrs start after the msgids
    for mstr in _mstrs:
        mstrs.extend([mstr, b'\0'])
        offsets.extend([len(mstr), offset])
        offset += len(mstr) + 1
    del _mstrs
    # Even though we don't use a hashtable, we still set its offset to be
    # binary compatible with the gnu gettext format produced by:
    #   msgfmt file.po --no-hash
    if sys.byteorder == 'big':
        offsets.byteswap()
    output = [struct.pack('<7I',
                          0x950412de,          # LE MAGIC
                          0,                   # Version
                          mcount,              # count of entries
                          headerlen,           # offset of msgid index
                          headerlen + idxlen,  # offset of msgstr index
                          0,                   # size of hashing table
                          offset_hash),        # offset of hashing table
              offsets.tobytes(),               # index tables of string offsets
                                               # no hashing table
              *mids,                           # string table msgid
              *mstrs]                          # string table msgstr
    return b''.join(output)


def process(infile, messages):
    CTXT = 'msgctxt'
    ID = 'msgid'
    IDP = 'msgid_plural'
    STR = 'msgstr'
    STRF = 'msgstr['

    # Start of default encoding (assuming Latin-1), so everything decodes
    # without failure, until we know the exact encoding
    # Last encoding would be checked for whether allow to merge all input files
    messages['encoding_last'] = messages.get('encoding')
    messages['encoding'] = _default_encoding
    messages['language'] = None

    # A proxy of `add` function to catch and raise exceptions
    def _add(*args):
        try:
            add(*args)
        except UnicodeEncodeError as msg:
            charset = supported_charset[encoding]
            raise PoSyntaxError('wrong charset {}, {}'.format(charset, msg),
                                infile, lno, l)

    # Parse the catalog
    section = msgctxt = None
    fuzzy = 0
    lno = 0
    for l in open(infile, 'rb').readlines():
        encoding = messages['encoding']
        try:
            l = l.decode(encoding).rstrip()  # strip ending whites
        except UnicodeDecodeError as msg:
            charset = supported_charset[encoding]
            raise PoSyntaxError('wrong charset {}, {}'.format(charset, msg),
                                infile, lno, l)
        lno += 1
        if l.startswith('#'):
            # If we get a comment line after a msgstr, this is a new entry
            if section and section.startswith(STR):
                _add(msgctxt, msgid, msgstr, fuzzy, messages)
                section = msgctxt = None
                fuzzy = 0
            # Record a fuzzy mark
            if l.startswith('#,') and 'fuzzy' in l:
                fuzzy = 1
            # Skip comments
            continue
        # Now we are in a msgid or msgctxt section, output previous section
        if l.startswith(CTXT):
            if section and section.startswith(STR):
                _add(msgctxt, msgid, msgstr, fuzzy, messages)
            elif section in (ID, IDP):
                raise PoSyntaxError('msgctxt followed ' + section,
                                    infile, lno, l)
            section = CTXT
            s = l[7:]
            msgctxt = ''
        # This is a message with plural forms
        elif l.startswith(IDP):
            if section != ID:
                raise PoSyntaxError('msgid_plural not preceded by msgid',
                                    infile, lno, l)
            section = IDP
            s = l[len(IDP):]
            msgid += '\0'  # separator of singular and plural
        elif l.startswith(ID):
            if section and section.startswith(STR):
                _add(msgctxt, msgid, msgstr, fuzzy, messages)
            elif section == IDP:
                raise PoSyntaxError('msgid_plural not preceded by msgid',
                                    infile, lno, l)
            section = ID
            s = l[len(ID):]
            msgid = msgstr = ''
        # Now we are in a msgstr section
        elif l.startswith(STRF):
            if section not in (IDP, STRF):
                raise PoSyntaxError('plural without msgid_plural',
                                    infile, lno, l)
            section = STRF
            s = l.split(']', 1)[1]
            if msgstr:
                msgstr += '\0'  # Separator of the various plural forms
        elif l.startswith(STR):
            if section == IDP:
                raise PoSyntaxError('indexed msgstr required for plural',
                                    infile, lno, l)
            if section != ID:
                raise PoSyntaxError('msgstr not preceded by msgid',
                                    infile, lno, l)
            section = STR
            s = l[len(STR):]
        else:
            s = l
        # Skip empty lines
        s = s.lstrip()
        if not s:
            continue
        if section is None:
            raise PoSyntaxError('unknown section', infile, lno, l)
        # Get/check available strings
        try:
            s = ast.literal_eval(s)
        except Exception as msg:
            raise PoSyntaxError(msg, infile, lno, l)
        assert isinstance(s, str), PoSyntaxError(
                                        'can not get {} string'.format(section),
                                        infile, lno, l)
        # Skip empty strings
        if not s:
            continue
        if section == CTXT:
            msgctxt += s
        elif section.startswith(ID):
            msgid += s
        elif section.startswith(STR):
            msgstr += s
    # Add last entry
    if section == STR:
        _add(msgctxt, msgid, msgstr, fuzzy, messages)
    if encoding == _default_encoding:
        print('Warning: found no charset from input file "{}"!'
              .format(infile), file=sys.stderr)


def writefile(infile, outfile, messages):
    # Compute .mo name from .po name and arguments
    dirname, basename = os.path.split(infile)
    if outfile is None:
        lang = messages.get('language')
        if lang and not dirname.endswith('LC_MESSAGES'):
            # Only effects for non-merged infiles
            outfile = os.path.join(dirname, lang, 'LC_MESSAGES', basename)
        else:
            outfile = infile
    elif os.path.isdir(outfile):
        os.path.join(outfile, basename)
    if outfile.endswith('.po'):
        outfile = outfile[:-2] + 'mo'
    elif not outfile.endswith('.mo'):
        outfile += '.mo'

    print("writing mo file '%s'" % outfile)
    output = generate(messages)
    with open(outfile, 'wb') as f:
        f.write(output)


def make(filenames, outfile=None):
    """This function is now member of the public interface.
    filenames is a string or an iterable of strings representing input file(s)
    outfile is a string for the name of an input file or None.

    If output is not None, it receives a merge of the input files
    If it is None, the output file is obtained by replacing the po extension of
    the input file with mo.
    Both ways are for compatibility reasons with previous behaviour.
    """
    if not filenames:
        raise ValueError('filenames must be a string or an iter of strings, '
                         'not ' + str(filenames))
    if isinstance(filenames, str):
        filenames = [filenames]

    messages = {}
    for filename in filenames:
        if filename.endswith('.po'):
            infile = filename
        else:
            infile = filename + '.po'
        infile = os.path.abspath(infile)  # for better error tips

        process(infile, messages)
        if outfile is None:
            writefile(infile, outfile, messages)
            messages.clear()

    if outfile:
        writefile(infile, outfile, messages)


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    try:
        opts, args = getopt.getopt(argv, 'hVo:',
                                   ['help', 'version', 'output-file='])
    except getopt.error as msg:
        usage(1, msg)

    outfile = None
    # parse options
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            usage(0)
        elif opt in ('-V', '--version'):
            print("msgfmt.py", __version__)
            sys.exit(0)
        elif opt in ('-o', '--output-file'):
            outfile = arg
    # do it
    if not args:
        print('No input file given', file=sys.stderr)
        print("Try `msgfmt --help' for more information.", file=sys.stderr)
        return

    try:
        make(args, outfile)
    except Exception as msg:
        print(msg, file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
