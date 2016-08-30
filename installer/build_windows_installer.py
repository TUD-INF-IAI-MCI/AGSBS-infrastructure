#!/usr/bin/env python3
# (c) 2015 Sebastian Humenda
"""Helper script to prepare environment (and nsis installation script) for
building a Windows installer. It also executes makensis.

The version is automatically extracted from MAGSBS.config.VERSION."""

import distutils.spawn
import os
import shutil, stat, sys

sys.path.insert(0, os.path.abspath('..')) # insert directory above as first path
from MAGSBS.config import VERSION


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
    remove("build")
    os.mkdir("build")
    for path in ["../matuc.py", "matuc.nsi", "../MAGSBS", "EnvVarUpdate.nsh",
            "binary", "3rdparty", "../COPYING"]:
        file = os.path.split(path)[-1]
        if not os.path.exists(path):
            raise OSError("%s not found!" % path)
        if os.path.isfile(path):
            shutil.copyfile(path, os.path.join("build", file))
        else:
            shutil.copytree(path, os.path.join("build", os.path.split(path)[-1]))

    os.chdir("build")
    os.rename("COPYING", "COPYING.txt")
    if distutils.spawn.find_executable("flip"):
        os.system("flip -bu COPYING.txt")

    # update installer version number and size
    update_installer_info("matuc.nsi", VERSION, get_size("."))
    ret = os.system("makensis matuc.nsi")
    if ret:
        sys.exit(9)

    out_file = "matuc_installer_" + VERSION + ".exe"

    os.rename("matuc_installer.exe", os.path.join("..", out_file))
    os.chdir("..")

    remove("build")
    if distutils.spawn.find_executable("chmod"):
        os.system("chmod a+r " + out_file)

build_installer()
