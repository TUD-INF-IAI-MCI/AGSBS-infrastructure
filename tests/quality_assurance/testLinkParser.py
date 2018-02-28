import unittest
from MAGSBS.quality_assurance.meta import ErrorMessage
from MAGSBS.quality_assurance.linkchecker import LinkExtractor


class TestLinkExtractor(unittest.TestCase):
    # Note: Test cases are taken from https://pandoc.org/MANUAL.html#links
    # and https://github.com/adam-p/markdown-here/wiki/Markdown-Cheatsheet

    def make_comparison(self, test_inputs, test_outputs, test_name):
        for i, in_string in enumerate(test_inputs):  # take all inputs
            link_checker = LinkExtractor()
            link_checker.find_links_in_markdown(in_string, '')
            # first test, if the number of results is as expected
            self.assertTrue(
                len(test_outputs[i]) == len(link_checker.links_list),
                "{}: For test input {}, the number of returned dictionaries "
                "({}) is not as expected ({})".format(test_name, i, len(
                    link_checker.links_list), len(test_outputs[i])))
            for j in range(len(test_outputs[i])):
                # find the difference to give it as a feedback
                difference = set(link_checker.links_list[j].items()) ^ \
                             set(test_outputs[i][j].items())

                self.assertTrue(difference == set(),
                                "Dictionary on position {}"
                                " is not same as expected. The differences"
                                " are as follows {}".format(j, difference))

    def test_parsing_inline_links(self):
        test_inputs = ["\nThis is an [inline link](/url), \n and here's [one "
                       "with \n a title](http://fsf.org \"click here for a "
                       "good time!\").",
                       "[Write me!](mailto:sam@green.eggs.ham)",
                       "[I'm an inline-style link](https://www.google.com)"]
        test_outputs = [
            [{'file': '', 'link_type': 'inline', 'line_no': 2,
              'is_image': False, 'link_text': 'inline link', 'spaces': 0,
              'link': '/url'},
             {'file': '', 'link_type': 'inline_with_title',
              'line_no': 3, 'is_image': False,
              'link_text': 'one with   a title', 'spaces': 0,
              'link': 'http://fsf.org',
              'link_title': 'click here for a good time!'}
             ],
            [{'file': '', 'link_type': 'inline', 'line_no': 1,
              'is_image': False, 'link_text': 'Write me!', 'spaces': 0,
              'link': 'mailto:sam@green.eggs.ham'}],
            [{'file': '', 'link_type': 'inline', 'line_no': 1,
              'is_image': False, 'link_text': "I'm an inline-style link",
              'spaces': 0, 'link': 'https://www.google.com'}]
        ]
        # run comparison
        self.make_comparison(test_inputs, test_outputs, "Inline links")

    def test_parsing_inline_links_with_tile(self):
        test_inputs = ["[I'm an inline-style link with title]"
                       "(https://www.google.com \"Google's Homepage\")"]
        test_outputs = [[{'file': '', 'link_type': 'inline_with_title',
                          'line_no': 1, 'is_image': False,
                          'link_text': "I'm an inline-style link with title",
                          'spaces': 0, 'link': 'https://www.google.com',
                          'link_title': "Google's Homepage"}]]
        # run comparison
        self.make_comparison(test_inputs, test_outputs,
                             "Inline links with title")

    def test_footnote_links(self):
        test_inputs = [
            "[I'm a reference-style link][Arbitrary case-insensitive reference text]",
            "[You can use numbers for reference - style link definitions][1]"]
        test_outputs = [[{'file': '', 'link_type': 'footnote',
                          'line_no': 1, 'is_image': False,
                          'link_text': "I'm a reference-style link",
                          'spaces': 0,
                          'link': 'Arbitrary case-insensitive reference text'}],
                        [{'file': '', 'link_type': 'footnote', 'line_no': 1,
                          'is_image': False,
                          'link_text': 'You can use numbers for reference - style link definitions',
                          'spaces': 0, 'link': '1'}],
                        ]
        # run comparison
        self.make_comparison(test_inputs, test_outputs, "Footnote links")

    def test_reference_links(self):
        test_inputs = ["[my label 1]: /foo/bar.html  \"My title, optional\"",
                       "[my label 2]: /foo",
                       "[my label 3]: http://fsf.org (The free software foundation)",
                       "[my label 4]: /bar#special  'A title in single quotes']",
                       "[my label 5]: <http://foo.bar.baz>",
                       "\n[my label 3]: http://fsf.org \n\t\"The free software foundation\""]
        test_outputs = [
            [{'file': '', 'link_type': 'reference', 'line_no': 1,
              'is_image': False, 'link_text': 'my label 1', 'spaces': 1,
              'link': '/foo/bar.html'}],
            [{'file': '', 'link_type': 'reference', 'line_no': 1,
              'is_image': False, 'link_text': 'my label 2', 'spaces': 1,
              'link': '/foo'}],
            [{'file': '', 'link_type': 'reference', 'line_no': 1,
              'is_image': False, 'link_text': 'my label 3',
              'spaces': 1, 'link': 'http://fsf.org'}],
            [{'file': '', 'link_type': 'reference', 'line_no': 1,
              'is_image': False,
              'link_text': 'my label 4', 'spaces': 1,
              'link': '/bar#special'}],
            [{'file': '', 'link_type': 'reference', 'line_no': 1,
              'is_image': False,
              'link_text': 'my label 5', 'spaces': 1,
              'link': 'http://foo.bar.baz'}],
            [{'file': '', 'link_type': 'reference',
              'line_no': 2, 'is_image': False,
              'link_text': 'my label 3', 'spaces': 1,
              'link': 'http://fsf.org'}]
        ]
        # run comparison
        self.make_comparison(test_inputs, test_outputs, "Reference links")

    def test_standalone_links(self):
        test_inputs = ["See[my website][]."]
        test_outputs = [[{'file': '', 'link_type': 'standalone_link',
                          'line_no': 1, 'link': 'my website'}]]
        # run comparison
        self.make_comparison(test_inputs, test_outputs, "Standalone links")

    def test_angle_brackets_links(self):
        test_inputs = ["URLs and URLs in angle brackets will automatically get"
                       " turned into links.\n http://www.example.com or "
                       "<http://www.example.com> and sometimes example.com "
                       "(but not on Github, for example).",
                       "<http://www.example.com>",
                        "<http://www.example.com>pokus<k01.md#heading1>"]
        test_outputs = [[{'file': '', 'link_type': 'angle_brackets',
                          'line_no': 2, 'link': 'http://www.example.com'}],
                        [{'file': '', 'link_type': 'angle_brackets',
                          'line_no': 1, 'link': 'http://www.example.com'}],
                        [{'file': '', 'link_type': 'angle_brackets',
                          'line_no': 1, 'link': 'http://www.example.com'},
                         {'file': '', 'link_type': 'angle_brackets',
                          'line_no': 1, 'link': 'k01.md#heading1'}]]
        # run comparison
        self.make_comparison(test_inputs, test_outputs, "Angle brackets links")

    def test_other_links(self):
        test_inputs = ["- [x] Finish changes\n[ ] Push my commits to GitHub"]
        test_outputs = [
            [{'file': '', 'link_type': 'standalone_link', 'line_no': 1,
              'link': 'x'}, {'file': '', 'link_type': 'standalone_link',
              'line_no': 1, 'link': ' '}]
        ]
        # run comparison
        self.make_comparison(test_inputs, test_outputs, "Other links")