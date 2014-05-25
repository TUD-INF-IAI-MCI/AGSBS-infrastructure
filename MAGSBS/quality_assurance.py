# This is free software licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2014 Sebastian Humenda <shumenda@gmx.de>

"""
This sub-module provides implementations for checking common lecture editing
errors.

There will be a global list of functions checking for one particular problem.
All functions take the text of a particular file and return a tuple with
(line_number, error_text_German)."""

import re, os, codecs
import MAGSBS.config as config
import MAGSBS.mparser as mparser
import MAGSBS.errors as errors
import MAGSBS.filesystem as filesystem

def common_latex_errors( text ):
    for num, line in enumerate( text.split('\n') ):
        # check whether cases environment is in $$ blah $$
        pos = line.find(r'\begin{cases}')
        if(pos >= 0):
            if(line[:pos].rfind('$$')>=0):
                continue
            elif(line[:pos].rfind(r"\(")>=0 or line[:pos].rfind(r"\\[")>=0):
                continue
            else:
                return (num+1, "Die mathematische Umgebung zur Fallunterscheidung (\\begin{cases} ... \\end{cases}) sollte in Displaymath gesetzt werden, d.h. doppelte Dollarzeichen anstatt ein Einzelnes sollten diese Umgebung umschließen. Dies erhält den Zeilenumbruch für den grafischen Alternativtext.") 

def page_number_is_paragraph(text):
    """Check whether all page numbers are on a paragraph on their own."""
    error_text = "Jede Seitenzahl muss in der Zeile darueber oder darunter eine Leerzeile haben, das heißt sie muss in einem eigenen Absatz stehen."
    paragraph_begun = True
    previous_line_pnum = False
    for num, line in enumerate(text.split('\n')):
        if(line.strip() == ''):
            paragraph_begun = True
            previous_line_pnum = False
        else:
            if(previous_line_pnum ): # previous_line_pnum and this is no empty line...
                previous_line_pnum = False
                return (num+1, error_text)
            elif(re.search(r'\|\|\s*' + config.PAGENUMBERING_REGEX, line.lower())):
                # line contains page number, is in front of a empty line?
                if(not paragraph_begun):
                    return (num+1, error_text)
                previous_line_pnum = True
            paragraph_begun = False # one line of text ends "paragraph begun"


def heading_is_paragraph(text):
    """Check whether all page numbers are on a paragraph on their own."""
    error_text = "Jede Ueberschrift muss in der Zeile darueber oder darunter eine Leerzeile haben, das heißt sie muss in einem eigenen Absatz stehen."
    paragraph_begun = True
    previous_line_heading = False
    for num, line in enumerate(text.split('\n')):
        if(line.strip() == ''):
            paragraph_begun = True
            previous_line_heading = False
        else:
            if(not paragraph_begun): # happens on the second line of a paragraph
                if(line.startswith('---') or line.startswith('===')):
                    previous_line_heading = True
                    continue
            if(previous_line_heading ): # previous_line_heading and this is no empty line...
                return (num+1, error_text)
            if(re.search(r'^#+.*', line.lower())):
                # line contains heading, is in front of a empty line?
                if(not paragraph_begun):
                    return (num+1, error_text)
                previous_line_heading = True
            paragraph_begun = False # one line of text ends "paragraph begun"

def level_one_heading(text):
    """Parse the document and raise errors if more than one level-1-heading was encountered."""
    try:
        m = mparser.simpleMarkdownParser( text, 'k01.md', 'k01.md')
        m.parse()
    except errors.StructuralError:
        return ('-', "In dem Dokument gibt es mehr als eine ueberschrift der Ebene 1. Dies ist nicht erlaubt. Beispielsweise hat jeder Foliensatz nur eine ueberschrift und auch ein Kapitel wird nur mit einer ueberschrift bezeichnet. Falls es doch mehrere große ueberschriften geben sollte, sollten diese auf eigene Kapitel oder Unterkapitel ausgelagert werden.")

def oldstyle_pagenumbering( text ):
    """Check whether the old page numbering style "###### - page xyz -" is used."""
    for num, line in enumerate( text.split('\n') ):
        obj = re.search(r'\s*######\s*-\s*(Seite|Slide|slide|page|Page|Folie)\s+(\d+)\s*-.*', line)
        if( obj ):
            return (num+1, 'Es wurde eine Seitenzahl im Format "###### - Seite xyz -" bzw. "###### - Seite xyz - ######" gefunden. dies ist nicht mehr erlaubt. Seitenzahlen muessen die Form "|| - Seite xyz -" haben.')

def page_numbering_text_is_lowercase( text ):
    for num, line in enumerate( text.split('\n') ):
        if(line.startswith('######') or line.startswith('||')):
            if(line.find('seite')>=0 or line.find('folie')>=0):
                return (num+1, 'Das Wort "Seite" wurde klein geschrieben. Dadurch wird es vom MAGSBS-Modul nicht erkannt, sodass keine automatische Seitennavigation erstellt werden kann.')

############################################

class Mistkerl():
    """Wrapper which wraps different levels of errors."""
    def __init__(self):
        self.__critical = [level_one_heading, page_number_is_paragraph,
                heading_is_paragraph, oldstyle_pagenumbering,
                page_numbering_text_is_lowercase, common_latex_errors]
        self.__warning = []
        self.__pedantic = [] # LaTeX stuff?
        self.__priority = 0
    def get_issues(self):
        issues = self.__critical
        if(self.get_priority() >= 1):
            issues += self.__warning
        if(self.get_priority() >= 2):
            issues += self.__pedantic
        return issues
    def set_priority(self, p):
        assert type(p) == int
        if(p < 0 or p > 2):
            raise ValueError("0 for critical, 1 for warning and 3 for pedantic allowed.")
        self.__prriority = p
    def get_priority(self): return self.__prriority
    def __iterate_errors(self, fn):
        """Iterate over all errors, amount depending of set priority."""
        output = []
        try:
            text = codecs.open( fn, "r", "utf-8" ).read()
        except UnicodeDecodeError:
            output.append('Datei ist nicht in UTF-8 kodiert, bitte waehle "UTF-8" als Zeichensatz im Editor.')
            return '\n'.join(output)
        text = text.replace('\r\n','\n').replace('\r','\n')
        for mistake in self.get_issues():
            data = mistake( text )
            if( data ):
                assert type(data) == tuple
                if(data[0] == '-'):
                    output.append( data[1] )
                else:
                    output.append( 'Zeile ' + str(data[0]) + ": " + data[1] )
        return (fn, output)

    def run( self, path ):
        """Take either a file and run checks or do the same for a directory
recursively."""
        output = {}
        if( os.path.isfile( path ) ):
            if( path.endswith('.md') ):
                fn, issues = self.__iterate_errors( path )
                output[ fn ] = issues
            else:
                print('Error: file name must end on ".md".')
                sys.exit( 127 )
        else:
            for directoryname, directory_list, file_list in filesystem.get_markdown_files( path ):
                for file in file_list:
                    fn, issues = self.__iterate_errors( os.path.join( directoryname, file) )
                    output[ fn ] = issues
        return output
