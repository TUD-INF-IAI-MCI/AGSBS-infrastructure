# This is free software, licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2015 Sebastian Humenda <shumenda |at| gmx |dot| de>
"""This module contains all factories for autote processes for lecture creation.
This is e.g. the creation of a table of contents, etc."""

import os
from . import datastructures
from . import datastructures
from . import config
from .errors import MissingMandatoryField
_ = config._


class ChapterNumberEnumerator:
    """Track headings and calculate chapter numbers. For that to work it is
    crucial that the headings are registered in the right order.

    Example:
    c = ChapterNumberEnumerator()
    c.register(some_level1_heading)
    c.register(some_level1_heading)
    c.register(some_level2_heading)
    assert c.fmtChapterNumber()) == '2.1'
    """
    def __init__(self):
        self.__registered = [0, 0, 0, 0, 0, 0]
        self.__lastchapter = None

    def register(self, heading):
        """Register heading for chapter number calculation.
        Return the result of fmtChapterNumber; fmtChapterNumber will return the same
        after this register call."""
        if not hasattr(heading, 'get_level') or not hasattr(heading,
                'get_chapter_number'):
            raise TypeError("The heading object must provide a "
                "get_level and get_chapter_number method, got " + str(type(heading)))
        if heading.get_chapter_number() != self.__lastchapter:
            # new chapter, new enumeration
            self.__registered = list(0 for x in range(len(self.__registered)))
            self.__registered[0] = heading.get_chapter_number()
            self.__lastchapter = heading.get_chapter_number()
        # increment received level
        if heading.get_level() > 1:
            self.__registered[heading.get_level()-1] += 1
            # all headings below level must be reset to 0 (e.g. 2.1.1 is followed by
            # 2.2 not 2.2.1)
            for index in range(heading.get_level(), len(self.__registered)):
                self.__registered[index] = 0
        return self.fmtChapterNumber()

    def fmtChapterNumber(self):
        """Format the current chapter number (as calculated by all registered
                headings) as a chapter num (string), delimited by "."."""
        return '.'.join(map(str, filter(bool, self.__registered)))


class index2markdown_TOC():
    # ToDo: make this class not dependent on the current working directory
    """index2markdown_TOC( OrderedDict(), lang, depth=4, use_appendix_prefix=False)
Take the ordered dict produced by create_index() and transform it  to a markdown
file. The language specifies in which language to output the title of the TOC.

This class must be run from the lecture root.
"""
    def __init__(self, index):
        self.__index = index
        c = config.confFactory()
        self.conf  = c.get_conf_instance()
        self.__use_appendix_prefix = self.conf['appendixPrefix']
        self.__headings = {'appendix' : [], 'normal' : [], 'preface': []}
        self.transform_index()

    def transform_index(self):
        """Walk through dictionary of file names and headings and create lists
for later output. For each heading, decide whether conf['depth'] > heading.depth,
and in- or exclude it."""
        enumerator = ChapterNumberEnumerator()
        for path, headings in self.__index.items():
            dummy, file = os.path.split(path)
            dummy, directory_above = os.path.split(dummy)
            for heading in headings:
                if heading.get_level() > self.conf['tocDepth']:
                    continue # skip those headings

                type = heading.get_type().name.lower()
                enumerator.register(heading)
                self.__headings[type].append(self.__heading2toclink(enumerator,
                    heading, directory_above, file))


    def get_markdown_page(self):
        """Format all headings into a markdown page."""
        title = _('table of contents').title() + ' - ' + \
                self.conf['lecturetitle']
        output = [ '%s\n' % title, '='*len(title), '\n\n'  ]
        if self.__headings['preface']:
            output.append('{}\n{}\n'.format(_('preface').capitalize(),
                '-'*len(_('preface'))))
            for h in self.__headings['preface']:
                output.append('\n%s\\' % h)
            output[-1] = output[-1][:-1] # strip last backslash
            output.append('\n\n{}'.format(_('chapters').title()))
            output.append('\n--------\n\n')
        for num, h in enumerate(self.__headings['normal']):
            output.append(h)
            if not num == len(self.__headings['normal'])-1:
                output.append('\\\n')
        if self.__headings['appendix']:
            output.append('\n\n\n')
            # only appendix heading if appendix chapters are not prefixed
            if not self.__use_appendix_prefix:
                output.append('{}\n------\n\n'.format(_('appendix').title()))
            for h in self.__headings['appendix']:
                output.append('%s\\\n' % h)

        if os.path.exists("info.md"):
            output.append('\n\n* * * * *\n\n[')
            output.append(_("remarks about the accessible edited version"))
            output.append('](info.html)\n')
        return ''.join(output) + '\n'

    def __heading2toclink(self, enumerator, heading, directory, file):
        """Convert a heading to a link as required in a TOC.
        The enumerator object must provide a method called fmtChapterNumber
        yielding the formatted chapter number."""
        prefix = ''
        if self.__use_appendix_prefix and \
                heading.get_type() == datastructures.Heading.Type.APPENDIX:
            prefix = 'A.'
        if not file.endswith('.md'):
            raise ValueError("File name must end on .md!")
        else:
            file = file[:-2] + 'html'
        return '[{}{}. {}]({}/{}#{})'.format(prefix,
                enumerator.fmtChapterNumber(), heading.get_text(), directory,
                file, heading.get_id())


