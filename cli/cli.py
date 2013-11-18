# -*- coding: utf-8 -*-
import os,sys
from optparse import OptionParser

# Todo: dirty trick, remove me!
parent = os.path.realpath( sys.argv[0]).split( os.sep )
sys.path.append( os.sep.join( parent[:-2] ) )

from MAGSBS import *


usage = """
magsbs <command> <options>

<command> determines which action to take. The syntax might vary between
commands. Use magsbs <command> -h for help.

Available commands are:

toc     - generate table of contents
navbar  - generate navigation bar at beginning of each page
"""

class main():
    def __init__(self):
        if(len(sys.argv) < 2):
            print(usage)
        else:
            if(sys.argv[1] == 'toc'):
                self.toc()
            elif(sys.argv[1] == 'navbar'):
                self.navbar()
            else:
                print(usage)
        """
        parser = OptionParser()#usage=usage)
        parser.add_option("-t", "--toc", dest="toc",
                  help="generate table of contents",
                  default='UTF-8')
        parser.add_option("-l", "--ligature",
                  action="store_true", dest="ligature", default=False,
                  help='replace ligatures through normal letters (at least in'+\
                          ' Latin languages where they are only for better '+\
                          'readibility)')
        parser.add_option("-o", "--output", dest="output",
                  help="set output file (if unset, overwrite input file)",
                  metavar="FILE")
        parser.add_option("-p", "--pdftotext",
                  action="store_true", dest="pdftotext", default=False,
                  help='Replace some signs generated just by PDFtotext')
        parser.add_option("-s", "--strip-newpage",
                  action="store_true", dest="strip_newline", default=False,
                  help='Strip the newpage character')
        parser.add_option("-u", "--userdict", dest="userdict",
                  help="set path to user-defined replacements/additions for "+\
                          "unicode mappings (format described in README)",
                  metavar="FILE", default=None)

        (self.options, self.args) = parser.parse_args()
"""

    def toc(self):
        c = create_index(sys.argv[2])
        c.walk()
        idx = index2markdown_TOC(c.get_index(), 'de')
        print(idx.get_markdown_page())


m = main()
