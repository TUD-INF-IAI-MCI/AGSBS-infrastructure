import itertools
import unittest
from urllib.parse import urlparse

from MAGSBS.quality_assurance import linkchecker
from MAGSBS.quality_assurance.meta import ErrorMessage


class TestHelpingFunctions(unittest.TestCase):

    def test_print_list(self):
        self.assertRaises(ValueError, linkchecker.print_list_of_extensions, [])
        self.assertEqual(linkchecker.print_list_of_extensions(["jpg"]), ".jpg")
        self.assertEqual(linkchecker.print_list_of_extensions(["jpg", "bmp"]),
                         ".jpg or .bmp")
        self.assertEqual(linkchecker.print_list_of_extensions(
            ["jpg", "bmp", "svg", "png"]), ".jpg, .bmp, .svg or .png")

    def test_replace_web_extension_with_md(self):
        self.assertEqual(linkchecker.replace_web_extension_with_md(""), "")
        self.assertEqual(linkchecker.replace_web_extension_with_md("no_dot"),
                         "no_dot")
        for ext in linkchecker.WEB_EXTENSIONS:
            self.assertEqual(linkchecker.replace_web_extension_with_md(
                "test/k01." + ext), "test/k01.md")
            self.assertEqual(linkchecker.replace_web_extension_with_md(
                "test.more.dots.k01." + ext), "test.more.dots.k01.md")


class TestLinkExtractor(unittest.TestCase):

    def test_create_dct(self):
        extractor = linkchecker.LinkExtractor()
        self.assertEqual(
            extractor.create_dct("file.md", "path", 5, "reference",
                                 ("!", "text", "link")),
            {"file": "file.md", "file_path": "path", "link_type": "reference",
             "line_no": 5, "is_image": True, "link_text": "text",
             "link": "link"})
        self.assertEqual(
            extractor.create_dct("file.md", "path", 5, "footnote",
                                 ("", "link", "")),
            {"file": "file.md", "file_path": "path", "link_type": "footnote",
             "line_no": 5, "is_image": False, "link": "link"})

class TestLinkChecker(unittest.TestCase):

    def test_check_correct_email_address(self):
        correct_link = {"file": "file.md", "file_path": "path", "link_type":
                    "reference", "line_no": 1, "is_image": False,
                    "link": "mailto: jones@gmail.com"}
        wrong_link = {"file": "file.md", "file_path": "path", "link_type":
                    "reference", "line_no": 5, "is_image": False,
                    "link": "mailto: fail@.@gmail.com"}

        checker = linkchecker.LinkChecker([])
        checker.check_correct_email_address(correct_link)
        self.assertEqual(checker.errors, [])
        checker.check_correct_email_address(wrong_link)
        self.assertEqual(len(checker.errors), 1)
        self.assertEqual(checker.errors[0].lineno, 5)

    def test_find_reference_for_link_and_link_for_reference(self):
        test_links = [
            {"file": "file.md", "file_path": "path", "link_type": "reference",
             "line_no": 1, "is_image": False, "link": "k01.html",
             "link_text": "my_reference"},
            {"file": "file.md", "file_path": "path", "link_type": "footnote",
             "line_no": 3, "is_image": False, "link": "1"}]

        correct_ref = {
            "file": "file.md", "file_path": "path", "link_type": "reference",
            "line_no": 6, "is_image": False, "link": "k01.html",
            "link_text": "1"}
        wrong_ref = {
            "file": "file.md", "file_path": "path", "link_type": "reference",
            "line_no": 8, "is_image": False, "link": "k01.html",
            "link_text": "non-existing link"}
        correct_foot = {
            "file": "file.md", "file_path": "path", "link_type": "footnote",
            "line_no": 10, "is_image": False, "link": "my_reference"}
        wrong_foot = {
            "file": "file.md", "file_path": "path", "link_type": "footnote",
            "line_no": 12, "is_image": False, "link": "incorrect_reference"}

        checker = linkchecker.LinkChecker(test_links)
        checker.find_link_for_reference(correct_ref)
        self.assertEqual(checker.errors, [])
        checker.find_link_for_reference(wrong_ref)
        self.assertEqual(len(checker.errors), 1)
        self.assertEqual(checker.errors[0].lineno, 8)

        checker = linkchecker.LinkChecker(test_links)
        checker.find_reference_for_link(correct_foot)
        self.assertEqual(checker.errors, [])
        checker.find_reference_for_link(wrong_foot)
        self.assertEqual(len(checker.errors), 1)
        self.assertEqual(checker.errors[0].lineno, 12)

    def test_check_extension(self):
        correct_link = {
            "file": "file.md", "file_path": "path", "link_type": "reference",
            "line_no": 10, "is_image": False, "link": "k01.html",
            "link_text": "1"}
        img_instead_html = {
            "file": "file.md", "file_path": "path", "link_type": "reference",
            "line_no": 1, "is_image": True, "link": "k01.html",
            "link_text": "1"}
        html_instead_img = {
            "file": "file.md", "file_path": "path", "link_type": "reference",
            "line_no": 2, "is_image": False, "link": "k01.jpg",
            "link_text": "1"}
        incorrect_link = {
            "file": "file.md", "file_path": "path", "link_type": "reference",
            "line_no": 3, "is_image": True, "link": "k01.md",
            "link_text": "1"}

        def get_path(link):
            parsed = urlparse(link.get("link"))
            return parsed.path

        checker = linkchecker.LinkChecker([])
        checker.check_extension(get_path(correct_link), correct_link)
        self.assertEqual(checker.errors, [])
        checker.check_extension(get_path(img_instead_html), img_instead_html)
        checker.check_extension(get_path(html_instead_img), html_instead_img)
        checker.check_extension(get_path(incorrect_link), incorrect_link)
        self.assertEqual(len(checker.errors), 3)
        for i in range(len(checker.errors)):
            self.assertEqual(checker.errors[i].lineno, i + 1)
