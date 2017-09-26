"""Output format formatters, currently only HTML."""
# vim: set expandtab sts=4 ts=4 sw=4:
# This is free software, licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2017 Sebastian Humenda <shumenda |at| gmx |dot| de>

import enum
import json
import os
import subprocess
import tempfile
from . import contentfilter
from .. import config, common, datastructures, errors, mparser


HTML_template = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
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
Each child should have constants called FILE_EXTENSION and PANDOC_FORMAT_NAME
(used for the file extension and the -t pandoc command line flag).

General usage:
>>> gen = MyGenerator(a_dictionary, language)
# method for children to implement (optional) things like template creation
>>> gen.setup() # needs to be called anyway
# convert json of document and write it to basefilename + '.' + format; may
# raises SubprocessError; the json is the Pandoc AST (intermediate file format)
>>> if gen.needs_update(path):
'''    ast = gen.convert(ast, title, path)
# clean up, e.g. deletion of templates. Should be executed even if gen.convert()
# threw an error
gen.cleanup()."""
    FILE_EXTENSION = 'None'
    PANDOC_FORMAT_NAME = 'plain'
    def __init__(self, meta, language):
        self.__meta = meta
        self.__language = language
        self.__conversion_profile = ConversionProfile.Blind

    def get_language(self):
        return self.__language

    def set_meta_data(self, data):
        self.__meta = data

    def get_meta_data(self):
        return self.__meta

    def setup(self):
        """Set up converter."""
        pass

    def convert(self, json_str, title, base_fn):
        """Read from JSON and return JSON, too.
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

    def set_profile(self, profile):
        self.__conversion_profile = profile

    def get_profile(self):
        return self.__conversion_profile

class HtmlConverter(OutputGenerator):
    """HTML output format generator. For documentation see super class;."""
    PANDOC_FORMAT_NAME = 'html'
    FILE_EXTENSION = 'html'

    def __init__(self, meta, language):
        super().__init__(meta, language)
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
        start_with_caps = lambda content: content[0].upper() + content[1:]
        data = HTML_template[:]
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
                    frames = '\n    '.join(frames),
                    boxes = '\n    '.join(boxes),
                    title = trans.get_translation("title"),
                    **meta)
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
        outputf = os.path.splitext(filename)[0] + '.' + self.FILE_EXTENSION
        pandoc_args = ['-s', '--template=%s' % self.template_path]
        # set title
        if title: # if not None
            pandoc_args += ['-V', 'pagetitle:' + title, '-V', 'title:' + title]
        # check whether "Math" occurs and therefore if GladTeX needs to be run
        use_gladtex = True in contentfilter.json_ast_filter(json_ast,
                contentfilter.has_math)
        if use_gladtex and self.get_profile() is ConversionProfile.Blind:
            outputf = os.path.splitext(filename)[0] + '.htex'
            pandoc_args.append('--gladtex')
        if self.get_profile() is ConversionProfile.VisuallyImpairedDefault:
            pandoc_args.append('--mathjax')
        execute(['pandoc'] + pandoc_args + ['-t', self.PANDOC_FORMAT_NAME, '-f','json',
            '+RTS', '-K25000000', '-RTS', # increase stack size
            '-o', outputf], stdin=json.dumps(json_ast), cwd=dirname)
        if use_gladtex and self.get_profile() is ConversionProfile.Blind:
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
            with open(file_path, 'r', encoding='utf-8') as f:
                paragraphs = mparser.rm_codeblocks(mparser.file2paragraphs(
                    f.read().split('\n')))
                formulas = mparser.parse_formulas(paragraphs)
            try:
                pos = list(formulas.keys())[number-1]
            except IndexError:
                # if improperly closed maths environments eixst, formulas cannot
                # be counted; although there's somewhere a LaTeX error which
                # we're trying to report, the improper maths environments HAVE
                # to reported and fixed first
                raise errors.SubprocessError(error.command, ("LaTeX reported an error "
                    "while converting a fomrula. Unfortunately, improperly closed "
                    "maths environments exist, therefore it cannot be determined "
                    "which formula was errorneous. Please re-read the document "
                    "and fix any unclosed maths environments."), file_path)

            # get LaTeX error output
            msg = details['Message'].rstrip().lstrip()
            msg = 'formula: {}\n{}'.format(list(formulas.values())[number-1], msg)
            e = errors.SubprocessError(error.command, msg, path=file_path)
            e.line = '{}, {}'.format(*pos)
            return e
        else:
            return error

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
            #pylint: disable=redefined-variable-type
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

def remove_temp(fn):
    if fn is None: return
    if os.path.exists(fn):
        try:
            os.remove( fn )
        except OSError:
            common.WarningRegistry().register_warning(
            "Couldn't remove tempfile", path=fn)


