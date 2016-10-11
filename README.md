<!-- vim: set ft=markdown sts=4 ts=4 sw=4 expandtab: -->
MAGSBS - MarkDown AG SBS module
===============================

Introduction
------------


This module and it's sample command client is meant to ease the work flow from
the [AG SBS](https://elvis.inf.tu-dresden.de/index.php?menuid=23). In short it
helps prepare lecture material for visually impaired and blind students. The
format for editing is MarkDown.

The MarkDown files are converted to HTML which is sent to the students.  HTML
has the advantage that images can be included and images can be described (using
the alt attribute) at the same time so that visually impaired/blind students can
work with their sighted colleagues using the same document.

This module automates a lot of processes and can be used in other applications
as a plug in or on the command line. It'll help convert the files (with a few AG
SBS-specific language extensions), create a table of contents for the lecture,
create navigation bars in the documents and more.

Installation
------------

You can install this module as well as the program from source. The following
sections describe the installation on Windows and GNU/Linux. The installation
for Mac should work similar. You're welcome to send corrections or improvement
requests.

### Dependencies

This version of MAGSBS / matuc depends on Python in version >= 3.4.

To test what your default Python is, execute:

    python --version

If it outputs a version starting with 3, everything is fine and you can execute
all commands below with "python". If however the command returns something like
2.x.x, you need to call every mentioned command instead with "python3". In the
latter case, you should also check that Python3 is instaled.

In addition you need [Pandoc](http://pandoc.org) (version >= 1.12),
[GladTeX](http://humenda.github.io/GladTeX) and Python-Pandocfilters.

**Note:** For Windows, there are pre-compiled installers available. If you don't want to
use those, you have to set up the dependencies manually:

    pip install pandocfilters

### Installation From Source On Windows


+ Windows: open a cmd window (e.g. press Windows + r and type there `cmd<enter>`),
  switch with the "cd"-command to the correct directory and execute the
  following command:

    setup.py install

Now you can run matuc, which was installed to `c:\python<version>\scripts`.
Consider adding this path to the `%PATH%` variable. Also keep in mind that by
default, you have to type matuc.py.

### Debian/Ubuntu/Mint, et al.

    sudo apt install python3-pandocfilters gladtex pandoc

Then proceed with the next section.

### unixoid systems

Please test, whether you have to run python3 or python. Try `python3 --version`
to find out whether python3 exists and if so, use that. Otherwise use python as
this:

    python setup.py install

You can run `matuc` straight away.
