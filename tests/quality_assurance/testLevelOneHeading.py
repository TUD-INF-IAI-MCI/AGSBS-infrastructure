# pylint: disable=too-many-public-methods,import-error,too-few-public-methods,missing-docstring,unused-variable,multiple-imports
import unittest
import random

from MAGSBS.quality_assurance import LevelOneHeading
from MAGSBS import datastructures


def make_headings(**headings):
    """Transform {'path':[1,2,3]) into {'path' : [<heading_object>, ...]}, where
    heading object is an heading with the specified number as heading level.
    path must be either "kxx" or "bilder", transformation example:
        k01 -> k01/k01.md
        bilder -> k01/bilder.md"""
    proper_headings = {}
    for path, headings in headings.items():
        if path.startswith("k"):
            path = "{0}/{0}.md".format(path, path[:3])
        else:
            path = "k01/%s.md" % path
        proper_headings[path] = []
        for level in headings:
            text = "h%s%s" % (level, random.randint(1, 999999999))
            h = datastructures.Heading(text, level)
            proper_headings[path].append(h)
    return proper_headings


def check(headings):
    return LevelOneHeading().worker(headings)


class TestLevelOneHeading(unittest.TestCase):
    def test_that_chapters_without_h1_dont_trigger(self):
        headings = make_headings(k01=[2, 3, 2, 3, 2, 3, 4, 5, 6])
        self.assertFalse(check(headings))

    def test_that_directories_with_just_one_h1_heading_dont_trigger(self):
        self.assertFalse(check(make_headings(k01=[1, 2, 3, 4, 5, 6])))

    def test_that_h1_in_image_file_is_ignored(self):
        h = make_headings(k01=[1, 2, 3, 4, 5, 6], bilder=[1, 2, 3, 2, 3, 2])
        self.assertFalse(check(h))

    def test_that_two_h1_in_one_directory_trigger(self):
        h = make_headings(k0101=[1, 2, 3, 4], k0102=[1, 2, 3, 4])
        self.assertTrue(check(h))
        h = make_headings(k0101=[1, 1, 2, 3])
        self.assertTrue(check(h))
