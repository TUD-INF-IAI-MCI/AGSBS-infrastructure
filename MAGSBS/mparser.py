# -*- coding: utf-8 -*-
import re
import datastructures

class markdownHeadingParser():
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

    def parse(self):
        """parse() -> parse the markdown data into a list of level 1, 2 and 6
        headings."""
        for line in self.__md.split('\n'):
            if(line.strip() == ''): # empty lines are start of next paragraph
                self.paragraph_begun = True
                continue # no further processing here
            else:
                self.paragraph_begun = False
            # what kind of element - we distinguish heading level 1-5 and level
            # 6 (for page numbers)
            level = -1
            text = ''
            is_shadowheading = False # is a shadow heading, when it's a page number
            if(line.startswith('===')):
                level = 1
                text = self.__lastchunk
            elif(line.startswith('---')):
                level = 2
                text = self.__lastchunk
            elif(line.startswith('#')):
                level = 0
                while(line.startswith('#')):
                    level += 1
                    line = line[1:]
                try: # match page number, else usual heading
                    re.search('.*- (slide|folie|seite|page) \d+ -.*',
                            line.lower()).groups()[0]
                    text = line
                    is_shadowheading = True
                except AttributeError:
                    text = line[1:] # strip whitespace
            # if a heading was encountered:
            if(level >= 0 and text != ''):
                h = datastructures.heading(self.__path, self.__file_name)
                h.set_level( level )
                h.set_text( text )
                h.set_shadow_heading( is_shadowheading )
                h.set_relative_heading_number(
                        self.determine_relative_heading_number( level ) )
                self.__headings.append( h )

            level = -1; text = ''
            self.__lastchunk = line # save current line

    def determine_relative_heading_number(self, level):
        """Which number has the fifth level-2 heading in k0103.md? This
function findsit out."""
        # set all variables below this level to 0 (its the start of a new section)
        for i in range(level-1, 6):
            self.__relative_heading_number[i] = 0
        # increase current level by one
        self.__relative_heading_number[level-1] += 1
        return self.__relative_heading_number[:level]

    def get_heading_list(self):
        """get_heading_list() -> list of datastructure.heading objects."""
        return self.__headings


