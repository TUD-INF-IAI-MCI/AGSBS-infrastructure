# pylint: disable=too-many-public-methods,import-error,too-few-public-methods,missing-docstring,unused-variable
import unittest
import MAGSBS.datastructures
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
                (
                    "only level-one "
                    "chapters should have been counted; got: {}"
                ).format(repr(c.get_heading_enumeration())),
            )
            self.assertEqual(
                c.get_heading_enumeration()[0],
                i,
                (
                    "the enumerator "
                    "should have counted to %d, but counted only to %d"
                )
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
                    "two level "
                    "should exist: chapter and section; got instead: {}"
                ).format(repr(c.get_heading_enumeration())),
            )
            self.assertEqual(
                c.get_heading_enumeration(),
                [1, i],
                (
                    "the enumerator "
                    "should have counted to %d, but counted only to %d"
                )
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
                    "two level "
                    "should exist: chapter and section; got instead: {}"
                ).format(repr(c.get_heading_enumeration())),
            )
            self.assertEqual(
                c.get_heading_enumeration(),
                [2, i],
                (
                    "the enumerator "
                    "should have counted to %d, but counted only to %d"
                )
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
