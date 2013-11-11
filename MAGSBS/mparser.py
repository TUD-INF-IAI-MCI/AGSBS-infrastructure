# -*- coding: utf-8 -*-
import re

class markdownParser():
    """Implement an own simple markdown parser. Just reads in the headings of
the given markdown string. If needs arises for more soffisticated stuff, use
python-markdown."""
    def __init__(self, string):
        self.__md = string
        self.__headings = [] # list of headings, format: (level, id, string)
        self.__pagenumbers = {} # id : number
        # some flags/variables for parsing
        self.paragraph_begun=True # first line is always a new paragraph
        self.__lastchunk = ''

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
            if(line.startswith('===')):
                self.__headings.append((1, self.__gen_id(self.__lastchunk),
                    self.__lastchunk))
            elif(line.startswith('---')):
                self.__headings.append((2, self.__gen_id(self.__lastchunk),
                    self.__lastchunk))
            elif(line.startswith('#')):
                level = 0
                while(line.startswith('#')):
                    level += 1
                    line = line[1:]
                try: # match page number, else usual heading
                    heading_text = re.search('.*(\d+).*',line).groups()[0]
                except AttributeError:
                    heading_text = line[1:] # strip whitespace
                self.__headings.append((6, self.__gen_id( line[6:] ),
                        heading_text))
            self.__lastchunk = line # save current line

    def get_data(self):
        """get_data() -> List of touples, each having three items:
1. heading level   : integer
2. heading id      : string
3. actual heading  : string"""
        return self.__headings

    def __gen_id(self, id):
        """gen_id(id) -> an ID for making links.

Todo: We ought to render the page (in memory) and find out the id's there, we do
here wild guessing. It MUST be reimplemented."""
        id = id.lower()
        res_id = ''
        for char in id:
            if(char == ' '):
                res_id += '-'
            elif(ord(char) >= 128): # might be still a valid char for id
                if(not (id in ['ä','ö','ü','ß'])):
                    continue # skip this character
            else:
                res_id += char 
        # strip trailing hyphens:
        while(res_id.startswith('-')):
            res_id = res_id[1:]
        return res_id



