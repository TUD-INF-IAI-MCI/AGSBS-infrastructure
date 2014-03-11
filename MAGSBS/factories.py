# -*- coding: utf-8 -*-

import os, sys
import datastructures, filesystem
from errors import TOCError

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
    def __init__(self, index, lang='de', depth=4, use_appendix_prefix=False):
        self.__index = index
        self.lang = lang
        self.depth = depth
        self.__use_appendix_prefix = use_appendix_prefix
        # two lists for headings
        self.__main = []
        self.__appendix = []
        self.__preface = filesystem.get_preface()
        self.transform_index()

    def transform_index(self):
        """Walk through dictionary of file names and headings and create lists
for later output."""
        for fn, headings in self.__index.items():
            headings = [h for h in headings   if(not h.is_shadow_heading())]
            for heading in headings:
                if(heading.get_level() > self.depth):
                    continue # skip those headings
                elif(heading.is_appendix()):
                    if(self.__use_appendix_prefix): h.use_appendix_prefix(True)
                    self.__appendix.append(heading.get_markdown_link())
                else:
                    self.__main.append(heading.get_markdown_link())

    def get_markdown_page(self):
        output = [ ('Inhaltsverzeichnis' if self.lang=='de'
                    else 'Table Of Contents') ]
        output.append( '\n=============\n\n' )
        if(self.__preface):
            preface = self.__preface[:-3]
            output.append( '[%s](%s.html)\n\n' % (preface.capitalize(),
                preface))
        for h in self.__main:
            output.append( h )
        if(len(self.__appendix)>0):
            output.append('\n\n')
            if(not self.__use_appendix_prefix):
                output += [ ('Anhang' if self.lang == 'de' else 'Appendix'),
                        '\n------\n\n']
            for h in self.__appendix:
                output.append( h )

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
i.set_chapter_path('k01/') # mandatory
data = i.get_output()

data is either a 1-tupel or a 2-tupel. A 1-tupel contains the string for an
embedded image. A 2-tupel means in the position 0 the string for the main
document and in position 1 the string for the outsourcing document.
"""
    def __init__(self, image_path, lang='de'):
        self.fileending = 'html'
        self.image_path = image_path
        self.description = '\n'
        self.lang = lang
        self.title = 'No title'
        self.outsource_long_descriptions = True
        # maximum length of image description before outsourcing it
        self.img_maxlength = 100
        self.chapter_path = '.'
        self.exclusion_file_name = ('bilder' if lang == 'de' else 'images')\
                self.output_format = 'html'

    def set_description(self, desc): self.description = desc
    def set_chapter_path(self, path):
        self.chapter_path = chapter_path
    def set_title(self, title):
        self.title = title
    def get_title(self): return self.title
    def use_outsourced_descriptions(self, flag):
        self.outsource_long_descriptions = flag
    def get_outsourcing_path(self):
        return os.path.join( self.exclusion_file_name, self.exclusion_file_name
            + '.' + self.format)

    def get_outsourcing_link(self):
        """Return the link for the case that the picture is excluded."""
        id = datastructures.gen_id( self.get_title() )
        link_text = ('Bildbeschreibung ausgelagert' if self.lang == 'de'
                            else 'description of image outsourced')
        return '![ [%s](%s) ](%s#%s)' % (id, link_text,
                    self.image_path, self.get_outsourcing_path(), id)

    def get_inline_description(self):
        """Return the markdown syntax for an inline image description."""
        return '![%s](%s)' % (self.description, self.image_path)

    def __get_outsourced_title(self, title):
        if(not self.title):
            raise MissingMandatoryField('"title" must be set for outsourced images.')
        text = ('### Bildbeschreibung von ' if self.lang == 'de' else
                        'Image description of ')
        text += title
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
        else:
            external_text = self.__get_outsourced_title() + '\n\n' +\
                        self.description + '\n\n* * * * *\n'

            return (self.get_outsourcing_link(), external_text)

