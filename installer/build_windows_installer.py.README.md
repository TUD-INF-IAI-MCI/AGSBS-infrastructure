The python script `build_windows_installer.py` builds a Windows package by
performing the following steps:

1.  Download an (embeddable) GladTeX release and the Pandoc installer
2.  Extract both to a build directory
3.  Compile Matuc with py2exe and move the result to the build directory
    -   If the host system is not Windows, the script will attempt to use Wine.
    -   The Python version of the GladTeX binary (contained in the file name)
        MUST match _exactly_ the version of Python with which Matuc is compiled.
    -   2016-10: py2exe does not support python 3.5, so only 3.4.4 works
4.  Move additional files (READMe, COPYING) to the build directory
5.  Rename `build` to `binary`, create a new build directory and move
    `binary`into it.
6.  Move the `matuc.nsi` installation script and the `EnvVarUpdate.nsh` helper
    into `build/`.
7.  Update version and a few other strings in `matuc.nsi`.
8.  Execute makensis, move the new executable into the installer/ directory.
9.  Clean up.

