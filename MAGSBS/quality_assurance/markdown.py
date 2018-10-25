# This is free software, licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2015-2018 Sebastian Humenda <shumenda |at| gmx |dot| de>
#pylint: disable=line-too-long,arguments-differ,too-few-public-methods,no-self-use
"""All checkers for MarkDown files belong here."""

import os
import re
from .meta import Mistake, MistakeType, OnelinerMistake
from .. import config, common
MetaInfo = config.MetaInfo

class PageNumberIsParagraph(Mistake):
    """Check whether all page numbers are on a paragraph on their own."""
    def __init__(self):
        super().__init__()
        self._error_text = _("Each line number has to have an empty line "
                    "before and after it, that is, on a paragraph of its own.")
        self.pattern = re.compile(r'^\|\|\s*' + config.PAGENUMBERING_PATTERN.pattern, re.VERBOSE)

    def error(self, lnum):
        return super().error(self._error_text, lnum)

    def worker(self, *args):
        for start_line, paragraph in args[0].items():
            if len(paragraph) == 1:
                continue # that's either a correct one or not interesting
            for num, line in enumerate(paragraph):
                # more than one line and a page number, bug
                result = self.pattern.search(line.lower())
                if result and None not in result.groups():
                    return self.error(start_line + num)


class LevelOneHeading(Mistake):
    """Parse the directory and raise errors if more than one level-1-heading was encountered."""
    mistake_type = MistakeType.headings_dir
    def worker(self, *args):
        found_h1 = False
        for path, headings in args[0].items():
            if os.path.basename(path).lower() == 'bilder.md':
                continue # do not count h1's in bilder.md

            for heading in headings:
                if heading.get_level() == 1:
                    if found_h1:
                        return self.error(_("There is more than one heading of "
                                "level one, which is not allowed. For instance,"
                                " a slide set or a chapter has only one heading"
                                " of level 1."))
                    else:
                        found_h1 = True


class ItemizeIsParagraph(Mistake):
    """Go through each paragraph and check whether a line is a valid item for
    an itemize environment. If Ignore first and last line of course. If it is,
    check whether first and last line are valid, else return error."""
    mistake_type = MistakeType.full_file

    def __init__(self):
        super().__init__()
        self._itemize_pattern = re.compile(r'''^\s*  # tolerate any whitespace in front
            (-|\+|\* # any itemize character
             |\(?(\d+|[iIvVlLxXcC]+)\) # understand any arabic/roman number enclosed or terminated by parenthesis
             |(\d+|[iIvVlLxXcC]+)\.)
            \s+ # at least one space required after item
            ''', re.VERBOSE)

    def worker(self, *args):
        """Only mark this as an error, when more than two itemize signs have
        been found at the beginning of a line, so that e.g. a dash which is ust
        in a text is not recognized as an itemize environment."""
        is_item = lambda line: bool(self._itemize_pattern.search(line))
        for start_line, paragraph in args[0].items():
            if not paragraph:
                continue
            # if first line is itemize, don't check this paragraph
            if is_item(paragraph[0]):
                continue
            item_encountered = False
            for lnum, line in enumerate(paragraph[1:]):
                if line and line[0].isspace():
                    continue # indented lines don't matter
                elif is_item(line):
                    # itemize encountered and first line was no itemize line?
                    if item_encountered:
                        err_message = _("A list or enumeration needs to be on "
                                "a paragraph of its own and needs to have at "
                                "least an empty line before.")
                        return self.error(err_message, start_line+lnum)
                    else:
                        item_encountered = True


class PageNumberWordIsMispelled(Mistake):
    """Sometimes small typos are made when marking a new page. That breaks
indexing of page numbers."""
    mistake_type = MistakeType.pagenumbers
    def __init__(self):
        Mistake.__init__(self)
        self.page_identifiers = config.PAGENUMBERINGTOKENS + \
                [e.title() for e in config.PAGENUMBERINGTOKENS]

    def worker(self, *args):
        for pnum in args[0]:
            if not pnum.identifier in self.page_identifiers:
                err_message = _("The page number \"{}\" can't be recognised, "
                        "possibly due to a typo, hence it is ignored at the "
                        "moment.").format(pnum.identifier)
                return self.error(err_message, pnum.line_no)