#pylint: disable=too-many-instance-attributes
class ImageDescription():
    """
ImageDescription(image_path)


Store and format a picture description. It is important here to read all the
method's doc-strings to understand how this class works.

An example:

i = image_description('bilder/bla.jpg')
i.set_description('''
A cow on a meadow eating gras and staring a bit stupidly. It says "moo".
    ''')  # setting the description is optional
i.use_outsourced_descriptions(True) # outsource image descriptions
                                      # outsourced when length of alt attribut > 100
i.set_title("a cow on a meadow") # not necessary for images which are not outsourced
data = i.get_output()

data is either a 1-tupel or a 2-tupel. A 1-tupel contains the string for an
embedded image. A 2-tupel means in the position 0 the string for the main
document and in position 1 the string for the outsourcing document.
"""
    def __init__(self, image_path):
        c = config.confFactory().get_conf_instance()
        self.__image_path = image_path
        self.__description = '\n'
        self.__title = None
        self.__outsource_descriptions = False
        # maximum length of image description before outsourcing it
        self.img_maxlength = 100
        self.__outsource_path = _('images') + '.' + c['format']

    def set_description(self, desc):
        """Set alternative image description."""
        self.__description = desc

    def set_title(self, title):
        """Set the title for an image description. Only use, when image is
        outsourced."""
        self.__title = title

    def get_title(self):
        return self.__title

    def set_outsource_descriptions(self, flag):
        """If set to True, descriptions are always outsourced."""
        self.__outsource_descriptions = flag

    def get_outsource_path(self):
        return self.__outsource_path

    def get_outsourcing_link(self):
        """Return the link for the case that the picture is excluded."""
        label = datastructures.gen_id( self.get_title() )
        link_text = _('external image description')
        return '[ ![%s](%s) ](%s#%s)' % (link_text, self.__image_path,
                self.get_outsource_path(), label)

    def get_inline_description(self):
        """Generate markdown image with description."""
        desc = self.__description.replace('\n',' ').replace('\r',' ').replace(' ',' ')
        return '![%s](%s)' % (desc, self.__image_path)

    def __get_outsourced_title(self):
        if(not self.__title):
            raise MissingMandatoryField('"title" must be set for outsourced images.')
        text = '### ' + _('image description of image').capitalize()
        text += ' ' + self.__title
        return text

    def will_be_outsourced(self):
        """Determine, depending on the setting, whether description is
        outsourced. If outsourced is set, it will always return true, otherwise
        it'll depend on the description length."""
        if self.__outsource_descriptions:
            return True
        return (True if len(self.__description) > self.img_maxlength else False)

    def get_output(self):
        """Dispatcher function for get_inline_description and
    get_outsourcing_link; will be either a tuple of (link, content for
            outsourced description) or just a tuple with the image
    description/the reference to the image. It'll always return an outsourced
    description if set by set_outsource_descriptions(True) or will automatically
    exclude images longer than 100 characters."""
        if not self.will_be_outsourced():
            return (self.get_inline_description(), )
        external_text = self.__get_outsourced_title() + '\n\n' +\
                    self.__description + '\n\n* * * * *\n'
        return (self.get_outsourcing_link(), external_text)

