# This is free software, licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2014 Sebastian Humenda <shumenda@gmx.de>
"""
This file contains all helper data structure which are not local to a specific
module. One example is the Heading class, used in mparser and quality_assurance.
Other datastructures might be in here as well to have them defined in a global
place.
"""

import re, os
from . import datastructures
from . import contentfilter as contentfilter

class SimpleMarkdownParser():
    """Implement an own simple markdown parser. Just reads in the headings of
the given markdown string. If needs arises for more soffisticated stuff, use
python-markdown."""
    def __init__(self, string, path, file_name):
        self.__md = string
        self.__headings = [] # list of headings, format: (level, id, string)
        self.__pagenumbers = {} # number : id
        # some flags/variables for parsing
        self.paragraph_begun=True # first line is always a new paragraph
        self.__lastchunk = ''
        self.__path = path
        self.__file_name = file_name
        # for the numbering of the headings relatively in the document; array
        # with each telling how often a specific heading has occured
        self.__relative_heading_number = [0,0,0,0,0,0]
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
            num = int(re.search(r'- \w+\s+(\d+)', text).groups()[0])
            self.__pagenumbers[ num ] = id

    def fetch_headings(self):
        """Fetch headings from extracted JSon AST."""
        # extract headings
        raw_headings = contentfilter.pandoc_ast_parser( self.__json,
                contentfilter.heading_extractor)
        for rHeading in raw_headings:
            h = datastructures.Heading(self.__path, self.__file_name)
            h.set_level( self.guess_heading_level( rHeading[0] ) )
            h.set_text( rHeading[1] )
            h.set_relative_heading_number(
                self.determine_relative_heading_number( rHeading[0] ) )
            dirname = os.path.split( self.__path )[-1]
            if dirname.startswith("anh"):
                h.set_type('appendix')
            elif dirname.startswith("v"): # is it a preface?
                if len(dirname) > 1 and dirname[1].isdigit():
                    h.set_type( "preface" )
            self.__headings.append( h )

    def guess_heading_level( self, internal_level ):
        """Guess the heading level. Let's take the usual chapter, starting with
"k" in the filename. Each depth has exactly two digits, deppth 0 is e.g. a file
name like "k01.md" and depth 1 is "k0105.md"."""
        fn = self.__file_name
        i=0
        # strip letters first
        while(fn != ""):
            if(fn[0].isalpha()): fn=fn[1:]
            else: break
        while(fn != ""):
            if(not fn[0].isdigit()): break
            i+=1
            fn=fn[1:]
        return int(i/2) -1 + internal_level

    def determine_relative_heading_number(self, level):
        """Which number has the fifth level-2 heading in k0103.md? This
function findsit out."""
        # set all variables below this level to 0 (its the start of a new section)
        for i in range(level, 6):
            self.__relative_heading_number[i] = 0
        # increase current level by one
        self.__relative_heading_number[level-1] += 1
        return self.__relative_heading_number[:level]

    def get_headings(self):
        """get_headings() -> list of datastructure.heading objects."""
        return self.__headings

    def get_page_numbers(self):
        return self.__pagenumbers

## The following is for those cases where parsing the Pandoc ast to get headings
## or page numbers would mean a substancial overhead

def create_heading(num, level, text):
    """Add heading object to a collection."""
    h = datastructures.Heading()
    h.set_level(level)
    h.set_line_number(num)
    h.set_text(text)
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
    this number of headings will be parsed."""
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


