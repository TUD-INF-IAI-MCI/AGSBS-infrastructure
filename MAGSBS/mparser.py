# This is free software, licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2015 Sebastian Humenda <shumenda |at| gmx |dot| de>
"""
This file contains a parser parsing certain syntactical structures of MarkDown
to be used for further post-processing. It is not a full MarkDown parser, but a
specialized subset parser.
"""

import re
from . import datastructures
from . import contentfilter
from . import errors

class SimpleMarkdownParser():
    """Implement an own simple markdown parser. Just reads in the headings of
the given markdown string. If needs arises for more soffisticated stuff, use
python-markdown."""
    def __init__(self, string, path, file_name):
        self.__md = string
        self.__headings = [] # list of headings, format: (level, id, string)
        self.__pagenumbers = {} # number : id
        # some flags/variables for parsing
        self.__path = path
        self.__file_name = file_name
        self.__level_1_heading_encountered = False
        self.__json = None

    def parse(self):
        """parse() -> parse the markdown data into a list of headings.
In previous versions, this was a handcrafted parser. Since this is error-prone,
Pandoc is now itself used to generate document AST (structured document) and the
xported JSon tree is then used for post-processing."""
        # get JSon-formatted Pandoc AST (the structured document)
        self.__json = contentfilter.run_pandoc( self.__md )

    def fetch_page_numbers(self):
        """Extract page numbers from stored JSon AST."""
        pages = contentfilter.pandoc_ast_parser( self.__json,
                contentfilter.page_number_extractor)
        for text, id in pages:
            try:
                num = int(re.search(r'-\s*\w+\s+(\d+)', text).groups()[0])
            except AttributeError:
                raise errors.PageNumberError(('Could not extract a page number '
                        'from "{}"').format(text))
            self.__pagenumbers[ num ] = id

    def fetch_headings(self):
        """Fetch headings from extracted JSon AST."""
        # extract headings
        raw_headings = contentfilter.pandoc_ast_parser( self.__json,
                contentfilter.heading_extractor)
        for level, text in raw_headings:
            h = datastructures.FileHeading(text, level, self.__file_name)
            self.__headings.append(h)

    def get_headings(self):
        """get_headings() -> list of datastructure.heading objects."""
        return self.__headings

    def get_page_numbers(self):
        return self.__pagenumbers

## The following is for those cases where parsing the Pandoc ast to get headings
## or page numbers would mean a substancial overhead

def create_heading(line_num, level, text):
    """Add heading object to a collection."""
    h = datastructures.Heading(text, level)
    h.set_line_number(line_num)
    return h

def split_into_level_text(text):
    """For markdown headings starting with #, return level and text as tuple."""
    level = 0
    while text.startswith('#'):
        level += 1
        text = text[1:]
    while text.endswith('#'):
        text = text[:-1]
    text = text.lstrip().rstrip()
    return (level, text)

def headingExtractor(paragraphs, max_headings=-1):
    """headingExtractor(list_of_paragraphs, max_headings=-1)
    Return list of heading objects; if max_headings is set to a value > -1, only
    this number of headings will be parsed.
    These headings contain only the text, the level and the line number and are
    primarely intended to be used in Mistkerl.
    """
    headings = []
    headings_encountered = 0
    for start_line, paragraph in paragraphs.items():
        if max_headings > -1 and headings_encountered >= max_headings:
            break
        level = 0
        text = None
        if len(paragraph) == 1:
            if paragraph[0].startswith('#'):
                level, text = split_into_level_text(paragraph[0])
        else:
            if paragraph[1].startswith('==='):
                level = 1
                text = paragraph[0]
            elif paragraph[1].startswith('---'):
                level = 2
                text = paragraph[0]
        if level and text:
            headings.append(create_heading(start_line, level, text))
            headings_encountered += 1
    return headings


def pageNumberExtractor(paragraphs):
    """Iterate over paragraphs and return a list of page numbers extracted from
    those paragraphs."""
    numbers = []
    rgx = re.compile(r"^\|\|\s*-\s*(.+?)\s*-")
    pars = [(l,e) for l,e in paragraphs.items() if len(e) == 1]
    for start_line, par in pars:
        result = rgx.search(par[0])
        if result:
            numbers.append((start_line, result.groups()[0]))
    return numbers


