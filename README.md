<!-- vim: set ft=markdown sts=4 ts=4 sw=4 expandtab: -->
MAGSBS - MarkDown AG SBS module
===============================

Introduction
------------


This module and its command-line client assists in preparing and editing lecture
material, books and more for visually impaired and blind students. It is
developed at the [AG SBS](https://elvis.inf.tu-dresden.de/index.php?menuid=23).
The format for editing is MarkDown and the accessible output
format is HTML.
HTML has the advantage that the referenced images can be described with an
alternate text for the screen reader user, while displaying the actual image on
the screen.
This enables visually impaired/blind students to work with their sighted
colleagues using the same document.

This module automates a lot of processes and can be used in other applications
as a plugin or on the command line. It converts the source markdown documents
(with a few AG SBS-specific language extensions), creates a table of contents
for the lecture, creates navigation bars in the documents and more.

Installation
------------

You can install this module as well as the program from source. The following
sections describe the installation for Windows, GNU/Linux and Mac. You are
welcome to send corrections or additions, as well as any requests.

### Dependencies (excluding Python modules)

-   Python
-   Pandoc: <https://github.com/jgm/pandoc>
-   a LaTeX distribution.
    -   On GNU/Linux, you should use your package manager to get a recent
        version of GladTeX and a LaTeX distribution. If you happen to run
        Debian, Linux Mint or Ubuntu, typing `sudo apt-get install gladtex
        texlive-full` installs everything (or hunt down the packages yourself).
    -   On OS/X, you should install
        [GladTeX](https://github.com/humenda/GladTeX) from source and install
        [MacTeX](www.tug.org/mactex/).
    -   On windows you can try [MikTeX](https://miktex.org/)
        -   It is advised that you install a 64 bit MikTeX on a 64 bit system
            because a mixture of 32 and 64 bit components is known to cause hard
            to debug issues.

NOTE: for development, you can look up the dependencies in setup.py and run
MAGSBS/matuc.py from source.

### Installation

On any platform, it is enough to change to the source directory and issue the
following commands:

-   If you have not pipx installed:

    `python -m pip install pipx`
-   Install the package:

    `pipx install .`
-   to reinstall:

    `pipx install -f .`

**Note:** on Debian and derivatives (Mint, Ubuntu), "python3" should be used
instead.

Localization
------------

MAGSBS/Matuc uses gettext for localisation.
Most of the process is handled transparently.
To do translations, we recommend installing gettext and use either the Makefile
or Python's gettext tooling to add translations.

Development
-----------

### Code Style

The source code is auto-formatted using the [black code
formatter](https://github.com/psf/black).

Before committing code changes, install it via ``pip install -U black`` and run ``black
.`` in the repository's root to ensure everything is formatted in a consistent manner.
