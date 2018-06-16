"""Output format formatters, currently only HTML."""
# vim: set expandtab sts=4 ts=4 sw=4:
# This is free software, licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2017-2018 Sebastian Humenda <shumenda |at| gmx |dot| de>

import enum
import json
import os
import re
import shutil
import subprocess
import tempfile
import pandocfilters
from ..config import MetaInfo
from ..errors import MathError
from . import contentfilter
from .. import config, common, datastructures, errors, mparser

#pylint: disable=line-too-long
HTML_TEMPLATE = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml"$if(lang)$ lang="$lang$" xml:lang="$lang$"$endif$>
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
  <meta name="author" content="{SourceAuthor}" />
$if(date-meta)$
  <meta name="date" content="$date-meta$" />
$endif$
  <title>$if(title-prefix)$$title-prefix$ - $endif$$pagetitle$</title>
  <style type="text/css">
    code {{ white-space: pre; }}
    .underline {{ text-decoration: underline }}
    .annotation {{ border:2px solid #000000; background-color: #FCFCFC; }}
    .annotation:before {{ content: "{annotation}: "; }}
    table, th, td {{ border:1px solid #000000; }}
    /* frames with their colours */
    .frame {{ border:1px solid #000000; }}
    .box {{ border:2px dotted #000000; }}
    {frames}
    {boxes}
    div.frame span.title:before {{ content: "\\A{title}: "; white-space:pre; }}
    div.frame span.title:after {{ content: "\\A"; white-space:pre; }}
    div.box span.title:before {{ content: "\\A{title}: "; white-space:pre; }}
    div.box span.title:after {{ content: "\\A"; white-space:pre; }}

$if(highlighting-css)$
$highlighting-css$
$endif$
  </style>
$if(math)$
  $math$
$endif$
$for(header-includes)$
  $header-includes$
$endfor$
  <!-- agsbs-specific -->
  <meta name='Einrichtung' content='{Institution}' />
  <meta href='Arbeitsgruppe' content='{WorkingGroup}' />
  <meta name='Vorlagedokument' content='{Source}' />
  <meta name='Lehrgebiet' content='{LectureTitle}' />
  <meta name='Semester der Bearbeitung' content='{SemesterOfEdit}' />
  <meta name='Bearbeiter' content='{Editor}' />
</head>
<body lang="{Language}">
$for(include-before)$
$include-before$
$endfor$
$if(toc)$
<div id="$idprefix$TOC">
$toc$
</div>
$endif$
$body$
$for(include-after)$
$include-after$
$endfor$
</body>
</html>
"""

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

class HtmlConverter(OutputGenerator):
    """HTML output format generator. For documentation see super class;."""
    PANDOC_FORMAT_NAME = 'html'
    FILE_EXTENSION = 'html'
    CONTENT_FILTERS = [contentfilter.page_number_extractor,
                    contentfilter.suppress_captions]

    def __init__(self, meta, language):
        if not shutil.which('pandoc'):
            raise errors.SubprocessError(['pandoc'],
                _('You need to have Pandoc installed.'))

        super().__init__(meta, language)
        self.template_path = None
        self.template_copy = HTML_TEMPLATE[:] # full copy

    def setup(self):
        """Set up the HtmlConverter. Prepare the template for later use."""
        self.template_path = tempfile.mktemp() + '.html'
        self.template_copy = self.get_template()
        with open(self.template_path, "w", encoding="utf-8") as file:
            file.write(self.template_copy)

    def get_template(self):
        """Construct template."""
        start_with_caps = lambda content: content[0].upper() + content[1:]
        data = HTML_TEMPLATE[:]
        meta = self.get_meta_data()
        if 'title' in meta:
            meta.pop('title') # title should not be replaced

        # get translator object to translate certain phrases according to
        # configured language
        trans = config.Translate()
        trans.set_language(super().get_language())
        annotation = start_with_caps(trans.get_translation('note of editor'))
        frames = ['.frame:before { content: "%s: "; }' % \
                    start_with_caps(trans.get_translation("frame")),
                '.frame:after { content: "\\A %s"; }' % start_with_caps(trans \
                    .get_translation("end of frame"))]
        boxes = ['.box:before { content: "%s: "; }' % \
                    trans.get_translation("box"),
                '.box:after { content: "\\A %s"; }' % start_with_caps(trans \
            .get_translation("end of box"))]
        colours = {'black': '#000000;', 'blue': '#0000FF', 'brown': '#A52A2A',
            'grey': '#A9A9A9', 'green': '#006400', 'orange': '#FF8C00',
            'red': '#FF0000', 'violet': '#8A2BE2', 'yellow': '#FFFF00'}
        for name, rgb in colours.items():
            frames.append('.frame.%s { border-color: %s; }' % (name, rgb))
            frames.append('.frame.%s:before { content: "%s: "; }' % (name, \
                start_with_caps(trans.get_translation('%s frame' % name))))
            boxes.append('.box.%s { border-color: %s; }' % (name, rgb))
            boxes.append('.box.%s:before { content: "%s: "; }' % \
                (name, trans.get_translation('%s box' % name)))

        try:
            return data.format(annotation=annotation,
                    frames='\n    '.join(frames),
                    boxes='\n    '.join(boxes),
                    title=trans.get_translation("title"),
                    **meta)
        except KeyError as e:
            raise errors.ConfigurationError(("The key %s is missing in the "
                "configuration.") % e.args[0], meta['path'])

    def set_meta_data(self, meta):
        """Overwrite parent settr to re-generate template generation."""
        super().set_meta_data(meta)
        self.setup()

    def convert(self, files, **kwargs):
        """See super class documentation."""
        if 'cache' not in kwargs:
            raise ValueError('cache must be passed to converter')
        cache = kwargs['cache']
        factory = config.ConfFactory()
        conf = None
        try:
            for file_name in files:
                # get correct configuration for each file
                newconf = factory.get_conf_instance(os.path.dirname(file_name))
                # get new converter (and template) if config changes
                if not newconf is conf:
                    conf = newconf
                self.__convert_document(file_name, cache, conf)
        except errors.MAGSBS_error as err:
            if not err.path:
                err.path = file_name
            raise err
        finally:
            self.cleanup()

    @staticmethod
    def __handle_error(file_name, err):
        # set path for error
        if not err.path:
            err.path = os.path.abspath(file_name).replace(os.getcwd(), '').\
                    lstrip(os.sep)
        if not isinstance(err, MathError):
            raise err
        # recover line and pos of formula
        eqns = mparser.parse_formulas(mparser.file2paragraphs(open(file_name)))
        line, pos = list(eqns.keys())[err.formula_count - 1]
        err.line = line
        err.pos = pos
        raise err from None # no TB here

    #pylint: disable=too-many-locals
    def __convert_document(self, path, file_cache, conf):
        """Convert a document by a given path. It takes a converter which takes
        actual care of the underlying format. The filecache caches the list of
        files in the lecture. The list of files within a lecture is required to
        build navigation links.
        This function also inserts a page navigation bar to navigate between
        chapters and the table of contents."""
        # only convert if output file is newer than input file
        if not self.needs_update(path):
            return
        with open(path, 'r', encoding='utf-8') as file:
            document = file.read()
        if not document:
            return # skip empty documents
        if OutputGenerator.IS_CHAPTER.search(os.path.basename(path)):
            try:
                nav_start, nav_end = generate_page_navigation(path, file_cache,
                    mparser.extract_page_numbers_from_par(
                            mparser.file2paragraphs(document)))
            except errors.FormattingError as e:
                e.path = path
                raise e from None
            document = '{}\n\n{}\n\n{}\n'.format(nav_start, document, nav_end)
        json_ast = contentfilter.load_pandoc_ast(document)
        self.__apply_filters(json_ast, path, conf[MetaInfo.Format])
        dirname, filename = os.path.split(path)
        outputf = os.path.splitext(filename)[0] + '.' + self.FILE_EXTENSION
        pandoc_args = ['-s', '--template=%s' % self.template_path]
        # set title
        title = contentfilter.get_title(json_ast)
        if title: # if not None
            pandoc_args += ['-V', 'pagetitle:' + title, '-V', 'title:' + title]
        # instruct pandoc to enumerate headings
        try:
            pandoc_args += ['--number-sections', '--number-offset',
                str(datastructures.extract_chapter_number(path) - 1)]
        except errors.StructuralError:
            pass # no enumeration of headings if not chapter
        # for 'blind' see __apply_filters, doesn't need a Pandoc argument
        if self.get_profile() is ConversionProfile.VisuallyImpairedDefault:
            pandoc_args.append('--mathjax')
        execute(['pandoc'] + pandoc_args + ['-t', self.PANDOC_FORMAT_NAME,
            '-f', 'json', '+RTS', '-K25000000', '-RTS', # increase stack size
            '-o', outputf], stdin=json.dumps(json_ast), cwd=dirname)


    def __apply_filters(self, json_ast, path, fmt):
        """add MarkDown extensions with Pandoc filters"""
        try:
            filter_ = None
            for filter_ in self.CONTENT_FILTERS:
                json_ast = pandocfilters.walk(json_ast, filter_, fmt, [])
        except KeyError as e: # API clash(?)
            raise errors.StructuralError(("Incompatible Pandoc API found, while "
                "applying filter %s (ABI clash?).\nKeyError: %s") % \
                        (filter.__name__, str(e)), path)
        # use GleeTeX if configured
        if self.get_profile() is ConversionProfile.Blind:
            cwd = os.getcwd()
            try:
                # GladTeX will take the full base_path for linking the image;
                # since the link needs to be relative to the HTML file, we need
                # to change to the corresponding chapter for image creation,
                # because each image folder is relative to the chapter
                # directory
                os.chdir(os.path.dirname(path))
                # this alters the Pandoc document AST -- no return required
                contentfilter.convert_formulas('bilder', json_ast)
            except MathError as err:
                HtmlConverter.__handle_error(path, err)
            finally:
                os.chdir(cwd)

    def cleanup(self):
        remove_temp(self.template_path)

    def needs_update(self, path):
        # if file exists and input is newer than output, needs to be converted
        # again
        output = os.path.splitext(path)[0] + '.' + self.FILE_EXTENSION
        if not os.path.exists(output):
            return True
        # True if source file is newer:

        return os.path.getmtime(path) > os.path.getmtime(output)

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
def generate_page_navigation(file_path, file_cache, page_numbers, conf=None):
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
        '.' + conf[MetaInfo.Format]))
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
            'table of contents').title(), conf[MetaInfo.Format])

    if previous:
        chapternav = previous + '  ' + chapternav
    if nxt:
        chapternav += "  " + nxt
    # navigation at start of page
    nav_start = '{0}\n\n{1}\n\n* * * *\n\n\n'.format(chapternav, navbar)
    # navigation bar at end of page
    nav_end = '\n\n* * * *\n\n{0}\n\n{1}\n'.format(navbar, chapternav)
    return (nav_start, nav_end)
