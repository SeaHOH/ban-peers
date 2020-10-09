#!/usr/bin/env python3

import os
import sys
import glob
import shutil
from distutils import log
from setuptools import setup, find_packages, Command
from setuptools.command.sdist import sdist as _sdist
from setuptools.command.develop import develop as _develop
from setuptools.command.bdist_egg import bdist_egg as _bdist_egg

try:
    from wheel.bdist_wheel import bdist_wheel as _bdist_wheel
except ImportError:
    pass


def read_file(path):
    with open(os.path.join(here, path), 'r', encoding='utf-8') as fp:
        return fp.read()


def get_metadata():
    module = os.path.join(src, package, '__init__.py')
    content = read_file(module)
    code = content[:content.find('# END OF METADATA')]
    metadata = {}
    exec(code, None, metadata)
    return metadata


here = os.path.abspath(os.path.dirname(__file__))
src = 'src'
packages = find_packages(src)
package, i18n = packages
pyz = f'{package}.pyz'
metadata = get_metadata()


class build_mo(Command):
    user_options = []
    def initialize_options(self): pass
    def finalize_options(self): pass

    def run(self):
        sys.path.insert(0, os.path.join(here, src))
        msgfmt = __import__(f'{i18n}.msgfmt', fromlist=['make'])
        pos = os.path.join(here, src, package, 'i18n/locale/*/*/*.po')
        msgfmt.make(glob.glob(pos))
        del sys.path[0]
        caches = os.path.join(here, src, package, '**/*cache*')
        for cache in glob.glob(caches, recursive=True):
            log.info("removing '%s' (and everything under it)", cache)
            shutil.rmtree(cache, ignore_errors=True)


class bdist_pyz(Command):
    user_options = [
        ('output=', 'o', f'The name of the output archive. (default: {pyz}).'),
        ('python=', 'p',
         'The name of the Python interpreter to use (default: no shebang line).'),
        ('compress', 'c',
         'Compress files with the deflate method. Files are stored uncompressed '
         'by default.')
    ]
    boolean_options = ['compress']

    def initialize_options(self):
        self.output = pyz
        self.python = None
        self.compress = False
        self.zipapp_args = [src, '-m', f'{package}:main']

    def finalize_options(self):
        self.zipapp_args.extend(['-o', self.output])
        if self.python:
            self.zipapp_args.extend(['-p', self.python])
        if self.compress:
            self.zipapp_args.append('-c')

    def run(self):
        import zipapp
        self.run_command('build_mo')
        log.info("Creating Zip App archive '%s'", self.output)
        zipapp.main(self.zipapp_args)


class _clear_mo:
    def run(self):
        mos = os.path.join(here, src, package, 'i18n/locale/*/*/*.mo')
        for mo in glob.glob(mos):
            log.info("removing mo file '%s'", mo)
            os.remove(mo)
        super().run()


class _build_mo:
    def run(self):
        self.run_command('build_mo')
        super().run()


class sdist(_clear_mo, _sdist): pass

class develop(_build_mo, _develop): pass

class bdist_egg(_build_mo, _bdist_egg): pass

try:
    class bdist_wheel(_build_mo, _bdist_wheel): pass
except NameError:
    bdist_wheel = None


setup(
    name=metadata['__app_name__'],
    version=metadata['__version__'],
    author=metadata['__author__'],
    author_email=metadata['__email__'],
    url=metadata['__webpage__'],
    license=metadata['__license__'],
    description=metadata['__doc__'].replace('uTorrent', 'μTorrent') \
                                   .replace('\n', ' ').strip(),
    long_description=read_file('README.md'),
    long_description_content_type='text/markdown',
    keywords='BitTorrent uTorrent anti-leech ban block XunLei anti-ads',
    package_dir={'': src},
    package_data={
        package: ['vendor.txt'],
        i18n: ['locale/*.pot', 'locale/*/*/*.[mp]o']
    },
    packages=packages,
    zip_safe=True,
    platforms='any',
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Environment :: Console',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Topic :: Utilities'
    ],
    python_requires=('>=' + metadata['__py_min__']),
    entry_points={
        'console_scripts': [f'{package}={package}:main']
    },
    cmdclass={
        'build_mo': build_mo,
        'bdist_pyz': bdist_pyz,
        'sdist': sdist,
        'develop': develop,
        'bdist_egg': bdist_egg,
        bdist_wheel and 'bdist_wheel': bdist_wheel
    }
)
