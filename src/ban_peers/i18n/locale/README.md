There are some files for Ban-Peer's localization support.

The pot (portable object template) files helps to generate po (portable object)
files, if you does not use GUN gettext utilities. We recommend use the utilities
to direct generate po(t) files from the newest source code, more details see
[GNU gettext manual](https://www.gnu.org/software/gettext/manual/).

The po files must use **UTF-8** as its charset and text encoding, **please
convert after generated**, they should finaly be put here:

    <THIS DIRECTORY>/<TARGET LANGUAGE>/LC_MESSAGES/<DOMAIN>.po

Don't translat words in like "%(WORD)s", this is a style for string formatting.

There are few simple guides:

- Initialize a new language po file

1. Generates a pot file from source use `xgettext`, some arguments (e.g.
   `--package-name`) could be used, or manual modify file after process done.

        cd src

        xgettext ban_peers/__init__.py -o banpeers.pot -p ban_peers/i18n/locale/<LANG>/LC_MESSAGES

1. Generates a po file from pot file use `msginit`, manual modify file's
   charset and text encoding to UTF-8 after process done. If msginit did not
   added your name and email address, write them manually.

        cd ban_peers/i18n/locale/<LANG>/LC_MESSAGES

        msginit -i banpeers.pot -o banpeers.po -l <LANG>

1. Now, the translation work can be officially start.

- Update a existing language po file. Commonly translators need only do the last
  one step.

1. Generates a pot file, does the same (like new languages).

1. Merge pot file into po file use `msgmerge`.

        cd ban_peers/i18n/locale/<LANG>/LC_MESSAGES

        msgmerge banpeers.po banpeers.pot -U

1. Now, the translation work can be officially start. After translation be
   updated, don't forget remove the marks of "fuzzy" in comment lines.

