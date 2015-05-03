# Markdown AGSBS (TU) Command line
# This is free software, licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2014 Sebastian Humenda <shumenda@gmx.de>


import os, sys
import argparse

import MAGSBS, MAGSBS.quality_assurance
from MAGSBS.errors import  MissingMandatoryField, TOCError


main_usage = """
%s <command> <options>

<command> determines which action to take. The syntax might vary between
commands. Use %s <command> -h for help.

Available commands are:

conf    - set, init or update a configuration
conv    - convert a markdown file using pandoc
imgdsc  - generate image description snippets
navbar  - generate navigation bar at beginning of each page
new     - create new project structure
mk      - invoke "mistkerl", a quality assurance helper
toc     - generate table of contents
version - output program version
""" % (sys.argv[0], sys.argv[0])

def error_exit(string):
    sys.stderr.write( string + ('\n' if not string.endswith('\n') else '') )
    sys.exit(127)

def getTerminalSize():
    """Get terminal size on GNU/Linux, default to 80 x 25 if not detectable."""
    #pylint: disable=bare-except
    env = os.environ
    def ioctl_GWINSZ(fd):
        try:
            import fcntl, termios, struct
            cr = struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ, '1234'))
        except:
            return
        return cr
    cr = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)
    if not cr:
        try:
            fd = os.open(os.ctermid(), os.O_RDONLY)
            cr = ioctl_GWINSZ(fd)
            os.close(fd)
        except:
            pass
        if not cr:
            cr = (env.get('LINES', 25), env.get('COLUMNS', 80))
    return int(cr[1]), int(cr[0])

class HelpfulParser(argparse.ArgumentParser):
    """Unlike the super class, this arg parse instance will print the error it
    encountered as well as the complete usage of the program."""
    def __init__(self, usage=None):
        if usage:
            super().__init__(usage=usage)
        else:
            super().__init__()

    def error(self, message):
        sys.stderr.write('error: %s\n' % message)
        self.print_help()
        sys.exit(2)

