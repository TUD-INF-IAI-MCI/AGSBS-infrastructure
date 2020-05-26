# pylint: disable=too-many-public-methods,import-error,too-few-public-methods,missing-docstring,unused-variable,multiple-imports
import os
import shutil
import tempfile
import unittest
from MAGSBS.common import is_within_lecture


def touch(path):
    """Create the path recursively. If the argument string does not end on a
    slash, it is taken as file name and created as an empty file below the
    prefix."""
    if path.endswith("/"):
        os.makedirs(path, exist_ok=True)
    else:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w") as f:
            f.write("\n")


class TestCommon(unittest.TestCase):
    def setUp(self):
        self.original_directory = os.getcwd()
        self.tmpdir = tempfile.mkdtemp()
        os.chdir(self.tmpdir)
        self.call_cleanup_on_me = None  # used for the OutputFormatters

    def tearDown(self):
        os.chdir(self.original_directory)
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        if self.call_cleanup_on_me:
            self.call_cleanup_on_me.cleanup()

    def test_that_a_file_that_doesnt_exist_is_invalid(self):
        self.assertFalse(is_within_lecture("/highway/to/hell"))

    def test_that_random_path_is_not_considered_correct(self):
        touch("mypath/anotherpath/subdirectory/")
        self.assertFalse(is_within_lecture("mypath/anotherpath/subdirectory/"))
        touch("Bees And Their Importance/paper/foo.tex")
        self.assertFalse(
            is_within_lecture("Bees And Their Importance/paper/foo.tex")
        )

    def test_that_chapter_file_within_invalid_directory_is_invalid_too(self):
        touch("mypath/invalid/k01.md")
        self.assertFalse(is_within_lecture("mypath/invalid/k01.md"))

    def test_that_files_within_correct_chapter_work(self):
        touch("mydir/k01/chapter.md")
        self.assertTrue(is_within_lecture("mydir/k01/chapter.md"))
        touch("mydir/k01/k01.md")
        self.assertTrue(is_within_lecture("mydir/k01/k01.md"))

    def test_that_correct_directories_or_subdirectories_work(self):
        touch("lecture/k01/")
        self.assertTrue(is_within_lecture("lecture/k01"))
        touch("lecture/k01/bilder/")
        self.assertTrue(is_within_lecture("lecture/k01/bilder"))

    def test_that_files_in_lecture_root_work(self):
        touch("myroot/k01//k01.md")  # a sample directory
        touch("myroot/info.md")
        self.assertTrue(is_within_lecture("myroot/info.md"))

    def test_that_directory_outside_a_lecture_returns_false(self):
        touch("myroot/")
        self.assertFalse(is_within_lecture("myroot"))
