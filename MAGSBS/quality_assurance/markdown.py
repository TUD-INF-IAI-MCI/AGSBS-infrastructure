# vim: set expandtab sts=4 ts=4 sw=4 tw=0 ft=python:
#pylint: disable=line-too-long
"""All mistakes made while writing Markdown files are put in here."""

from .meta import Mistake, MistakeType, MistakePriority, onelinerMistake
import os, re
from .. import config

class page_number_is_paragraph(Mistake):
    """Check whether all page numbers are on a paragraph on their own."""
    def __init__(self):
        Mistake.__init__(self)
        self.set_priority(MistakePriority.critical)
        self._error_text = "Jede Seitenzahl muss in der Zeile darueber oder darunter eine Leerzeile haben, das heißt sie muss in einem eigenen Absatz stehen."
    def error(self, lnum):
        return super().error(self._error_text, lnum)
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
                if(previous_line_pnum): # previous_line_pnum and this is no empty line...
                    #previous_line_pnum = False
                    return self.error(num+1)
                elif(re.search(r'\|\|\s*' + config.PAGENUMBERING_REGEX,
                        line.lower())):
                    # line contains page number, is in front of a empty line?
                    if(not paragraph_begun):
                        return self.error(num+1)
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
        self.set_priority(MistakePriority.critical)
        self.set_type(MistakeType.full_file)
    def worker(self, *args):
        """Check whether all page numbers are on a paragraph on their own. Also
        checks whether headings do NOT start with a number."""
        if(len(args) < 1):
            raise ValueError("At least one parameter with the file content expected.")
        error_text = "Jede Ueberschrift muss in der Zeile darueber oder darunter eine Leerzeile haben, das heißt sie muss in einem eigenen Absatz stehen."
        error_text_number = "Die Überschriftsnummerierungen werden automatisch generiert und sollen daher weggelassen werden."
        def check_numbering(num, line):
            res = re.search(r"^(\#*)\s*(\d+\.\d*)", line)
            if(res):
                return self.error(error_text_number, num+1)
        paragraph_begun = True
        previous_line_heading = False
        previous_line = ''
        for num, line in enumerate(args[0].split('\n')):
            if(line.strip() == ''):
                paragraph_begun = True
                previous_line_heading = False
            else:
                if(not paragraph_begun): # happens on the second line of a paragraph
                    if(line.startswith('---') or line.startswith('===')):
                        #res = check_numbering(num, previous_line)
                        #if(res): return (res[0]-1, res[1])
                        previous_line_heading = True
                        continue
                if(previous_line_heading): # previous_line_heading and this is no empty line...
                    return self.error(error_text, num+1)
                if(re.search(r'^#+.*', line)):
                    #res = check_numbering(num, line)
                    #if(res): return res
                    # line contains heading, is in front of a empty line?
                    if(not paragraph_begun):
                        return self.error(error_text, num+1)
                    previous_line_heading = True
                paragraph_begun = False # one line of text ends "paragraph begun"
            previous_line = line

class level_one_heading(Mistake):
    """Parse the directory and raise errors if more than one level-1-heading was encountered."""
    def __init__(self):
        Mistake.__init__(self)
        self.set_priority(MistakePriority.critical)
        self.set_type(MistakeType.need_headings_dir)
    def __error(self, msg, path):
        super().error(msg, lnum=None, path=path)
    def worker(self, *args):
        found_h1 = False
        for path, headings in args[0].items():
            is_image_path = False
            for dest_lang in config.L10N.supported_languages:
                translate_dict = getattr(config.L10N, 'en_' + dest_lang)
                if(path.lower().find(translate_dict["images"]) >= 0):
                    is_image_path = True
            if(is_image_path or path.lower().find("images") >= 0):
                continue # do not count h1's in bilder.md

            for lnum, level, text in headings:
                if(level == 1):
                    if(found_h1):
                        return self.__error("In diesem Verzeichnis gibt es mehr" +
                                " als eine Überschrift der Ebene 1. Dies ist " +
                                "nicht erlaubt. Beispielsweise hat jeder " +
                                "Foliensatz nur eine Hauptüberschrift und auch" +
                                " ein Kapitel wird nur mit einer Überschrift " +
                                "bezeichnet.", lnum)
                    else:
                        found_h1 = True


