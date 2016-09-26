#] vim: set expandtab sts=4 ts=4 sw=4:
# This is free software, licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2016 Sebastian Humenda <shumenda |at| gmx |dot| de>
"""
This module abstracts everything related to calling pandoc and modifiying the
template for additional meta data in the output document(s).

Converter to different output formats can be easily added by adding the class to
the field converters of the pandoc class.
"""
#pylint: disable=multiple-imports

import json
import os
import re
import subprocess, sys
import tempfile
from . import config
from . import common
from . import contentfilter
from . import datastructures
from . import errors
from . import filesystem
from . import mparser

HTML_template = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml"$if(lang)$ lang="$lang$" xml:lang="$lang$"$endif$>
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
  <meta name="author" content="{sourceAuthor}" />
$if(date-meta)$
  <meta name="date" content="$date-meta$" />
$endif$
  <title>$if(title-prefix)$$title-prefix$ - $endif$$pagetitle$</title>
  <style type="text/css">
    code {{ white-space: pre; }}
    .underline {{ text-decoration: underline }}
    .frame {{ border:1px solid #000000; }}
    .annotation {{ border:2px solid #000000; background-color: #FCFCFC; }}
    .annotation:before {{ content: "{annotation}: "; }}
    table, th, td {{ border:1px solid #000000; }}
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
  <meta name='Einrichtung' content='{institution}' />
  <meta href='Arbeitsgruppe' content='{workinggroup}' />
  <meta name='Vorlagedokument' content='{source}' />
  <meta name='Lehrgebiet' content='{lecturetitle}' />
  <meta name='Semester der Bearbeitung' content='{semesterofedit}' />
  <meta name='Bearbeiter' content='{editor}' />
</head>
<body lang="{language}">
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


def remove_temp(fn):
    if fn is None: return
    if os.path.exists(fn):
        try:
            os.remove( fn )
        except OSError:
            sys.stderr.write("Error, couldn't remove tempfile %s.\n" % fn)

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
        msg = str(args[0]) + ': ' + str(e + ' ' + str(text))
        raise errors.SubprocessError(args, msg)
    if not proc:
        raise ValueError("No subprocess handle exists, even though it " + \
                "should. That's a bug to be reported.")
    ret = proc.wait()
    if ret:
        msg = '\n'.join(map(datastructures.decode, text))
        raise errors.SubprocessError(args, msg)
    return datastructures.decode(text[0])


class OutputGenerator():
    """Base class for document output generators. They usually call pandoc (and
optionally additional programs) to convert source files into a target format.

General usage:
gen = MyGenerator(a_dictionary, language)
# method for children to implement (optional) things like template creation
gen.setup() # needs to be called anyway
# convert json of document and write it to basefilename + '.' + format; may
# raises SubprocessError; the json is the Pandoc AST (intermediate file format)
if gen.needs_update(path):
    gen.convert(json, title, path)
# clean up, e.g. deletion of templates. Should be executed even if gen.convert()
# threw an error
gen.cleanup()."""
    def __init__(self, meta, language):
        self.__meta = meta
        self.__language = language
        self.format = '.html'

    def get_language(self):
        return self.__language

    def set_format(self, fmt):
        self.format = fmt

    def get_format(self):
        return self.format

    def set_meta_data(self, data):
        self.__meta = data

    def get_meta_data(self):
        return self.__meta


    def setup(self):
        """Set up converter."""
        pass

    def convert(self, json_str, title, base_fn):
        """The actual conversion process.
        json_str: json representation of the documented, encoded as string
        title: title of document
        path: path to file"""
        pass

    def cleanup(self):
        pass

    def needs_update(self, path):
        """Returns True, if the given file needs to be converted again. If i.e.
        the output file is newer than the input (MarkDown) file, no conversion
        is necessary."""
        raise NotImplementedError()



class HtmlConverter(OutputGenerator):
    """HTML output format generator. For documentation see super class;."""
    format = 'html'

    def __init__(self, meta, language):
        super().__init__(meta, language)
        super().set_format('html')
        self.template_path = None
        self.template_copy = HTML_template[:] # in-memory copy of current template to be written when required

    def setup(self):
        """Set up the HtmlConverter. Prepare the template for later use."""
        self.template_path = tempfile.mktemp() + '.html'
        self.template_copy = self.get_template()
        with open(self.template_path, "w", encoding="utf-8") as f:
            f.write(self.template_copy)

    def get_template(self):
        """Construct template."""
        data = HTML_template[:]
        meta = self.get_meta_data()
        if 'title' in meta:
            meta.pop('title') # title should not be replaced

        # get translator object to translate certain phrases according to
        # configured language
        trans = config.Translate()
        trans.set_language(super().get_language())
        annotation = trans.get_translation('note of editor')
        if annotation[0].islower(): # capitalize _first_ character
            annotation = annotation[0].upper() + annotation[1:]

        try:
            return data.format(annotation=annotation, **meta)
        except KeyError as e:
            raise errors.ConfigurationError(("The key %s is missing in the "
                "configuration.") % e.args[0], meta['path'])

    def set_meta_data(self, meta):
        """Overwrite parent settr to re-generate template generation."""
        super().set_meta_data(meta)
        self.setup()

    def convert(self, json_ast, title, path):
        """See super class documentation."""
        dirname, filename = os.path.split(path)
        outputf = os.path.splitext(filename)[0] + '.' + self.get_format()
        pandoc_args = ['-s', '--template=%s' % self.template_path]
        # set title
        if title: # if not None
            pandoc_args += ['-V', 'pagetitle:' + title, '-V', 'title:' + title]
        # check whether "Math" occurs and therefore if GladTeX needs to be run
        use_gladtex = True in contentfilter.json_ast_filter(json_ast,
                contentfilter.has_math)
        if use_gladtex:
            outputf = os.path.splitext(filename)[0] + '.htex'
            pandoc_args.append('--gladtex')
        execute(['pandoc'] + pandoc_args + ['-t', super().get_format(), '-f','json',
            '-o', outputf], stdin=json.dumps(json_ast), cwd=dirname)
        if use_gladtex:
            try:
                execute(["gladtex", "-R", "-n", "-m", "-a", "-d", "bilder",
                    outputf], cwd=dirname)
            except errors.SubprocessError as e:
                raise self.__handle_gladtex_error(e, filename, dirname)
            else: # remove GladTeX .htex file
                remove_temp(os.path.join(dirname, outputf))

    def cleanup(self):
        remove_temp(self.template_path)

    def __handle_gladtex_error(self, error, file_path, dirname):
        """Retrieve formula position from GladTeX' error output, match it
        against the formula of the Markdown document and report it to the
        user.
        Note: file_path is relative to dirname, so both is required."""
        try:
            output = dict(line.split(': ', 1) for line in error.message.split('\n')
                if ': ' in line)
        except ValueError as e:
            # output was not formatted as expected, report that
            msg = "couldn't parse GladTeX output: %s\noutput: %s" % \
                (str(e), error.message)
            return errors.SubprocessError(error.command, msg, path=dirname)
        if output and 'Number' in output and 'Message' in output:
            number = int(output['Number'])
            with open(os.path.join(dirname, file_path), 'r', encoding='utf-8') as f:
                paragraphs = mparser.remove_codeblocks(mparser.file2paragraphs(
                    f.read().split('\n')))
                formulas = mparser.parse_formulas(paragraphs)
            pos = list(formulas.keys())[number-1]
            # get LaTeX error output
            msg = output['Message'].rstrip().lstrip()
            msg = 'formula: {}\n{}'.format(list(formulas.values())[number-1], msg)
            e = errors.SubprocessError(error.command, msg, path=dirname)
            e.line = '{}, {}'.format(*pos)
            raise e
        else:
            return error

    def needs_update(self, path):
        # if file exists and input is newer than output, needs to be converted
        # again
        output = os.path.splitext(path)[0] + '.' + self.get_format()
        if not os.path.exists(output):
            return True
        # True if source file is newer:
        return os.path.getmtime(path) > os.path.getmtime(output)


class Pandoc:
    """Abstract the translation by pandoc into a class which add meta-information
to the output, handles errors and checks for the correct encoding.
The parameter `format` can be supplied to override the configured output format.
"""
    # json content filters:
    CONTENT_FILTERS = [contentfilter.page_number_extractor,
                    contentfilter.suppress_captions]
    IS_CHAPTER = re.compile(r'^[a-z|A-Z]\d+\.md$')

    def __init__(self, conf=None):
        self.converters = [HtmlConverter]
        self.__conf = (config.confFactory().get_conf_instance(os.getcwd())
                if not conf else conf)
        self.__meta_data = {
                'editor' : self.__conf['editor'],
                'sourceAuthor' : self.__conf['sourceAuthor'],
                'workinggroup': self.__conf['workinggroup'],
                'institution': self.__conf['institution'],
                'source': self.__conf['source'],
                'lecturetitle': self.__conf['lecturetitle'],
                'semesterofedit': self.__conf['semesterofedit'],
                'path': 'None',
                'language': 'en'}

    def get_formatter_for_format(self, format):
        """Get converter object."""
        try:
            return next(filter(lambda converter: converter.format == format,
                self.converters))(self.__meta_data, self.__conf['language']) # get new instance
        except StopIteration:
            supported_formats = ', '.join(map(lambda c: c.format, self.converters))
            raise NotImplementedError(("The configured format {} is not "
                "supported at the moment. Supported formats: {}").format(
                format, supported_formats))

    def __update_metadata(self, conf):
        """Set latest meta data from given configuration."""
        self.__meta_data = {
                'editor' : conf['editor'],
                'sourceAuthor' : conf['sourceAuthor'],
                'workinggroup': conf['workinggroup'],
                'institution': conf['institution'],
                'source': conf['source'],
                'lecturetitle': conf['lecturetitle'],
                'semesterofedit': conf['semesterofedit'],
                'title': None,
                'language': conf['language'],
                'path': conf.get_path()}

    def get_lecture_root(self, some_file):
        """Return lecture root for a file or raise exception if it cannot be
        determined."""
        path = os.path.abspath(some_file)
        if os.path.isfile(path):
            path = os.path.split(path)[0]
        is_fs_root = lambda path: os.path.dirname(path) == path
        while path and not is_fs_root(path) and not common.is_lecture_root(path):
            path = os.path.split(path)[0]
        if path:
            return path
        else:
            raise errors.StructuralError(("Could not guess the lecture root "
                "for this file"), path)

    def convert_files(self, files):
        """Convert a list of files. They should share all the meta data, except
        for the title. All files must be part of one lecture.
        `files` can be either a cache object or a list of files to convert."""
        if isinstance(files, str):
            raise TypeError("list or tuple of files required.")
        elif isinstance(files, datastructures.FileCache):
            cache = files
            files = cache.get_all_files()
        else:
            fw = filesystem.FileWalker(self.get_lecture_root(files[0]))
            cache = datastructures.FileCache(fw.walk())
        converter = None # outer scope for finally
        try:
            c = config.confFactory()
            conf = None
            converter = None
            for file_name in files:
                # get correct configuration for each file
                newconf = c.get_conf_instance(os.path.dirname(file_name))
                # get new converter (and template) if config changes
                if not newconf == conf:
                    conf = newconf
                    self.__update_metadata(conf)
                    converter = self.get_formatter_for_format(conf['format'])
                    converter.set_meta_data(self.__meta_data)
                    converter.setup()
                self.__convert_document(file_name, cache, converter, conf)
        except errors.MAGSBS_error as e:
            # set path for error
            if not e.path:
                e.path = os.path.abspath(file_name)
            raise e
        finally:
            if converter:
                converter.cleanup()

    def __convert_document(self, path, file_cache, converter, conf):
        """Convert a document by a given path. It takes a converter which takes
        actual care of the underlying format. The filecache caches the list of
        files in the lecture. The list of files within a lecture is required to
        build navigation links.
        This function also inserts a page navigation bar to navigate between
        chapters and the table of contents."""
        # if output file name exists and is newer than the original, it doesn need to be converted again
        if not converter.needs_update(path):
            return
        with open(path, 'r', encoding='utf-8') as f:
            document = f.read()
        if not document:
            return # skip empty documents
        ## ToDo: rethink: is it better to parse pandoc ast or use own mparser
        ## for pnum extraction? Own pnum extraction does a lot of string splitting
        ## while splitting document into paragraphs
        if self.IS_CHAPTER.search(os.path.split(path)[-1]):
            nav_start, nav_end = generate_page_navigation(path, file_cache,
                    mparser.extract_page_numbers_from_par(mparser.file2paragraphs(document)))
            document = remove_nav(document) # remove old style nav bar from document
            document = '{}\n\n{}\n\n{}\n'.format(nav_start, document, nav_end)
        json_ast = self.load_json(document)
        # add MarkDown extensions with Pandoc filters
        for filter in Pandoc.CONTENT_FILTERS:
            json_ast = contentfilter.jsonfilter(json_ast, filter,
                    conf['format'])
        converter.convert(json_ast,
                contentfilter.get_title(json_ast),
                path)

    def load_json(self, document):
        """Load JSon input from ''inputf`` and return a reference to the loaded
        json document tree."""
        return contentfilter.text2json_ast(document)

# ToDo: marked for REMOVAL
def remove_nav(page):
    """remove_nav(page)
Remove navigation bar at top and bottom of document, if any. The navigation bar
must start with
    <!-- page navigation; DO NOT EDIT UNTIL end page navigation"! OTHERWISE DATA IS LOST! -->'

and end again with
    <!-- end page navigation -->"""
    NAVIGATION_END = '<!-- end page navigation -->'
    NAVIGATION_BEGIN = '<!-- page navigation; DO NOT EDIT UNTIL ' + \
                '"end page navigation"! OTHERWISE DATA IS LOST! -->'

    navbar_started = False
    newpage = []
    for line in page.split('\n'):
        if line.find(NAVIGATION_BEGIN[:16]) >= 0:
            navbar_started = True
        elif navbar_started and (line.find(NAVIGATION_END) >= 0):
            navbar_started = False
        else:
            if not navbar_started:
                newpage.append( line )
    return '\n'.join(newpage)


#pylint: disable=redefined-variable-type,too-many-locals
def generate_page_navigation(file_path, file_cache, page_numbers, conf=None):
    """generate_page_navigation(path, file_cache, page_numbers, conf=None)
    Generate the page navigation for a page. The file path must be relative to
    the lecture root. The file cache must be the datastructures.FileCache, the
    page numbers must have the format of mparser.extract_page_numbers_from.
    `conf=` should not be used, it is intended for testing purposes.
    Returned is a tuple with the start and the end navigation bar. The
    navigation bar itself is a string.
    """
    if not os.path.exists(file_path):
        print('jo',file_path, os.getcwd())
        raise errors.StructuralError("File doesn't exist", file_path)
    if not file_cache:
        raise ValueError("Cache with values may not be null")
    if not conf:
        conf = config.confFactory().get_conf_instance(os.path.split(file_path)[0])
    trans = config.Translate()
    trans.set_language(conf['language'])
    relative_path = os.sep.join(file_path.rsplit(os.sep)[-2:])
    previous, next = file_cache.get_neighbours_for(relative_path)
    make_path = lambda path: '../{}/{}'.format(path[0], path[1].replace('.md',
        '.' + conf['format']))
    if previous:
        previous = '[{}]({})'.format(trans.get_translation('previous').title(),
                make_path(previous))
    if next:
        next = '[{}]({})'.format(trans.get_translation('next').title(), make_path(next))
    for index, (line, _x, number_str) in enumerate(page_numbers):
        try:
            page_numbers[index] = int(number_str)
        except ValueError:
            raise errors.FormattingError("cannot recognize page number on %d as number"\
                            % line, number_str, file_path)

    navbar = []
    if page_numbers:
        navbar.append(trans.get_translation('pages').title() + ': ')
        for num in range(0, page_numbers[-1], conf['pageNumberingGap']):
            if num in page_numbers:
                navbar.append('[[{0}]](#p{0}), '.format(num))
        navbar[-1] = navbar[-1][:-2] # strip ", " from last chunk
    navbar = ''.join(navbar)
    chapternav = '[{}](../inhalt.{})'.format(trans.get_translation(
            'table of contents').title(), conf['format'])

    if previous:
        chapternav = previous + '  ' + chapternav
    if next:
        chapternav += "  " + next
    # navigation at start of page
    nav_start = '{0}\n\n{1}\n\n* * * *\n\n\n'.format(chapternav, navbar)
    # navigation bar at end of page
    nav_end = '\n\n* * * *\n\n{0}\n\n{1}\n'.format(navbar, chapternav)
    return (nav_start, nav_end)


