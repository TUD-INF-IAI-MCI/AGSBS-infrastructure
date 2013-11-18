# -*- coding: utf-8 -*-

import os, sys
import datastructures

if(int(sys.version[0]) >= 3):
    import urllib.parse
    URLencode = urllib.parse.urlencode
else:
    import urllib
    URLencode = urllib.urlencode

class index2markdown_TOC():
    """index2markdown_TOC( OrderedDict(), lang )

Take the ordered dict produced by create_index() and transform it  to a markdown
file. The language specifies in which language to output the title of the TOC.
"""
    def __init__(self, index, lang='de'):
        self.__index = index
        self.lang = lang
        self.__output = []
        self.transform_index()

    def transform_index(self):
        """Walk through the dict; they key (file name) is used to determine the
heading number. It is assumed, that file names HAVE the form of k01.md for
chapter 1 and NOT k1.html or something similar.

Currently, there are NO files like k0101 recognized. It makes absolutely no
sense to device chapters further then by 1.1 in output files. Everything else is
fragmentation!"""
        output = [ ('Inhaltsverzeichnis' if self.lang=='de'
                    else 'Table Of Contents') ]
        output += ['\n=============\n\n']

        for fn, headings in self.__index.items():
            headings = [h for h in headings   if(not h.is_shadow_heading())]
            for heading in headings:
                output.append( '\n%s\n' % (heading.get_markdown_link() ))

        self.output = output

    def get_markdown_page(self):
        return ''.join(self.output)


class image_description():
    """
image_description(self, image_path, description)


Store and format a picture description. It is important here to read all the
method's doc-strings to understand how this class works.

An example:

i = image_description('bilder/bla.jpg', 'A cow making "moo"')
i.use_outsourced_descriptions( True ) # outsource image descriptions > 100
i.set_outsourcing_path('k01/images.md')  # necessary for outsourcing!
# needs to be HTML, for the link in the output format
i.set_chapter_path('k01/k01.html')   # necessary for outsourcing! 
data = i.get_output()

data can be a tuple with one element (image directive with alternative
description). When the tuple has, the first item is the text for the chapter,
containing the image reference and a link to the outsourced image descrption,
contained in the second item.
"""
    def __init__(self, image_path, description):
        self.image_path = image_path
        self.enc = 'utf-8'
        self.description = description
        self.lang = 'de'
        self.exclusion_path = ('bilder.md' if self.lang == 'de' else
                'images.md')
        self.outsource_long_descriptions = True
        # maximum length of image description before outsourcing it
        self.img_maxlength = 100
        self.chapter_path = None

    def set_chapter_path(self, path): self.chapter_path = path
    def use_outsourced_descriptions(self, flag):
        self.outsource_long_descriptions = flag
    def set_outsourcing_path(self, path):
        self.exclusion_path = path

    def get_outsourcing_link(self, title):
        """Return the link for the case that the picture is excluded."""
        # generate from the title the part of the link after the #. Important:
        # urlencode only encodes key:value, so we must strip the trailing '='
        # and we must replace the '+' through "%20"
        id = URLencode({'':title}).replace('+','%20')[1:]
        link_text = ('Bildbeschreibung ausgelagert' if self.lang == 'de'
                            else 'description of image outsourced')
        return '[%s](%s#%s)' % (link_text, self.image_path, id)

    def get_inline_description(self, title):
        """Return the markdown syntax for a image description."""
        return '![%s](%s)' % (title, self.image_path)

    def __get_outsourced_title(self, title):
        text = ('### Bildbeschreibung von ' if self.lang == 'de' else
                        'Image description of ')
        text += title
        return text

    def get_output(self, title):
        """Dispatcher function for get_inline_description and
get_outsourcing_link; will be either a tuple of (link, content for outsourced
    description) or just a tuple with the image description/the reference to the
image. It'll always return a inline description if set by
use_outsourced_descriptions(False) or will automatically exclude images longer
than 100 characters."""
        if(not self.outsource_long_descriptions
                or len(self.description) < self.img_maxlength):
            return (get_inline_description(title), )
        else:
            external_text = []
            external_text += [self.__get_outsourced_title( title )]
            external_text += ['\n\n', self.description,'\n\n']
            #external_text += ['[%s](%s#%s' % (
            #        ('zurück' if self.lang=='de' else 'back'),
            #        self.chapter_path, 
            #        datastructures.gen_id( title )) ]
            external_text.append('\n\n* * * * *\n')

            return (self.get_outsourcing_link( title ),
                    ''.join( external_text))

