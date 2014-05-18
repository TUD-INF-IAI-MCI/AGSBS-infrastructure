# -*- coding: utf-8 -*-
import re
import MAGSBS.datastructures as datastructures
from MAGSBS.errors import StructuralError
import MAGSBS.contentfilter as contentfilter

class simpleMarkdownParser():
    """Implement an own simple markdown parser. Just reads in the headings of
the given markdown string. If needs arises for more soffisticated stuff, use
python-markdown."""
    def __init__(self, string, path, file_name):
        self.__md = string
        self.__headings = [] # list of headings, format: (level, id, string)
        self.__pagenumbers = {} # id : number
        # some flags/variables for parsing
        self.paragraph_begun=True # first line is always a new paragraph
        self.__lastchunk = ''
        self.__path = path
        self.__file_name = file_name
        # for the numbering of the headings relatively in the document; array
        # with each telling how often a specific heading has occured
        self.__relative_heading_number = [0,0,0,0,0,0]
        self.__level_1_heading_encountered = False

    def parse(self):
        """parse() -> parse the markdown data into a list of headings."""
        # new method to extract page numbers:
        pages = contentfilter.pandoc_ast_parser( self.__md,
                contentfilter.page_number_extractor)
        for text, id in pages:
            num = int(re.match('- \w+ (\d+) .*', text).groups()[0])
            self.__pagenumbers[ id ] = num
        # Todo: write filter which gets all headings; below the heading data
        # structure which needs to be used
        #h = datastructures.heading(self.__path, self.__file_name)
        #h.set_level( level )
        #h.set_text( text )
        #h.set_relative_heading_number(
        #        self.determine_relative_heading_number( level ) )
        #self.__headings.append( h )

    def determine_relative_heading_number(self, level):
        """Which number has the fifth level-2 heading in k0103.md? This
function findsit out."""
        # set all variables below this level to 0 (its the start of a new section)
        for i in range(level, 6):
            self.__relative_heading_number[i] = 0
        # increase current level by one
        self.__relative_heading_number[level-1] += 1
        return self.__relative_heading_number[:level]

    def get_heading_list(self):
        """get_heading_list() -> list of datastructure.heading objects."""
        return self.__headings