class itemize_is_paragraph(Mistake):
    def __init__(self):
        Mistake.__init__(self)
        self.set_priority(MistakePriority.critical)
        self.set_type(MistakeType.full_file)
        self._match = re.compile(r"^\d+\. ")
        self.__lastlines = []
    def __legalstart(self, line):
        if(line.startswith("- ") or self._match.search(line)): return True
        else: return False
    def __in_itemize(self, line):
        if(len(self.__lastlines) < 2): return False
        elif(self.__legalstart(line)):
            last = self.__lastlines[-1]
            if(self.__legalstart(line)):
                return True
        return False

    def worker(self, *args):
        def empty(string):
            return string.replace(" ","").replace("\t", "")
        for num, line in enumerate(args[0].split("\n")):
            if(self.__in_itemize(line)):
                if(not (self.__lastlines[0] == '') and \
                        not self.__legalstart(line)):
                    return self.error("Jede Aufzählung muss darüber und darunter Leerzeilen haben, damit sie bei der Umwandlung als Aufzählung erkannt wird.", num)
            if(len(self.__lastlines) == 2):
                del self.__lastlines[0]
            if(empty(line) == ''):
                self.__lastlines.append('')
            else:
                self.__lastlines.append(line)


class oldstyle_pagenumbering(Mistake):
    def __init__(self):
        Mistake.__init__(self)
        self.set_priority(MistakePriority.critical)
        self.set_type(MistakeType.oneliner)
    def worker(self, *args):
        """Check whether the old page numbering style "###### - page xyz -" is used."""
        if(len(args)< 2): raise ValueError("Two arguments expected.")
        obj = re.search(r'\s*######\s*-\s*(' +
            '|'.join(config.PAGENUMBERINGTOKENS)+')',
            args[1].lower())
        if(obj):
            return self.error('Es wurde eine Seitenzahl im Format "###### - Seite xyz -" bzw. "###### - Seite xyz - ######" gefunden. dies ist nicht mehr erlaubt. Seitenzahlen müssen die Form "|| - Seite xyz -" haben.', args[0])

class page_numbering_text_is_lowercase(Mistake):
    def __init__(self):
        Mistake.__init__(self)
        self.set_type(MistakeType.need_pagenumbers)
    def worker(self, *args):
        for lnum, text in args[0]:
            if(text.find('seite')>=0 or text.find('folie')>=0):
                return self.error('Das Wort "Seite" wurde klein geschrieben. Dadurch wird es vom MAGSBS-Modul nicht erkannt, sodass keine automatische Seitennavigation erstellt werden kann.', lnum)

class pageNumberWordIsMispelled(Mistake):
    """Sometimes small typos are made when marking a new page. That breaks
indexing of page numbers."""
    def __init__(self):
        Mistake.__init__(self)
        self.set_priority(MistakePriority.critical)
        self.set_type(MistakeType.need_pagenumbers)
        self._match = re.compile(config.PAGENUMBERING_REGEX)
    def worker(self, *args):
        for lnum, text in args[0]:
            if not self._match.search(text):
                self.error("Die Seitenzahl %s enthält keines der folgenden Wörter: %s. Eventuell ist dies lediglich ein Tippfehler." \
                        % (text, ', '.join(config.PAGENUMBERINGTOKENS)), lnum)


class uniform_pagestrings(Mistake):
    def __init__(self):
        Mistake.__init__(self)
        self.set_priority(MistakePriority.normal)
        self.set_type(MistakeType.need_pagenumbers_dir)
    def _error(self, first, later_fn, later_lnum, later_text):
        first_fn = os.path.split(first[0])[-1]
        later_fn = os.path.split(later_fn)[-1]
        second_piece = ''
        if(first_fn == later_fn):
            second_piece = "später dann aber aber \"%s\"" % (later_text)
        else:
            second_piece = "in der Datei \"%s\" dann aber \"%s\"" \
                        % (later_fn, later_text)
        return self.error("In der Datei \"%s\"  wurde zuerst \"%s\" verwendet, " \
                % (first_fn, first[-1]) + second_piece + ". Dies sollte " +
                "einheitlich sein.", later_lnum)

    def worker(self, *args):
        rgx = re.compile(config.PAGENUMBERING_REGEX)
        first = None # first page string found
        for fn, PNUMS in args[0].items():
            for lnum, text in PNUMS:
                match = rgx.search(text.lower())
                if(not match):
                    continue
                else:
                    match = match.groups()
                if(first == None):
                    first = (fn, lnum, match[0])
                elif(first[2] != match[0]):
                    return self._error(first, fn, lnum, match[0])

