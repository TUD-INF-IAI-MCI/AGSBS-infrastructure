#!/usr/bin/env python3
# (C) 2016 Sebastian Humenda
"""Helper script to prepare environment (and nsis installation script) for
building a Windows installer. It also executes makensis.

The version is automatically extracted from MAGSBS.config.VERSION.

Dependencies: nsis (Nullsoft Installer), python3.4, pandocfilters, 
If running from Windows: haskell-platform
"""

import os
import shutil
import stat
import subprocess
import sys

sys.path.insert(0, os.path.abspath('..')) # insert directory above as first path
from MAGSBS.config import VERSION

GLADTEX_BINARY_URL = "https://github.com/humenda/GladTeX/releases/download/v2.0/gladtex-embeddable-2.0.zip"
PANDOC_INSTALLER_URL = "https://github.com/jgm/pandoc/releases/download/1.17.2/pandoc-1.17.2-windows.msi"
BUILD_DIRECTORY = "build"


def subprocess_call(cmd):
    ret = os.system(cmd)
    if ret:
        print("Subprocess halted, command:", cmd)
        sys.exit(127)


class SetUp:
    """Check and retrieve build dependencies."""
    def __init__(self):
        self.python = 'python'
        self.needs_wine = (True if not sys.platform.startswith('win') else
                False)

    def check_for_command(self, cmd, debian_pkg, install_otherwise, silent=False):
        """Check whether given command exists and give instruction how to
        install, if not found. If silent=True, no messages are printed and
        True/False is returned."""
        if shutil.which(cmd):
            return True
        else:
            if silent:
                return False
            else:
                print("`%s` not installed, which is required for building the Windows installer." % cmd)
                if shutil.which('dpkg'):
                    print("  Install it using `sudo apt-get install %s`." % debian_pkg)
                else:
                    print("  " + install_otherwise)
                sys.exit(2)


    def check_for_module(self, module):
        """Check whether a library exists."""
        command_prefix = ('wine ' if self.needs_wine else '')
        module_found = os.system('%s%s -c "import %s"' % \
                (command_prefix, self.python, module)) == 0
        if not module_found:
            print("%s missing, install using `%spip install %s`" % (
                module, command_prefix, module))
            sys.exit(10)

    def detect_build_dependencies(self):
        if self.needs_wine:
            self.check_for_command('wine', 'wine64', 'Install it from https://www.winehq.org/download')
            # detect python; -h switch is used to notprint output
            if os.system('wine python -h 2>&1 > /dev/null'):
                # if command python3 not found, try python
                print("Python not installed, install it in wine using ?`wine msiexec /i <msi-name>`")
        else:
            self.check_for_command('python -h')

        import re
        # detect python version
        wine = (['wine'] if self.needs_wine else [])
        proc = subprocess.Popen(wine + [self.python, '--version'],
                    stdout=subprocess.PIPE)
        data = proc.communicate()[0].decode(sys.getdefaultencoding())
        if proc.wait():
            print('error while retrieving python version: ', repr(data))
            sys.exit(3)
        pyversion = re.search(r'.*ython.*\s+(3\.\d+).*', data)
        if pyversion:
            pyversion = pyversion.groups()[0]
            if not pyversion.startswith('3'):
                print("Python version >= 3.2 required, found %s" % pyversion.groups()[0])
        else:
            print("Python version >= 3.2 required.")

        # test for py2exe
        self.check_for_module('py2exe')
        self.check_for_module('pandocfilters')
        # check for nsis generator
        self.check_for_command('makensis', 'nsis',
                "Please install it from http://nsis.sourceforge.net/Download.")
        self.check_for_command('7z', 'p7zip-full',
                'Please install it from http://7-zip.org')


    def retrieve_dependencies(self):
        """Check whether all dependencies have been installed and downloaded."""
        #pylint: disable=unused-variable,multiple-imports
        # fetch gladtex
        os.mkdir(BUILD_DIRECTORY)
        import io, urllib.request, zipfile
        print("Downloading " + GLADTEX_BINARY_URL)
        with urllib.request.urlopen(GLADTEX_BINARY_URL) as u:
            zip = u.read()
        zip = zipfile.ZipFile(io.BytesIO(zip))
        zip.extractall(BUILD_DIRECTORY)
        # if it had a subdirectory, move contents out of it
        build_contents = os.listdir(BUILD_DIRECTORY)
        if len(build_contents) == 1:
            subdir = os.path.join(BUILD_DIRECTORY, build_contents[0])
            if os.path.isdir(subdir):
                # move all files from subdirectory one level higher
                for f in (os.path.join(subdir, f) for f in os.listdir(subdir)):
                    shutil.move(f, BUILD_DIRECTORY)
                os.rmdir(subdir)

        # fetch pandoc installer, extract pandoc.exe (is a static binary)
        tmp = os.path.join(BUILD_DIRECTORY, 'tmp.pandoc')
        os.mkdir(tmp)
        print("Downloading", PANDOC_INSTALLER_URL)
        with urllib.request.urlopen(PANDOC_INSTALLER_URL) as u:
            with open(os.path.join(tmp, 'x.msi'), 'wb') as f:
                f.write(u.read())
        os.chdir(tmp)
        subprocess_call('7z x x.msi')
        os.rename('pandocEXE', os.path.join('..', 'pandoc.exe'))
        os.chdir("..")
        shutil.rmtree(os.path.basename(tmp)) # remove pandoc's temp directory
        os.chdir("..")


