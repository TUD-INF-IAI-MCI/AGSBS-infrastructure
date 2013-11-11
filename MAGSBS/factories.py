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

        chapter_number = 1
        for chapter, headings in self.__index.items():
            # strip markdown ending
            filename = 'k'+chapter[1:3] + os.sep + chapter[:-2] + 'html'
            chapter = chapter[1:] # strip trailing k
            if(chapter.endswith('.md')):
                chapter = chapter[:-3]
            else:
                raise ValueError('File must end with .md')
            if(len(chapter)>6):
                raise ValueError('Only files of form kxx.md" are accepted.')
            chapter = chapter[1:3]
            
            # insert first-level-heading by hand, MUST be first heading!
            if(not headings[0][0] == 1):
                raise ValueError("First heading needs to be a h1 heading.")
            else:
                output.append( '\n[%s. %s](%s)\n' % (chapter_number,
                        headings[0][2], filename) )

            # get list of headings (and exclude page numbers); raise error if
            # first-level-heading occures twice
            headings = [h for h in headings[1:]   if(h[0] < 6  and  h[0] > 1)]
            for h_num, heading in enumerate(headings):
                output.append( '\n[%s.%s. %s](%s)\n' %
                                (chapter_number, h_num+1, heading[2],
                                filename + '#' + heading[1])
                             )
            chapter_number += 1

        self.output = output

    def get_markdown_page(self):
        return ''.join(self.output)



