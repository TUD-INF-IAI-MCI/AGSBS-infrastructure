# vim: set expandtab sts=4 ts=4 sw=4:
"""
This module abstracts everything related to calling pandoc and modifiying the
template for additional meta data in the output document(s).

Converter to different output formats can be easily added by adding the class to
the field converters of the pandoc class.
"""

import html, re, json
import tempfile, os, sys, subprocess
from . import config
from . import contentfilter
from . import filesystem
from . import mparser

HTML_template = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml"$if(lang)$ lang="$lang$" xml:lang="$lang$"$endif$>
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
  <meta http-equiv="Content-Style-Type" content="text/css" />
  <meta name="generator" content="pandoc" />
  <meta name="author" content="$$SourceAuthor" />
$if(date-meta)$
  <meta name="date" content="$date-meta$" />
$endif$
  <title>$$title</title>
  <style type="text/css">code{white-space: pre;}</style>
$if(highlighting-css)$
  <style type="text/css">
$highlighting-css$
  </style>
$endif$
$for(css)$
  <link rel="stylesheet" href="$css$" $if(html5)$$else$type="text/css" $endif$/>
$endfor$
$if(math)$
  $math$
$endif$
$for(header-includes)$
  $header-includes$
$endfor$
<!-- agsbs-specific -->
    <meta name='Einrichtung' content='$$institution' />
    <meta href='Arbeitsgruppe' content="$$workinggroup" />
    <meta name='Vorlagedokument' content='$$source' />
    <meta name='Lehrgebiet' content='$$lecturetitle' />
    <meta name='Semester der Bearbeitung' content='$$semesterofedit' />
    <meta name='Bearbeiter' content='$$editor' />
</head>
<body>
$for(include-before)$
$include-before$
$endfor$
$if(title)$
<div id="$idprefix$header">
<h1 class="title">$title$</h1>
$for(author)$
<h2 class="author">$author$</h2>
$endfor$
$if(date)$
<h3 class="date">$date$</h3>
$endif$
</div>
$endif$
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
    if fn == None: return
    if os.path.exists(fn):
        try:
            os.remove( fn )
        except OSError:
            sys.stderr.write("Error, couldn't remove tempfile %s.\n" % fn)

