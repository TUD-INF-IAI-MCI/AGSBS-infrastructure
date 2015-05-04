# vim: set expandtab sts=4 ts=4 sw=4 tw=0 ft=python:
#pylint: disable=line-too-long,arguments-differ,unused-variable
"""All checkers for MarkDown files belong here."""

from .meta import Mistake, MistakeType, MistakePriority, OnelinerMistake
import os, re
from .. import config

class PageNumberIsParagraph(Mistake):
    """Check whether all page numbers are on a paragraph on their own."""
    def __init__(self):
        Mistake.__init__(self)
        self.set_priority(MistakePriority.critical)
        self._error_text = "Jede Seitenzahl muss in der Zeile darueber oder darunter eine Leerzeile haben, das heißt sie muss in einem eigenen Absatz stehen."
        self.pattern = re.compile(r'^\|\|\s*' + config.PAGENUMBERING_REGEX)

    def error(self, lnum):
        return super().error(self._error_text, lnum)

    def worker(self, *args):
        for start_line, paragraph in args[0].items():
            if len(paragraph) == 1: continue # that's either a correct one or not interesting
            for num, line in enumerate(paragraph):
                # more than one line and a page number, bug
                if self.pattern.search(line.lower()):
                    return self.error(start_line + num)


# previous versions of Pandoc weren#t clever enough to detect that
#class HeadingIsParagraph(Mistake):
#    """Only check for ==== or ---- headings, for the others Pandoc is clever enough."""
#    def __init__(self):
#        Mistake.__init__(self)
#        self.set_priority(MistakePriority.critical)
#        self.set_type(MistakeType.full_file)
#
#    def worker(self, *args):
#        """Check whether all headings are on a paragraph on it's own."""
#        error_text = "Jede Überschrift muss in der Zeile darüber oder darunter eine Leerzeile haben, das heißt sie muss in einem eigenen Absatz stehen."
#        for start_line, paragraph in args[0].items():
#            if len(paragraph) == 1:
#                continue # possibly correct
#            # if --- is encountered, it is first checked whether there is another --- in the paragraph, if so it is ignored because it is a table
#            last_line = ''
#            for lnum, line in enumerate(paragraph):
#                if line.startswith('===') or line.startswith('---'):
#                    if "|" in line or " " in line.rstrip():
#                        continue # that's a table
#                    if len(paragraph) == 2:
#                        return # one line text, one ascii line, so it's all right
#                    # check whether marker comes up again, if yes, it's a table -> ignore. Else error.
#                    for line in paragraph[lnum+1:]:
#                        if line.startswith('---'):
#                            return # found it again, is a table, ignore
#                    return self.error(error_text, start_line + lnum)
#                elif line.startswith('#'):
#                    return self.error(error_text, start_line + lnum)

class LevelOneHeading(Mistake):
    """Parse the directory and raise errors if more than one level-1-heading was encountered."""
    def __init__(self):
        Mistake.__init__(self)
        self.set_priority(MistakePriority.critical)
        self.set_type(MistakeType.need_headings_dir)
        self.namesForImage = ["images"]
        for dest_lang in config.L10N.supported_languages:
            translate_dict = getattr(config.L10N, 'en_' + dest_lang)
            self.namesForImage.append(translate_dict['images'])

    def worker(self, *args):
        found_h1 = False
        for path, headings in args[0].items():
            if os.path.split(path)[-1] in self.namesForImage:
                continue # do not count h1's in bilder.md

            for heading in headings:
                if heading.get_level() == 1:
                    if found_h1:
                        return self.error("""In diesem Verzeichnis gibt es
                                mehr als eine Überschrift der Ebene 1. Dies ist
                                nicht erlaubt. Beispielsweise hat jeder
                                Foliensatz nur eine Hauptüberschrift und auch
                                ein Kapitel wird nur mit einer Überschrift
                                bezeichnet.""", heading.get_line_number())
                    else:
                        found_h1 = True


