# This is free software licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2014 Sebastian Humenda <shumenda@gmx.de>

"""
This sub-module provides implementations for checking common lecture editing
errors.

In the Mistkerl class, the only one which should be used from outside, there is
a list of "mistakes". Mistkerl iterates through them and takes the appropriate
steps to run the mistake checks.

A mistake is a child of the Mistake class. It can set its priority and its type
(what it wants to see from the document) in its __init__-function. The common
run-function then implements the checking.

All mistakes take a list of arguments (which depends on the set type, see
MistakeType) and return a tuple with (line_number, detailed_error_text_German).

For the documentation of the mistake types, see the appropriate class."""

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

type                parameters      Explanation
full_file           (content, name) applied to a whole file
oneliner            (num, line)     applied to line, starting num = 1
need_headings       (lnum, level,   applied to all headings
                     title)
need_headings_dir   [(path, [lnum,  applied to all headings in a directory
                     level, title]))
need_pagenumbers    (lnum, level,   applied to all page numbers of page
                 string)
need_pagenumbers_dir   see headings applied to all page numbers of directory"""
    full_file = 1
    oneliner = 2
    need_headings = 3
    need_headings_dir = 4
    need_pagenumbers = 5
    need_pagenumbers_dir = 6

class Mistake:
    """Convenience class which saves the actual method and the type of
    mistake."""
    def __init__(self):
        self._type = MistakeType.full_file
        self._priority = MistakePriority.normal
        self.__apply = True
    def should_be_run(self):
        """Can be set e.g. for oneliners which have already found an error."""
        return self.__apply
    def set_run(self, value):
        assert type(value) == bool
        self.__apply = value
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
        if( not self.should_be_run ):
            return
        return self.worker( *args )
    def worker(self, *args):
        raise NotImplementedError("The method run must be overriden by a child class.")


class common_latex_errors( Mistake ):
    def __init__(self):
        Mistake.__init__( self )
        # full_file is automatic
    def worker(self, *args):
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
    def worker(self, *args):
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
    # ToDo: two errors are here checked, instead split it into two error classes
    # to avoid swallowed mistakes ;)
    # ToDo II: check_numbering is commented out: it may be the case that we have
    # an aabstract in a paper and therefore the first heading is NOT 1. but has
    # no number; then the editor chooses to make the second heading with the
    # number
    # "1.". We ought to decide how to deal with that
    def __init__(self):
        Mistake.__init__(self)
        self.set_priority( MistakePriority.critical )
        self.set_type( MistakeType.full_file )
    def worker(self, *args):
        """Check whether all page numbers are on a paragraph on their own. Also
        checks whether headings do NOT start with a number."""
        if(len(args) < 1):
            raise ValueError("At least one parameter with the file content expected.")
        error_text = "Jede Ueberschrift muss in der Zeile darueber oder darunter eine Leerzeile haben, das heißt sie muss in einem eigenen Absatz stehen."
        error_text_number = "Die Überschriftsnummerierungen werden automatisch generiert und sollen daher weggelassen werden."
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
                        #res = check_numbering( num, previous_line )
                        #if( res ): return (res[0]-1, res[1])
                        previous_line_heading = True
                        continue
                if(previous_line_heading ): # previous_line_heading and this is no empty line...
                    return (num+1, error_text)
                if(re.search(r'^#+.*', line)):
                    #res = check_numbering( num, line )
                    #if( res ): return res
                    # line contains heading, is in front of a empty line?
                    if(not paragraph_begun):
                        return (num+1, error_text)
                    previous_line_heading = True
                paragraph_begun = False # one line of text ends "paragraph begun"
            previous_line = line

class level_one_heading( Mistake ):
    """Parse the directory and raise errors if more than one level-1-heading was encountered."""
    def __init__(self):
        Mistake.__init__(self)
        self.set_priority( MistakePriority.critical )
        self.set_type( MistakeType.need_headings_dir )
    def worker(self, *args):
        assert type( args[0] ) == dict or \
                type( args[0] ) == collections.OrderedDict
        found_h1 = False
        for path, headings in args[0].items():
            is_image_path = False
            for dest_lang in config.L10N.supported_languages:
                translate_dict = getattr( config.L10N, 'en_' + dest_lang )
                if( path.lower().find( translate_dict["images"] ) >= 0 ):
                    is_image_path = True
            if( is_image_path or path.lower().find( "images" ) >= 0 ):
                continue # do not count h1's in bilder.md

            for lnum, level, text in headings:
                if( level == 1 ):
                    if( found_h1 ):
                        dir = os.path.split( path )[0]
                        return ('-', "In dem Verzeichnis " + dir + " gibt es mehr als eine Überschrift der Ebene 1. Dies ist nicht erlaubt. Beispielsweise hat jeder Foliensatz nur eine Überschrift und auch ein Kapitel wird nur mit einer Überschrift bezeichnet.")
                    else:
                        found_h1 = True

class itemize_is_paragraph(Mistake):
    def __init__(self):
        Mistake.__init__(self)
        self.set_priority( MistakePriority.critical )
        self.set_type( MistakeType.full_file )
        self._match = re.compile(r"^\d+\. ")
        self.__lastlines = []
    def __legalstart( self, line ):
        if(line.startswith("- ") or self._match.search( line )):
            return True
        else:
            return False
    def __in_itemize( self, line ):
        if( len(self.__lastlines) < 2): return False
        elif( self.__legalstart( line ) ):
            last = self.__lastlines[-1]
            if( self.__legalstart( line ) ):
                return True
        return False

    def worker(self, *args):
        def empty( string ):
            return string.replace(" ","").replace("\t", "")
        for num, line in enumerate( args[0].split("\n") ):
            if( self.__in_itemize( line ) ):
                if( not (self.__lastlines[0] == '') and \
                        not self.__legalstart( line ) ):
                    return (num, "Jede Aufzählung muss darüber und darunter Leerzeilen haben, damit sie bei der Umwandlung als Aufzählung erkannt wird.")
            if( len(self.__lastlines) == 2):
                del self.__lastlines[0]
            if( empty( line ) == ''):
                self.__lastlines.append( '' )
            else:
                self.__lastlines.append( line )


class oldstyle_pagenumbering(Mistake):
    def __init__(self):
        Mistake.__init__(self)
        self.set_priority( MistakePriority.critical )
        self.set_type( MistakeType.oneliner )
    def worker(self, *args):
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
    def worker(self, *args):
        for lnum, text in args[0]:
            if(text.find('seite')>=0 or text.find('folie')>=0):
                return (lnum, 'Das Wort "Seite" wurde klein geschrieben. Dadurch wird es vom MAGSBS-Modul nicht erkannt, sodass keine automatische Seitennavigation erstellt werden kann.')

class page_string_varies(Mistake):
    """Some editors tend to use "slide" on the first page but "page" on the
    second. That's inconsistent."""
    def __init__(self):
        Mistake.__init__(self)
        self.set_priority( MistakePriority.normal )
        self.set_type( MistakeType.need_pagenumbers ) # todo: could be page_numbers_dir as well
        self._match = re.compile( config.PAGENUMBERING_REGEX )
    def _error_syntax(self, num, text):
        return (num, 'Die Überschrift muss die Form "- Seite ZAHL -" haben, wobei ZAHL durch eine Zahl ersetzt werden muss. Wahrscheinlich wurden die Bindestriche vergessen.')
    def _error_word(self, num, text):
        return ( num, 'In der Überschrift "%s" kommt keines der folgenden Wörter vor: %s' \
                        % (text, ', '.join( config.PAGENUMBERINGTOKENS )) )
    def worker(self, *args):
        page_string = ''  # e.g. "page", used to check whether one diverges
        for lnum, text in args[0]:
            text = text.lower()
            text_word = self._match.search( text )
            if( not text_word ):
                found = False
                for t in config.PAGENUMBERINGTOKENS:
                    if(text.lower().find( t ) >= 0):
                        found = True
                        break
                if( found ):
                    self._error_syntax( lnum, text )
                else:
                    return self._error_word(lnum, text)
            else: text_word = text_word.groups()
            if( page_string == '' ):
                for t in config.PAGENUMBERINGTOKENS:
                    if(text.find( t )>= 0):
                        page_string = t

