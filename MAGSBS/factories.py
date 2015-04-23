# This is free software, licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2015 Sebastian Humenda <shumenda |at| gmx |dot| de>
"""This module contains all file system related functionality. Starting from a
customized os.walk()-alike function to classes modifying Markdown documents."""

import os
from . import datastructures
from .datastructures import Heading
from . import config
from .errors import MissingMandatoryField
_ = config._


class index2markdown_TOC():
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
        # three lists for headings
        self.__main = []
        self.__appendix = []
        self.__preface = []
        self.transform_index()

    def transform_index(self):
        """Walk through dictionary of file names and headings and create lists
for later output. For each heading, decide whether conf['depth'] > heading.depth,
and in- or exclude it."""
        for headings in self.__index.values():
            for heading in headings:
                if heading.get_level() > self.conf['tocDepth']:
                    continue # skip those headings

                if heading.get_type() == Heading.Type.APPENDIX:
                    if self.__use_appendix_prefix:
                        heading.use_appendix_prefix(True)
                    self.__appendix.append(heading.get_markdown_link())
                elif heading.get_type() == Heading.Type.PREFACE:
                    self.__preface.append( heading.get_markdown_link() )
                else:
                    self.__main.append(heading.get_markdown_link())

    def get_markdown_page(self):
        title = _('table of contents').title() + ' - ' + \
                self.conf['lecturetitle']
        output = [ '%s\n' % title, '='*len(title), '\n\n'  ]
        if(self.__preface):
            output.append( _('preface').capitalize() + '\n' + '-'*len(_('preface')) + '\n\n')
            for h in self.__preface:
                output += [ h, '\\\n']
            # strip last \ at end of last line
            output[-1] = output[-1][:-2]
            output.append('\n\n')
            output.append(_('chapters').title())
            output.append('\n--------\n\n')
        for num,h in enumerate(self.__main):
            output.append( h )
            if(not num == len(self.__main)-1):
                output.append('\\\n')
        if(len(self.__appendix)>0):
            output.append('\n\n\n')
            if(not self.__use_appendix_prefix):
                output.append(_('appendix').title())
                output.append('\n------\n\n')
            for h in self.__appendix:
                output.append( h )
                output.append('\\\n')

        if( os.path.exists( "info.md" ) ):
            output.append('\n\n* * * * *\n\n[')
            output.append(_("remarks about the accessible edited version"))
            output.append('](info.html)')
            output.append("\n")

        return ''.join(output) + '\n'


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

