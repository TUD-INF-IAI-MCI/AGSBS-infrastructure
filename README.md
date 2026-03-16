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

-   Python
-   Pandoc: <https://github.com/jgm/pandoc>
-   a LaTeX distribution.
    -   On GNU/Linux, use your package manager to install a recent LaTeX
        distribution. If you happen to run Debian, Linux Mint or Ubuntu,
        typing `sudo apt-get install texlive-full` installs a full setup (or
        hunt down the packages yourself).
    -   On OS/X, install [MacTeX](https://www.tug.org/mactex/).
    -   On windows you can try [MikTeX](https://miktex.org/)
        -   It is advised that you install a 64 bit MikTeX on a 64 bit system
            because a mixture of 32 and 64 bit components is known to cause hard
            to debug issues.

NOTE: Python package dependencies and console scripts are declared in
`pyproject.toml`.
The Python package dependencies are installed via `pyproject.toml`.
AGSBS currently pins GladTeX/GleeTeX to upstream commit
`990f6526873a135683fe75e84e754f3059e63b7e`, because the latest PyPI release
does not provide the Pandoc API required by the current conversion pipeline.
Pandoc and a LaTeX distribution still need to be installed separately on the
system.

### Installation

On any platform, it is enough to change to the source directory and issue one
of the following commands:

-   Install the command-line tool in an isolated environment via `pipx`:

    `python -m pip install pipx`

    `pipx install .`
-   Install the package into the current Python environment:

    `python -m pip install .`
-   Install an editable development environment:

    `python -m pip install -e .`
-   Reinstall via `pipx` after local changes:

    `pipx install --force .`

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
