#!/usr/bin/env python3

from setuptools import find_packages, setup

from MAGSBS.config import VERSION


setup(
    name = "MAGSBS-matuc",
    version = str(VERSION),
    description = "MAGSBS - MarkDown AG SBS module",
    url = "https://github.com/TUD-INF-IAI-MCI/AGSBS-infrastructure",
    author = "Sebastian Humenda, Jens Voegler",
    license = "LGPL",
    packages = find_packages("."),
    zip_safe = False,
    entry_points = {
       "console_scripts": [
            "matuc = matuc.matuc:main",
            "matuc_js = matuc.matuc_js:main",
        ],
    },
    install_requires = [
        "pandocfilters >= 1.4.2",
    ],
)
