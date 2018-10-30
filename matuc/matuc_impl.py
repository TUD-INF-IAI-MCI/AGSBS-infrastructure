"""
This module contains the actual implementation of the matuc and the matuc_js
command-line frontend.
It provides:


-   A base output formatter that controls how the text is displayed
    (currently matuc.py implements a text interface, matuc_js a json.
    interface)
-   A few methods to parse arguments and to control all the functionality
    offered by the MAGSBS module.

The actual output is formatted and printed using scripts called matuc and
matuc_js. They share *all* of the functionality of this module and just define a
text and a JSON interface."""
#pylint: disable=invalid-name
from abc import ABCMeta, abstractmethod
import argparse
import collections
import io
import os
import sys
import textwrap

import MAGSBS.common
import MAGSBS.config
import MAGSBS.datastructures
import MAGSBS.errors
import MAGSBS.factories
import MAGSBS.filesystem
import MAGSBS.master
import MAGSBS.mparser
from MAGSBS import pagenumbering
import MAGSBS.pandoc
import MAGSBS.quality_assurance
import MAGSBS.toc

PROCNAME = os.path.basename(sys.argv[0])

#necessary for function '_'
MAGSBS.common.setup_i18n()

MAIN_USAGE = _("""%s <command> <options>

<command> determines which action to take. The syntax might vary between
commands. Use %s <command> -h for help.

Available commands are:

addpnum         - generate new page number, relative to its predecessors
conf            - set, init or update a configuration
conv            - convert a project
fixpnums        - fix incorrect page numbering of a document
imgdsc          - generate image description (snippets)
iswithinlecture - test, whether a certain path is part of a project
new             - create new project structure
mk              - invoke "mistkerl", a quality assurance helper
toc             - generate table of contents
version         - output program version
""" % (PROCNAME, PROCNAME))


