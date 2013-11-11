# -*- coding: utf-8 -*-

"""Getting started:

# create index:
c = create_index('.')
c.walk()

# index 2 markdown:
md = index2markdown_TOC(c.get_data(), 'de')
my_fancy_page = c.get_markdown_page()
"""

import os, sys, codecs, re
import collections

class create_index():
    """create_index(dir)
    
Walk the file system tree from "dir" and have a look in all files who end on
.md. Take headings of level 1 or 2 and add it to the index.
    
Format of index: dict of lists: every file is a list of headings, each heading
is a tuple of heading level, id and actual name. Thos are then stored in a
OrderedDict with the key being the file name and the value being the list just
described.

E.g. { 'k01.html' : [(1,'art','art'), (6,'seite-1--',' -Seite 1 -')], [...] }
"""
    def __init__(self, dir):
        self.__dir = dir
        if(not os.path.exists(dir)):
            raise(OsError("Directory doesn't exist."))
        self.__index = collections.OrderedDict()

    def walk(self):
        """walk()

By calling the function, the actual index is build."""
        tmp_dict = {}
        for directoryname, directory_list, file_list in os.walk(self.__dir):
            for file in file_list:
                if(not file.endswith('.md') and not file.startswith('k')):
                    continue # skip all files except markdown files
                # open with systems default encoding
                # todo: if we have progressive utf-8-windows-users?
                data = codecs.open( directoryname + os.sep + file, 'r', \
                            sys.getdefaultencoding()).read()
                m = markdownParser( data )
                m.parse()
                tmp_dict[ file ] = m.get_data()
        # dicts do not keep the order of their keys (we need such for the TOC)
        # and os.walk does not read files/directories alphabetically either, so
        # sort it:

        keys = list(tmp_dict.keys())
        keys.sort()
        for key in keys:
            self.__index[key] = tmp_dict[key]


    def get_index(self):

        return self.__index

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


class index2markdown_TOC():
    """index2markdown_TOC( OrderedDict(), lang )

Take the ordered dict produced by create_index() and transform it  to a markdown
file. The language specifies in which language to output the title of the TOC.
"""
    def __init__(self, index, lang='de'):
        self.__index = index
        self.lang = lang
        self.__output = []
        self.transform_index()

    def transform_index(self):
        """Walk through the dict; they key (file name) is used to determine the
heading number. It is assumed, that file names HAVE the form of k01.md for
chapter 1 and NOT k1.html or something similar.

Currently, there are NO files like k0101 recognized. It makes absolutely no
sense to device chapters further then by 1.1 in output files. Everything else is
fragmentation!"""
        output = [ ('Inhaltsverzeichnis' if self.lang=='de'
                    else 'Table Of Contents') ]
        output += ['\n=============\n\n']

        chapter_number = 1
        for chapter, headings in self.__index.items():
            # strip markdown ending
            filename = 'k'+chapter[1:3] + os.sep + chapter[:-2] + 'html'
            chapter = chapter[1:] # strip trailing k
            if(chapter.endswith('.md')):
                chapter = chapter[:-3]
            else:
                raise ValueError('File must end with .md')
            if(len(chapter)>6):
                raise ValueError('Only files of form kxx.md" are accepted.')
            chapter = chapter[1:3]
            
            # insert first-level-heading by hand, MUST be first heading!
            if(not headings[0][0] == 1):
                raise ValueError("First heading needs to be a h1 heading.")
            else:
                output.append( '\n[%s. %s](%s)\n' % (chapter_number,
                        headings[0][2], filename) )

            # get list of headings (and exclude page numbers); raise error if
            # first-level-heading occures twice
            headings = [h for h in headings[1:]   if(h[0] < 6  and  h[0] > 1)]
            for h_num, heading in enumerate(headings):
                output.append( '\n[%s.%s. %s](%s)\n' %
                                (chapter_number, h_num+1, heading[2],
                                filename + '#' + heading[1])
                             )
            chapter_number += 1

        self.output = output

    def get_markdown_page(self):
        return ''.join(self.output)


def test_markdown_parser():
    m = markdownParser("Heya\n====\n\nImportant advisories\n---------\n\n\n###### - Seite 6 -\n")
    m.parse()
    for item in m.get_data():
        print(repr(item))
    print("Done.")

def test_file_walk():
    c = create_index('examples')
    c.walk()
    for key, value in c.get_index().items():
        print(key+repr(value)+'\n\n')
    return c.get_index()

# -- if not imported but run as main module, test functionality --

def test_index2markdown_TOC():
    idx = test_file_walk()
    c = index2markdown_TOC(idx, 'de')
    print(c.get_markdown_page())

if __name__ == '__main__':
    #test_markdown_parser()
    #test_file_walk()
    test_index2markdown_TOC()
