# pylint: disable=too-many-public-methods,import-error,too-few-public-methods,missing-docstring,unused-variable,multiple-imports
import random
import unittest

import MAGSBS.quality_assurance.markdown as markdown
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
    return markdown.TooManyHeadings().worker(headings)


class TestTooManyHeadings(unittest.TestCase):
    def test_only_a_few_headings_dont_trigger(self):
        h = make_headings(k01=[1, 2, 3, 4, 2, 3, 4, 2, 2, 2, 2, 2, 2, 2, 2])
        self.assertFalse(check(h))

    def test_that_many_headings_of_same_level_trigger(self):
        h = make_headings(k01=[1] + [2] * 22)
        self.assertTrue(check(h))
        h = make_headings(k01=[1, 2] + [3] * 22)
        self.assertTrue(check(h))

    def test_that_nested_structures_trigger_too(self):
        h = make_headings(k02=[1] + [2, 3] * 22)
        self.assertTrue(check(h))

        def test_that_image_files_are_ignored(self):
            h = make_headings(bilder=[1] + [2] * 2222)
            self.assertFalse(check(h))
