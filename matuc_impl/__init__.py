"""
This module defines everything required to write a command-line frontend for
MAGSBS:

-   A base output formatter, that control how the text is displayed
    (currently matuc.py implements a text interface, matuc_js a json.
    interface)
-   A few methods to parse arguments and to control all the functionality
    offered by the MAGSBS module.
"""
from abc import ABCMeta, abstractmethod
import argparse
import collections
import io
import os
import shutil
import sys
import textwrap

import MAGSBS
import MAGSBS.quality_assurance

PROCNAME = os.path.basename(sys.argv[0])

main_usage = """%s <command> <options>

<command> determines which action to take. The syntax might vary between
commands. Use %s <command> -h for help.

Available commands are:

conf            - set, init or update a configuration
conv            - convert a markdown file using pandoc
imgdsc          - generate image description (snippets)
iswithinlecture - test, whether a certain path is part of a lecture
new             - create new project structure
master          - perform toc generation (see below) and call `conv` on every file
mk              - invoke "mistkerl", a quality assurance helper
toc             - generate table of contents
version         - output program version
""" % (PROCNAME, PROCNAME)


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


class OutputFormatter:
    """The OutputFormatter provides abstract methods to format the output produced
    by Matuc to either a TTY or into other formats, i.e. usable by a GUI or
    another program. This way, matuc can emit its results to the formatter and
    this will take care of writing it to stdout or i.e. to a JSON stream.
    Valid inputs for the functions may be strings, lists/tuples and dicts. Each
    will be handled appropriately. If a dict is found with the key verbatim, the
    value of that field will be printed without modification. The rest of this
    dictionary is ignored. Note: anything exporting to an JSON API must convert
    this special case of {'verbatim:' 'something'} into 'something'. to be
    compliant with the JSON API specification."""
    __metaclass__ = ABCMeta
    def register_warning(self, warn):
        """A simple wrapper to pass the warning to the warning registry."""
        if not hasattr('__getitem__'):
            raise TypeError('Dictionary-alike object required')
        if not 'message' in warn:
            raise ValueError("A warning must have a message.")
        MAGSBS.common.WarningRegistry().register_warning(warn)

    def get_warnings(self):
        """Simple wrapper to retrieve all warnings registered. Flushes the list
        afterwards."""
        return MAGSBS.common.WarningRegistry().get_warnings()

    @abstractmethod
    def emit_error(self, error):
        """Emit an error. All child classes must write the warnings present as
        well. Error can either be a string or a proper error object as specified
        in the JSON API."""
        pass

    @abstractmethod
    def emit_result(self, result):
        pass

    @abstractmethod
    def clear(self):
        """Depending on the output formatter, this method will clear the
        underlying stream or a tty or simply do nothing."""

    @abstractmethod
    def emit_usage(self, usage, error=None):
        """Emit program usage and an optional error (in case i.e. an argument
        was supplied incorrectly. Both have to be of type string."""
        pass

class HelpfulParser(argparse.ArgumentParser):
    """Unlike the super class, this arg parse instance will print the error it
    encountered as well as the complete usage of the program. It will also
    redirect the usage to a output formatter."""
    def __init__(self, name, output_formatter, description=None):
        self.formatter = output_formatter
        if description:
            super().__init__(prog=name, description=description)
        else:
            super().__init__(name=name)

    def print_help(self, file=None):
        """Override super method and redirect output to the output formatter."""
        if not file:
            buffer = io.StringIO()
        else:
            buffer = file
        super().print_help(buffer)
        if not file: # own buffer, write to emit_usage
            buffer.seek(0) # jump back in logical stream
            self.formatter.emit_usage(buffer.read())

    def error(self, message):
        """Print error message and usage information."""
        buffer = io.StringIO()
        self.print_help(buffer)
        buffer.seek(0)
        self.formatter.emit_usage(buffer.read(), error='Error: ' + message)
        sys.exit(2)