class uniform_pagestrings(Mistake):
    def __init__(self):
        self.set_priority( MistakePriority.normal )
        self.set_type( MistakeType.need_pagenumbers_dir )
    def _error(self, f_fn, f_num, f_text, l_fn, l_num, l_text):
        l_fn = os.path.split( l_fn )[-1]
        f_fn = os.path.split( f_fn )[-1]
        second_piece = ''
        if( f_fn == l_fn ):
            second_piece = "später dann aber aber \"%s\"" % (l_text)
        else:
            second_piece = "in der Datei \"%s\" dann aber \"%s\"" % (l_fn, l_text)
        return (l_num, "In der Datei \"%s\", Zeile %s wurde zuerst \"%s\" verwendet, " % (f_fn, f_num, f_text) + \
                second_piece + ". Dies sollte einheitlich sein.")

    def worker(self, *args):
        rgx = re.compile( config.PAGENUMBERING_REGEX )
        first = None
        for fn, NUMS in args[0].items():
            for lnum, text in NUMS:
                match = rgx.search( text.lower() )
                if( not match ): continue
                else: match = match.groups()
                if( first == None ):
                    first = (fn, lnum, match[0])
                elif( first[2] != match[0] ):
                    return self._error( first[0], first[1], first[2], fn, lnum,
                            match[0])

