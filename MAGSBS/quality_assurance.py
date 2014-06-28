# This is free software licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2014 Sebastian Humenda <shumenda@gmx.de>

"""
ToDo: rewrite me
This sub-module provides implementations for checking common lecture editing
errors.

There will be a global list of functions checking for one particular problem.
All functions take the text of a particular file and return a tuple with
(line_number, error_text_German)."""

import re, os, sys
import codecs, collections
import MAGSBS.config as config
import MAGSBS.filesystem as filesystem
import MAGSBS.errors as errors
import MAGSBS.filesystem as filesystem
import enum

class MistakePriority(enum.Enum):
    critical = 1
    normal = 2
    pedantic = 3

class MistakeType(enum.Enum):
    """The mistake type determines the arguments and the environment in which to
    run the tests.

    type                parameters
    full_file           file content, file name
    oneliner            line number (starting form 1), line
    need_headings       argument is return value of HeadingExtractor class
    need_headings_dir   all headings in a directory
    need_pagenumbers   (line_num, level, string) # output of pageNumberExtractor"""
    full_file = 1
    oneliner = 2
    need_headings = 3
    need_headings_dir = 4
    need_pagenumbers = 5

class Mistake:
    """Convenience class which saves the actual method and the type of
    mistake."""
    def __init__(self):
        self._type = MistakeType.full_file
        self._priority = MistakePriority.normal
    def get_type(self): return self._type
    def set_type(self, t):
        if( isinstance( t, MistakeType) ):
            self._type = t
        else:
            raise TypeError("Argument must be of enum type MistakeType")
    def get_priority(self): return self._priority
    def set_priority(self, p):
        if( isinstance( p, MistakePriority ) ):
            self._priority = p
        else:
            raise TypeError("This method expects an argument of type enum.")

    def run(self, *args):
        raise NotImplementedError("The method run must be overriden by a child class.")


class common_latex_errors( Mistake ):
    def __init__(self):
        Mistake.__init__( self )
        # full_file is automatic
    def run(self, *args):
        if( len(args) < 1 ):
            raise TypeError("An argument with the file content to check is expected.")
        for num, line in enumerate( args[0].split('\n') ):
            # check whether cases has no line break
            if( line.find(r'\begin{cases}')>=0 and
                    line.find(r"\end{cases}")>=0):
                return (num+1, "Die LaTeX-Umgebung zur Fallunterscheidung (cases) sollte Zeilenumbrüche an den passenden Stellen enthalten, um die Lesbarkeit zu gewährleisten.")
            # check whether cases environment is in $$ blah $$
            pos = line.find(r'\begin{cases}')
            if(pos >= 0):
                if(line[:pos].rfind('$$')>=0):
                    continue
                elif(line[:pos].rfind(r"\(")>=0 or line[:pos].rfind(r"\\[")>=0):
                    continue
                else:
                    return (num+1, "Die mathematische Umgebung zur Fallunterscheidung (\\begin{cases} ... \\end{cases}) sollte in Displaymath gesetzt werden, d.h. doppelte Dollarzeichen anstatt ein Einzelnes sollten diese Umgebung umschließen. Dies erhält den Zeilenumbruch für den grafischen Alternativtext.") 

class page_number_is_paragraph(Mistake):
    """Check whether all page numbers are on a paragraph on their own."""
    def __init__(self):
        Mistake.__init__(self)
        self.set_priority( MistakePriority.critical )
        self._error_text = "Jede Seitenzahl muss in der Zeile darueber oder darunter eine Leerzeile haben, das heißt sie muss in einem eigenen Absatz stehen."
    def run(self, *args):
        if(len(args)<1):
            raise ValueError("At least one argument (file content) expected.")
        paragraph_begun = True
        previous_line_pnum = False
        for num, line in enumerate(args[0].split('\n')):
            if(line.strip() == ''):
                paragraph_begun = True
                previous_line_pnum = False
            else:
                if(previous_line_pnum ): # previous_line_pnum and this is no empty line...
                    #previous_line_pnum = False
                    return (num, self._error_text)
                elif(re.search(r'\|\|\s*' + config.PAGENUMBERING_REGEX, line.lower())):
                    # line contains page number, is in front of a empty line?
                    if(not paragraph_begun):
                        return (num+1, self._error_text)
                    previous_line_pnum = True
                paragraph_begun = False # one line of text ends "paragraph begun"


class heading_is_paragraph(Mistake):
    def __init__(self):
        Mistake.__init__(self)
        self.set_priority( MistakePriority.critical )
        self.set_type( MistakeType.full_file )
    def run(self, *args):
        """Check whether all page numbers are on a paragraph on their own. Also
        checks whether headings do NOT start with a number."""
        if(len(args) < 1):
            raise ValueError("At least one parameter with the file content expected.")
        error_text = "Jede Ueberschrift muss in der Zeile darueber oder darunter eine Leerzeile haben, das heißt sie muss in einem eigenen Absatz stehen."
        error_text_number = "Die Überschriftsnummerierungen werden automatisch generiert und sollen daher nicht am Anfang der Überschrift stehen, sondern weggelassen werden."
        def check_numbering( num, line ):
            res = re.search(r"^(\#*)\s*(\d+\.\d*)", line)
            if( res ):
                return (num+1, error_text_number)
        paragraph_begun = True
        previous_line_heading = False
        previous_line = ''
        for num, line in enumerate( args[0].split('\n')):
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