#pylint: disable=too-few-public-methods
class ErrorHandler:
    """Contet handler to handle exceptions gracefully."""
    def __init__(self, output_formatter):
        self.output_formatter = output_formatter

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        import traceback
        error = {}
        if exc_type:
            if isinstance(exc_value, MAGSBS.errors.MAGSBS_error):
                error = exc_value.to_json()
            else:
                error['message'] = exc_type.__name__  + ': ' + str(exc_value)
            if os.environ.get('DEBUG'):
                error['traceback'] = {'verbatim':
                        ''.join(traceback.format_exception(exc_type,
                        exc_value, tb))}
            self.output_formatter.emit_error(error)
            sys.exit(119)


class main():
    def __init__(self, output_formatter):
        self.output_formatter = output_formatter

    def run(self, args):
        if len(args) < 2:
            self.output_formatter.emit_usage(main_usage)
        else:
            # try to get a handler for it
            try:
                invokation_command = '%s %s' % (PROCNAME, sys.argv[1])
                func = getattr(self, 'handle_%s' % args[1])
            except AttributeError:
                self.output_formatter.emit_usage(main_usage, "Invalid command: " + args[1])
                sys.exit(127)
            func(invokation_command, args[2:])
            sys.exit(0)

    def handle_toc(self, cmd, args):
        "Table Of Contents"
        parser = HelpfulParser(cmd, self.output_formatter, description="Generate table of contents.")
        parser.add_argument("-o", "--output", dest="output",
                  help="write output to file instead of stdout",
                  metavar="FILENAME", default='stdout')
        parser.add_argument('directory',
                help='Input directory where search for headings is performed.')
        options = parser.parse_args(args)

        file = None
        if options.output == 'stdout':
            file = io.StringIO()
        else:
            file = open(options.output, 'w', encoding='utf-8')
        directory = options.directory
        if not os.path.exists(directory):
            self.output_formatter.emit_error("Directory %s does not exist" % directory)
            sys.exit(126)

        with ErrorHandler(self.output_formatter):
            c = MAGSBS.toc.HeadingIndexer(directory)
            c.walk()
            if not c.is_empty():
                fmt = MAGSBS.toc.TOCFormatter(c.get_index(),
                        directory)
                file.write(fmt.format())
                if isinstance(file, io.StringIO):
                    file.seek(0)
                    self.output_formatter.emit_result(file.read())
                else:
                    file.close()

    def handle_conf(self, cmd, args):
        """Create or update configuration."""
        description="""Allowed subcommands are `show`, `update` and `init`. `show` shows the current
configuration settings, default values if none present.
`update` and `show` try to find the correct configuration: if none exists
in the current directory and you are in a subdirectory of a project, they try to
determine the project root and read the configuration for there if present
(else the default values are used).
`init` on the other hand behaves basically like update (it sets configuration
values), but it does that for the current directory. This is handy for
sub-directory configurations or initialization of a new project."""
        parser = HelpfulParser(cmd, self.output_formatter, description)
        parser.add_argument("-a", dest="appendixPrefix",
                  help='use "A" as prefix to appendix chapter numbering and omit the additional header "appendix" (or its localized version)',
                  action="store_true", default=False)
        parser.add_argument("-A", dest="sourceAuthor",
                  help="set author of source document", default=None)
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
                  help="set source document information",
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

        if len(args) == 0 or args[0] not in ['show', 'update', 'init']:
            parser.error("Error: no subcommand specified.")
            sys.exit(88)
        subcmd = args[0]

        options = parser.parse_args(args[1:])
        if subcmd == 'init':
            # read configuration from cwd, if present
            inst = MAGSBS.config.LectureMetaData(MAGSBS.config.CONF_FILE_NAME)
            inst.write()
        else:
            inst = MAGSBS.config.confFactory().get_conf_instance(os.getcwd())
            try:
                inst.read()
            except FileNotFoundError:
                pass

        def print_configuration(prefix):
            self.output_formatter.emit_result({prefix: inst})

        if subcmd == 'show':
            print_configuration("Current settings:")
        elif subcmd == 'update' or subcmd == 'init':
            for opt, value in options.__dict__.items():
                if value is not None:
                    inst[opt] = value
            print_configuration("New settings")
            inst.write()
        else:
            parser.print_help()



    def handle_conv(self, cmd, args):
        """Convert files."""
        parser = HelpfulParser(cmd, self.output_formatter, "Convert a file from MarkDown "
                    "to HTML.")
        parser.add_argument("file", help="input file or directory")
        args = parser.parse_args(args)
        if not os.path.exists(args.file):
            self.output_formatter.emit_error('file not found: ' + args.file)
            sys.exit(127)
        if os.path.isdir(args.file):
            self.output_formatter.emit_error('file required, directory found: ' + args.file)
            sys.exit(98)

        with ErrorHandler(self.output_formatter):
            p = MAGSBS.pandoc.Pandoc()
            p.convert_files((args.file,))


    def handle_imgdsc(self, cmd, args):
        description = ("The working directory must be a chapter of a book or of "
                      "another kind of material; the image name must be a path "
                      "relative to the current working directory.")
        parser = HelpfulParser(cmd, self.output_formatter, description)
        parser.add_argument("-d", "--description", dest="description",
                help="image description string (or - for stdin)",
                metavar="DESC", default='no description')
        parser.add_argument("-o", "--outsource-descriptions", dest="outsource",
                action="store_true", default=False,
                help="if set, images will be outsourced, no matter how long they are.")
        parser.add_argument("-t", "--title", dest="title",
                default=None,
                help="set title for outsourced images (mandatory if outsourced)")
        parser.add_argument('path', nargs="?", help="path to image file")
        options = parser.parse_args(args)
        if not options.path:
            parser.error("no path specified!")
            exit(1)
        if options.description == "-":
            desc = sys.stdin.read()
        else:
            desc = options.description
        img = MAGSBS.factories.ImageDescription(options.path)
        img.set_description(desc)
        img.set_outsource_descriptions(options.outsource)
        if options.title:
            img.set_title(options.title)
        with ErrorHandler(self.output_formatter):
            # wrap all values in a "verbatim" dict, telling the formatter to not
            # reindent this value
            self.output_formatter.emit_result({key: {'verbatim': value}
                for key, value in img.get_output().items()})

    def handle_iswithinlecture(self, cmd_name, args):
        """Tell the user whether a given path is part of a lecture or not."""
        usage = ("Usage: {} iswithinlecture <path>\n\nTest whether the given "
        "file or directory is part of a lecture.\n").format(cmd_name)
        if len(args) == 0:
            self.output_formatter.emit_usage(usage, "path required.")
            sys.exit(127)
        elif len(args) > 1:
            self.output_formatter.emit_usage(usage, "only one path at a time allowed.")
            sys.exit(127)
        else:
            if args[0] == '-h' or args[0] == '--help':
                self.output_formatter.emit_usage(usage)
                sys.exit(0)
            else:
                self.output_formatter.emit_result({ 'is within a lecture':
                    MAGSBS.common.is_within_lecture(args[0]) })


    def handle_new(self, cmd, args):
        description = "Initialize a new lecture material or book directory (tree)."
        parser = HelpfulParser(cmd, self.output_formatter, description)
        parser.add_argument("-a", dest="appendix_count", default="0", type=int,
                metavar="COUNT",
                help="number of appendix chapters (default 0)")
        parser.add_argument("-c", dest="chapter_count", default="2", type=int,
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
        parser.add_argument('directory', nargs="?",
                help="new directory to create lecture in")
        options = parser.parse_args(args)
        if not options.directory:
            parser.print_help()
            sys.exit(1)
        try:
            a = int(options.appendix_count)
            c = int(options.chapter_count)
        except ValueError:
            self.output_formatter.emit_error("The number of chapters and "
                    "appendix chapters must be integers.")
            sys.exit(125)
        builder = MAGSBS.filesystem.InitLecture(options.directory, c, options.lang)
        builder.set_amount_appendix_chapters(a)
        if options.preface:
            builder.set_has_preface(True)
        if options.nochapter:
            builder.set_no_chapters(True)
        builder.generate_structure()

    def handle_mk(self, cmd, args):
        description = textwrap.dedent("""
        Run "mistkerl", a quality assurance helper. It checks for common errors and
        outputs them on the command line.""")
        parser = HelpfulParser(cmd, self.output_formatter, description)
        parser.add_argument("-c", dest="critical_first", action="store_true",
                help="Sort critical errors first")
        parser.add_argument("-s", dest="squeeze_output", action="store_true",
                help="use less blank lines")
        parser.add_argument("-l", dest="live_view", action="store_true",
                help=" less blank lines")
        parser.add_argument("input", nargs="?",
                help="specify file or directory to be checked")
        options = parser.parse_args(args)

        if not options.input:
            self.output_formatter.emit_error("input file name required.")
            sys.exit( 127 )
        if not os.path.exists(options.input):
            self.output_formatter.emit_error("Error: %s does not exist." \
                    % options.input)
            sys.exit(5)

        def format_errors():
            mistkerl = MAGSBS.quality_assurance.Mistkerl()
            mistakes = mistkerl.run(options.input)
            if not mistakes:
                return ("Nun denn, ich konnte keine Fehler entdecken. Hoffen "
                        "wir, dass es auch wirklich keine gibt ;-).")
            else:
                transformed = collections.OrderedDict()
                # sort mistakes by path
                for m in sorted(mistakes, key=lambda x: x.path):
                    # convert m.lineno, m.pos_on_line attribute into tuple; second arg is optional
                    pos = tuple(filter(bool, (m.lineno, m.pos_on_line)))
                    new = {pos: m.message}
                    if not m.path in transformed: # add sublist, if none present yet
                        transformed[m.path] = []
                    transformed[m.path].append(new)
                # sort errors by (lineno, pos_on_line); convert to readable string representation
                for messages in transformed.values():
                    messages.sort(key=lambda x: next(iter(x)))
                    for index, message in enumerate(messages):
                        key = next(iter(message))
                        if not key:
                            messages[index] = message[key]
                        else:
                            messages[index] = {', '.join(map(str, key)): message[key]}
                return transformed

        if options.live_view:
            import time
            try:
                while True:
                    mistakes = format_errors() # fetch them before clearing the screen
                    self.output_formatter.clear()
                    self.output_formatter.emit_result(mistakes)
                    time.sleep(5)
            except KeyboardInterrupt:
                pass # stop
        else:
            self.output_formatter.emit_result(format_errors())

    def handle_master(self, cmd, args):
        #pylint: disable=unused-argument
        # help requested / invalid command line:
        if not args or '-h' in args or '--help' in args:
            self.output_formatter.emit_usage(("{} master <lecture directory>\n"
                "The master command will perform all actions available to "
                "automate lecture conversion:\n"
                "-    generate a table of contents\n"
                "-    convert custom MarkDown extensions\n"
                "-    apply custom layout definition\n"
                "-    and do that for all MarkDown files within the specified "
                "directory").format(PROCNAME))
            sys.exit(0)
        if not os.path.exists(args[0]):
            self.output_formatter.emit_error("No such file or directory: " \
                    + args[0])
            sys.exit(124)
        elif not os.path.isdir(args[0]):
            self.output_formatter.emit_error("%s: is not a directory" % args[0])
            sys.exit(123)
        else:
            with ErrorHandler(self.output_formatter):
                m = MAGSBS.master.Master(args[0])
                m.run()

    #pylint: disable=unused-argument
    def handle_version(self, dont, care):
        self.output_formatter.emit_result({'version': str(MAGSBS.config.VERSION)})

