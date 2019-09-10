#!/usr/bin/env python3
import gettext
import os
import shlex
import shutil
import sys

import setuptools
from setuptools import Command
from setuptools.command.build_py import build_py as build
from setuptools.command.install import install

from MAGSBS.config import VERSION

BUILD_DIR = 'build'
POT_FILE = 'matuc.pot'
mo_base = lambda lang: os.path.join(BUILD_DIR, 'mo', lang, 'LC_MESSAGES')

def shell(cmd, hint=None):
    ret = os.system(cmd)
    if ret:
        print("Command exited with error %d: %s\nAborting." % (ret, cmd))
        if hint:
            print(hint)
        sys.exit(ret)

def mkmo(podir, pofile):
    outpath = mo_base(os.path.splitext(pofile)[0])
    if os.path.exists(outpath):
        shutil.rmtree(outpath)
    os.makedirs(outpath)
    inpath = os.path.join(podir, pofile)
    shell("msgfmt %s -o %s%s%s.mo" % (inpath, outpath, os.sep, 'matuc'))

class I18nBuild(build):
    """Build gettext locale files and install them appropriately."""
    user_options = build.user_options
    def run(self, *args):
        for pofile in os.listdir('po'):
            mkmo('po', pofile)
        build.run(self, *args)

#pylint: disable=protected-access
#pylint: disable=inconsistent-return-statements
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

class I18nGeneration(Command):
    description = "Create/update po/pot translation files"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        files = (shlex.quote(os.path.join(dname, file))
                for dname, _d, files in os.walk('.') for file in files
                if file.endswith('.py') and not 'build' in dname
                    and not 'setup' in file and not 'test' in dname)
        create_pot = not os.path.exists('matuc.pot')
        if not create_pot:
            # query last modification time of py source files
            matuc_mtime = os.path.getmtime('matuc.pot')
            if any(os.path.getmtime(p) > matuc_mtime for p in files):
                create_pot = True
        if create_pot:
            print("Extracting translatable strings...")
            shell('pygettext --keyword=_ --output=matuc.pot %s' \
                    % ' '.join(files))
        # merge new strings and old translations
        for lang_po in os.listdir('po'):
            shell("msgmerge -F -U %s matuc.pot" % os.path.join('po', lang_po))

class I18nInstall(install):
    """Install compiled .mo files."""
    user_options = install.user_options
    def run(self):
        install.run(self)
        for pofile in os.listdir('po'):
            if not pofile.endswith('.po'):
                continue
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
        'build_i18n': I18nGeneration,
        'build_py': I18nBuild,
        'install': I18nInstall
        },
    description="MAGSBS - MarkDown AG SBS module",
    entry_points={
       "console_scripts": [
           "matuc = MAGSBS.matuc:main",
            "matuc_js = MAGSBS.matuc_js:main",
        ],
    },
    install_requires=[
        "pandocfilters >= 1.4.2",
    ],
    include_package_data=True,
    license="LGPL",
    name="MAGSBS-matuc",
    packages=setuptools.find_packages("."),
    url="https://github.com/TUD-INF-IAI-MCI/AGSBS-infrastructure",
    version=str(VERSION),
    zip_safe=True
)
