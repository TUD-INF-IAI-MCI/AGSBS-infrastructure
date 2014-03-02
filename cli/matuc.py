# -*- coding: utf-8 -*-
# Markdown AGSBS (TU) Command line

import os, sys, codecs
from optparse import OptionParser

from MAGSBS import *
import MAGSBS


usage = """
%s <command> <options>

<command> determines which action to take. The syntax might vary between
commands. Use %s <command> -h for help.

Available commands are:

conv    - convert a markdown file using pandoc
imgdsc  - generate image description snippets
navbar  - generate navigation bar at beginning of each page
toc     - generate table of contents
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
            elif(sys.argv[1] == 'conv'):
                self.conv()
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

        try:
            c = create_index( dir )
            c.walk()
            idx = index2markdown_TOC(c.get_index(), options.lang, depth,
                options.appendixprefix)
            file.write( idx.get_markdown_page() )
            file.close()
        except OSError:
            sys.stderr.write("OSError: " + e.message+'\n')
            sys.exit(127)
        except TOCError:
            sys.stderr.write("TOCError: " + e.message+'\n')
            sys.exit(127)
    def conv(self):
        usage = sys.argv[0]+' conv [input_directory|input_file]'
        usage += "\n\nNote: the output file name will be the input file name + the new extension.\n\n"
        parser = OptionParser(usage=usage)
        parser.add_option("-f", dest="format",
                  help="select output format",
                  metavar="FMT", default='html')
        parser.add_option("-w", dest="workinggroup",
                  help="set working group",
                  metavar="GROUP", default=None)
        parser.add_option("-s", dest="source",
                  help="set source document",
                  metavar="SRC", default=None)
        parser.add_option("-e", dest="editor",
                  help="set editor",
                  metavar="NAME", default=None)
        parser.add_option("-i", dest="institution",
                  help="set institution (default TU Dresden)",
                  metavar="NAME", default=None)
        parser.add_option("-S", dest="semesterofedit",
                  help="set semester of edit (will be guessed else)",
                  metavar="SEMYEAR", default=None)
        parser.add_option("-l", dest="lecturetitle",
                  help="set lecture title (else try to use h1 heading, in any present",
                  metavar="TITLE", default=None)

        (options, args) = parser.parse_args(sys.argv[2:])
        if(len(args)<1):
            parser.print_help()
            sys.exit(1)
        elif(not os.path.exists( args[0] )):
            print('Error: '+args[0]+' not found')
            sys.exit(127)

        p = MAGSBS.pandoc(options.format)
        if(options.workinggroup):
            p.set_workinggroup(self, options.workinggroup)
        if(options.source):
            p.set_source(self, source)
        if(options.editor):
            p.set_editor(options.editor)
        if(options.institution):
            p.set_institution(options.institution)
        if(options.lecturetitle):
            p.set_lecturetitle(options.lecturetitle)
        if(options.semesterofedit):
            p.set_semesterofedit(options.date)
        if(os.path.isdir(args[0])):
            MAGSBS.pandoc.convert_dir(p, args[0] ) # Todo: write this function
        else:
            p = p.convert( args[0] )


    def navbar(self):
        usage = sys.argv[0]+' navbar [OPTIONS] input_directory]\n'
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
            dir = '.'
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
