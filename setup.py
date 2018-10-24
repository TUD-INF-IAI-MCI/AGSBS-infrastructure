#!/usr/bin/env python3
import gettext
import os
import shutil
import sys

import setuptools
from setuptools.command.build_py import build_py as build
from setuptools.command.install import install

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

def locale_destdir():
    """Find best suitable directory for locales."""
    loc_dirs = [gettext._default_localedir]
    if sys.platform in ["linux", "darwin"]:
        loc_dirs += ["/usr/share/locale", "/usr/local/share/locale"]
    elif sys.platform == "win32":
        # default installer place
        loc_dirs.append(os.path.join(os.getenv('ProgramData'), "matuc",
                "locale"))
    loc_dirs.append(os.path.join(os.path.dirname(os.path.dirname(
                    os.path.abspath(sys.argv[0]))), 'share', 'locale'))

    dir_with_no_perms = None
    for directory in loc_dirs:
        if os.path.exists(directory):
            if os.access(directory, os.W_OK):
                return directory
            dir_with_no_perms = directory
        else: # doesn't exist, but maybe a parent?
            dirpath = directory[:]
            while dirpath and not os.path.exists(dirpath):
                dirpath = os.path.dirname(dirpath)
            if dirpath and os.access(dirpath, os.W_OK):
                return directory
    if dir_with_no_perms:
        print("Insufficient rights to install translations (.mo) to " +
                dir_with_no_perms)
        sys.exit(81)

class I18nInstall(install):
    """Install compiled .mo files."""
    user_options = install.user_options
    def run(self):
        install.run(self)
        for pofile in os.listdir('po'):
            lang = os.path.splitext(pofile)[0]
            destdir = os.path.join(locale_destdir(), lang, 'LC_MESSAGES')
            if not os.path.exists(destdir):
                os.makedirs(destdir)
            src_mo = os.path.join('build', 'mo', lang, 'matuc.mo')
            print("Installing %s to %s" % (src_mo, destdir))
            shutil.copy(src_mo, destdir)

setuptools.setup(
    author="Sebastian Humenda, Jens Voegler",
    cmdclass={
        'build_py': I18nBuild,
        'install': I18nInstall
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
