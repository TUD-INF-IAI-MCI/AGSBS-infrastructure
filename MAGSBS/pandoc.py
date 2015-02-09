# vim: set expandtab sts=4 ts=4 sw=4:
"""
This module abstracts everything related to calling pandoc and modifiying the
template for additional meta data in the output document(s)."""

import datetime, tempfile
import html
import os, sys, subprocess
from . import config
from . import mparser
from . import contentfilter
from .errors import SubprocessError, WrongFileNameError, FileNotFoundError

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
    if(fn == None): return
    if( os.path.exists(fn)):
        os.remove( fn )

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

class pandoc():
    """Abstract the translation by pandoc into a class which add meta-information
to the output, handles errors and checks for the correct encoding."""
    def __init__(self, use_gladtex=False):
        c = config.confFactory()
        self.conf = c.get_conf_instance()
        self.format = self.conf['format']
        self.tempfile = None
        self.use_gladtex = use_gladtex
        self.__hvalues = {
                'editor' : self.conf['editor'],
                'SourceAuthor' : self.conf['SourceAuthor'],
                'workinggroup': self.conf['workinggroup'],
                'institution': self.conf['institution'],
                'source': self.conf['source'],
                'lecturetitle': self.conf['lecturetitle'],
                'semesterofedit': self.conf['semesterofedit'],
                'title':None}

    def set_title(self, title):
        """set_title(title) - set title for document
In some cases, the lecture title / the level-1-heading is not sufficient for the
title of the document, hence allow setting it separately."""
        self.__hvalues['title'] = title
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

    def __guess_title(self, inputf):
        try:
            mp = mparser.simpleMarkdownParser(
                    open(inputf, 'r', encoding='utf-8').read(),
                    os.path.split(inputf)[0], os.path.split(inputf)[1])
            mp.parse()
            mp.fetch_headings()
            hs = mp.get_headings()
            for h in hs:
                if(h.get_level() == 1):
                    return h.get_text()
            return inputf[:-3].capitalize()
        except WrongFileNameError:
            return inputf[:-3].capitalize()


    def mktemplate(self, inputf):
        if(self.format != 'html'):
            raise NotImplementedError("Only HTML is supported currently.")
        return self.mktemplate_html(inputf)

    def mktemplate_html(self, inputf):
        assert inputf != bytes
        # is file name unicode?

        # adjust semesterofedit and title:
        if(not self.__hvalues['semesterofedit']):
            self.__hvalues['semesterofedit'] = datetime.datetime.now().strftime('%m/%Y')
        if(not self.__hvalues['title']):
            self.__hvalues['title'] = self.__guess_title(inputf)
        # filter configuration variables whether one is None
        if(list(filter(lambda x: x==None, self.__hvalues.values())) != []):
            print(repr(self.__hvalues))
            raise ValueError("One of the required fields for the HTML meta data has not been set.")
        data = HTML_template[:]
        for key, value in self.__hvalues.items():
            data = data.replace('$$'+key, html.escape( value ))
        self.tempfile = tempfile.mktemp() + '.html'
        open(self.tempfile, "w", encoding="utf-8").write(data)
        return self.tempfile

    def convert(self, inputf):
        if(self.format != 'html'):
            raise NotImplementedError("Only HTML output is supported currently.")
        else:
            try:
                self.convert_html(inputf)
            except FileNotFoundError:
                raise SubprocessError("Pandoc not found. Make sure it is in the PATH environment variable.")
        # ToDo: make me a real pandoc filter
        OutFilter(self.format, inputf[:inputf.rfind('.')]+'.'+self.format)

    def convert_html(self, inputf):
        """convert_html(inputf) -> write to inputf.html
Convert inputf to outputf. raise OSError if either pandoc  has not been found or
it gave an error return code"""
        # strip .md, construct the output file name (different when using
        # GladTeX)
        inputfStripped = inputf[:inputf.rfind('.')]
        if(self.use_gladtex):
            outputf = inputfStripped + '.htex'
        else:
            outputf = inputfStripped + '.' + self.format
        template = self.mktemplate(inputf)
        pandoc_args = ['-s', '--template=%s' % template ]
        if(self.use_gladtex):
            pandoc_args.append('--gladtex')

        # run pandoc, read in the JSon output
        proc = subprocess.Popen(['pandoc'] + pandoc_args + \
                ['-t','json', inputf],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        text = proc.communicate()
        JSon = text[0].decode( sys.getdefaultencoding() )
        ret = proc.wait()
        if(ret): # if ret != 0, error; clean up
            remove_temp( self.tempfile)
            print('\n'.join(text))
            raise OSError("Pandoc gave error status %s." % ret)

        # filter json and give it as input to pandoc
        JSon = contentfilter.jsonfilter( JSon,
                contentfilter.page_number_extractor, self.conf['format'] )
        # check whether "Math" occurs and therefore if GladTeX needs to be run
        if( not self.use_gladtex ): # only check if GladTeX is not selected yet
            need_gladtex = contentfilter.pandoc_ast_parser( JSon,
                contentfilter.has_math)
            if( type(need_gladtex) == list and len(need_gladtex) != 0):
                self.use_gladtex = need_gladtex[0]
                outputf = inputfStripped + '.htex'
                pandoc_args.append('--gladtex')
        JSon = JSon.encode( sys.getdefaultencoding() )
        proc = subprocess.Popen(['pandoc'] + pandoc_args + \
                ['-t', self.conf['format'], '-f','json', '-o', outputf],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        data = proc.communicate( JSon )
        ret = proc.wait()
        if(ret):
            remove_temp( self.tempfile)
            print('\n'.join([e.decode( sys.getdefaultencoding() )
                    for e in data]))
            raise OSError("Pandoc gave error status %s." % ret)
        remove_temp( self.tempfile)

        if(self.use_gladtex):
            # read in the generated file. Its a dirt-fix: pandoc strips newlines
            # from equations, try to get some back
            data = open(outputf, 'r', encoding='utf-8').read()
            data = data.replace('\\\\', '\\\\\n')
            open(outputf, 'w', encoding='utf-8').write( data )
            try:
                proc = subprocess.Popen(['gladtex'] + \
                        self.conf['GladTeXopts'].split(' ') + [outputf],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except OSError:
                raise SubprocessError("Either GladTeX is not installed or not in the search path.")
            text = proc.communicate()
            ret = proc.wait()
            if(ret):
                raise SubprocessError(text[1].decode( sys.getdefaultencoding()))
            os.remove( outputf )

