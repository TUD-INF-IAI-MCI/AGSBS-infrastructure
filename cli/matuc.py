# -*- coding: utf-8 -*-
# Markdown AGSBS (TU) Command line

import os, sys, codecs
from optparse import OptionParser

# Todo: dirty trick, remove me!
parent = os.path.realpath( sys.argv[0]).split( os.sep )
sys.path.append( os.sep.join( parent[:-2] ) )

from MAGSBS import *


usage = """
%s <command> <options>

<command> determines which action to take. The syntax might vary between
commands. Use %s <command> -h for help.

Available commands are:

toc     - generate table of contents
navbar  - generate navigation bar at beginning of each page
""" % (sys.argv[0], sys.argv[0])

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
            elif(sys.argv[1] == 'imgdsc'):
                self.imgdsc()
            else:
                print(usage)
    
    def toc(self):
        usage = sys.argv[0]+' toc [OPTIONS] -o output_file input_directory'
        parser = OptionParser(usage=usage)
        parser.add_option("-a", dest="appendixprefix",
                  help='use "A" as prefix to appendix chapter numbering and turn the extra heading "appendix" (or translated equivalent) off',
                  action="store_true", default=False)
        parser.add_option("-d", "--depth", dest="depth",
                  help="to which depth headings should be included in the output",
                  metavar="NUM", default='4')
        parser.add_option("-l", "--lang", dest="lang",
                  help="select language (currently just 'de' and 'en' supported)",
                  metavar="LANG", default='de')
        parser.add_option("-o", "--output", dest="output",
                  help="write output to file instead of stdout",
                  metavar="FILENAME", default='stdout')
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
        idx = index2markdown_TOC(c.get_index(), options.lang, depth,
                options.appendixprefix)
        file.write( idx.get_markdown_page() )
        file.close()
    def navbar(self):
        usage = sys.argv[0]+' navbar [OPTIONS] input_directory\n'+\
                "\nIf input_directory is omitted, the current directory will "+\
                "be taken. Please note\n also that all pages will get a page "+\
                "navigation.\n\n"
        parser = OptionParser(usage=usage)
        #parser.add_option("-o", "--output", dest="output",
        #          help="write output to file instead of stdout",
        #          metavar="FILENAME", default='stdout')
        parser.add_option("-l", "--lang", dest="lang",
                  help="select language (currently just 'de' and 'en' supported)",
                  metavar="LANG", default='de')
        parser.add_option("-p", "--pnum-gap", dest="pnum_gap",
                  help="gap in numbering between page links.",
                  metavar="NUM", default='5')
        (options, args) = parser.parse_args(sys.argv[2:])
        if(len(args)<1):
            parser.print_help()
            exit(0)
        else:
            dir = args[0]
        try:
            pnumgap = int( options.pnum_gap )
        except ValueError:
            error_exit("Argument of -p must be an integer.")

        #output = None
        #if(options.output == 'stdout'):
        #    output = sys.stdout
        #else:
        #    output = codecs.open(options.output, 'w', 'utf-8')

        p=page_navigation(dir, pnumgap, options.lang)
        p.iterate()

    def imgdsc(self):
        usage = sys.argv[0]+' imgdsc [OPTIONS] image_name image_title\n'+\
                "\nBy default, the image description is read from stdin, use -f to read from a file.\n\n"
        parser = OptionParser(usage=usage)
        parser.add_option("-i", "--iage-description-file", dest="imgdescfile",
                  help="file name (without path) where outsourced image "+\
                          "descriptions will be written to; has no effect, wenn -a is used.",
                  metavar="FILENAME", default='bilder.md')
        parser.add_option("-l", "--lang", dest="lang",
                  help="select language (currently just 'de' and 'en' supported)",
                  metavar="LANG", default='de')
        (options, args) = parser.parse_args(sys.argv[2:])
        if(len(args)<1):
            parser.print_help()
            exit(0)
        else:
            dir = args[0]
        try:
            pnumgap = int( options.pnum_gap )
        except ValueError:
            error_exit("Argument of -p must be an integer.")

        #output = None
        #if(options.output == 'stdout'):
        #    output = sys.stdout
        #else:
        #    output = codecs.open(options.output, 'w', 'utf-8')

        p=page_navigation(dir, pnumgap, options.lang)
        p.iterate()



m = main()