def execute(args, stdin=None):
    """Convenience wrapper to subprocess.Popen). It'll append the process' stderr
    to the message from the raised exception. Returned is the unicode stdout
    output of the program. If stdin=some_value, a pipe to the child is opened
    and the argument passed."""
    decode = lambda x: x.decode(sys.stdout.encoding)
    if stdin:
        proc = subprocess.Popen(args, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, stdin=subprocess.PIPE)
        text = proc.communicate(stdin.encode(sys.stdin.encoding))
    else:
        try:
            proc = subprocess.Popen(args, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
            text = proc.communicate()
            ret = proc.wait()
            if ret:
                msg = '\n'.join(map(decode, text))
                raise subprocess.SubprocessError(' '.join(args) + ': ' + msg)
        except FileNotFoundError as e:
            raise subprocess.SubprocessError(e)
    return decode(text[0])

class OutFilter():
    """If desired, you can here add functionality to alter the generated source.
Please note: this code will be highly pandoc-version-dependend, since
post-processing auto-generated data is likely to fail as soon as the pandoc
generator fails."""
    def __init__(self, format, inputf):
        self.__supported = ['html']
        self.format = format
        self.inputf = inputf
        if(not (format in self.__supported)):
            self.noop()
        else:
            self.filter_html()
    def noop(self):    pass
    def filter_html(self):
        """Images will be in a extra div with a caption - remove that."""
        data = open(self.inputf, 'r', encoding='utf-8').read()
        while( (data.find('<div class="figure">')>=0)):
            pos = data.find('<div class="figure">')
            data = data[:pos] + '<p>' + data[pos + len('<div class="figure">') : ]
            div_end = data[pos:].find('</div>') + pos
            p_start = data[pos:].find('<p class="caption">') + pos
            p_end = data[p_start:].find('</p>') + p_start
            if(div_end == -1 or p_start == -1 or p_end == -1 or
                    p_start > div_end):
                #raise ValueError("Something is wrong in the HTML file, p and diff tag in wrong order?")
                pass # Todo: nicer solution anyway
            data = data[:p_start] + data[p_end+len('</p>'):]
            div_end = data[pos:].find('</div>')
            if(div_end == -1):
                #raise ValueError('no matching </div> for image div block')
                break # just skip this file
            else:
                div_end += pos
                data = data[:div_end] + '</p>' +data[div_end + 6 :]
        open(self.inputf, 'w', encoding='utf-8').write( data )

class OutputGenerator():
    """Base class for all converters to provide a common type.

General usage:
gen = MyGenerator()
# Supply optional dictionary of meta information. Some converter might require
# that step.
gen.set_meta_data(dict)
# step for children to implement (optional) things like template creation
gen.setup()
# convert json of document and write it to basefilename + '.' + format; may
# throw SubprocessError
gen.convert(json, title, basefilename)
# clean up, e.g. deletion of templates. Should be xecuted even if gen.convert()
# threw error
gen.cleanup()."""
    def __init__(self):
        self.__meta = {}
        self.format = '.html'

    def set_format(self, fmt):
        self.format = fmt

    def get_format(self):
        return self.format

    def set_meta_data(self, data):
        self.__meta = data

    def get_meta_data(self):
        return self.__meta

    def get_output_file_name(self, base_fn):
        return base_fn + '.' + self.get_format()

    def setup(self):
        pass

    def convert(self, json_str, title, base_fn):
        """The actual conversion process.
        json_str: json representation of the documented, encoded as string
        title: title of document
        base_fn: file path without file extension and dot."""
        pass

    def cleanup(self):
        pass

class HtmlConverter(OutputGenerator):
    """HTML output format generator. For documentation see super class;."""
    format = 'html'
    def __init__(self):
        super().__init__()
        super().set_format('html')
        self.template_path = None
        self.template_copy = ''

    def setup(self):
        data = HTML_template[:]
        for key, value in self.get_meta_data().items():
            if value == None:
                continue
            data = data.replace('$$'+key, html.escape( value ))
        self.template_path = tempfile.mktemp() + '.html'
        self.template_copy = data[:]
        open(self.template_path, "w", encoding="utf-8").write(data)

    def update_title_in_template(self, title):
        self.template_copy = re.sub('(<title>).*?(</title>)', r'\1%s\2' % title,
                self.template_copy)
        open(self.template_path, "w", encoding="utf-8").write(self.template_copy)

    def convert(self, jsonstr, title, base_name):
        """See super class documentation."""
        outputf = self.get_output_file_name(base_name)
        pandoc_args = ['-s', '--template=%s' % self.template_path]
        use_gladtex = False
        # filter json and give it as input to pandoc
        # check whether "Math" occurs and therefore if GladTeX needs to be run
        need_gladtex = contentfilter.pandoc_ast_parser( jsonstr,
                contentfilter.has_math)
        if type(need_gladtex) == list and len(need_gladtex) != 0:
            use_gladtex = need_gladtex[0]
            outputf = base_name + '.htex'
            pandoc_args.append('--gladtex')
        self.update_title_in_template(title)
        execute(['pandoc'] + pandoc_args + ['-t', super().get_format(), '-f','json',
            '-o', outputf], stdin=jsonstr)
        if use_gladtex:
            try:
                execute(["gladtex", "-a", "-d", "bilder", outputf])
            except:
                raise
            finally: # remove GladTeX .htex file
                if use_gladtex:
                    remove_temp(base_name + '.htex')

    def cleanup(self):
        remove_temp(self.template_path)

class pandoc():
    """Abstract the translation by pandoc into a class which add meta-information
to the output, handles errors and checks for the correct encoding."""
    def __init__(self):
        self.converters = [HtmlConverter]
        c = config.confFactory()
        self.conf = c.get_conf_instance()
        supported_formats = [f.format for f in self.converters]
        format = self.conf['format']
        if not format in supported_formats:
            raise ValueError("The configured format " + format + ' is not ' +
                    'supported" at the moment. Supported formats: ' +
                    ', '.join(supported_formats))
        self.format = format
        self.converter_class = None
        for c in self.converters:
            if c.format == format:
                self.converter_class = c
                break
        self.__hvalues = {
                'editor' : self.conf['editor'],
                'SourceAuthor' : self.conf['SourceAuthor'],
                'workinggroup': self.conf['workinggroup'],
                'institution': self.conf['institution'],
                'source': self.conf['source'],
                'lecturetitle': self.conf['lecturetitle'],
                'semesterofedit': self.conf['semesterofedit'],
                'title':None}

    def set_workinggroup(self, group):
        self.__hvalues['workinggroup'] = group
    def set_source(self, source):
        self.__hvalues['source'] = source
    def set_editor(self, editor):
        self.__hvalues['editor'] = editor
    def set_institution(self, institution):
        self.__hvalues['institution'] = institution
    def set_lecturetitle(self, subject):
        self.__hvalues['lecturetitle'] = subject
    def set_semesterofedit(self, date):
        self.__hvalues['semesterofedit'] = date

    def __guess_title(self, document):
        """Guess the title from the first heading and return it."""
        paragraphs = filesystem.file2paragraphs(document)
        headings = mparser.headingExtractor(paragraphs, 1)
        return (headings[0].get_text() if headings else 'UNKNOWN')

    def convert_files(self, files):
        """Convert a list of files. They should share all the meta data, except
        for the title."""
        conv = self.converter_class()
        conv.set_meta_data(self.__hvalues)
        conv.setup()
        try:
            for file_name in files:
                dot = file_name.rfind('.')
                base_name = (file_name[:dot]  if dot > 0  else file_name)
                document = open(file_name, encoding='utf-8').read()
                title = self.__guess_title(document)
                # pre-filter document, to replace all inline math environments
                # through displaymath environments
                mathfilter = contentfilter.InlineToDisplayMath(document)
                mathfilter.parse()
                document = mathfilter.get_document()
                json_ast = self.load_json(document)
                filters = [contentfilter.page_number_extractor]
                # modify ast, recognize page numbers
                for filter in filters:
                    json_ast = contentfilter.jsonfilter(json_ast, filter,
                            self.conf['format'] )
                conv.convert(json.dumps(json_ast), title, base_name)
        except:
            raise
        finally:
            conv.cleanup()

    def convert_file(self, inputf):
        self.convert_files([inputf])

    def load_json(self, document):
        """Load JSon input from ''inputf`` and return a reference to the loaded
        object."""
        # run pandoc, read in the JSon output
        js = execute(['pandoc', '-f', 'markdown', '-t', 'json'], stdin=document)
        return json.loads(js)

