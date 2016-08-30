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
import sys

sys.path.insert(0, os.path.abspath('..')) # insert directory above as first path
from MAGSBS.config import VERSION

GLADTEX_BINARY_URL = "https://github.com/humenda/GladTeX/releases/download/v2.0/gladtex-embeddable-2.0.zip"
BUILD_DIRECTORY = "build"

def subprocess_call(cmd):
    ret = os.system(cmd)
    if ret:
        print("Generation halted.")
        sys.exit(127)

def retrieve_dependencies():
    """Check whether all dependencies have been installed and downloaded."""
    #pylint: disable=unused-variable,multiple-imports
    def checkfor(cmd, debian_pkg, install_otherwise):
        if not shutil.which(cmd):
            print("`%s` not installed, which is required for building the Windows installer." % cmd)
            if shutil.which('dpkg'):
                print("  Install it using `sudo apt-get install %s`." % debian_pkg)
            else:
                print("  " + install_otherwise)
            sys.exit(2)
    try:
        import pandocfilters
    except ImportError:
        print("Error: module pandocfilters is missing.")
        if shutil.which('dpkg'): # Debian-based OS
            print("  Install it using `sudo apt-get install python3-pandocfilters`.")
        else:
            print("  Install it using `sudo pip install pandocfilters`.")
        sys.exit(2)
    # test for makensis
    checkfor('makensis', 'nsis', "Please install it from http://nsis.sourceforge.net/Download.")

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

    if sys.platform.lower().startswith('win'):
        checkfor('cabal', 'cabal-install', 'https://www.haskell.org/platform')
        # build static pandoc
        subprocess_call('cabal update')
        subprocess_call('cabal install hsb2hs')
        subprocess_call('cabal install --flags="embed_data_files" citeproc-hs')
        subprocess_call('cabal configure --flags="embed_data_files"')
        subprocess_call('cabal build')
        shutil.move('dist/build/pandoc.exe', BUILD_DIRECTORY)
        shutil.rmtree('dist')
    else:
        print("Sorry, but cannot build Windows executables from another platform.")

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
    vlist = version.split(".")
    if not all(map(str.isdigit, vlist)):
        raise ValueError("Version may only contain numbers")
    else:
        vlist = list(map(int, vlist))
    if len(vlist) > 3 or len(vlist) < 2:
        raise ValueError("Version must have either two or three steps.")
    if len(vlist) == 2:
        vlist.append(0)
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
retrieve_dependencies()
build_installer()
clean()
