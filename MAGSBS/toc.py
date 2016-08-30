# This is free software, licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2016 Sebastian Humenda <shumenda |at|gmx |dot| de>
"""This file contains the classes necessary for the automated index
generation."""

import collections
import os
import re

from . import config, errors, mparser, filesystem as fs, datastructures


# alias datastructures.Heading.Type
HeadingType = datastructures.Heading.Type
class HeadingIndexer():
    """create_index(dir)

Walk the file system tree from "dir" and have a look in all files which end on
.md. Take headings of level 1 or 2 and add it to the index.

Format of index: dict of lists: every filename is the key, the list of heading
[objects] is the value in the OrderedDict()."""
    def __init__(self, path):
        if not os.path.exists(path):
            raise errors.StructuralError("Directory doesn't exist.", path)
        self.__dir = path
        self.__index = collections.OrderedDict()


    def is_empty(self):
        return not bool(self.__index)

    def walk(self):
        """walk()
By calling the function, the actual index is build."""
        conf = config.confFactory().get_conf_instance_safe(self.__dir)
        if conf['generateToc'] == 0:
            return # don't generate a TOC
        for directory, directories, files in fs.get_markdown_files(self.__dir):
            for file in files:
                path = os.path.join(directory, file)
                headings = self.__retrieve_headings_from(path)
                if os.path.split(directory)[-1].startswith("anh") :
                    for heading in headings: # reference
                        heading.set_type(datastructures.Heading.Type.APPENDIX)
                # preface headings
                elif re.search(r'^v\d\d', os.path.split(directory)[-1]):
                    for heading in headings: # reference
                        heading.set_type(datastructures.Heading.Type.PREFACE)

                full_fn = os.path.join( directory, file)
                self.__index[full_fn] = headings


    def __retrieve_headings_from(self, path):
        """Retrieve headings from path and annotate them with 'unedited' if the
        file was not edited yet."""
        with open(path, 'r', encoding='utf-8') as f:
            paragraphs = mparser.file2paragraphs(f.read())
        headings = mparser.extract_headings(path, paragraphs)
        heading_lines = [h.get_line_number() for h in headings]

        all_lines_are_headings = lambda x: all(l.startswith('#') for l in x)
        # check whether any text has been inserted and if not; if so, return
        # unmodified heading list
        for start_line, lines in paragraphs.items():
            if len(lines) > 2:
                # is it an actual heading:
                if not all_lines_are_headings(lines):
                    return headings
            elif len(lines) == 2:
                # only paragraphs with underlined headings or two ##-headings
                # are accepted:
                if not all_lines_are_headings(lines) and \
                        not (('----' in lines[1] or '====' in lines[1]) and start_line in heading_lines):
                    return headings # modification detected, was edited
            else: # paragraph with exactly one line
                if not start_line in heading_lines:
                    return headings

        #  at this point, no modifications found, construct new headings
        conf = config.confFactory().get_conf_instance(path)
        trans = config.Translate()
        trans.set_language(conf['language'])

        for heading in headings:
            heading.set_text('{} ({})'.format(heading.get_text(),
                trans.get_translation('not edited')))
        return headings


    def get_index(self):
        tmp = collections.OrderedDict()
        for key in sorted(self.__index):
            tmp[key] = self.__index[ key ]
        return tmp

class ChapterNumberEnumerator:
    """Track headings and calculate chapter numbers. For that to work it is
    crucial that the headings are registered in the right order.

    Example:
    c = ChapterNumberEnumerator()
    c.register(some_level1_heading)
    c.register(some_level1_heading)
    c.register(some_level2_heading)
    assert c.get_heading_enumeration()) == '2.1'
    """
    MAX_DEPTH = 6
    def __init__(self):
        self.__registered = [0 for x in range(6)]
        self.__lastchapter = None

    def register(self, heading):
        """Register heading for chapter number calculation.
        For this the heading object must provide the get_level and
        get_chapter_number methods."""
        if not hasattr(heading, 'get_level') or not hasattr(heading,
                'get_chapter_number'):
            raise TypeError("The heading object must provide a "
                "get_level and get_chapter_number method, got " + str(type(heading)))
        elif heading.get_chapter_number() is None or heading.get_level() is None:
            raise ValueError(("Neither get_level() nor get_chapter_number() "
                "may be None for the given heading"))
            # each chapter has its own sections, so if new chapter, reset all
            # section counters
        if heading.get_chapter_number() != self.__lastchapter:
            self.__registered = [0 for x in range(ChapterNumberEnumerator.MAX_DEPTH)]
            self.__registered[0] = heading.get_chapter_number()
            self.__lastchapter = heading.get_chapter_number()
        # increment received level
        if heading.get_level() > 1:
            self.__registered[heading.get_level()-1] += 1
            # all headings below level must be reset to 0 (e.g. 2.1.1 is followed by
            # 2.2 not 2.2.1)
            for index in range(heading.get_level(), len(self.__registered)):
                self.__registered[index] = 0

    def get_heading_enumeration(self):
        """Return current number/enumeration as shown in table of contents.
        The result is a list of integers representing the current heading."""
        chapter_number = self.__registered[:]
        # strip all 0's beginning from the right; this way leading 0's are kept
        while chapter_number and chapter_number[-1] == 0:
            chapter_number = chapter_number[:-1]
        return chapter_number