class too_many_headings(Mistake):
    """Are there too many headings of the same level in a directory next to each
other? E.g. 40 headings level 2. The figure can be controled using
self.threshold."""
    def __init__( self ):
        self.set_priority( MistakePriority.critical )
        self.set_type( MistakeType.need_headings_dir )
        self.threshold = 20
        conf = config.confFactory().get_conf_instance()
        self.maxdepth = conf['tocDepth']

    def worker( self, *args ):
        levels = [0,0,0,0,0,0]
        for fpath, headings in args[0].items():
            for lnum, level, title in headings:
                if( level > self.maxdepth ): continue
                levels[level-1] += 1
                # + 1 for the current level and reset all levels below
                for i in range( level, len(levels) ):
                    levels[i] = 0
                if( levels[level-1] > self.threshold ):
                    return self.error_text( level )

    def error_text( self, heading_level ):
        return ("-", "Es existieren mehr als %d " % self.threshold + \
                "Überschriften der Ebene %d. " % heading_level + \
                "Das macht das Inhaltsverzeichnis sehr übersichtlich."+\
                " Man kann entweder in der Konfiguration tocDepth kleiner setzen, "+\
                "um Überschriften dieser Ebene nicht ins Inhaltsverzeichnis"+\
                " aufzunehmen (für Foliensätze z.B. tocDepth 1) oder die Anzahl "+\
                "an Überschriften minimieren, sofern möglich.")


class page_string_but_no_page_number(Mistake):
    def __init__(self):
        Mistake.__init__(self)
        # cannot be need_pagenumbers, because this leaves out incorrect page numbers
        self.set_type( MistakeType.oneliner )
        self.set_priority( MistakePriority.critical )

    def worker( self, *args ):
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

class Mistkerl():
    """Wrapper which wraps different levels of errors."""
    def __init__(self):
        self.__issues = [common_latex_errors, page_number_is_paragraph,
                heading_is_paragraph, level_one_heading, oldstyle_pagenumbering,
                itemize_is_paragraph, page_numbering_text_is_lowercase,
                page_string_but_no_page_number, page_string_varies,
                uniform_pagestrings, too_many_headings ]
        self.__cache_pnums = collections.OrderedDict()
        self.__cache_headings = collections.OrderedDict()
        self.__output = {}
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

    def __append(self, path, value):
        if( value ):
            if( not path in self.__output.keys() ):
                self.__output[ path ] = []
            self.__output[ path ].append( self.__format_out( value ) )


    def run( self, path ):
        """Take either a file and run checks or do the same for a directory
recursively."""
        last_dir = None
        for directoryname, directory_list, file_list in filesystem.\
                        get_markdown_files( path, all_markdown_files=True ):
            if( not (last_dir == directoryname) ):
                self.run_directory_filters( last_dir )
                last_dir = directoryname


            for file in file_list:
                file_path = os.path.join( directoryname, file )
                try:
                    text = codecs.open( file_path, "r", "utf-8" ).read()
                except UnicodeDecodeError:
                    self.__append( file_path, ('-','Datei ist nicht in UTF-8 kodiert, bitte waehle "UTF-8" als Zeichensatz im Editor.'))
                    continue
                text = text.replace('\r\n','\n').replace('\r','\n')
                self.__run_filters_on_file( file_path, text )
        # the last directory must be processed, even so there was no directory
        # change
        self.run_directory_filters( directoryname )
        return self.__output
 

    def __run_filters_on_file( self, file_path, text ):
        """Execute all filters which operate on one file."""
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
        for issue in FullFile:
            self.__append( file_path, issue.run( text ) )
        for num, line in enumerate(text.split('\n')):
            if( num > 2500 and not overlong ):
                overlong = True
                self.__append( file_path, ("-", "Die Datei ist zu lang. Um die Navigation zu erleichtern und die einfache Lesbarkeit zu gewährleisten sollten lange Kapitel mit mehr als 2500 Zeilen in mehrere Unterdateien nach dem Schema kxxyy.md oder kleiner aufgeteilt werden."))
            for issue in OneLiner:
                if( issue.should_be_run() ):
                    res = issue.run( num+1, line )
                    if( res ):
                        self.__append( file_path, res )
                        issue.set_run( False )
        # cache headings and page numbers
        pnums = pageNumberExtractor( text )
        hdngs = HeadingExtractor( text )
        self.__cache_pnums[ file_path ] = pnums
        self.__cache_headings[ file_path ] = hdngs

        for issue in NeedPnums:
            self.__append( file_path, issue.run( pnums ) )
        for issue in NeedHeadings:
            self.__append( file_path, issue.run( hdngs ) )
                       
    def run_directory_filters(self, dname):
        """Run all filters depending on the output of a directory."""
        if( len(self.__cache_pnums) > 0 ):
            x = [e for e in self.get_issues() if e.get_type() == MistakeType.need_pagenumbers_dir]
            for issue in x:
                self.__append( dname, issue.run( self.__cache_pnums ) )
        if( len(self.__cache_headings) > 0 ):
            x = [e for e in self.get_issues() if e.get_type() == MistakeType.need_headings_dir]
            for issue in x:
                self.__append( dname, issue.run( self.__cache_headings ) )
        self.__cache_pnums.clear()
        self.__cache_headings.clear()