class main():
    def __init__(self, args):
        self.conf = MAGSBS.config.confFactory().get_conf_instance()
        self.args = args

    def run(self):
        if len(self.args) < 2:
            print(main_usage)
        else:
            # try to get a handler for it
            try:
                invokation_command = self.args[0] + ' ' + self.args[1]
                func = getattr(self, 'handle_%s' % self.args[1])
            except AttributeError:
                error_exit("Invalid command: " + self.args[1] + "\n" + main_usage)
            func(invokation_command, self.args[2:])
            sys.exit(0)

    def handle_toc(self, cmd, args):
        "Table Of Contents"
        usage = cmd + ' [OPTIONS] -o output_file input_directory'
        parser = HelpfulParser(usage=usage)
        parser.add_argument("-o", "--output", dest="output",
                  help="write output to file instead of stdout",
                  metavar="FILENAME", default='stdout')
        options = parser.parse_args(args)

        file = None
        if options.output == 'stdout':
            file = sys.stdout
        else:
            file = open(options.output, 'w', encoding='utf-8')
        directory = '.'
        if args:
            directory = args[0]
            if not os.path.exists(directory):
                error_exit("Directory %s does not exist" % directory)

        try:
            c = MAGSBS.filesystem.create_index(directory)
            c.walk()
            if not c.is_empty():
                idx = MAGSBS.factories.index2markdown_TOC(c.get_index())
                file.write( idx.get_markdown_page() )
                file.close()
        except OSError:
            error_exit("OSError: " + e.message+'\n')
        except TOCError as e:
            error_exit("TOCError: " + str(e.args[0]) + '\n')

    def handle_conf(self, cmd, args):
        """Create or update configuration."""
        usage = cmd + """ <subcmd> [options] <action>

Allowed subcommands are `show`, `update` and `init`. `show` shows the current
configuration settings, default values if none present.
`update` and `show` try to find the correct configuration: if none exists
in the current directory and you are in a subdirectory of a project, they try to
determine the project root and read the configuration for there if present
(else
the default values are used).
`init` on the other hand behaves basically like update (it sets configuration
values), but it does that for the current directory. This is handy for
sub-directory configurations or initialization of a new project."""
        parser = HelpfulParser(usage=usage)
        parser.add_argument("-a", dest="appendixPrefix",
                  help='use "A" as prefix to appendix chapter numbering and turn the extra heading "appendix" (or translated equivalent) off',
                  action="store_true", default=False)
        parser.add_argument("-f", dest="format",
                  help="select output format",
                  metavar="FMT", default=None)
        parser.add_argument("-e", dest="editor",
                  help="set editor",
                  metavar="NAME", default=None)
        parser.add_argument("-i", dest="institution",
                  help="set institution (default TU Dresden)",
                  metavar="NAME", default=None)
        parser.add_argument("-l", dest="lecturetitle",
                  help="set lecture title (else try to use h1 heading, if present)",
                  metavar="TITLE", default=None)
        parser.add_argument("-L", dest='language',
                  help="set language (default de)", metavar="LANG",
                  default='de')
        parser.add_argument("-p", "--pnum-gap", dest="pageNumberingGap",
                  help="gap in numbering between page links.",
                  metavar="NUM", default=None)
        parser.add_argument("-s", dest="source",
                  help="set source document",
                  metavar="SRC", default=None)
        parser.add_argument("-S", dest="semesterofedit",
                  help="set semester of edit (will be guessed else)",
                  metavar="SEMYEAR", default=None)
        parser.add_argument("--toc-depth", dest="tocDepth",
                  help="to which depth headings should be included in the table of contents",
                  metavar="NUM", default=None)
        parser.add_argument("-w", dest="workinggroup",
                  help="set working group",
                  metavar="GROUP", default=None)

        options = parser.parse_args(args[1:])
        if len(args) == 0:
            sys.stderr.write("Error: no subcommand specified.\n")
            parser.print_help()
            sys.exit(88)

        if args[0] == 'init':
            # read configuration from cwd, if present
            inst = MAGSBS.config.LectureMetaData(MAGSBS.config.CONF_FILE_NAME)
            inst.read()
        else:
            inst = MAGSBS.config.confFactory()
            inst = inst.get_conf_instance()

        print_conf = lambda prefix: print('{}\n{}'.format(prefix, '\n'.join(
                ['{:<20}{}'.format(k,v)  for k, v in inst.items()])))

        if args[0] == 'show':
            print_conf("Current settings are:\n\n")
        elif args[0] == 'update' or args[0] == 'init':
            for opt, value in options.__dict__.items():
                if value is not None:
                    inst[opt] = value
            print_conf("New settings are:\n\n")
            inst.write()
        else:
            parser.print_help()



    def handle_conv(self, cmd, args):
        usage = 'Usage: ' + cmd + ' <input_directory | input_file>\n\nConvert" +
        " given input files and/or directories from MarkDown to HTML'
        if len(args) < 1 or sys.argv[0].startswith("-"):
            print(usage)
            sys.exit(1)
        elif not os.path.exists(args[0]):
            print('Error: '+sys.argv[2]+' not found')
            sys.exit(127)

        try:
            p = MAGSBS.pandoc.pandoc()
            files = []
            path = args[0]
            if os.path.isdir(path):
                files += [os.path.join(path, e) for e in os.listdir(path)]
            else:
                files.append(path)
            p.convert_files(files)
        except MAGSBS.errors.SubprocessError as e:
            error_exit('Error: ' + str(e))

    def handle_navbar(self, cmd, args):
        usage = cmd + """ [OPTIONS] <input_directory>\n
Work recursively through <input_directory> and add to each file where it makes
sense the navigation bar at the top and bottom.
"""
        parser = HelpfulParser(usage=usage)
        parser.add_argument("-p", "--pnum-gap", dest="pnum_gap",
                  help="gap in numbering between page links. (temporary setting)",
                  metavar="NUM", default=None)
        options = parser.parse_args(args)
        if len(args) < 1:
            directory = '.'
        else:
            directory = args[0]
        if options.pnum_gap:
            try:
                self.conf['pageNumberingGap'] = int(options.pnum_gap)
            except ValueError:
                error_exit("Argument of -p must be an integer.")

        p = MAGSBS.filesystem.page_navigation(directory)
        p.iterate()

    def imgdsc(self, cmd, args):
        usage = cmd + ' [OPTIONS] image_name\n' + \
                "The working directory must be a chapter; the image name must be a relative path like 'images/image.jpg'\n"
        parser = HelpfulParser(usage=usage)
        parser.add_argument("-d", "--description", dest="description",
                help="image description string (or - for stdin)",
                metavar="DESC", default='no description')
        parser.add_argument("-o", "--outsource-descriptions", dest="outsource",
                action="store_true", default=False,
                help="if set, images will be outsourced, no matter how long they are.")
        parser.add_argument("-t", "--title", dest="title",
                default=None,
                help="set title for outsourced images (mandatory if outsourced)")
        options = parser.parse_args(args)
        if len(args) != 1:
            parser.print_help()
            exit(0)
        path = args[0]
        if options.description == "-":
            desc = sys.stdin.read()
        else:
            desc = options.description
        img = MAGSBS.factories.ImageDescription(path)
        img.set_description(desc)
        img.set_outsource_descriptions(options.outsource)
        if options.title:
            img.set_title(options.title)
        try:
            print('\n----\n'.join(img.get_output()))
        except MissingMandatoryField as e:
            error_exit('Error: ' + e.args[0] + '\n')

    def handle_new(self, cmd, args):
        usage = cmd + ''' <directory>
Initialize a new lecture.
'''
        parser = HelpfulParser(usage=usage)
        parser.add_argument("-a", dest="appendix_count", default="0",
                metavar="COUNT",
                help="number of appendix chapters (default 0)")
        parser.add_argument("-c", dest="chapter_count", default="2",
                metavar="COUNT",
                help="number of chapters (default 2)")
        parser.add_argument("-p", dest="preface", default=False,
                action="store_true",
                help="sets whether a preface exists (default None)")
        parser.add_argument("-n", dest="nochapter", default=False,
                action="store_true",
                help='if set, blattxx will be used instead of kxx')
        parser.add_argument("-l", dest="lang", default="de",
                help="sets language (default de)")
        options = parser.parse_args(args)
        if len(args) != 1:
            parser.print_help()
            sys.exit(1)
        try:
            a = int(options.appendix_count)
            c = int(options.chapter_count)
        except ValueError:
            error_exit("The number of chapters and appendix chapters must be integers.")
        builder = MAGSBS.filesystem.init_lecture(args[0], c, options.lang)
        builder.set_amount_appendix_chapters(a)
        if options.preface:
            builder.set_has_preface(True)
        if options.nochapter:
            builder.set_no_chapters(True)
        builder.generate_structure()

    def handle_mk(self, cmd, args):
        usage = cmd + ''' [FILE|DIRECTORY]
        Run "mistkerl", a quality assurance helper. It checks for common errors and
        outputs it on the command line.'''
        parser = HelpfulParser(usage=usage)
        parser.add_argument("-c", dest="critical_first", action="store_true",
                help="Sort critical errors first")
        parser.add_argument("-s", dest="squeeze_output", action="store_true",
                help="use less blank lines")
        options = parser.parse_args(args)

        if (len(args) != 1):
            print(usage)
            sys.exit( 127 )
        if not os.path.exists( args[0] ):
            print("Error: %s does not exist." % args[0] )
            sys.exit(5)
        mistkerl = MAGSBS.quality_assurance.Mistkerl()
        errors = mistkerl.run(args[0])
        if len(errors) == 0:
            print("Nun denn, ich konnte keine Fehler entdecken. Hoffen wir, dass es auch wirklich\nkeine gibt ;-).")
            sys.exit( 0 )
        formatter = MAGSBS.quality_assurance.error_formatter()
        formatter.set_itemize_sign("  ")
        formatter.set_width(getTerminalSize()[0])
        if options.squeeze_output:
            formatter.set_with_blank_lines(False)
        if options.critical_first:
            formatter.sort_critical_first(True)
        print(formatter.format_errors(errors))

    def handle_master(self, cmd, args):
        #pylint: disable=unused-argument
        if not os.path.exists(args[0]):
            print("No such file or directory.")
            sys.exit(1)
        elif not os.path.isdir(args[0]):
            print("%s: is not a directory" % args[0])
            sys.exit(1)
        else:
            m = MAGSBS.master.Master(args[0])
            m.run()

    def version(self):
        print('Version: ' + str(MAGSBS.config.VERSION))

main_inst = main(sys.argv)
main_inst.run()