class TOCFormatter:
    """TOCFormatter(OrderedDict(), lang, depth=4, use_appendix_prefix=False)
Take the ordered dict produced by HeadingIndexer() and transform it
to a markdown file containing the formatted table of contents. With the
specified path, the TOCFormatter is able to fetch the configuration to format
the TOC corrrectly."""
    def __init__(self, index, path):
        self.__index = index
        self.__path = path
        c = config.confFactory()
        self.conf = c.get_conf_instance(path)
        self.__use_appendix_prefix = self.conf['appendixPrefix']
        self.__headings = {HeadingType.APPENDIX : [], HeadingType.NORMAL : [],
                HeadingType.PREFACE: []}
        if self.conf['generateToc'] == 1:
            self.build_index()

    def build_index(self):
        """Walk through dictionary of file names and headings and create cache
        mapping from heading type to a list of headings. The list of headings
        contains 1) chapter number, 2) heading and 3) path to the file. In short
        this method builds the tree of information required for the TOC."""
        enumerators = {HeadingType.NORMAL: ChapterNumberEnumerator(),
                HeadingType.APPENDIX: ChapterNumberEnumerator(),
                HeadingType.PREFACE: ChapterNumberEnumerator()}
        for path, headings in self.__index.items():
            path, file = os.path.split(path)
            directory_above = os.path.split(path)[-1] # necessary for relative link
            for heading in headings:
                if heading.get_level() > self.conf['tocDepth']:
                    continue # skip headings above configured threshold
                h_type = heading.get_type()
                if not isinstance(h_type, HeadingType):
                    raise TypeError(("Internal error: Heading %s has incorrect"
                            " heading type %s\nFile: %s") % (heading.get_text(),
                                repr(type(h_type)), os.path.join(directory_above, file)))
                enumerators[h_type].register(heading)
                self.__headings[h_type].append((enumerators[h_type].get_heading_enumeration(),
                    heading, os.path.join(directory_above, file)))



    def format(self):
        """Format all headings into a markdown page."""
        if self.conf['generateToc'] == 0:
            return ''
        l10n = config.Translate()
        l10n.set_language(self.conf['language'])
        _ = l10n.get_translation
        title = _('table of contents').title() + ' - ' + \
                self.conf['lecturetitle']
        output = ['%s\n' % title, '='*len(title), '\n\n']
        def add_entry(file_name, toc_entry):
            if os.path.exists(file_name) or os.path.exists(file_name.lower()):
                output.append(toc_entry)

        # if manual title page exists, link to it
        add_entry("titel.md", '[%s](titel.%s\n\n' % (_('title page').title(),
                self.conf['format']))

        if self.__headings[HeadingType.PREFACE]:
            output += self.format_section(_('preface').title(),
                    self.__headings[HeadingType.PREFACE])

        # include section title "chapters" if a preface exists
        output += self.format_section(
                _('chapters').title() if self.__headings[HeadingType.PREFACE] else None,
                self.__headings[HeadingType.NORMAL])
        if self.__headings[HeadingType.APPENDIX]:
            title = (None if self.__use_appendix_prefix else _('appendix').title())
            output += self.format_section(title, self.__headings[HeadingType.APPENDIX])
        output.append('\n\n')

        add_entry('glossar.md',
                '[{}](glossar.{})\\\n'.format(_('glossary').capitalize(),
            self.conf['format']))
        add_entry('index.md', '[{}](index.{})\\\n'.format(_('index').title(),
            self.conf['format']))
        add_entry('kurz.md', '[{}](kurz.{})\\\n'.format(
                _('list of abbreviations').capitalize(), self.conf['format']))
        add_entry('taktil.md', '[{}](taktil.{})\\\n'.format(
                _('list of tactile graphics').capitalize(), self.conf['format']))
        add_entry('copyright.md', '[{}](copyright.{})\\\n'.format(
                _('copyright notice').capitalize(), self.conf['format']))

        if output[-1].endswith('\\\n'): # strip \\ from last line
            output[-1] = output[-1][:-2] + '\n'

        # include info.md, if it exists
        add_entry("info.md", ('\n\n* * * * *\n\n[{}](info.{})\n').format(
                _("remarks about the accessible version").capitalize(),
                self.conf['format']))
        return ''.join(output) + '\n'

    def format_section(self, title, headings):
        """Format a section of the table of contents. Sections are i.e. appendix
        or preface. Title can be none to create a section without heading.
        Returned is a list of chunks which can be joined to a string."""
        chunks = []
        if title:
            chunks = [title, '\n', '-' * len(title), '\n\n']
        for index, (chapter_number, heading, path) in enumerate(headings):
            chunks.append('\n%s' % self.__heading2toclink(chapter_number,
                heading, path))
            if index != len(headings)-1:
                chunks.append('\\')
        chunks.append('\n\n')
        return chunks


    def __heading2toclink(self, chapter_number, heading, path):
        """Convert a heading to a link as required in a TOC.
        The enumerator object must provide a method called format_chap_number
        yielding the formatted chapter number."""
        prefix = ''
        if self.__use_appendix_prefix and heading.get_type() == HeadingType.APPENDIX:
            prefix = 'A.'
        path = path.replace('.md', '.' + self.conf['format'])
        return '[{}{}. {}]({}#{})'.format(prefix,
                '.'.join(map(str, chapter_number)), # (int, int...) -> str
                heading.get_text(), path, heading.get_id())



