# -*- coding: utf-8 -*-
import os, sys, codecs
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

def error_exit(string):
    sys.stderr.write( string + ('\n' if not string.endswith('\n') else '') )
    sys.exit(127)

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
        parser.add_option("-l", "--lang", action="store_true", dest="lang",
                default=False, help='select output language')
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
        usage = sys.argv[0]+' toc [OPTIONS] -o output_file input_file'
        parser = OptionParser(usage=usage)
        parser.add_option("-d", "--depth", dest="depth",
                  help="to which depth headings should be included in the output",
                  metavar="NUM", default='4')
        parser.add_option("-o", "--output", dest="output",
                  help="write output to file instead of stdout",
                  metavar="FILENAME", default='stdout')
        parser.add_option("-l", "--lang", dest="lang",
                  help="select language (currently just 'de' and 'en' supported)",
                  metavar="LANG", default='de')
        (options, args) = parser.parse_args(sys.argv[2:])

        file = None
        if(options.output == 'stdout'):
            file = sys.stdout
        else:
            file = codecs.open(options.output, 'w', 'utf-8')
        try:
            depth = int( options.depth )
        except ValueError:
            error_exit("Depth must be an integer.")
        dir = '.'
        if(not args == []):
            dir = args[0]
            if(not os.path.exists( dir )):
                error_exit("Directory %s does not exist" % dir)

        c = create_index( dir )
        c.walk()
        idx = index2markdown_TOC(c.get_index(), options.lang, depth)
        file.write( idx.get_markdown_page() )
        file.close()


m = main()
