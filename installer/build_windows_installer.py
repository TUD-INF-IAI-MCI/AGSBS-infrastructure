#!/usr/bin/env python3
# (C) 2015-2018 Sebastian Humenda
"""Helper script to prepare environment (and nsis installation script) for
building a Windows installer. It also executes makensis.

The version is automatically extracted from MAGSBS.config.VERSION.

Dependencies:

* nsis (Nullsoft Installer)
* python >= 3.4
* pandocfilters
* 7z or unzip (command-line programs)
If running from Windows: haskell-platform
"""

import os, os.path as path
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.abspath('..')) # insert directory above as first path

GLADTEX_REPO_URL = "https://codeload.github.com/humenda/GladTeX/zip/v3.0.0"
PANDOC_INSTALLER_URL = "https://github.com/jgm/pandoc/releases/download/2.1.3/pandoc-2.1.3-windows.zip"
BUILD_DIRECTORY = "build"


def subprocess_call(cmd, other_dir=None):
    cwd = os.getcwd()
    if other_dir:
        os.chdir(other_dir)
    ret = os.system(cmd)
    if ret:
        print("Subprocess halted, command:", cmd)
        sys.exit(127)
    if other_dir:
        os.chdir(cwd)


class SetUp:
    """Check and retrieve build dependencies."""
    def __init__(self):
        self.needs_wine = (True if not sys.platform.startswith('win') else
                False)
        self.python_command = ('wine python' if self.needs_wine else 'python')

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
        module_found = os.system('%s -c "import %s"' % \
                (self.python_command, module)) == 0
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
            self.check_for_command('python', 'python3', 'Install it from https://www.winehq.org/download')

        import re
        # detect python version
        proc = subprocess.Popen(self.python_command.split(' ') + ['--version'],
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

        # test for pyinstaller
        self.check_for_command('pyinstaller', 'pyinstaller', 'Please run'\
                                'pip install pyinstaller')
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
        # take gladtex from host
#        print("Downloading " + GLADTEX_REPO_URL)
#        with urllib.request.urlopen(GLADTEX_REPO_URL) as u:
#            zip = u.read()
#        zip = zipfile.ZipFile(io.BytesIO(zip))
#        zip.extractall(BUILD_DIRECTORY)
#        # if it had a subdirectory, move contents out of it
#        build_contents = os.listdir(BUILD_DIRECTORY)
#        if len(build_contents) == 1:
#            subdir = os.path.join(BUILD_DIRECTORY, build_contents[0])
#            if os.path.isdir(subdir):
#                subprocess_call('pyinstaller --onefile build{0}GladTeX-master{0}gladtex.py' \
#                        .format(os.sep))
#                shutil.move('dist{0}gladtex.exe'.format(os.sep), BUILD_DIRECTORY)
#                # move all files from subdirectory one level higher
#                for f in (os.path.join(subdir, f) for f in os.listdir(subdir)):
#                    shutil.move(f, BUILD_DIRECTORY)
#                os.rmdir(subdir)

        # fetch pandoc installer, extract pandoc.exe (is a static binary)
        tmp = os.path.join(BUILD_DIRECTORY, 'tmp.pandoc')
        os.mkdir(tmp)
        print("Downloading", PANDOC_INSTALLER_URL)
        with urllib.request.urlopen(PANDOC_INSTALLER_URL) as u:
            with open(os.path.join(tmp, 'x.zip'), 'wb') as f:
                f.write(u.read())
        os.chdir(tmp)
        if not shutil.which('7z'):
            subprocess_call('7z x x.zip')
        else:
            subprocess_call('7z x x.zip')
        subdir = os.listdir('.')[0] # unzips with subdirectory
        if not os.path.isdir(subdir):
            raise OSError("Pandoc zip file layout changed, please fix this script.")
        os.rename(os.path.join(subdir, 'pandoc.exe'),
                os.path.join('..', 'pandoc.exe'))
        os.chdir("..")
        shutil.rmtree(os.path.basename(tmp)) # remove pandoc's temp directory
        os.chdir("..")


def clean():
    """Remove build directory."""
    if not os.path.basename(os.getcwd()) == 'installer':
        raise ValueError("BUG, expected to be in directory `installer`, but am in " + os.getcwd())
    if os.path.exists(BUILD_DIRECTORY):
        shutil.rmtree(BUILD_DIRECTORY)
    if os.path.exists(os.path.join('..', 'dist')):
        shutil.rmtree(os.path.join('..', 'dist'))


def get_size(directory):
    """Return the size of a directory by recursively querying the size of all
    files in it."""
    size = 0
    for path, _, files in os.walk(directory):
        for file in files:
            size += os.path.getsize(os.path.join(path, file))
    return size / 1024 # bytes -> kB



def update_installer_info(filename, version, total_size_kb):
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
                line = '!define INSTALLSIZE %d\n' % total_size_kb
            # else: keep line
            data.append(line)
    with open(filename, 'w', encoding="utf-8") as file:
        for line in data:
            file.write(line)


def compile_scripts(python_command, target):
    """Compile matuc using py2exe. Cross-compilation is determined by
    `python_command` (either 'python' or 'wine python')."""
    installer_src = path.dirname(path.abspath(__file__))
    mod_path = path.join(path.dirname(installer_src), 'MAGSBS')
    import gleetex # required for getting path to gleetex module
    subprocess_call('pyinstaller --clean -d all MAGSBS{0}matuc.py --onefile  --distpath installer{0}{1} '\
               '--paths MAGSBS --paths MAGSBS{0}pandoc '\
               '--paths {2} '\
               '--hidden-import=gleetex --additional-hooks-dir=.'\
                .format(os.sep, target, os.path.dirname(gleetex.__file__)),
            other_dir=path.abspath('..'))


def build_installer():
    """Prepare environment to build Windows installer using makensis."""
    # move a few files like e.g. README to distribution; MAGSBS and matuc_impl are
    # required, since py2exe doesn't include them properly
    target = lambda x: os.path.join(BUILD_DIRECTORY, x)
    shutil.copytree(os.path.join('..', 'MAGSBS'), target('MAGSBS'))
    shutil.copyfile(os.path.join('..', 'COPYING'), target('COPYING.txt'))
    shutil.copyfile(os.path.join('..', 'README.md'), target('README.md'))
    # make text files readable for Windows users
    os.chdir(BUILD_DIRECTORY)
    if shutil.which('flip'):
        os.system('flip -bm COPYING.txt')
    os.chdir('..')



    # move all files from BUILD_DIRECTORY to a subdirectory; this way a
    # temporary .nsis-file can be used
    os.rename(BUILD_DIRECTORY, 'binary')
    os.mkdir(BUILD_DIRECTORY)
    os.rename('binary', os.path.join(BUILD_DIRECTORY, 'binary'))

    # copy matuc.nsi and *.nsh to build/
    shutil.copy('EnvVarUpdate.nsh', os.path.join(BUILD_DIRECTORY,
        'EnvVarUpdate.nsh'))
    shutil.copy('matuc.nsi', os.path.join(BUILD_DIRECTORY, 'matuc.nsi'))
    #pylint: disable=import-error
    # update installer version number and size
    from MAGSBS.config import VERSION
    update_installer_info(os.path.join(BUILD_DIRECTORY, 'matuc.nsi'), VERSION,
            get_size(BUILD_DIRECTORY))
    # remove existing binary installer
    out_file = "matuc-installer-" + str(VERSION) + ".exe"
    if os.path.exists(out_file):
        os.remove(out_file)

    subprocess_call("makensis matuc.nsi", other_dir=BUILD_DIRECTORY)

    os.rename(os.path.join(BUILD_DIRECTORY, "matuc-installer.exe"), out_file)
    if shutil.which("chmod"):
        os.system("chmod a+r " + out_file)

def main():
    clean() # clean up previous build files
    st = SetUp()
    st.detect_build_dependencies()
    st.retrieve_dependencies()
    compile_scripts(st.python_command, BUILD_DIRECTORY)
    build_installer()
    clean()

main()
