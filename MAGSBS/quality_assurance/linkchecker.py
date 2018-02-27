# This is free software, licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2018 Sebastian Humenda <shumenda |at|gmx |dot| de>
#               Jaromir Plhak <xplhak |at| gmail |dot| com>

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

INLINE_LINK = r"(!?)\[([^\]]+)\](\s*)\(([^)\"']+)\)"
INLINE_LINK_WITH_TITLE = r"(!?)\[([^\]]+)\](\s*)\((\S+)\s*['\"](.+)['\"]\)"
FOOTNOTE_LINK_TEXT = r"(!?)\[([^\]]+)\](\s*)\[([^\]]+)\]"
REFERENCE = r"(!?)\[([^\]]+)\]:(\s*)(\S+)"
# ^ accepts also ones with title that is ignored (not necessary for testing)
STANDALONE_LINK = r"[^\]\(\s]\s*\[[^\]]+\][\[\]]?\s*[^\[\(\s\:]"
ANGLE_BRACKETS_LINK = r"[^(:\])\s]\s*<([^>]+)>"  # should be revised

"""
Issue #20

A common source of error are broken links. Normal link checkers won't work,
since they are working on HTML files. It is hence necessary to parse all
MarkDown links and implement the destination checks manually (to the
resulting HTML files). As a plus, references within the document could be
checked as well.

For checking IDs, it is a good idea to generate IDs of the target document.
Headings get automatic IDs, which can be generated using datastructures.gen_id.
Furthermore, the user may create own anchors with <span id="foo"/> or the
div equivalent.

Checking links in the markdown document
- a) parse the links
- b) test if they are correctly structured
- c) check internal links (no need to be online, files should be on the disk)
    - ca) check the structure of the link
    - ca) check if files are generated
    - cb) if they are - check all links given by markdown
"""


