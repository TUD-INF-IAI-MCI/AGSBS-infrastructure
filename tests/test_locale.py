#pylint: disable=too-many-public-methods,import-error,too-few-public-methods,missing-docstring,unused-variable,multiple-imports
import os
import unittest
from unittest.mock import patch
import tempfile
import sys
from MAGSBS.common import _get_localedir


def fake_mo(actual_path, desired=None):
    if desired.lower() in actual_path.lower():
        return [(os.path.join(desired, 'de', 'LC_MESSAGES'), [], ['matuc.mo'])]
    else:
        return [('./', (), ())]

fake_usr_local = lambda x: fake_mo(x, desired="/usr/locales")
fake_c_program_files = lambda x: fake_mo(x, desired='C:\\ProgramData')
fake_none = lambda x: fake_mo(x, ".")

def normalise_path(path):
    """Enable comparison of UNIX and Windows paths."""
    return path.replace('\\', '/').lower()
class test_locale(unittest.TestCase):

    @patch("os.walk", fake_usr_local)
    def test_that_locale_is_available_Linux(self):
        if sys.platform == "linux":
            loc_dir = _get_localedir()
            self.assertTrue(loc_dir == '/usr/share/locale' or
                loc_dir == os.path.join(os.path.dirname(
                os.path.abspath(sys.argv[0])), 'share', 'locale')
                or os.path.join(os.path.dirname(os.path.dirname(os.environ['_'])),
                'share', 'locale'))
        elif sys.platform == "darwin":
           loc_dir = normalise_path(_get_localedir())
           # ToDo: niemals mehrere Bedingungen in einem asserteq, immer mehrere
           # asserteq bzw. assertfalse bzw. asserttrue
           self.assertTrue(loc_dir == '/usr/share/locale' or
                           loc_dir == os.path.join(os.path.dirname(
                           os.path.abspath(sys.argv[0])), 'share', 'locale'))

    @patch("os.walk", fake_c_program_files)
    @patch("sys.platform", "win32")
    @patch("os.getenv", lambda x: r'c:\ProgramData')
    def test_that_locale_is_available_Windows(self):
        # platform unknown, as is the os.sep, use slash *always*
        self.assertEqual(normalise_path(_get_localedir()),
                "c:/programdata/matuc/locale")

        # ToDo: test name ergibt keinen sinn, Testaufbau schlecht. Daten aus
        # Code sammeln, assert* ausführen
    @patch("os.walk", fake_none)
    def test_install_locale_returns_none(self):
        self.assertEqual(_get_localedir(), None)
