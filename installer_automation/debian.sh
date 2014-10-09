#!/bin/sh
# Build a debian package out of the source. Must be called from source root
set -e

PACKAGE_NAME=magsbs
BUILDDIR=/tmp/$PACKAGE_NAME

rm -rf $BUILDDIR

mkdir $BUILDDIR
cp -dpr MAGSBS $BUILDDIR
cp -dpr cli setup.py $BUILDDIR
CWD=`pwd`
cd $BUILDDIR/..
tar czf $PACKAGE_NAME'_0.1.orig.tar.gz' $PACKAGE_NAME

cd $CWD
cp -dpr debian/ $BUILDDIR

cd $BUILDDIR
dpkg-buildpackage
echo "Package can be found in /tmp."