class level_one_heading( Mistake ):
    """Parse the document and raise errors if more than one level-1-heading was encountered."""
    def __init__(self):
        Mistake.__init__(self)
        self.set_priority( MistakePriority.critical )
        self.set_type( MistakeType.need_headings_dir )
    def run(self, *args):
        found_h1 = False
        for fn, headings in args[0]:
            for lnum, level, text in headings:
                if( level == 1 ):
                    if( found_h1 ):
                        dir = fn.split( os.sep )
                        if(len(dir) >= 2): dir = dir[-2]
                        else: dir = dir[-1]
                        return ('-', "In dem Verzeichnis " + dir + " gibt es mehr als eine Überschrift der Ebene 1. Dies ist nicht erlaubt. Beispielsweise hat jeder Foliensatz nur eine ueberschrift und auch ein Kapitel wird nur mit einer ueberschrift bezeichnet. Es ist Aufgabe des Bearbeiters, Foliensätze ohne erkennbare Struktur mit einer Struktur zu versehen.")
                    else:
                        found_h1 = True

class itemize_is_paragraph(Mistake):
    def __init__(self):
        Mistake.__init__(self)
        self.set_priority( MistakePriority.critical )
        self.set_type( MistakeType.full_file )
        self._match = re.compile(r"^\d+\. ")
    def run(self, *args):
        paragraph_begun = True
        def Strip( string ):
            return string.replace(" ","").replace("\t","")
        for num, line in enumerate( args[0].split("\n") ):
            if(Strip( line ) == ''):
                paragraph_begun = True
            else:
                if((line.startswith("- ") or self._match.search(line)) \
                        and not paragraph_begun):
                    return (num+1, "Jede Aufzählung muss darüber und darunter Leerzeilen haben, damit sie bei der Umwandlung als Aufzählung erkannt wird.")
                paragraph_begun = False


class oldstyle_pagenumbering(Mistake):
    def __init__(self):
        Mistake.__init__(self)
        self.set_priority( MistakePriority.critical )
        self.set_type( MistakeType.oneliner )
    def run(self, *args):
        """Check whether the old page numbering style "###### - page xyz -" is used."""
        if(len(args)< 2): raise ValueError("Two arguments expected.")
        obj = re.search(r'\s*######\s*-\s*(' +
            '|'.join(config.PAGENUMBERINGTOKENS)+')',
            args[1].lower() )
        if( obj ):
            return (args[0], 'Es wurde eine Seitenzahl im Format "###### - Seite xyz -" bzw. "###### - Seite xyz - ######" gefunden. dies ist nicht mehr erlaubt. Seitenzahlen müssen die Form "|| - Seite xyz -" haben.')

class page_numbering_text_is_lowercase(Mistake):
    def __init__(self):
        Mistake.__init__(self)
        self.set_type( MistakeType.need_pagenumbers )
    def run(self, *args):
        for lnum, text in args[0]:
            if(text.find('seite')>=0 or text.find('folie')>=0):
                return (lnum, 'Das Wort "Seite" wurde klein geschrieben. Dadurch wird es vom MAGSBS-Modul nicht erkannt, sodass keine automatische Seitennavigation erstellt werden kann.')

class page_string_but_no_page_number(Mistake):
    def __init__(self):
        Mistake.__init__(self)
        # cannot be need_pagenumbers, because this leaves out incorrect page numbers
        self.set_type( MistakeType.oneliner )
        self.set_priority( MistakePriority.critical )

    def run( self, *args ):
        """Sometimes one types "- page -" and forgets the digit."""
        line = args[1]
        if( not line.startswith("||") ): return None
        line = line.replace(" ", "")
        for t in config.PAGENUMBERINGTOKENS:
            idx = line.lower().find( t )
            if( idx >= 0 ):
                if( len(line) > idx + len( t ) ):
                    if( not line[idx + len(t)].isdigit() ):
                        return (args[0], "Wahrscheinlich wurde an dieser Stelle eine Seitenzahl notiert, bei der nach dem Wort die anschließende Nummer vergessen wurde.")


