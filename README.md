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

### Dependencies

This version of MAGSBS / matuc depends on Python in version >= 3.6.

To test what your default Python is, execute:

    python --version

If it outputs a version starting with 3, everything is fine and you can execute
all commands below with "python" (and "pip". If however the command returns
something like 2.x.x, you need to call every mentioned command instead with
"python3". In the latter case, you should also check that Python3 is instaled.

***Other dependencies:***

-   Pandoc: <https://github.com/jgm/pandoc>
-   pandocfilters for python
    -   pip3 install pandocfilters
-   GladTeX: <http://humenda.github.io/GladTeX/downloads.html>
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


### Installation

On any platform, it is enough to change to the source directory and issue the
following command:

    pip install --upgrade .

**Note:** on Debian and derivatives (Mint, Ubuntu), pip3 should be used instead.

Localization
------------

For correct running of different language versions, it is now necessary to
manually generate .mo files and create appropriate structure given by
[gettext](https://docs.python.org/3/library/gettext.html), i.e.
localedir/language/LC_MESSAGES/domain.mo for each language (encoded using
two-letter codes given by [ISO-639-1](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes)).

For generation, you can use the e.g. the [msgfmt script]
(http://refspecs.linuxbase.org/LSB_3.0.0/LSB-PDA/LSB-PDA/msgfmt.html)


Development
-----------

### Code Style

The source code is auto-formatted using the [black code
formatter](https://github.com/psf/black).

Before committing code changes, install it via ``pip install -U black`` and run ``black
.`` in the repository's root to ensure everything is formatted in a consistent manner.
