"""Output format formatters, currently only HTML."""
# vim: set expandtab sts=4 ts=4 sw=4:
# This is free software, licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2017-2018 Sebastian Humenda <shumenda |at| gmx |dot| de>

import enum
import os
import re
import subprocess
from ..config import MetaInfo
from .. import config, common, datastructures, errors, mparser


class ConversionProfile(enum.Enum):
    """Defines the enums for the conversion depending on the the impairment."""
    Blind = 'blind'
    VisuallyImpairedDefault = 'vid'

    @staticmethod
    def from_string(string):
        for profile in ConversionProfile:
            if profile.value == string:
                return profile
        known = ', '.join(x.value for x in ConversionProfile)
        raise ValueError("Unknown profile, known profiles: " + known)

class OutputFormat(enum.Enum):
    """Defines the enums for the output format."""
    Html = 'html'
    Epub = 'epub'

    @staticmethod
    def from_string(string):
        for format_ in OutputFormat:
            if format_.value == string:
                return format_
        known = ', '.join(x.value for x in OutputFormat)
        raise ValueError("Unknown output format, known formats: " + known)

class OutputGenerator():
    """Base class for document output generators. The actual conversion doesn't
take place in this class. The conversion method receives a Pandoc (JSON) AST and
transforms it, as required. The transformed AST is returned.
Each child class should have constants called FILE_EXTENSION and
PANDOC_FORMAT_NAME (used for the file extension and the -t pandoc command line
flag).

General usage:
>>> gen = MyGenerator(pandoc_ast, language)
# method for child classes to implement (optional) things like template creation
>>> gen.setup() # set up, if required (always called)
# convert json of document and write it to basefilename + '.' + format; may
# raise SubprocessError; the JSON is the Pandoc AST (intermediate file format)
>>> if gen.needs_update(path):
'''    ast = gen.convert(ast, path)
# clean up, e.g. deletion of templates. Should be executed even if gen.convert()
# threw an error
gen.cleanup()."""
    FILE_EXTENSION = 'None'
    PANDOC_FORMAT_NAME = 'plain'
    # json content filters:
    CONTENT_FILTERS = []
    # recognize chapter prefixes in paths, e.g. "anh01" for appendix chapter one
    IS_CHAPTER = re.compile(r'^%s\d+\.md$' % '|'.join(common.VALID_FILE_BGN))

    def __init__(self, meta, language):
        self.__meta = meta
        self.__language = language
        self.__conversion_profile = ConversionProfile.Blind

    def get_language(self):
        return self.__language

    def set_meta_data(self, meta):
        self.__meta = meta

    def get_meta_data(self):
        return self.__meta

    def setup(self):
        """Set up the converter."""
        pass

    def convert(self, files, **kwargs):
        """Convert given files using Pandoc.
        files: Pandoc JSON AST (dictionaries)
        kwargs: filter specific arguments"""
        pass

    def cleanup(self):
        pass

    def needs_update(self, path):
        """Returns True, if the given file needs to be converted again. If i.e.
        the output file is newer than the input (MarkDown) file, no conversion
        is necessary."""
        raise NotImplementedError()

    def set_profile(self, profile):
        self.__conversion_profile = profile

    def get_profile(self):
        return self.__conversion_profile


def execute(args, stdin=None, cwd=None):
    """Convenience wrapper to subprocess.Popen). It'll append the process' stderr
    to the message from the raised exception. Returned is the unicode stdout
    output of the program. If stdin=some_value, a pipe to the child is opened
    and the argument passed."""
    text = None
    proc = None
    text = None
    cwd = (cwd if cwd else '.')
    text = ''
    try:
        if stdin:
            proc = subprocess.Popen(args, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, stdin=subprocess.PIPE, cwd=cwd)
            text = proc.communicate(stdin.encode(datastructures.get_encoding()))
        else:
            proc = subprocess.Popen(args, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, cwd=cwd)
            text = proc.communicate()
    except FileNotFoundError as e:
        msg = '%s:_: %s %s ' %(args[0], str(e), text)
        raise errors.SubprocessError(args, msg)
    if not proc:
        raise ValueError("No subprocess handle exists, even though it " + \
                "should. That's a bug to be reported.")
    ret = proc.wait()
    if ret:
        msg = '\n'.join(map(datastructures.decode, text))
        raise errors.SubprocessError(args, msg)
    return datastructures.decode(text[0])

