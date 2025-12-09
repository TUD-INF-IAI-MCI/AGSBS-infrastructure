"""This module contains common datastructures, functions and constants."""
# vim: set expandtab sts=4 ts=4 sw=4:
# This is free software, licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2016-2025 Sebastian Humenda <shumenda |at| gmx |dot| de>
import atexit
import gettext
import itertools
import locale
import os
import sys
import sysconfig


VALID_PREFACE_BGN = ["v"]
VALID_MAIN_BGN = [
    "k",
    "blatt",
    "Blatt",
    "paper",
    "Übung",
    "übung",
    "uebung",
    "Uebung",
]
VALID_APPENDIX_BGN = ["anh"]
VALID_FILE_BGN = VALID_PREFACE_BGN + VALID_MAIN_BGN + VALID_APPENDIX_BGN

def dbg(*text):
    """Output a piece of text if debugging is enabled."""
    if "DEBUG" in os.environ and os.environ["DEBUG"] in ("1", "true"):
        for piece in text:
            print(piece, end="")
    if not text[-1].endswith("\n"):
        print()


# pylint: disable=too-few-public-methods
class Singleton:
    """A non-thread-safe helper class to ease implementing singletons.
This should be used as a decorator -- not a metaclass -- to the class that
should be a singleton.

The decorated class can define one `__init__` function that takes only the
`self` argument. Other than that, there are no restrictions that apply to the
decorated class.

Limitations: The decorated class cannot be inherited from.
"""

    def __init__(self, decorated):
        self._decorated = decorated
        self._instance = None

    def __call__(self):
        """Returns the singleton instance. Upon its first call, it creates a
new instance of the decorated class and calls its `__init__` method.  On all
subsequent calls, the already created instance is returned.  """
        if not self._instance:
            self._instance = self._decorated()
        return self._instance

    def __instancecheck__(self, inst):
        return isinstance(inst, self._decorated)


def format_warning(warning):
    if not hasattr(warning, "get") or not warning.get("message"):
        raise TypeError(
            ('Expected a dictionary with at least a key called "message."')
        )
    string = ["Warning: ", warning.pop("message"), "\n"]
    for key, val in warning.items():
        string.append(f"  {key.title()}: {val}\n")
    return "".join(string)


@Singleton
class WarningRegistry:
    """This globally available class gathers all warnings during the conversion
    process. They are gathered during the conversion process and can be
    retrieved at the end. If they are not requested, they will be displayed when
    the program exits."""

    def __init__(self):
        self.__warnings = []  # lists are actually thread-safe regarding .append

    def register_warning(self, msg, lnum=None, path=None):
        warning = {"message": msg}
        if lnum:
            warning["line"] = lnum
        if path:
            warning["path"] = path
        self.__warnings.append(warning)

    def get_warnings(self):
        """Return all warnings an flush the list of warnings."""
        warnings = self.__warnings[:]
        self.__warnings = []
        return warnings


def flush_warnings():
    """Print all warnings to stderr which were gathered during execution and
    have not been retrieved since."""
    registry = WarningRegistry()
    for warning in registry.get_warnings():
        sys.stderr.write(format_warning(warning))


# pylint: disable=invalid-name
def pairwise(something):
    """Iterate pairwise over the given ocllection / iterator."""
    a, b = itertools.tee(something)
    next(b, None)
    for pair in zip(a, b):
        yield (pair[0], pair[1])


def is_valid_file(path):
    """is_valid_file(path)
    Return True if file is a valid fiele as defined in the specifications (e.g.
    it's a chapter, etc.). `path` may be any path, including an absolute path or
    None."""
    if not path:
        return False
    path = os.path.basename(path)
    for token in VALID_FILE_BGN:
        if path.startswith(token) and len(path) > len(token) + 1:
            # if prefix token is followed by digit, it's valid
            if path[len(token)].isdigit():
                return True
    return False


