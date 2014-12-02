"""All mistakes made while writing Markdown files are put in here."""

from MAGSBS.quality_assurance.mistkerl import Mistake, MistakeType, \
                                MistakePriority, onelinerMistake

class page_number_is_paragraph(Mistake):
    """Check whether all page numbers are on a paragraph on their own."""
    def __init__(self):
        Mistake.__init__(self)
        self.set_priority(MistakePriority.critical)
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
                if(previous_line_pnum): # previous_line_pnum and this is no empty line...
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
                return (num+1, error_text_number)
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
                    return (num+1, error_text)
                if(re.search(r'^#+.*', line)):
                    #res = check_numbering(num, line)
                    #if(res): return res
                    # line contains heading, is in front of a empty line?
                    if(not paragraph_begun):
                        return (num+1, error_text)
                    previous_line_heading = True
                paragraph_begun = False # one line of text ends "paragraph begun"
            previous_line = line

class level_one_heading(Mistake):
    """Parse the directory and raise errors if more than one level-1-heading was encountered."""
    def __init__(self):
        Mistake.__init__(self)
        self.set_priority(MistakePriority.critical)
        self.set_type(MistakeType.need_headings_dir)
    def worker(self, *args):
        assert type(args[0]) == dict or \
                type(args[0]) == collections.OrderedDict
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
                        dir = os.path.split(path)[0]
                        return ('-', "In dem Verzeichnis " + dir + " gibt es mehr als eine Überschrift der Ebene 1. Dies ist nicht erlaubt. Beispielsweise hat jeder Foliensatz nur eine Überschrift und auch ein Kapitel wird nur mit einer Überschrift bezeichnet.")
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
        if(line.startswith("- ") or self._match.search(line)):
            return True
        else:
            return False
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
                    return (num, "Jede Aufzählung muss darüber und darunter Leerzeilen haben, damit sie bei der Umwandlung als Aufzählung erkannt wird.")
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
            return (args[0], 'Es wurde eine Seitenzahl im Format "###### - Seite xyz -" bzw. "###### - Seite xyz - ######" gefunden. dies ist nicht mehr erlaubt. Seitenzahlen müssen die Form "|| - Seite xyz -" haben.')

class page_numbering_text_is_lowercase(Mistake):
    def __init__(self):
        Mistake.__init__(self)
        self.set_type(MistakeType.need_pagenumbers)
    def worker(self, *args):
        for lnum, text in args[0]:
            if(text.find('seite')>=0 or text.find('folie')>=0):
                return (lnum, 'Das Wort "Seite" wurde klein geschrieben. Dadurch wird es vom MAGSBS-Modul nicht erkannt, sodass keine automatische Seitennavigation erstellt werden kann.')

class page_string_varies(Mistake):
    """Some editors tend to use "slide" on the first page but "page" on the
    second. That's inconsistent."""
    def __init__(self):
        Mistake.__init__(self)
        self.set_priority(MistakePriority.normal)
        self.set_type(MistakeType.need_pagenumbers) # todo: could be page_numbers_dir as well
        self._match = re.compile(config.PAGENUMBERING_REGEX)
    def _error_syntax(self, num, text):
        return (num, 'Die Überschrift muss die Form "- Seite ZAHL -" haben, wobei ZAHL durch eine Zahl ersetzt werden muss. Wahrscheinlich wurden die Bindestriche vergessen.')
    def _error_word(self, num, text):
        return (num, 'In der Überschrift "%s" kommt keines der folgenden Wörter vor: %s' \
                        % (text, ', '.join(config.PAGENUMBERINGTOKENS)))
    def worker(self, *args):
        page_string = ''  # e.g. "page", used to check whether one diverges
        for lnum, text in args[0]:
            text = text.lower()
            text_word = self._match.search(text)
            if(not text_word):
                found = False
                for t in config.PAGENUMBERINGTOKENS:
                    if(text.lower().find(t) >= 0):
                        found = True
                        break
                if(found):
                    self._error_syntax(lnum, text)
                else:
                    return self._error_word(lnum, text)
            else: text_word = text_word.groups()
            if(page_string == ''):
                for t in config.PAGENUMBERINGTOKENS:
                    if(text.find(t)>= 0):
                        page_string = t

class uniform_pagestrings(Mistake):
    def __init__(self):
        Mistake.__init__(self)
        self.set_priority(MistakePriority.normal)
        self.set_type(MistakeType.need_pagenumbers_dir)
    def _error(self, f_fn, f_num, f_text, l_fn, l_num, l_text):
        l_fn = os.path.split(l_fn)[-1]
        f_fn = os.path.split(f_fn)[-1]
        second_piece = ''
        if(f_fn == l_fn):
            second_piece = "später dann aber aber \"%s\"" % (l_text)
        else:
            second_piece = "in der Datei \"%s\" dann aber \"%s\"" % (l_fn, l_text)
        return (l_num, "In der Datei \"%s\", Zeile %s wurde zuerst \"%s\" verwendet, " % (f_fn, f_num, f_text) + \
                second_piece + ". Dies sollte einheitlich sein.")

    def worker(self, *args):
        rgx = re.compile(config.PAGENUMBERING_REGEX)
        first = None
        for fn, NUMS in args[0].items():
            for lnum, text in NUMS:
                match = rgx.search(text.lower())
                if(not match): continue
                else: match = match.groups()
                if(first == None):
                    first = (fn, lnum, match[0])
                elif(first[2] != match[0]):
                    return self._error(first[0], first[1], first[2], fn, lnum,
                            match[0])

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
        for fpath, headings in args[0].items():
            for lnum, level, title in headings:
                if(level > self.maxdepth): continue
                levels[level-1] += 1
                # + 1 for the current level and reset all levels below
                for i in range(level, len(levels)):
                    levels[i] = 0
                if(levels[level-1] > self.threshold):
                    return self.error_text(level)

    def error_text(self, heading_level):
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
                        return (args[0], "Wahrscheinlich wurde an dieser Stelle eine Seitenzahl notiert, bei der nach dem Wort die anschließende Nummer vergessen wurde.")


def HeadingExtractor(text):
    headings = []
    paragraph_begun = True
    previous_line_heading = False
    previous_line = ''
    for num, line in enumerate(text.split('\n')):
        if(line.strip() == ''):
            paragraph_begun = True
            previous_line_heading = False
        else:
            if(not paragraph_begun): # happens on the second line of a paragraph
                if(line.startswith('---')):
                    previous_line_heading = True
                    headings.append((num, 2, previous_line)) # heading level 2
                elif(line.startswith('===')):
                    previous_line_heading = True
                    headings.append((num, 1, previous_line)) # heading level 2
                    continue
            if(line.startswith("#")):
                if(paragraph_begun):
                    level = 0
                    while(line.startswith("#") or line.startswith(" ")):
                        if(line[0] == "#"): level += 1
                        line = line[1:]
                    while(line.endswith("#") or line.endswith(" ")):
                        line = line[:-1]

                    headings.append((num+1, level, line))
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
    for num, line in enumerate(data.split('\n')):
        if(line.startswith("||")):
            numbers.append((num+1, line[2:]))
    return numbers

############################################