class too_many_headings(Mistake):
    """Are there too many headings of the same level in a directory next to each
other? E.g. 40 headings level 2. The figure can be controled using
self.threshold."""
    def __init__(self):
        Mistake.__init__(self)
        self.set_priority(MistakePriority.critical)
        self.set_type(MistakeType.need_headings_dir)
        self.threshold = 20
        conf = config.confFactory().get_conf_instance()
        self.maxdepth = conf['tocDepth']

    def worker(self, *args):
        levels = [0,0,0,0,0,0]
        for headings in args[0].values():
            for lnum, level, title in headings:
                if(level > self.maxdepth): continue
                levels[level-1] += 1
                # + 1 for the current level and reset all levels below
                for i in range(level, len(levels)):
                    levels[i] = 0
                if(levels[level-1] > self.threshold):
                    return self.__error(level)

    def __error(self, heading_level):
        return super.error("Es existieren mehr als %d " % self.threshold + \
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
        self.set_type(MistakeType.oneliner)
        self.set_priority(MistakePriority.critical)

    def worker(self, *args):
        """Sometimes one types "- page -" and forgets the digit."""
        line = args[1]
        if(not line.startswith("||")): return None
        line = line.replace(" ", "")
        for t in config.PAGENUMBERINGTOKENS:
            idx = line.lower().find(t)
            if(idx >= 0):
                if(len(line) > idx + len(t)):
                    if(not line[idx + len(t)].isdigit()):
                        return self.error("Wahrscheinlich wurde an dieser Stelle eine Seitenzahl notiert, bei der nach dem Wort die anschließende Nummer vergessen wurde.", args[0])

class headingOccursMultipleTimes(Mistake):
    """Parse headings; report doubled headings; ignore headings below
tocDepth."""
    def __init__(self):
        Mistake.__init__(self)
        self.set_priority(MistakePriority.normal)
        self.set_type(MistakeType.need_headings)
    def worker(self, *args):
        error_message = """Überschriften gleichen Namens machen
Inhaltsverzeichnisse schwer lesbar und erschweren die Navigation. Häufig kommt
dies bei Foliensätzen vor. Am Besten man setzt das TocDepth so, dass nur die
Überschrift des Foliensatzes (oft Ebene 1) aufgenommen wird und alle
Überschriften, mitsamt der Überschriften die doppelt sind, gar nicht erst im
Inhaltsverzeichnis erscheinen."""
        last_heading = None
        for lnum, heading_level, text in args[0]:
            if(heading_level > config.confFactory().get_conf_instance()):
                continue # skip it
            if last_heading == text:
                return self.error(error_message, lnum)
            last_heading = text

class PageNumbersWithoutDashes(onelinerMistake):
    """Page number should look like "|| - page 8 -", people sometimes write
"|| page 8"."""
    def __init__(self):
        onelinerMistake.__init__(self)
        pattern = r'\|\|\s*(' + '|'.join(config.PAGENUMBERINGTOKENS) + ')'
        self.pattern = re.compile(pattern.lower())
    def check(self, num, line):
        if(self.pattern.search(line.lower())):
            return self.error("Es fehlt ein \"-\" in der Seitenzahl. Vorgabe: " +
                    "\"|| - Seite xyz -\"", num)

class DoNotEmbedHTMLLineBreaks(onelinerMistake):
    """Instead of <br> for an empty line, a single \\ can be used."""
    def __init__(self):
        onelinerMistake.__init__(self)
        self.pattern = re.compile(r'<br.*/?>')
    def check(self, num, line):
        if(self.pattern.search(line.lower())):
            return self.error("Es sollte kein Umbruch mittels HTML-Tags erzeugt " +
                    "werden. Platziert man einen \\ als einziges Zeichen auf " +
                    "eine Zeile und lässt davor und danach eine Zeile frei, " +
                    "hat dies denselben Effekt.",  num)

class EmbeddedHTMLComperators(onelinerMistake):
    """Instead of &lt;&gt;, use \\< \\>."""
    def __init__(self):
        onelinerMistake.__init__(self)
        self.pattern = re.compile(r'&(lt|gt);')
    def check(self, num, line):
        if(self.pattern.search(line.lower())):
            return self.error("Relationsoperatoren sollten nicht mittels HTML, " +
                    "sondern mittels \\< und \\> erzeugt werden.", num)