class ItemizeIsParagraph(Mistake):
    """Go through each paragraph and check whether a line is a valid item for
    an itemize environment. If Ignore first and last line of course. If it is,
    check whether first and last line are valid, else return error."""
    def __init__(self):
        Mistake.__init__(self)
        self.set_priority(MistakePriority.critical)
        self.set_type(MistakeType.full_file)
        self._match = re.compile(r"^\d+\. ")
        self.__lastlines = []

    def is_item_line(self, line):
        for c in ['+ ', '* ', '- ']:
            if line.startswith(c):
                # ignore "* *" which are used for horizontal bars
                if '* *' not in line:
                    return True
        if self._match.search(line):
            return True
        return False

    def worker(self, *args):
        """Only mark this as an error, when more than two itemize signs have
        been found at the beginning of a line, so that e.g. a dash which is ust
        in a text is not recognized as an itemize environment."""
        for start_line, paragraph in args[0].items():
            # if first line is itemize, don't check this paragraph
            if len(paragraph) > 0:
                if self.is_item_line(paragraph[0]):
                    continue
            # abort if it's a table
            if len(paragraph) >= 2:
                if '---' in paragraph[1] and ' ' in paragraph[1].rstrip():
                    continue
            item_encountered = False
            for lnum, line in enumerate(paragraph):
                if self.is_item_line(line):
                    # itemize encountered and first line was no itemize line?
                    if lnum != 0:
                        if item_encountered:
                            return self.error("""Eine Aufzählung muss in einem eigenen
                                Absatz stehen, d. h. es muss davor und danach
                                eine Leerzeile sein.""", start_line+lnum)
                        else:
                            item_encountered = True


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

class PageNumberingTextIsLowercase(Mistake):
    def __init__(self):
        Mistake.__init__(self)
        self.set_type(MistakeType.need_pagenumbers)

    def worker(self, *args):
        for lnum, text in args[0]:
            if(text.find('seite')>=0 or text.find('folie')>=0):
                return self.error('Das Wort "Seite" wurde klein geschrieben. Dadurch wird es vom MAGSBS-Modul nicht erkannt, sodass keine automatische Seitennavigation erstellt werden kann.', lnum)

class PageNumberWordIsMispelled(Mistake):
    """Sometimes small typos are made when marking a new page. That breaks
indexing of page numbers."""
    def __init__(self):
        Mistake.__init__(self)
        self.set_priority(MistakePriority.critical)
        self.set_type(MistakeType.full_file)
        self._match = re.compile(r'\|\|\s*-\s*(\w+)\s+.*-')

    def worker(self, *args):
        for start, par in args[0].items():
            if len(par) > 1: continue
            res = self._match.search(par[0].lower())
            if res and not (res.groups()[0] in config.PAGENUMBERINGTOKENS):
                return self.error("""Die Seitenzahl %s wird nicht erkannt,
                        wahrscheinlich handelt es sich um einen Tippfehler. Die
                        Seitenzahl wird ignoriert.""" % res.groups()[0], start)


class UniformPagestrings(Mistake):
    def __init__(self):
        Mistake.__init__(self)
        self.set_priority(MistakePriority.normal)
        self.set_type(MistakeType.need_pagenumbers_dir)
        self.pattern = re.compile('.*(%s).*' % '|'.join(config.PAGENUMBERINGTOKENS))

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
        first = None # first page string found
        for fn, PNUMS in args[0].items():
            for lnum, text in PNUMS:
                match = self.pattern.search(text.lower())
                if(not match):
                    continue
                else:
                    match = match.groups()
                if(first == None):
                    first = (fn, lnum, match[0])
                elif(first[2] != match[0]):
                    return self._error(first, fn, lnum, match[0])

class TooManyHeadings(Mistake):
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
            for heading in headings:
                if heading.get_level() > self.maxdepth:
                    continue
                levels[heading.get_level()-1] += 1
                # + 1 for the current level and reset all levels below
                for i in range(heading.get_level(), len(levels)):
                    levels[i] = 0
                if levels[heading.get_level()-1] > self.threshold:
                    return self.__error(heading.get_level())

    def __error(self, heading_level):
        return super().error("""Es existieren mehr als %d Überschriften der Ebene
                %d. Das macht das Inhaltsverzeichnis sehr unübersichtlich.  Man
                kann entweder in der Konfiguration tocDepth kleiner setzen, um
                Überschriften dieser Ebene nicht ins Inhaltsverzeichnis
                aufzunehmen (für Foliensätze z.B. tocDepth 1) oder die Anzahl
                an Überschriften minimieren, sofern möglich.""" % \
                (self.threshold, heading_level), lnum=None)