class UniformPagestrings(Mistake):
    mistake_type = MistakeType.pagenumbers_dir
    def __init__(self):
        Mistake.__init__(self)
        self.pattern = re.compile('.*(%s).*' % '|'.join(config.PAGENUMBERINGTOKENS))

    def _error(self, first_fn, first_pnum, later_fn, later_pnum):
        first_fn = os.path.basename(first_fn)
        later_fn = os.path.basename(later_fn)
        first = _("Two differing page number identifiers were found.")
        second = None
        if first_fn == later_fn:
            second = _("First \"{pagenum}\", later \"{another}\".").format(
                     pagenum=first_pnum.identifier,
                     another=later_pnum.identifier)
        else:
            second = _("First \"{pagenum}\", but then \"{another}\" in "
                     "\"{file}\".").format(pagenum=first_pnum.identifier,
                             another=later_pnum.identifier, file=later_fn)
        return super().error('%s %s' % (first, second), lnum=first_pnum.line_no,
                path=first_fn)

    def worker(self, *args):
        first = () # (fn, first page number)
        for fn, page_numbers in args[0].items():
            for pnum in page_numbers:
                match = self.pattern.search(pnum.identifier.lower())
                if not match:
                    continue
                match = match.groups()
                if not first:
                    first = (fn, pnum)
                elif first[1].identifier.lower() != match[0].lower():
                    return self._error(first[0], first[1], fn, pnum)


class TooManyHeadings(Mistake):
    """Are there too many headings of the same level in a directory next to each
other? E.g. 40 headings level 2. The number can be controled using
self.threshold."""
    mistake_type = MistakeType.headings_dir
    def __init__(self):
        super().__init__()
        self.threshold = 20

    def worker(self, *args):
        levels = [0, 0, 0, 0, 0, 0]
        directory = os.path.dirname(next(iter(args[0].keys())))
        directory = (directory if directory else '.')
        conf = config.ConfFactory().get_conf_instance_safe(directory)
        maxdepth = int(conf[MetaInfo.TocDepth])
        for headings in args[0].values():
            for heading in headings:
                if heading.get_level() > maxdepth:
                    continue
                levels[heading.get_level()-1] += 1
                # + 1 for the current level and reset all levels below
                for level in range(heading.get_level(), len(levels)):
                    levels[level] = 0
                if levels[heading.get_level()-1] > self.threshold:
                    return self.__error(heading.get_level())

    def __error(self, heading_level):
        return super().error(_("There are more than {count} headings of level "
                "{depth}. This can be circumvented by decreasing the heading "
                "depth which will end up the the table of contents, by "
                "decreasing the value tocDepth in the configuration.").format(
                    count=self.threshold, depth=heading_level),)


class ForgottenNumberInPageNumber(Mistake):
    """This is not a oneliner, because it is more efficient to go though all
    paragraphs and check for paragraphs with length 1 instead of iterating
    through *all* lines."""
    mistake_type = MistakeType.full_file
    PAGE_IDENTIFICATION = re.compile(r'^\|\|\s+-\s+\w+\s+(.*?)\s*-\s*$')

    def __init__(self):
        super().__init__()

    def worker(self, *args):
        """Sometimes digits of page number get lost when typing."""
        for start, par in (p for p in args[0].items() if len(p[1]) == 1):
            line = par[0]
            if not line.startswith("||"):
                continue
            match = self.PAGE_IDENTIFICATION.search(line)
            if not match:
                continue
            number = match.groups()[0].split('-')[0] # if it's a range
            # roman number regex returns empty string if nothing found
            if not any(x.isdigit() for x in number) and not \
                        config.ROMAN_NUMBER.search(number).end():
                return self.error(_("A page number was marked up, but the "
                        "actual number has not been inserted."), start)

class PageNumbersWithoutDashes(Mistake):
    """Page number should look like "|| - page 8 -", people sometimes write
"|| page 8"."""
    mistake_type = MistakeType.full_file
    def __init__(self):
        super().__init__()
        pattern = r'\|\|\s*(?:-)?\s*(' + '|'.join(config.PAGENUMBERINGTOKENS) + ')'
        self.pattern = re.compile(pattern.lower())

    def worker(self, *args):
        for num, par in args[0].items():
            if len(par) > 1:
                continue
            first_ln = par[0].lstrip().rstrip()
            if self.pattern.search(first_ln.lower()):
                first_ln = first_ln[2:].lstrip()
                # if all spaces and |'s are stripped, last character and first char must be dashes
                if not first_ln.startswith('-') or not first_ln.endswith('-'):
                    return self.error(_("A \"-\" in the page number is missing,"
                            " required: \"|| - Page xyz -\""), lnum=num)