class LinkParser:
    # ToDo: document: files must be relative to document being checked
    # ToDo: how to thread ..? just check with os.path.exists()? needs base
    # directory
    # def __init__(self, links, images, files):
    def __init__(self):
        self.__errors = []  # generated errors
        self.links_list = []  # links generated in the examined files
        self.__regexps = {"inline": INLINE_LINK,
                          "inline_with_title": INLINE_LINK_WITH_TITLE,
                          "footnote": FOOTNOTE_LINK_TEXT,
                          "reference": REFERENCE,
                          "standalone_link": STANDALONE_LINK,
                          "angle_brackets": ANGLE_BRACKETS_LINK
                          }

    def get_list_of_md_files(self, file_tree):
        """ This method creates list of paths to .md files which links should
        be tested. It also returns the name of the file. """
        md_file_list = []
        for directory_name, _, file_list in file_tree:
            for file in file_list:
                if file.endswith(".md"):  # only .md files will be inspected
                    file_path = os.path.join(directory_name, file)
                    # check if file exists
                    if os.path.isfile(file_path):
                        # whole path for generation, filename for feedback
                        md_file_list.append((file_path, file))
        return md_file_list

    def parse_all_links_in_md_files(self, file_tree):
        """ Parses all links in the .md files and stores them in the dictionary
        that has the following structure:
        "file": name of the file, where the link is stored
        "link_type": type of the link - this should be as follows:
            "inline": basic inline link in square brackets, syntax
            "inline_with_title": inline link that contains title
            "footnote": link to the footnote that is referenced somewhere else
                in the document
            "standalone_link": link in square brackets referenced somewhere
                else in the document
            "reference": reference to the footnote and standalone_links types.
                References with titles are not detected as they are not
                relevant to the link testing
            "angle_brackets": link given by square brackets
        "line_no": number of line where regular expression
        "is_picture": 'True' if the link is a picture, 'False' otherwise
        "link": explored link
        "link_text": contains link text, if exists
        "link_title": title of the link, if exists """
        for file_path, file_name in self.get_list_of_md_files(file_tree):
            # encoding should be already checked
            with open(file_path, encoding="utf-8") as file_data:
                # call the function for finding links
                self.find_links_in_markdown(file_data.read(), file_name)
        print(self.links_list)  # TODO: remove this testing string

    def find_links_in_markdown(self, text, file_name):
        """ Updates the list of dictionaries that contains the links retrieved
        from the markdown string. """

        for description, reg_expr in self.__regexps.items():
            # detects the line numbers
            line_nums = self.get_starting_line_numbers(reg_expr, text)
            # detect links using regexps (no need to have line breaks)
            links = re.compile(reg_expr).findall(text.replace('\n', ' '))
            if len(line_nums) != len(links):
                raise ValueError("Line numbers count should be the same"
                                 " as the number of regular expression "
                                 "matches in file {}.".format(file_name))

            for i, link in enumerate(links):
                self.links_list.append(self.create_dct(file_name, line_nums[i],
                                                       description, link))

    def create_dct(self, file_name, line_no, link_type, link):
        """ This method generates the dictionary that contains all the
        important data for the link. """
        link_dict = dict()
        link_dict["file"] = file_name
        link_dict["link_type"] = link_type
        link_dict["line_no"] = line_no + 1
        if isinstance(link, str):  # angle_brackets and text_link_itself
            link_dict["link"] = link
        if isinstance(link, tuple) and len(link) > 3:
            link_dict["is_image"] = True if link[0] == "!" else False
            link_dict["link_text"] = link[1]
            # number of spaces between brackets
            link_dict["spaces"] = len(link[2])
            link_dict["link"] = link[3]  # link itself
        if isinstance(link, tuple) and len(link) > 4:
            link_dict["link_title"] = link[4]

        # strip all unnecessary characters from the link
        link_dict["link"] = self.cleanse_link(link_dict["link"])

        return link_dict

    @staticmethod
    def cleanse_link(link):
        """ This static method clear the string as the regular expression is
        not able to return the string in the preferred form. """
        if not isinstance(link, str) or len(link) < 1:
            return ""

        output = link
        if output[0] == '<' and output[-1] == '>':
            output = output[1:-1]
        if '[' in link and ']' in link:  # strip trash before [ and after ]
            output = output[output.find('[') + 1: output.find(']')]
        return output

    @staticmethod
    def get_starting_line_numbers(reg_expr, text):
        """ This method searches for the line number of the regular expression
        matches.
        Note: This is not the most efficient way to do this. In case, the
        examined data will have non-trivial length and number of links,
        this function should be reimplemented. """
        line_numbers = []
        matches = re.compile(reg_expr, re.MULTILINE | re.DOTALL)
        for match in matches.finditer(text):
            line_numbers.append(text[0:match.start()].count('\n'))
        return line_numbers

    def target_exists(self, target_file_name):
        pass


class LinkStructureChecker():
    """ Structure of the link should follow the basic rules of creating
    links. """
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


class TitleInLinkIsCorrect():
    # check if it is correctly build using " or ' (the last
    # char should be the there at least twice - and first one
    # is the end of the link
    pass


class TitleInLinkCannotContainFormatting():
    """ When using INLINE_LINK_WITH_TITLE, it is not allowed to have
    formatting information within link title. """
    pass


class DetectCorrectEmail():
    """ When 'mailto:' is used, the structure of the email address should
    be detected. """

    def detect_email_address(self, link):
        """ Detecting, if the link is email address. It only checks, if the
        'mailto' is the starting substring of the link. """
        return link.find("mailto:") == 0


class TitleIsTooLong():
    """ Title should be 'reasonably' long. Long text lowers the readability
    and they also can be caused by a incorrect syntax of link. """
    pass


class IncorrectImageFormattingUsingAngleBrackets():
    """It is not allowed to enter image using angle brackets."""
    pass

# TODO: Detect images
# TODO: link within picture description
# value = d.get(key)