def clean():
    """Remove build directory."""
    if os.path.exists(BUILD_DIRECTORY):
        shutil.rmtree(BUILD_DIRECTORY)


def remove(directory):
    """Remove directory, without asking."""
    if not os.path.exists(directory):
        return
    # use onerror callback to clear readonly bit and reattempt removal
    def remove_readonly(func, fpath, _):
        "Clear the readonly bit and reattempt the removal"
        os.chmod(fpath, stat.S_IWRITE)
        func(fpath)
    shutil.rmtree(directory, onerror=remove_readonly)

def get_size(directory):
    """Return the size of a directory by recursively querying the size of all
    files in it."""
    size = 0
    for path, _, files in os.walk(directory):
        for file in files:
            size += os.path.getsize(os.path.join(path, file))
    return size



def update_installer_info(filename, version, total_size):
    """Update fields in the installer nsi script like size and version
    number."""
    vlist = tuple(version.version)
    data = []
    with open(filename, encoding="utf-8") as file:
        for line in file:
            if '!define VERSIONMAJOR' in line:
                line = '!define VERSIONMAJOR %d\n' % vlist[0]
            elif '!define VERSIONMINOR' in line:
                line = '!define VERSIONMINOR %d\n' % vlist[1]
            elif '!define VERSIONBUILD' in line:
                line = '!define VERSIONBUILD %d\n' % vlist[2]
            elif '!define INSTALLSIZE' in line:
                line = '!define INSTALLSIZE %d\n' % total_size
            # else: keep line
            data.append(line)
    with open(filename, 'w', encoding="utf-8") as file:
        for line in data:
            file.write(line)


def build_installer():
    """Prepare environment to build Windows installer using makensis."""
    for path in ["../matuc.py", "matuc.nsi", "../MAGSBS", "EnvVarUpdate.nsh",
            "../COPYING"]:
        basename = os.path.basename(path)
        if not os.path.exists(path):
            raise OSError("%s not found!" % path)
        elif os.path.isfile(path):
            shutil.copyfile(path, os.path.join(BUILD_DIRECTORY, basename))
        else:
            shutil.copytree(path, os.path.join(BUILD_DIRECTORY, basename))

    os.chdir(BUILD_DIRECTORY)
    os.rename("COPYING", "COPYING.txt")
    if shutil.which('flip'):
        subprocess_call("flip -bu COPYING.txt")

    # update installer version number and size
    update_installer_info("matuc.nsi", VERSION, get_size("."))
    subprocess_call("makensis matuc.nsi")

    out_file = "matuc_installer_" + VERSION + ".exe"

    os.rename("matuc_installer.exe", os.path.join("..", out_file))
    os.chdir("..")
    if shutil.which("chmod"):
        os.system("chmod a+r " + out_file)


clean()
st = SetUp()
st.detect_build_dependencies()
st.retrieve_dependencies()
build_installer()
