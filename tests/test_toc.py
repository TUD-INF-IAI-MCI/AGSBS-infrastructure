# pylint: disable=too-many-public-methods,import-error,too-few-public-methods,missing-docstring,unused-variable
import os
import shutil
import tempfile
import unittest
import MAGSBS.datastructures
from MAGSBS import config
import MAGSBS.toc as toc

# shorthand for creating headings
def h(text, level, chapter=None):
    heading = MAGSBS.datastructures.Heading(text, level)
    if chapter:
        heading.set_chapter_number(chapter)
    return heading


class test_factories(unittest.TestCase):
    ##############################################################
    # [heading] enumerater
    def test_that_chapters_are_enumerated_subsequently(self):
        c = toc.ChapterNumberEnumerator()
        for i in range(1, 11):
            heading = h("stuff %d" % i, 1)
            heading.set_chapter_number(i)  # always a new chapter
            c.register(heading)
            self.assertEqual(
                len(c.get_heading_enumeration()),
                1,
                ("only level-one " "chapters should have been counted; got: {}").format(
                    repr(c.get_heading_enumeration())
                ),
            )
            self.assertEqual(
                c.get_heading_enumeration()[0],
                i,
                ("the enumerator " "should have counted to %d, but counted only to %d")
                % (i, c.get_heading_enumeration()[0]),
            )

    def test_that_sections_within_chapters_are_enumerated_subsequently(self):
        c = toc.ChapterNumberEnumerator()
        # try to chapters; chapter 1:
        heading = h("absolute h1", 1, 1)
        c.register(heading)
        self.assertEqual(c.get_heading_enumeration(), [1])
        for i in range(1, 6):
            heading = h("stuff %d" % i, 2, chapter=1)
            c.register(heading)
            self.assertEqual(
                len(c.get_heading_enumeration()),
                2,
                (
                    "two level " "should exist: chapter and section; got instead: {}"
                ).format(repr(c.get_heading_enumeration())),
            )
            self.assertEqual(
                c.get_heading_enumeration(),
                [1, i],
                ("the enumerator " "should have counted to %d, but counted only to %d")
                % (i, c.get_heading_enumeration()[0]),
            )

        # chapter 2
        heading = h("absolute h1", 1, 2)
        c.register(heading)
        self.assertEqual(c.get_heading_enumeration(), [2])
        for i in range(1, 6):
            heading = h("stuff %d" % i, 2, chapter=2)
            c.register(heading)
            self.assertEqual(
                len(c.get_heading_enumeration()),
                2,
                (
                    "two level " "should exist: chapter and section; got instead: {}"
                ).format(repr(c.get_heading_enumeration())),
            )
            self.assertEqual(
                c.get_heading_enumeration(),
                [2, i],
                ("the enumerator " "should have counted to %d, but counted only to %d")
                % (i, c.get_heading_enumeration()[0]),
            )

    def test_that_objects_with_missing_methods_cause_type_error(self):
        with self.assertRaises(TypeError):
            c = toc.ChapterNumberEnumerator()
            c.register(9)

    def test_that_headings_with_none_values_cause_value_error(self):
        class has_no_level:  # heading mock
            def get_chapter_number(self):
                return 9

            def get_level(self):
                return None

        c = toc.ChapterNumberEnumerator()
        with self.assertRaises(ValueError):
            c.register(has_no_level())  # heading with level set
        with self.assertRaises(ValueError):
            c.register(h("h1 without chapter", 99))


class TestHeadingIndexer(unittest.TestCase):
    def setUp(self):
        self.orig_cwd = os.getcwd()
        self.tmpdir = tempfile.mkdtemp()
        os.chdir(self.tmpdir)

    def tearDown(self):
        os.chdir(self.orig_cwd)
        shutil.rmtree(self.tmpdir)

    def write_conf(self):
        lecture_meta = config.LectureMetaData(config.CONF_FILE_NAME)
        lecture_meta[config.MetaInfo.GenerateToc] = 1
        lecture_meta[config.MetaInfo.LectureTitle] = "Test"
        lecture_meta[config.MetaInfo.SemesterOfEdit] = "SS 2026"
        lecture_meta.write()

    def test_that_hashed_lines_in_fenced_code_blocks_are_ignored_for_toc(self):
        self.write_conf()
        os.mkdir("k01")
        with open(os.path.join("k01", "k01.md"), "w", encoding="utf-8") as file:
            file.write(
                "# Title\n\n"
                "```text\n"
                "Some text\n\n"
                "# Yields erroneously a heading entry\n\n"
                "Some other text\n"
                "# This does not create a heading\n"
                "```\n"
            )

        indexer = toc.HeadingIndexer(".")
        indexer.walk()
        output = toc.TocFormatter(indexer.get_index(), ".").format()

        self.assertIn("Title", output)
        self.assertNotIn("Yields erroneously a heading entry", output)