class OutputFormatter:
    """The OutputFormatter provides abstract methods to format the output
    produced by Matuc to either a TTY or into other formats, i.e. usable by a
    GUI or another program. This way, matuc can emit its results to the
    formatter and this will take care of writing it to stdout or i.e. to a JSON
    stream.
    Valid inputs for the functions may be strings, lists/tuples and dicts. Each
    will be handled appropriately. If a dict is found with the key verbatim, the
    value of that field will be printed without modification. The rest of this
    dictionary is ignored. Note: anything exporting to a JSON API must convert
    this special case of {'verbatim': 'something'} into 'something'. to be
    compliant with the JSON API specification."""
    __metaclass__ = ABCMeta
    @staticmethod
    def register_warning(warn):
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
            self.output_formatter.emit_usage(MAIN_USAGE)
        else:
            # try to get a handler for it
            try:
                invokation_command = '%s %s' % (PROCNAME, sys.argv[1])
                func = getattr(self, 'handle_%s' % args[1])
            except AttributeError:
                self.output_formatter.emit_usage(MAIN_USAGE,
                        _("Invalid command: %s" % args[1]))
                sys.exit(127)
            ret = func(invokation_command, args[2:])
            if not ret:
                ret = 0
            sys.exit(ret)

    def handle_toc(self, cmd, args):
        "Table Of Contents"
        parser = HelpfulParser(cmd, self.output_formatter,
                description=_("Generate table of contents."))
        parser.add_argument("-o", "--output", dest="output",
                  help=_("write output to file instead of stdout"),
                  metavar="FILENAME", default='stdout')
        parser.add_argument('directory',
                help=_('material directory (containing chapters)'))
        options = parser.parse_args(args)

        file = None
        if options.output == 'stdout':
            file = io.StringIO()
        else:
            file = open(options.output, 'w', encoding='utf-8')
        directory = options.directory
        if not os.path.exists(directory):
            self.output_formatter.emit_error(("Directory %s does not exist") \
                    % directory)
            sys.exit(126)

        with ErrorHandler(self.output_formatter):
            idxer = MAGSBS.toc.HeadingIndexer(directory)
            idxer.walk()
            if not idxer.is_empty():
                fmt = MAGSBS.toc.TocFormatter(idxer.get_index(), directory)
                file.write(fmt.format())
                if isinstance(file, io.StringIO):
                    file.seek(0)
                    self.output_formatter.emit_result({'verbatim': file.read()})
                else:
                    file.close()

    def handle_conf(self, cmd, args):
        """Create or update configuration."""
        description = _("""Allowed subcommands are `show`, `update` and `init`.
`show` shows the current configuration settings, default values if none present.
`update` and `show` try to find the correct configuration: if none exists in the
current directory and you are in a subdirectory of a project, the project root
will be queried for a configuration. If no file was found, the default settings
are displayed.

`init` on the other hand behaves basically like update (it sets configuration
values), but it does that for the current directory. This is handy for
sub-directory configurations or initialization of a new project.""")
        parser = HelpfulParser(cmd, self.output_formatter, description)
        parser.add_argument("-a", dest="AppendixPrefix",
                  help=_('insert "A" as prefix for each chapter number in the '
                          'appendix and omit the header "appendix"'),
                  action="store_true", default=False)
        parser.add_argument("-A", dest="SourceAuthor",
                  help=_('set author of source document'))
        parser.add_argument("-e", dest="Editor",
                  help=_('set project editor'),
                  metavar="NAME", default=None)
        parser.add_argument("-i", dest="Institution",
                  help=_('set institution (default TU Dresden)'),
                  metavar="NAME", default=None)
        parser.add_argument("-l", dest="LectureTitle",
                  help=_('set title of project (first heading level 1 by '
                      'default)'),
                  metavar="TITLE", default=None)
        parser.add_argument("-L", dest='Language',
                  help=_('set document language (de by default)'),
                  default='de')
        parser.add_argument("-p", "--pnum-gap", dest="PageNumberingGap",
                  help=_('specify gap between page numbering links in '
                      'navigation bar (default: 5)'),
                  metavar="NUM", default=None)
        parser.add_argument("-s", dest="Source",
                  help=_('set information about source document'),
                  metavar="SRC", default=None)
        parser.add_argument("-S", dest="SemesterOfEdit",
                  help=_('set semester of edit (will be guessed otherwise)'),
                  metavar="SEMYEAR", default=None)
        parser.add_argument("--toc-depth", dest="TocDepth",
                  help=_('limit the heading depth for the table of contents'),
                  metavar="NUM", default=None)
        parser.add_argument("-w", dest="WorkingGroup",
                  help=_('set working group'),
                  metavar="GROUP", default=None)

        if not args or args[0] not in ['show', 'update', 'init']:
            parser.error(_('Error: no subcommand specified.'))
            sys.exit(88)
        subcmd = args[0]

        options = parser.parse_args(args[1:])
        if subcmd == 'init':
            # read configuration from cwd, if present
            inst = MAGSBS.config.LectureMetaData(MAGSBS.config.CONF_FILE_NAME)
            inst.write()
        else:
            inst = MAGSBS.config.ConfFactory().get_conf_instance(os.getcwd())
            try:
                inst.read()
            except FileNotFoundError:
                pass

        if subcmd == 'show':
            self.output_formatter.emit_result({_("Current settings"):
                    {key.name: value for key, value in inst.items()}})
        elif subcmd in ('update', 'init'):
            for opt, value in options.__dict__.items():
                if value is not None:
                    inst[MAGSBS.config.MetaInfo[opt]] = value
            self.output_formatter.emit_result({_("New settings"):
                    {key.name: value for key, value in inst.items()}})
            inst.write()
        else:
            parser.print_help()


    def handle_conv(self, cmd, args):
        """Convert files."""
        usage = _("Converts a file or directory containing a project.\n\n"
                 "If a directory is supplied, additional steps such as "
                 "generating a table of contents are performed as well.")
        parser = HelpfulParser(cmd, self.output_formatter, usage)
        parser.add_argument("-f", dest="format",
                            help=_('select output format (html or epub, '
                                'default html)'),
                            metavar="FMT", default=None)
        parser.add_argument("path", help=_("path to input file or directory"))
        args = parser.parse_args(args)
        if not os.path.exists(args.path):
            self.output_formatter.emit_error(_('file or directory not found: %s'
                        % args.path))
            sys.exit(127)
        with ErrorHandler(self.output_formatter):
            if os.path.isdir(args.path):
                from MAGSBS.pandoc.formats import ConversionProfile, OutputFormat
                m = MAGSBS.master.Master(
                    args.path,
                    ConversionProfile.Blind,
                    (OutputFormat.Html if not args.format
                     else OutputFormat.from_string(args.format)))
                m.run()
            else:
                p = MAGSBS.pandoc.converter.Pandoc()
                if args.profile:
                    p.set_conversion_profile(
                        MAGSBS.pandoc.formats.ConversionProfile.from_string(
                                args.profile))
                # do not handle format argument as only html is supported for
                # convcerting a single file.
                p.convert_files((args.path,))


    def handle_imgdsc(self, cmd, args):
        description = _("The working directory must be within a project; "
                "the image path must be relative to the current "
                "working directory.")
        parser = HelpfulParser(cmd, self.output_formatter, description)
        parser.add_argument("-d", "--description", dest="description",
                help=_('image description string (- for reading stdin)'),
                metavar="DESC", default='no description')
        parser.add_argument("-o", "--outsource-descriptions", dest="outsource",
                action="store_true", default=False,
                help=_('outsource image descriptions regardless of their '
                    'length'))
        parser.add_argument("-t", "--title", dest="title",
                default=None,
                help=_('set title for outsourced images (mandatory if '
                    'outsourced)'))
        parser.add_argument('path', nargs="?", help="path to image file")
        options = parser.parse_args(args)
        if not options.path:
            parser.error(_("no path specified"))
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
        usage = _("Usage: {} iswithinlecture <path>\n\nTest whether the given "
        "file or directory is part of a lecture.\n").format(cmd_name)
        if not args:
            self.output_formatter.emit_usage(usage, _("path required"))
            sys.exit(127)
        elif len(args) > 1:
            self.output_formatter.emit_usage(usage,
                    _("only one path at a time allowed."))
            sys.exit(127)
        else:
            if args[0] == '-h' or args[0] == '--help':
                self.output_formatter.emit_usage(usage)
                sys.exit(0)
            else:
                self.output_formatter.emit_result({'is within a lecture':
                    MAGSBS.common.is_within_lecture(args[0])})


    def handle_new(self, cmd, args):
        description = _('Initialize a new lecture material or book directory.')
        parser = HelpfulParser(cmd, self.output_formatter, description)
        parser.add_argument("-a", dest="appendix_count", default="0", type=int,
                metavar="COUNT",
                help=_('number of appendix chapters (default 0)'))
        parser.add_argument("-c", dest="chapter_count", default="2", type=int,
                metavar="COUNT",
                help=_('number of chapters (default 2)'))
        parser.add_argument("-p", dest="preface", default=False,
                action="store_true",
                help=_('add a preface (default no)")'))
        parser.add_argument("-n", dest="nochapter", default=False,
                action="store_true",
                help=_('if set, blattxx will be used instead of kxx'))
        parser.add_argument("-l", dest="lang", default="de",
                help=_('set language (default de)'))
        parser.add_argument('directory', nargs="?",
                help=_('new directory to create project in'))
        options = parser.parse_args(args)
        if not options.directory:
            parser.print_help()
            sys.exit(1)
        try:
            a = int(options.appendix_count)
            c = int(options.chapter_count)
        except ValueError:
            self.output_formatter.emit_error(_("The number of chapters and "
                    "appendix chapters must be integers."))
            sys.exit(125)
        builder = MAGSBS.filesystem.InitLecture(options.directory, c,
                options.lang)
        builder.set_amount_appendix_chapters(a)
        if options.preface:
            builder.set_has_preface(True)
        if options.nochapter:
            builder.set_no_chapters(True)
        builder.generate_structure()

    def handle_mk(self, cmd, args):
        description = textwrap.dedent(_("""
        Run "mistkerl", a quality assurance helper. It checks for common errors
        in accessible markdown documents and
        outputs them on the command line."""))
        parser = HelpfulParser(cmd, self.output_formatter, description)
        parser.add_argument("-c", dest="critical_first", action="store_true",
                help=_("Sort critical errors first"))
        parser.add_argument("-s", dest="squeeze_output", action="store_true",
                help=_("use less blank lines in output"))
        parser.add_argument("-l", dest="live_view", action="store_true",
                help=_("open a console-only live view, refreshing the list of "
                    "errors every few seconds"))
        parser.add_argument("input", nargs="?",
                help=_("specify file or directory to be checked"))
        options = parser.parse_args(args)

        if not options.input:
            self.output_formatter.emit_error(_("input file name required."))
            sys.exit(127)
        if not os.path.exists(options.input):
            self.output_formatter.emit_error(_("Error: %s does not exist.") \
                    % options.input)
            sys.exit(5)

        def format_errors():
            mistkerl = MAGSBS.quality_assurance.Mistkerl()
            mistakes = mistkerl.run(options.input)
            if not mistakes:
                return _("No errors found. Hopefully there are none :-).")
            transformed = collections.OrderedDict()
            # sort mistakes by path
            for mt in sorted(mistakes, key=lambda x: x.path):
                # convert m.lineno, m.pos_on_line attribute into tuple;
                # second arg is optional
                pos = tuple(filter(bool, (mt.lineno, mt.pos_on_line)))
                new = {pos: mt.message}
                if not mt.path in transformed: # add sublist if not present
                    transformed[mt.path] = []
                transformed[mt.path].append(new)
            # sort errors by (lineno, pos_on_line); convert to readable
            # string representation
            for messages in transformed.values():
                messages.sort(key=lambda x: next(iter(x)))
                for index, message in enumerate(messages):
                    key = next(iter(message))
                    if not key:
                        messages[index] = message[key]
                    else:
                        messages[index] = {', '.join(
                                map(str, key)): message[key]}
            return transformed

        if options.live_view:
            import time
            try:
                while True:
                    mistakes = format_errors() # fetch before clearing screen
                    self.output_formatter.clear()
                    self.output_formatter.emit_result(mistakes)
                    time.sleep(5)
            except KeyboardInterrupt:
                pass # stop
        else:
            self.output_formatter.emit_result(format_errors())


    def handle_addpnum(self, cmd, args):
        """Return a new page number (roman and arabic supported).
        The new page number is generated using it's predecessors. It both
        respects the numbering from the predecessor, as also the format (roman
        or arabic)."""
        parser = HelpfulParser(cmd, self.output_formatter, description=_(
                "Generate a page number for a given context. A context "
                "consists of a line and a file. The enumeration will "
                "happen automatically (including distinction between roman and "
                "arabic), as well as the detection of the language of the "
                "lecture. This command will not insert the newly created "
                "page number by default, but print it to stdout. This is meant "
                "to be used by applications embedding Matuc's logic."))
        parser.add_argument("-f", dest="read_from_file", action="store_true",
                default=False, help=_("read from specified path instead of "
                    "reading from standard input"))
        parser.add_argument("-F", dest="rw_from_file", action="store_true",
                default=False, help=_("read from specified path instead of "
                    "reading from standard input and write result back to file; "
                    "this could lead to race conditions on concurrent "
                    "modifications"))
        parser.add_argument('path', nargs=1,
                help=_("Path to load configuration from. This can be either a "
                "file or a directory. If -f is given, the path is used as "
                "input file (by default, input is read from stdin)"))
        parser.add_argument('line_number', nargs=1,
                help=_("Line number for which to generate the page number"))

        options = parser.parse_args(args)
        path = options.path[0]
        if not os.path.exists(path):
            self.output_formatter.emit_error(_("Given path has to exist."))
            return 29
        try:
            line_number = int(options.line_number[0])
        except ValueError:
            self.output_formatter.emit_error(_("Argument 2 is not a number."))
            return 5
        # try to read from stdin or from file if -f or -F; write to stdout or to
        # file if -F given
        if options.read_from_file or options.rw_from_file:
            if not os.path.isfile(path):
                self.output_formatter.emit_error(_("Given path is not a file, "
                        "but reading from it with -f has been requested."))
                return 99
            text = pagenumbering.add_page_number(path, line_number).format()

            if options.read_from_file: # print to stdout
                self.output_formatter.emit_result({'pagenumber': text})
            else: # read and write into given path
                with open(path, encoding='utf-8') as f:
                    lines = f.read().split('\n')
                lines = insert_line(lines, line_number, text)
                with open(path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines))
        else:
            data = sys.stdin.read()
            self.output_formatter.emit_result({'pagenumber':
                pagenumbering.add_page_number_from_str(data, line_number,
                    path=path).format()})
        return 0


    def handle_fixpnums(self, cmd, args):
        """Please see usage info."""
        parser = HelpfulParser(cmd, self.output_formatter, description= \
            _("Check the page numbers of a document and warn / fix the page "
                "numbering, if the numbers do not strictly increase by one.\n"
                "This command reads from stdin by default, see -f."))
        parser.add_argument("-f", dest="file", metavar="FILE",
                default=None, help=_("read from specified path instead of "
                    "reading from standard input"))
        parser.add_argument("-i", dest="in_place", action="store_true",
            help=_("if -f is given, replace the page numbering in the "
                "file in-place"))

        options = parser.parse_args(args)

        if options.in_place and not options.file:
            self.output_formatter.emit_error(_("In-place modifications "
                    "requested, but no file given."))
            sys.exit(73)

        if options.file and not os.path.exists(options.file):
            self.output_formatter.emit_error(_("Given path has to exist."))
            sys.exit(74)
        pnums = None
        if options.file:
            pnums = MAGSBS.mparser.extract_page_numbers(options.file)
        else:
            paragraphs = MAGSBS.mparser.file2paragraphs(sys.stdin.read())
            pnums = MAGSBS.mparser.extract_page_numbers_from_par(paragraphs)

        errorneous = MAGSBS.pagenumbering.check_page_numbering(pnums)
        if not errorneous:
            self.output_formatter.emit_result([])
            sys.exit(0)

        corrected = [] # correct page numbers
        for pnum, expected_num in errorneous:
            pnum.number = expected_num
            corrected.append({str(pnum.line_no): pnum.format()})

        if options.in_place:
            with open(options.file, 'r', encoding='utf-8') as f:
                lines = f.read().split('\n')
                # destructure list of dicts into list of tuples
                for lnum, string in (x for d in corrected for x in d.items()):
                    lines[int(lnum) - 1] = string # inefficient, but easier to
            with open(options.file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
        else:
            self.output_formatter.emit_result(corrected)
            sys.exit(0)


    #pylint: disable=unused-argument
    def handle_version(self, dont, care):
        self.output_formatter.emit_result({'version':
                str(MAGSBS.config.VERSION)})

def insert_line(lines, line_number, line):
    """This function allows the insertion of a line into a list of lines. It
    will take care that the line is inserted as a last element, if the index is
    great than the length of the list. If the line exists, it will take care of
    inserting empty lines('') so that the line is a paragraph on its own."""
    # this function has been outsourced to make handle_addpnum more readable
    if line_number < 1:
        raise ValueError("line numbers count from one")
    # careful: line_number counts from 1
    if line_number >= len(lines): # end of document
        if lines and lines[-1].strip(): # no newline at end
            lines.append('')
        lines.append(line)
    elif line_number == 1:
        lines.insert(0, line)
        if len(lines) > 1 and lines[1].strip():
            lines.insert(1, '')
    else:
        if not lines[line_number-2] == '':
            lines = lines[:line_number-1] + [''] + lines[line_number-1:]
        lines = lines[:line_number] + [line] + lines[line_number:]
        print(lines[line_number])
        if lines[line_number+1].strip(): # no newline at end
            lines = lines[:line_number+1] + [''] + lines[line_number+1:]
    return lines