def is_lecture_root(directory):
    """is_lecture_root(directory)
    Check whether the given directory is the lecture root.
    Algorithm: if dir starts with a valid chapter prefix, it is obviously not.
    for all other cases, try to obtain a list of files and if _one_
    **directory** starts with a chapter prefix, it is a valid chapter root. As
    an addition, a ".LectureMetaData.dcxml" will also mark a lecture root."""
    directory = os.path.abspath(directory)
    # if cwd starts with a chapter prefix, it is no lecture root
    if is_valid_file(directory):
        return False
    subdir = (e for e in os.listdir(directory)
            if os.path.isdir(os.path.join(directory, e)))
    # if any of the subdirectories is a valid file, it's a lecture root
    if any(directory for directory in subdir if is_valid_file(directory)):
        return True  # at least one chapter, so this is a lecture root
    return False


def is_within_lecture(path):
    """Check whether given path is within a lecture. Since explanation of the
    whole lecture hirarchy does not belong here, a few examples instead:
    path = os.path.abspath(path)
    True:
        foo/k01/k01.md
        foo/k01/blah.md
        k01/blah.md
        foo/k01/bilder/x.png
        k01/k01.md
        lecture/k01/
        lecture/info.md
    False:
        completely/invalid/stuff.md
        lecture/chapter/k01.md

    NOTE: in order to detect a file correctly from the lecture root, at least
    one correct chapter directory hs to exist.
    """
    parent = os.path.dirname
    if not os.path.exists(path):
        return False
    if os.path.isfile(path):
        return is_valid_file(parent(path)) \
                or is_valid_file(parent(parent(path))) \
                or is_lecture_root(parent(path))
    # directories:
    return is_valid_file(path) or is_valid_file(parent(path))


################################################################################
# register atexit hook to flush warnings, if they haven't been queried
atexit.register(flush_warnings)

# pylint: disable=protected-access
def _get_localedir():
    """Get locale dirs depending on operating system."""
    loc_dirs = []
    # development or pipx paths should take precedence
    executable_parent_dir = os.path.dirname(os.path.dirname(
            os.path.abspath(sys.argv[0])))
    # for development, it might be in `SCRIPT`/../mo
    loc_dirs.append(os.path.join(executable_parent_dir, "mo"))
    # for pipx, use sysconfig to get the data path
    loc_dirs.append(os.path.join(sysconfig.get_path("data"), "share", "locale"))

    loc_dirs.append(gettext._default_localedir)
    if sys.platform in ["linux", "darwin"]:
        loc_dirs += ["/usr/share/locale", "/usr/local/share/locale"]
    elif sys.platform == "win32":
        # default installer place
        loc_dirs.append(os.path.join(os.getenv("ProgramData"),
                "agsbs", "matuc", "locale"))
    dbg("potential directories with locales:\n  ", '\n  '.join(loc_dirs))
    locale_dir_with_matuc = None
    for directory in loc_dirs:
        loc_dir_lang = os.path.join(directory, locale.getlocale()[0][:2])
        if any(file == "matuc.mo" or file == "MAGSBS-matuc.mo"
                for _d, _ds, files in os.walk(loc_dir_lang) for file in files):
            locale_dir_with_matuc = directory
            dbg("localisation found in ", locale_dir_with_matuc)
            break
    if not locale_dir_with_matuc:
        print("Envs: ")
        for k,v in os.environ.items():
            print(f"{k} = {v}")
        WarningRegistry().register_warning("Couldn't find 'locale' directory with "
            "translations.")  # → None
    return locale_dir_with_matuc


def setup_i18n():
    """Set up internationalisation support in MAGSBS/matuc."""
    # ignore country suffix for now, we are lucky if we find localisation for
    # German or Spanish and we do not care too much about the rather small
    # differences between these, for *now*
    localedir = _get_localedir()
    trans = None
    try:
        trans = gettext.translation(
            "matuc", localedir=localedir, languages=[locale.getlocale()[0][:2]],
        )
    except (FileNotFoundError, AttributeError):
        trans = gettext.translation("matuc", localedir=localedir, fallback=True)

    trans.install()
