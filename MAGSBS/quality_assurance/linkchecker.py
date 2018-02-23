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

INLINE_LINK = re.compile(r'\[([^\]]+)\]\(([^)^"]+)\)')
INLINE_LINK_WITH_TITLE = re.compile(r'\[([^\]]+)\]\(([^)]+("|\')[^)]+)\)')
# FOOTNOTE_LINK_TEXT_RE = re.compile(r'\[([^\]]+)\]\[(\d+)\]')
# FOOTNOTE_LINK_URL_RE = re.compile(r'\[(\d+)\]:\s+(\S+)')

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
    - cb) if online - test the reachability of the 
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
        self.errors = []  # generated errors
        self.file_tree = file_tree  # files to be examined
        self.links_list = []


    def get_list_of_md_files(self):
        """
        This function creates list of paths to .md files which links should be
        tested.
        :return: List of paths to .md files to be tested
        """
        md_file_list = []
        for directory_name, dir_list, file_list in self.file_tree:
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
        print(self.links_list) # TODO: remove this testing string

    def find_md_links(self, md_file_data, file_name):
        """ Updates the list of dictionaries that contains the links retrieved
        from the markdown string
        """

        for line_i, line in enumerate(md_file_data, 1):
            for reg_expr in ["INLINE_LINK", "INLINE_LINK_WITH_TITLE"]:
                # detect links using regular expressions
                links = eval(reg_expr + ".findall(line)")
                # links to be have at least two information - link heading and
                # link itself - otherwise it not be checked
                if links and len(links) > 0 and len(links[0]) > 1:
                    self.links_list.append(self.create_dct(file_name, reg_expr,
                                                           line_i, links))

            # footnote_links = dict(FOOTNOTE_LINK_TEXT_RE.findall(line))
            # footnote_urls = dict(FOOTNOTE_LINK_URL_RE.findall(line))

        # for key, value in footnote_links.items():
        #    footnote_links[key] = footnote_urls[value]
        # links.update(footnote_links)


    def create_dct(self, file_name, type, line_no, links):
        """
        This function generates the dictionary that contains all the important
        data for the link
        """
        link_dictionary = {}
        link_dictionary["file"] = file_name
        link_dictionary["type"] = type.lower()
        link_dictionary["line_no"] = line_no
        link_dictionary["link_title"] = links[0][0]  # get title
        link_dictionary["link"] = links[0][1]  # get link itself
        return link_dictionary

    def target_exists(self, target_file_name):
        pass


class LinkStructureChecker():
    pass

class LinkOnlineChecker():
    pass

class RelativeUrlChecker():
    pass