def HeadingExtractor(text):
    headings = []
    paragraph_begun = True
    previous_line_heading = False
    previous_line = ''
    for num, line in enumerate( text.split('\n')):
        if(line.strip() == ''):
            paragraph_begun = True
            previous_line_heading = False
        else:
            if(not paragraph_begun): # happens on the second line of a paragraph
                if(line.startswith('---')):
                    previous_line_heading = True
                    headings.append( (num, 2, previous_line) ) # heading level 2
                elif(line.startswith('===')):
                    previous_line_heading = True
                    headings.append( (num, 1, previous_line) ) # heading level 2
                    continue
            if(line.startswith("#")):
                if(paragraph_begun):
                    level = 0
                    while(line.startswith("#") or line.startswith(" ")):
                        if(line[0] == "#"): level += 1
                        line = line[1:]
                    while(line.endswith("#") or line.endswith(" ")):
                        line = line[:-1]

                    headings.append( (num+1, level, line) )
                    previous_line_heading = True
            paragraph_begun = False # one line of text ends "paragraph begun"
        previous_line = line
    return headings


def pageNumberExtractor(data):
    """Iterate over lines and extract all those starting with ||. The page
    number and the rest of the line is returned as a tuple."""
    # ToDo: write me as a kind of cool class which is called always when all
    # one-liners are called; potentially saves some iterations
    numbers = []
    for num, line in enumerate( data.split('\n') ):
        if(line.startswith("||")):
            numbers.append( (num+1, line[2:]) )
    return numbers

############################################

# ToDo: implement need_headings_dir
class Mistkerl():
    """Wrapper which wraps different levels of errors."""
    def __init__(self):
        self.__issues = [common_latex_errors, page_number_is_paragraph,
                heading_is_paragraph, level_one_heading, oldstyle_pagenumbering,
                itemize_is_paragraph, page_numbering_text_is_lowercase,
                page_string_but_no_page_number]
        self.__cache_pnums = collections.OrderedDict()
        self.__cache_headings = collections.OrderedDict()
        self.__cache_content = collections.OrderedDict()
        self.requested_level = MistakePriority.normal

    def get_issues(self):
        for issue in self.__issues:
            i = issue()
            if(self.get_priority().value >= i.get_priority().value):
                yield i
    def set_priority(self, p):
        assert type(p) == MistakePriority
        self.__priority = p
    def get_priority(self): return self.__priority
    def __format_out( self, data ):
        if(data[0] == '-'):
            return data[1]
        else:
            return 'Zeile ' + str(data[0]) + ": " + data[1]

    def run( self, path ):
        """Take either a file and run checks or do the same for a directory
recursively."""
        output = {}
        file_iterator = None
        if( os.path.isfile( path ) ):
            if( path.endswith('.md') ):
                def onefile( path ):
                    yield (os.path.split(path)[0], [], [os.path.split(path)[-1]])
                file_iterator = onefile
            else:
                print('Error: file name must end on ".md".')
                sys.exit( 127 )
        else:
            file_iterator = lambda path: filesystem.get_markdown_files( path,
                    all_markdown_files=True )
        def Append( path, x ):
            if( x ):
                if( not path in output.keys() ):
                    output[ path ] = []
                output[ path ].append( self.__format_out( x ) )

        for directoryname, directory_list, file_list in file_iterator( path ):
            # presort issues
            FullFile = [e for e in self.get_issues() \
                        if e.get_type() == MistakeType.full_file]
            OneLiner = [e for e in self.get_issues() if e.get_type() ==
                    MistakeType.oneliner]
            NeedPnums = [e for e in self.get_issues() if e.get_type() ==
                        MistakeType.need_pagenumbers]
            NeedHeadings = [e for e in self.get_issues() if e.get_type() ==
                        MistakeType.need_headings]

            overlong = False
            for file in file_list:
                file_path = os.path.join( directoryname, file )
                try:
                    text = codecs.open( file_path, "r", "utf-8" ).read()
                except UnicodeDecodeError:
                    Append( file_path, ('-','Datei ist nicht in UTF-8 kodiert, bitte waehle "UTF-8" als Zeichensatz im Editor.'))
                    continue
                text = text.replace('\r\n','\n').replace('\r','\n')
                self.__cache_content[ file_path ] = text

                for issue in FullFile:
                    Append( file_path, issue.run( text ) )
                for num, line in enumerate(text.split('\n')):
                    if( num > 800 and not overlong ):
                        overlong = True
                        Append( file_path, ("-", "Die Datei ist zu lang. Um die Navigation zu erleichtern und die einfache Lesbarkeit zu gewährleisten sollten lange Kapitel mit mehr als 800 Zeilen in mehrere Unterdateien nach dem Schema kxxyy.md oder kleiner aufgeteilt werden."))
                    for issue in OneLiner:
                        Append( file_path, issue.run( num+1, line ) )
                # cache headings and page numbers
                # ToDo: DEBUG both
                pnums = pageNumberExtractor( text )
                hdngs = HeadingExtractor( text )
                self.__cache_pnums[ file_path ] = pnums
                self.__cache_headings[ file_path ] = hdngs

                for issue in NeedPnums:
                    Append( file_path, issue.run( pnums ) )
                for issue in NeedHeadings:
                    Append( file_path, issue.run( hdngs ) )
                        
        new = collections.OrderedDict()
        for k, v in sorted(output.items(), key=lambda x: x[0]):
            new[k] = sorted( v )
        return new