def remove_temp(fn):
    if fn is None:
        return
    if os.path.exists(fn):
        try:
            os.remove(fn)
        except OSError:
            common.WarningRegistry().register_warning(
            "Couldn't remove tempfile", path=fn)

def __handle_gladtex_error(error, file_path, dirname):
    """Retrieve formula position from GladTeX' error output, match it
    against the formula of the Markdown document and report it to the
    user.
    Note: file_path is relative to dirname, so both is required."""
    file_path = os.path.join(dirname, file_path) # full path is better
    try:
        details = dict(line.split(': ', 1) for line in error.message.split('\n')
            if ': ' in line)
    except ValueError as e:
        # output was not formatted as expected, report that
        msg = "couldn't parse GladTeX output: %s\noutput: %s" % \
            (str(e), error.message)
        return errors.SubprocessError(error.command, msg, path=dirname)
    if details and 'Number' in details and 'Message' in details:
        number = int(details['Number'])
        with open(file_path, 'r', encoding='utf-8') as file:
            paragraphs = mparser.rm_codeblocks(mparser.file2paragraphs(
                file.read().split('\n')))
            formulas = mparser.parse_formulas(paragraphs)
        try:
            pos = list(formulas.keys())[number-1]
        except IndexError:
            # if improperly closed maths environments eixst, formulas cannot
            # be counted; although there's somewhere a LaTeX error which
            # we're trying to report, the improper maths environments HAVE
            # to reported and fixed first
            raise errors.SubprocessError(error.command, _(
                    "LaTeX reported an error while converting a fomrula. "
                    "Unfortunately, improperly closed formula environments "
                    "exist, therefore it cannot be determined which formula "
                    "was errorneous. Please re-read the document and fix "
                    "any unclosed formula environments."), file_path)

        # get LaTeX error output
        msg = details['Message'].rstrip().lstrip()
        msg = 'formula: {}\n{}'.format(list(formulas.values())[number-1], msg)
        e = errors.SubprocessError(error.command, msg, path=file_path)
        e.line = '{}, {}'.format(*pos)
        return e
    return error

#pylint: disable=too-many-locals
def generate_page_navigation(file_path, file_cache, page_numbers, file_extension, conf=None):
    """generate_page_navigation(path, file_cache, page_numbers, conf=None)
    Generate the page navigation for a page. The file path must be relative to
    the lecture root. The file cache must be the datastructures.FileCache, the
    page numbers must have the format of mparser.extract_page_numbers_from.
    `conf=` should not be used, it is intended for testing purposes.
    Returned is a tuple with the start and the end navigation bar. The
    navigation bar itself is a string."""
    if not os.path.exists(file_path):
        raise errors.StructuralError("File doesn't exist", file_path)
    if not file_cache:
        raise ValueError("Cache with values may not be None")
    if not conf:
        conf = config.ConfFactory().get_conf_instance(os.path.dirname(file_path))
    trans = config.Translate()
    trans.set_language(conf[MetaInfo.Language])
    relative_path = os.sep.join(file_path.rsplit(os.sep)[-2:])
    previous, nxt = file_cache.get_neighbours_for(relative_path)
    make_path = lambda path: '../{}/{}'.format(path[0], path[1].replace('.md',
        '.' + file_extension))
    if previous:
        previous = '[{}]({})'.format(trans.get_translation('previous').title(),
                make_path(previous))
    if nxt:
        nxt = '[{}]({})'.format(trans.get_translation('next').title(),
                make_path(nxt))
    navbar = []
    # take each pnumgapth element
    page_numbers = [pnum for pnum in page_numbers
        if (pnum.number % conf[MetaInfo.PageNumberingGap]) == 0]
    if page_numbers:
        navbar.append(trans.get_translation('pages').title() + ': ')
        navbar.extend('[[{0}]](#p{0}), '.format(num) for num in page_numbers)
        navbar[-1] = navbar[-1][:-2] # strip ", " from last chunk
    navbar = ''.join(navbar)
    chapternav = '[{}](../inhalt.{})'.format(trans.get_translation(
            'table of contents').title(), file_extension)

    if previous:
        chapternav = previous + '  ' + chapternav
    if nxt:
        chapternav += "  " + nxt
    # navigation at start of page
    nav_start = '{0}\n\n{1}\n\n* * * *\n\n\n'.format(chapternav, navbar)
    # navigation bar at end of page
    nav_end = '\n\n* * * *\n\n{0}\n\n{1}\n'.format(navbar, chapternav)
    return (nav_start, nav_end)
