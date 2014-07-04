#!/bin/sh

set -e

rm -rf build
mkdir build
cp ../cli/matuc.py build
cp matuc.nsi build
cp EnvVarUpdate.nsh build
cp -dpr ../MAGSBS build
cp -dpr binary build
cp -dpr 3rdparty build
cp -dpr ../COPYING build/COPYING.txt
flip -bu build/COPYING.txt
cd build
makensis matuc.nsi
mv matuc_installer.exe ..
cd ..
rm -rf build
chmod a+r matuc_installer.exe