class DoNotEmbedHtml(OnelinerMistake):
    """Do not use HTML. Especially, don't use <br/>."""
    def __init__(self):
        super().__init__()
        self.pattern = re.compile(r'</?(\w+)\s*/?(:?\s+\w+=["\']\w+["\'])*\s*>')

    def check(self, num, line):
        match = self.pattern.search(line.lower())
        tag = (match.groups()[0] if match else None)
        if tag and tag not in ['div', 'span', 'hr']:
            pos_on_line = match.span()[1]
            if tag.lower() == 'br':
                return self.error(_("\"{tag}\" is not allowed, use a new "
                        "paragraph or a \"\\\" at the end of a line.") \
                        .format(tag=tag.lower()), lnum=num, pos=pos_on_line)
            else:
                return self.error(_("It is not allowed to use HTML tags, "
                        "except for div and span."), lnum=num, pos=pos_on_line)

class EmbeddedHTMLComperators(OnelinerMistake):
    """Instead of &lt;&gt;, use \\< \\>."""
    def __init__(self):
        super().__init__()
        self.pattern = re.compile(r'&(lt|gt);')

    def check(self, num, line):
        matched = self.pattern.search(line.lower())
        if matched:
            return self.error(_("Comparison operators shouldn't be marked up "
                    "in HTML, but with \\< and \\>."), lnum=num,
                        pos=matched.span()[1])

class HeadingsUseEitherUnderliningOrHashes(Mistake):
    mistake_type = MistakeType.headings
    def worker(self, *args):
        for heading in args[0]:
            if heading.get_text().startswith('#'):
                return self.error(_("The heading was underlined and also "
                        "marked with #'s."), lnum=heading.get_line_number())

class ParagraphMayNotEndOnBackslash(Mistake):
    r"""If a paragraph ends on a backslash, the next line will be treated as
    being part of the paragraph. Therefore the intentional paragraph break is
    lost. Example:

        ~~~~
        some text\

        -   item one
        -   item two
        ~~~~"""
    mistake_type = MistakeType.full_file
    def worker(self, *args):
        for start_line, paragraph in args[0].items():
            if paragraph and paragraph[-1].rstrip().endswith('\\'):
                return self.error(_("If a paragraph ends on a \\, the next "
                        "empty line will become part of the paragraph and "
                        "hence the next paragraph is formatted incorrectly."),
                    lnum=start_line + len(paragraph))

class DetectStrayingDollars(OnelinerMistake):
    """An uneven number of dollar signs can indicate either a multi-line formula enclosed by only $...$ or a forgotten closing formula. Both is errorneous."""
    def check(self, lnum, line):
        if not '$' in line:
            return
        line = line.replace("$$", "").replace('\\$', '')
        # count single $-signs
        num_dollars = line.count('$')
        # check that no $<num> (US-american price) is contained in the line:
        if num_dollars == 1:
            index = line.index('$')
            if index < (len(line)-1) and line[index+1].isdigit():
                return

        if num_dollars % 2: # odd number of dollars
            return self.error(_("Line contains uneven number of dollar signs. "
                    "Either a formula wasn't closed or an embedded formula was "
                    "stretched across multiple lines (try double dollars). If "
                    "you meant a real dollar sign, prepend a \\ to it."), lnum)


class TextInItemizeShouldntStartWithItemizeCharacter(Mistake):
    """In an itemize environment, there shoulnd't be a itemize character like "+", "-", "*" directly after an itemize character. For instance:

            - item 1
            -   item 2
            - + much more items

This will lead to Pandoc identifying these as sublists.
"""
    mistake_type = MistakeType.full_file
    def __init__(self):
        super().__init__()
        # match "- 1." or "* +" or "- +" or "1. -"
        self._pattern = re.compile(r'''^\s*(?:-|\+|\*|\d+\.)\s+
            # prohibit matching a horizontal rule (* * * or - - -) and bold / slanted text and also not european-style dates
            (?![\*-]\s[\*-]| # horizontal rule
                \*\*|\*\*?[a-z|A-Z]| # bold or slanted text
                \d+\.[0-9a-zA-z]) # european-style dates dd.mm.YYYY
                (.*)$''', re.VERBOSE)

    def worker(self, *args):
        is_enum_item = re.compile(r'^\d{1,2}\.') # only match enumerations, not (German) dates like "2016."

        for start_line, paragraph in args[0].items():
            enumeration_signs = 0
            errorneous_line = 0
            for rel_lnum, line in enumerate(paragraph):
                match = self._pattern.search(line)
                if match and match.groups()[0]: # didn't match the empty string
                    enumeration_signs += 1
                    text = match.groups()[0]
                    if text[0] in ['-', '+'] or is_enum_item.search(text):
                        errorneous_line = start_line + rel_lnum
                        if enumeration_signs >= 2: # it's a proper enumeration
                            break # an error case was encountered
            if errorneous_line:
                return self.error(_("In enumerations and lists, the enumeration"
                        " character may not immediately be followed by another "
                        "such character, because it will be recognised as a "
                        "sublist. A \\ in front of a character or in front of "
                        "the dot for enumerations will suppress this."),
                    lnum=errorneous_line-1)


