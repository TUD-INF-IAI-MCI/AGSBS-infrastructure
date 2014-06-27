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


def heading_is_paragraph(text, fn):
    """Check whether all page numbers are on a paragraph on their own. Also
    checks whether headings do NOT start with a number."""
    error_text = "Jede Ueberschrift muss in der Zeile darueber oder darunter eine Leerzeile haben, das heißt sie muss in einem eigenen Absatz stehen."
    error_text_number = "Die Überschriftsnummerierungen werden automatisch generiert und sollen daher nicht am Anfang der Überschrift stehen, sondern weggelassen werden."
    def check_numbering( num, line ):
        res = re.search(r"^(\#*)\s*(\d+\.?\d*)", line)
        if( res ):
            return (num+1, error_text_number)
    paragraph_begun = True
    previous_line_heading = False
    previous_line = ''
    for num, line in enumerate(text.split('\n')):
        if(line.strip() == ''):
            paragraph_begun = True
            previous_line_heading = False
        else:
            if(not paragraph_begun): # happens on the second line of a paragraph
                if(line.startswith('---') or line.startswith('===')):
                    res = check_numbering( num, previous_line )
                    if( res ): return (res[0]-1, res[1])
                    previous_line_heading = True
                    continue
            if(previous_line_heading ): # previous_line_heading and this is no empty line...
                return (num+1, error_text)
            if(re.search(r'^#+.*', line)):
                res = check_numbering( num, line )
                if( res ): return res
                # line contains heading, is in front of a empty line?
                if(not paragraph_begun):
                    return (num+1, error_text)
                previous_line_heading = True
            paragraph_begun = False # one line of text ends "paragraph begun"
        previous_line = line

def level_one_heading(text):
    """Parse the document and raise errors if more than one level-1-heading was encountered."""
    try:
        m = mparser.simpleMarkdownParser( text, 'k01.md', 'k01.md')
        m.parse()
    except errors.StructuralError:
        return ('-', "In dem Dokument gibt es mehr als eine ueberschrift der Ebene 1. Dies ist nicht erlaubt. Beispielsweise hat jeder Foliensatz nur eine ueberschrift und auch ein Kapitel wird nur mit einer ueberschrift bezeichnet. Falls es doch mehrere große ueberschriften geben sollte, sollten diese auf eigene Kapitel oder Unterkapitel ausgelagert werden.")

def oldstyle_pagenumbering( line ):
    """Check whether the old page numbering style "###### - page xyz -" is used."""
    obj = re.search(r'\s*######\s*-\s*(Seite|Slide|slide|page|Page|Folie)\s+(\d+)\s*-.*', line)
    if( obj ):
        return 'Es wurde eine Seitenzahl im Format "###### - Seite xyz -" bzw. "###### - Seite xyz - ######" gefunden. dies ist nicht mehr erlaubt. Seitenzahlen muessen die Form "|| - Seite xyz -" haben.'

def page_numbering_text_is_lowercase( line ):
    if(line.startswith('######') or line.startswith('||')):
        if(line.find('seite')>=0 or line.find('folie')>=0):
            return 'Das Wort "Seite" wurde klein geschrieben. Dadurch wird es vom MAGSBS-Modul nicht erkannt, sodass keine automatische Seitennavigation erstellt werden kann.'

def page_string_but_no_page_number( line ):
    """Sometimes one types "- page -" and forgets the digit."""
    if( not line.startswith("||") ): return None
    line = line.replace(" ", "")
    for t in config.PAGENUMBERINGTOKENS:
        idx = line.lower().find( t )
        if( idx >= 0 ):
            if( len(line) > idx + len( t ) ):
                if( not line[idx + len(t)].isdigit() ):
                    return "Wahrscheinlich wurde an dieser Stelle eine Seitenzahl notiert, bei der nach dem Wort die anschließende Nummer vergessen wurde."



############################################

class Mistkerl():
    """Wrapper which wraps different levels of errors."""
    def __init__(self):
        self.__oneliner = [oldstyle_pagenumbering,
                page_numbering_text_is_lowercase, page_string_but_no_page_number ]
        self._needs_file_name = [ heading_is_paragraph]
        self.__critical = [level_one_heading, page_number_is_paragraph,
                common_latex_errors ] + self.__oneliner + self._needs_file_name
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
    def get_priority(self): return self.__priority
    def __iterate_errors(self, fn):
        """Iterate over all errors, amount depending of set priority."""
        def format_output( data ):
            if(data[0] == '-'):
                return data[1]
            else:
                return 'Zeile ' + str(data[0]) + ": " + data[1]

        output = []
        try:
            text = codecs.open( fn, "r", "utf-8" ).read()
        except UnicodeDecodeError:
            output.append('Datei ist nicht in UTF-8 kodiert, bitte waehle "UTF-8" als Zeichensatz im Editor.')
            return '\n'.join(output)
        text = text.replace('\r\n','\n').replace('\r','\n')
        for mistake in self.get_issues():
            if mistake in self.__oneliner: continue
            if mistake in self._needs_file_name:
                data = mistake( text, fn )
            else:
                data = mistake( text )
            if( data ):
                assert type(data) == tuple
                output.append( format_output( data ) )
        already_checked = []
        for num, line in enumerate( text.split('\n') ):
            for mistake in self.get_issues():
                if mistake in self.__oneliner and not (mistake in already_checked):
                    data = mistake( line )
                    if( data ):
                        assert type(data) == str
                        output.append( format_output( (num+1, data ) ) )
                        already_checked.append( mistake )

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
            sortedFiles = filesystem.get_markdown_files( path,
                    all_markdown_files=True )
            sortedFiles = sorted( sortedFiles,
                    key=lambda x: x)
            for directoryname, directory_list, file_list in sortedFiles:
                for file in file_list:
                    fn, issues = self.__iterate_errors( os.path.join( directoryname, file) )
                    output[ fn ] = issues
        return output
