#!/usr/bin/env python3
import os
import shutil
import sys

import setuptools
from setuptools.command.build_py import build_py as build

from MAGSBS.config import VERSION

BUILD_DIR = 'build'
POT_FILE = 'matuc.pot'
mo_base = lambda lang: os.path.join(BUILD_DIR, 'mo', lang)

def shell(cmd, hint=None):
    ret = os.system(cmd)
    if ret:
        print("Command exited with error %d: %s\nAborting." % ret, cmd)
        if hint:
            print(hint)
        sys.exit(ret)

def mkmo(podir, lang):
    outpath = mo_base(lang)
    if os.path.exists(outpath):
        shutil.rmtree(outpath)
    os.makedirs(outpath)
    inpath = os.path.join(podir, lang + ".po")
    shell("msgfmt %s -o %s/%s.mo" % (inpath, outpath, 'matuc'))

def merge_i18n(podir):
    if not shutil.which('msgmerge'):
        print("Error, either msgmerge or intltool is required, aborting")
        sys.exit(111)
    for pofile in podir:
        shell('msgmerge -F -U %s %s' % os.path.join(podir, pofile), POT_FILE)

class I18nBuild(build):
    """Build gettext locale files and install them appropriately."""
    user_options = build.user_options
    def run(self, *args):
        for pofile in os.listdir('po'):
            mkmo('po', os.path.splitext(pofile)[0])
        build.run(self, *args)

setuptools.setup(
    author="Sebastian Humenda, Jens Voegler",
    cmdclass={
        'build_py': I18nBuild
        },
    description="MAGSBS - MarkDown AG SBS module",
    entry_points={
       "console_scripts": [
           "matuc = matuc.matuc:main",
            "matuc_js = matuc.matuc_js:main",
        ],
    },
    install_requires=[
        "pandocfilters >= 1.4.2",
    ],
    license="LGPL",
    name="MAGSBS-matuc",
    packages=setuptools.find_packages("."),
    url="https://github.com/TUD-INF-IAI-MCI/AGSBS-infrastructure",
    version=str(VERSION),
    zip_safe=False
)
