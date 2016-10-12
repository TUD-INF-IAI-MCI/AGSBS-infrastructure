Making A Release
================

1.  Check that the ChangeLog contains all relevant changes.
2.  Make sure that all tests pass.
3.  Build the Windows installer:
    1.  cd installer
    2.  python3 build_windows_installer.py
    3.  Use scp or similar to release the file under `elvis/downloads`.
4.  Update the download link in the wiki under
    `https://elvis.inf.tu-dresden.de/wiki/index.php/Matuc#Windows`.
5.  Add a new tag, it should start with a v (like version) and contain three
    version digits. It should match `MAGSBS.config.VERSION`. Example:

        git tag v2.8.7

    Push the tags:

        git push --tags
6.  Make the release known.

