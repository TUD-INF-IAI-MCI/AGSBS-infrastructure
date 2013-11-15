import os

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
                output.append( '\n%s' % (heading.get_markdown_link() ) + '\n')

        self.output = output

    def get_markdown_page(self):
        return ''.join(self.output)



