# This is free software, licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2014 Sebastian Humenda <shumenda@gmx.de>

import os, sys
from . import datastructures
from . import filesystem
from . import config
from .errors import TOCError, MissingMandatoryField
_ = config._

if(int(sys.version[0]) >= 3):
    import urllib.parse
    URLencode = urllib.parse.urlencode
else:
    import urllib
    URLencode = urllib.urlencode

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
        self.lang = self.conf[ 'language' ]
        self.depth = self.conf[ 'tocDepth' ]
        self.__use_appendix_prefix = self.conf[ 'appendixPrefix']
        # two lists for headings
        self.__main = []
        self.__appendix = []
        self.__preface = []
        self.transform_index()

    def transform_index(self):
        """Walk through dictionary of file names and headings and create lists
for later output. For each heading, decide whether self.depth > heading.depth,
and in- or exclude it."""
        for fn, headings in self.__index.items():
            headings = [h for h in headings   if(not h.is_shadow_heading())]
            for heading in headings:
                if(heading.get_level() > self.depth):
                    continue # skip those headings
                else:
                    if(heading.get_type() == 'appendix'):
                        if(self.__use_appendix_prefix): h.use_appendix_prefix(True)
                        self.__appendix.append(heading.get_markdown_link())
                    elif(heading.get_type() == 'preface'):
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


class image_description():
    """
image_description(self, image_path, description)


Store and format a picture description. It is important here to read all the
method's doc-strings to understand how this class works.

An example:

i = image_description('bilder/bla.jpg', lang='de')  # language specifies whether bilder.md or images.md is used
i.set_description('''
A cow on a meadow eating gras and staring a bit stupidly. It says "moo".
    '''  # setting the description is optional
i.use_outsourced_descriptions( True ) # outsource image descriptions
                                      # outsourced when length of alt attribut > 100
i.set_title("a cow on a meadow") # not necessary for images which are not outsourced
data = i.get_output()

data is either a 1-tupel or a 2-tupel. A 1-tupel contains the string for an
embedded image. A 2-tupel means in the position 0 the string for the main
document and in position 1 the string for the outsourcing document.
"""
    def __init__(self, image_path):
        c = config.confFactory()
        c = c.get_conf_instance()
        self.format = c['format']
        self.image_path = image_path
        self.description = '\n'
        self.lang = c['language']
        self.title = None
        self.outsource_long_descriptions = True
        # maximum length of image description before outsourcing it
        self.img_maxlength = 100
        self.exclusion_file_name = _('images')

    def set_description(self, desc): self.description = desc
    def set_title(self, title):
        self.title = title
    def get_title(self): return self.title
    def use_outsourced_descriptions(self, flag):
        self.outsource_long_descriptions = flag
    def get_outsourcing_path(self):
        return self.exclusion_file_name + '.' + self.format

    def get_outsourcing_link(self):
        """Return the link for the case that the picture is excluded."""
        id = datastructures.gen_id( self.get_title() )
        link_text = _('description of image outsourced')
        return '[ ![%s](%s) ](%s#%s)' % (link_text, self.image_path,
                self.get_outsourcing_path(), id)

    def get_inline_description(self):
        """Return the markdown syntax for an inline image description."""
        desc = self.description.replace('\n',' ').replace('\r',' ').replace(' ',' ')
        return '![%s](%s)' % (desc, self.image_path)

    def __get_outsourced_title(self):
        if(not self.title):
            raise MissingMandatoryField('"title" must be set for outsourced images.')
        text = '###' + _('image description of').capitalize()
        text += self.title
        return text

    def get_output(self):
        """Dispatcher function for get_inline_description and
get_outsourcing_link; will be either a tuple of (link, content for outsourced
    description) or just a tuple with the image description/the reference to the
image. It'll always return a inline description if set by
use_outsourced_descriptions(False) or will automatically exclude images longer
than 100 characters."""
        if(not self.outsource_long_descriptions):
            if(len(self.description) < self.img_maxlength):
                return (self.get_inline_description(), )
        if(not self.title):
            raise MissingMandatoryField("Image got outsourced, but no title present.")
        external_text = self.__get_outsourced_title() + '\n\n' +\
                    self.description + '\n\n* * * * *\n'
        return (self.get_outsourcing_link(), external_text)

