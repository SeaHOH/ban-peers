There are some files for Ban-Peer's localization support.

The pot (portable object template) files helps to generate po (portable object)
files, if you does not use GUN gettext utilities. We recommend use the utilities
to direct generate po(t) files from the newest source code, more details see
[GNU gettext manual](https://www.gnu.org/software/gettext/manual/).

The po files must use **UTF-8** as its charset and text encoding, **please convert
after generated**, they should finaly be put here:

    <this directory>/<target language>/LC_MESSAGES/<domain>.po
