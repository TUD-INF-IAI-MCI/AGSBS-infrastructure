# This is free software, licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2016 Sebastian Humenda <shumenda |at|gmx |dot| de>
"""
Link checker for MarkDown documents.

When linking to another file, the link has to use the target format extension
(i.e. .html) and hence that has to be considered when looking for broken links.
This link checker is hence tailored to MarkDown.

This link checker also checks for broken image references.

This link checker does not touch the file system. It requires a list of files
(as produced by os.walk()) and all links and images. Helper function extract
those for the link checker.
"""

import os
import re

INLINE_LINK = re.compile(r'\[([^\]]+)\]\s*\(([^)^"]+)\)')
INLINE_LINK_WITH_TITLE = re.compile(r'\[([^\]]+)\]\s*\(([^)]+("|\')[^)]+)\)')
FOOTNOTE_LINK_TEXT = re.compile(r'\[([^\]]+)\]\s*\[([^\]]+)\]')
FOOTNOTE_LINK_REFERENCE = re.compile(r'\[([^\]]+)\]:\s*(\S+)')
STANDALONE_LINK = re.compile(r'[^\]\(\s]\s*\[[^\]]+\]\s*[^\[\(\s]')
ANGLE_BRACKETS_LINK = re.compile(r'<[^>]+>')

"""
def_links = re.compile(
    r'^ *\[([^^\]]+)\]: *'  # [key]:
    r'<?([^\s>]+)>?'  # <link> or link
    r'(?: +["(]([^\n]+)[")])? *(?:\n+|$)'
)
"""

"""
A common source of error are broken links. Normal link checkers won't work,
since they are working on HTML files. It is hence necessary to parse all
MarkDown links and implement the destination checks manually (to the
resulting HTML files). As a plus, references within the document could be
checked as well.

For checking IDs, it is a good idea to generate IDs of the target document.
Headings get automatic IDs, which can be generated using datastructures.gen_id.
Furthermore, the user may create own anchors with <span id="foo"/> or the
div equivalent.
"""

"""
Checking links in the markdown document
- a) parse the links
- b) test if they are corretly structured
- c) check external links
    - ca) test if the computer is online
    - cb) if online - test the reachability of the link
- d) check internal links (no need to be online, files should be on the disk)
    - da) check if files are generated
    - db) if they are - check all links given by markdown
"""


class LinkParser():
    # ToDo: document: files must be relative to document being checked
    # ToDo: how to thread ..? just check with os.path.exists()? needs base
    # directory
    # def __init__(self, links, images, files):
    def __init__(self, file_tree):
        self.__errors = []  # generated errors
        self.__file_tree = file_tree  # files to be examined
        self.__links_list = []
        self.__regexps = {"inline": INLINE_LINK,
                          "inline_with_title": INLINE_LINK_WITH_TITLE,
                          "footnote": FOOTNOTE_LINK_TEXT,
                          "reference": FOOTNOTE_LINK_REFERENCE,
                          "standalone_link": STANDALONE_LINK,
                          "angle_brackets": ANGLE_BRACKETS_LINK
                          }

    def get_list_of_md_files(self):
        """ This function creates list of paths to .md files which links should
        be tested. It also returns the name of the file. """
        md_file_list = []
        for directory_name, dir_list, file_list in self.__file_tree:
            for file in file_list:
                if file.endswith(".md"):  # only .md files will be inspected
                    file_path = os.path.join(directory_name, file)
                    # check if file exists
                    if os.path.isfile(file_path):
                        # whole path for generation, filename for feedback
                        md_file_list.append((file_path, file))
        return md_file_list

    def extract_links(self):
        for file_path, file_name in self.get_list_of_md_files():
            # encoding should be already checked
            with open(file_path, encoding="utf-8") as f:
                # call the function for finding links
                self.find_md_links(f, file_name)
        print(self.__links_list)  # TODO: remove this testing string

    def find_md_links(self, md_file_data, file_name):
        """ Updates the list of dictionaries that contains the links retrieved
        from the markdown string. """

        text = md_file_data.read()
        for description, reg_expr in self.__regexps.items():
            # detect links using regular expressions
            links = reg_expr.findall(text)
            for link in links:
                self.__links_list.append(self.create_dct(file_name,
                                                         description, link))

        # TODO: find the line of the link
        # TODO: if the link is with the title
            # check if it is correctly build using " or ' (the last
            # char should be the there at least twice - and first one
            # is the end of the link
        # TODO: detect also TEXT_LINK_ITSELF - link only in []
            # error if it has no reference in footnote_link_url
        # TODO: link within picture description

    def create_dct(self, file_name, type, link):
        """ This function generates the dictionary that contains all the
        important data for the link """
        print(link)
        link_dict = {}
        link_dict["file"] = file_name
        link_dict["type"] = type.lower()
        link_dict["line_no"] = "NaN"
        link_dict["link"] = None
        link_dict["link_title"] = None
        if isinstance(link, str):  # angle_brackets and text_link_itself
            link_dict["link"] = link
        elif isinstance(link, str):  # the result has two parts
            link_dict["link_title"] = link[0]  # title
            link_dict["link"] = link[1]  # link itself
        link_dict["link"] = self.cleanse_link(type, link)
        # ^ strip all unnecessary characters from the link

        return link_dict

    def cleanse_link(self, type, link):
        """ This function clear the string as the regular expression is
        not able to return the string in the preferred form. """
        if isinstance(link, str) or len(link) < 1:
            return ""

        output = link
        if output[0] == '<' and output[-1] == ">":
            output = output[1:-1]
        if "[" in link and "]" in link:  # strip trash before [ and after ]
            output = output[output.find('[') + 1: output.find(']')]
        return output

    def target_exists(self, target_file_name):
        pass

    def is_system_online(self):
        """ Returns True, if the system is online, False otherwise."""
        pass


class LinkStructureChecker():
    """"""
    pass


class LinkDefinitionShouldBeLinkedToReferenceLink():
    """ When FOOTNOTE_LINK_TEXT or TEXT_LINK_ITSELF is used, it should be
    connected to the reference link with []: syntax. Otherwise it should not
    be paired together.
    Note: Links are not case sensitive """


class NoSpaceBetweenRoundAndSquareBrackets():
    """ When the inline link or footnote link is used, it is not allowed by
    pandoc to have a space/spaces between square and round brackets."""
    pass


class TitleInLinkCannotContailFormatting():
    """ When using INLINE_LINK_WITH_TITLE, it is not allowed to have
    formatting information within link title. """
    pass


class DetectCorrectEmail():
    """ When 'mailto:' is used, the structure of the email address should
    be detected. """
    pass

    def detect_email_address(self, link):
        """ Detecting, if the link is email address. It only checks, if the
        'mailto' is the starting substring of the link. """
        return link.find("mailto:") == 0