class ToDosInImageDescriptionsAreBad(OnelinerMistake):
    """Some people tend to leave "to do" or similar in their material to mark areas as being not completed yet."""
    def __init__(self):
        super().__init__()
        self._todo_pattern = re.compile(r'''
                ((?:to|To|TO)\s*(?:do|Do|DO))\s*
                # expect punctuation, etc. to not match false positives
                (?:\.|,|:|$)
                ''', re.VERBOSE)

    def check(self, lnum, line):
        match = self._todo_pattern.search(line)
        if match:
            return self.error(_("The image description is probably incomplete, "
                    "since \"{marker}\" has been found. ").format(
                        marker=match.groups()[0]), lnum=lnum)


class BrokenImageLinksAreDetected(OnelinerMistake):
    def __init__(self):
        super().__init__()
        # phrase is everything except ()[]; inserted into {0} below for easier readability
        self._pattern = re.compile(r'''^\s*
            (\![^[]+?\]\([^)]+\) # image link where [ has been forgotten
             |\!\[[^]]+\([^)]+\) # image link where ] has been forgotten
             |\!\[[^]]+\][^(]+?\) # image link where ( has been forgotten
             |\[[^]]+\]\s*\([^)]+?\.(?:jpg|png|tif|gif|svg)\) # image link where ! has been forgotten
             |\!\[[^]]+?\]\([^)]+$) # image link where ) has been forgotten
            ''', re.VERBOSE)

    def check(self, num, line):
        if self._pattern.search(line.lower()):
            # check whether ! [ ] ( ) are all in the line, if so, it's a false positive
            for punct in ['(', ')', '[', ']', '!']:
                if not punct in line:
                    return self.error(_("The included image is using wrong "
                            "syntax, the converter will ignore it."), num)

class HyphensFromJustifiedTextWereRemoved(Mistake):
    """When copy-pasting text from i.e. PDFs, it is easy to forget to remove
    the hyphenation at the end of the line. This checker attempts to warn in
    the obvious cases."""
    HYPHENS = ['-', '\xad']
    mistake_type = MistakeType.full_file
    def __init__(self):
        super().__init__()

    def ends_with_hyphen(self, line):
        line = line.rstrip()
        if any(line.endswith(h) for h in self.HYPHENS) and len(line) > 1:
            if line[-2].isalpha(): # part of a word
                return True
        return False

    def worker(self, *args):
        has_next_line = lambda ln, lines: ln < len(lines) - 1
        for start_line, lines in args[0].items():
            # iterate over all lines
            for lnum, line in enumerate(lines):
                # if hyphen and there's a next line
                if self.ends_with_hyphen(line) and has_next_line(lnum, lines):
                    next_line = lines[lnum+1].lstrip()
                    # it was justified text, if next line starts with a word
                    if next_line and next_line[0].isalpha() and not \
                            (next_line.startswith('und') or next_line.startswith('and')):
                        return self.error(_("A hyphen was found which possibly "
                                "originates from copied justified text. This "
                                "will be incorrectly formatted in the output."),
                            start_line + lnum)


class DetectEmptyImageDescriptions(Mistake):
    """Detect headings in bilder.md with no described images below."""
    mistake_type = MistakeType.headings_dir
    def get_heading_ranges(self, headings, last_line):
        for pair in common.pairwise(headings):
            yield tuple(p.get_line_number() for p in pair)
        # at the end, emit a pair with last heading line number and the line
        # number from the end of the document
        if headings:
            # last_line + 1 is necessary, because normally, -1 is subtracted to
            # not include the next heading in the range. At the enf of the
            # file, all lines should be included, because they might be part of
            # the image description
            yield (headings[-1].get_line_number(), last_line + 1)

    def worker(self, *args):
        imgdesc = [(p, h) for p, h in args[0].items()
                if os.path.basename(p).lower() == 'bilder.md']
        if not imgdesc:
            return
        path, headings = imgdesc[0]
        with open(path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        headings = [h for h in headings if h.get_level() > 1] # ignore level 1 headings
        for start_line, end_line in self.get_heading_ranges(headings, len(lines)):
            image_description_found = False
            for line in lines[start_line : end_line-1]: # lines counted from 1; ignore heading line
                if not line.strip():
                    continue # nothing found, check next line
                elif '===' in line or '---' in line:
                    continue # underline of heading needss to be ignored
                else: # some text, not a heading, so image described
                    image_description_found = True
                    break
            if not image_description_found:
                return self.error(_("No image description provided."),
                    lnum=start_line, path=path)