class ForgottenNumberInPageNumber(Mistake):
    """This is not a oneliner, because it is more efficient to go though all
    paragraphs and check for paragraphs with length 1 instead of iterating
    through *all* lines."""
    def __init__(self):
        super().__init__()
        # cannot be need_pagenumbers, because this leaves out incorrect page numbers
        self.set_priority(MistakePriority.critical)
        self.set_type(MistakeType.full_file)
        self.pattern = re.compile(r'\s*-\s*(%s)' +
                '|'.join(config.PAGENUMBERINGTOKENS) + '\\s+')

    def worker(self, *args):
        """Sometimes digits of page number get lost when typing."""
        for start, par in args[0].items():
            if len(par) > 1: continue # skip
            line = par[0]
            if not line.startswith("||"): return
            match = self.pattern.search(line.lower())
            if match:
                if not re.search('.*\\d+', line):
                    return self.error("Wahrscheinlich wurde an dieser Stelle eine Seitenzahl notiert, bei der nach dem Wort die anschließende Nummer vergessen wurde.", start)

class HeadingOccursMultipleTimes(Mistake):
    """Parse headings; report doubled headings; ignore headings below
tocDepth."""
    def __init__(self):
        Mistake.__init__(self)
        self.set_priority(MistakePriority.normal)
        self.set_type(MistakeType.need_headings)

    def worker(self, *args):
        error_message = """Überschriften gleichen Namens machen
                Inhaltsverzeichnisse schwer lesbar und erschweren die
                Navigation. Häufig kommt dies bei Foliensätzen vor. Am Besten
                man setzt das TocDepth so, dass nur die Überschrift des
                Foliensatzes (oft Ebene 1) aufgenommen wird und alle
                Überschriften, mitsamt der Überschriften die doppelt sind, gar
                nicht erst im Inhaltsverzeichnis erscheinen."""
        last_heading = None
        for heading in args[0]:
            if heading.get_level() > config.confFactory().get_conf_instance()['tocDepth']:
                continue # skip it
            if last_heading == heading.get_text():
                return self.error(error_message, heading.get_line_number())
            last_heading = heading.get_text()

class PageNumbersWithoutDashes(Mistake):
    """Page number should look like "|| - page 8 -", people sometimes write
"|| page 8"."""
    def __init__(self):
        super().__init__()
        pattern = r'\|\|\s*(' + '|'.join(config.PAGENUMBERINGTOKENS) + ')'
        self.set_type(MistakeType.full_file)
        self.pattern = re.compile(pattern.lower())

    def worker(self, *args):
        for num, par in args[0].items():
            if len(par) > 1: continue
            if self.pattern.search(par[0].lower()):
                return self.error("Es fehlt ein \"-\" in der Seitenzahl. Vorgabe: " +
                    "\"|| - Seite xyz -\"", num)

class DoNotEmbedHTMLLineBreaks(OnelinerMistake):
    """Instead of <br> for an empty line, a single \\ can be used."""
    def __init__(self):
        super().__init__()
        self.pattern = re.compile(r'<br.*/?>')

    def check(self, num, line):
        if self.pattern.search(line.lower()):
            return self.error("Es sollte kein Umbruch mittels HTML-Tags erzeugt " +
                    "werden. Platziert man einen \\ als einziges Zeichen auf " +
                    "eine Zeile und lässt davor und danach eine Zeile frei, " +
                    "hat dies denselben Effekt.",  num)

class EmbeddedHTMLComperators(OnelinerMistake):
    """Instead of &lt;&gt;, use \\< \\>."""
    def __init__(self):
        OnelinerMistake.__init__(self)
        self.set_priority(MistakePriority.pedantic)
        self.pattern = re.compile(r'&(lt|gt);')

    def check(self, num, line):
        if(self.pattern.search(line.lower())):
            return self.error("Relationsoperatoren sollten möglichst nicht mittels HTML, " +
                    "sondern besser mittels \\< und \\> erzeugt werden.", num)

class HeadingsUseEitherUnderliningOrHashes(Mistake):
    def __init__(self):
        Mistake.__init__(self)
        self.set_priority(MistakePriority.critical)
        self.set_type(MistakeType.need_headings)

    def worker(self, *args):
        for heading in args[0]:
            if heading.get_text().startswith('#'):
                return self.error("""Die Überschrift wurde unterstrichen und
                        gleichzeitig mit # bzw. ## als Überschrift
                        gekennzeichnet. Am Besten ist es, die # zu entfernen,
                        da sie sonst als Text angezeigt werden.""",
                        lnum=heading.get_line_number())


