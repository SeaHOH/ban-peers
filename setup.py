#!/usr/bin/env python

import os
import re

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


def read_file(path):
    with open(os.path.join(here, path), "r", encoding="utf-8") as fp:
        return fp.read()

def get_version():
    content = read_file(module_name + ".py")
    version_match = re.search("^__version__ = ['\"]([^'\"]+)", content, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")

here = os.path.abspath(os.path.dirname(__file__))
module_name = "ban_peers"

setup(
    name="Ban-Peers",
    version=get_version(),
    author="SeaHOH",
    author_email="seahoh@gmail.com",
    url="https://github.com/SeaHOH/ban-peers",
    license="MIT",
    description=("Checking & banning BitTorrent leech peers via Web API, "
                 "remove ads, working for μTorrent."),
    long_description=read_file("README.md"),
    long_description_content_type="text/markdown",
    keywords="BitTorrent uTorrent anti-leech ban block XunLei anti-ads",
    py_modules=[module_name],
    zip_safe=True,
    platforms="any",
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Environment :: Console",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Topic :: Utilities"
    ],
    python_requires=">=3.7",
    entry_points={"console_scripts": ["ban_peers=ban_peers:main"]},
)