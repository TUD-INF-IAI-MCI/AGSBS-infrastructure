# -*- coding: utf-8 -*-

import os, sys, codecs, re
import collections

# internal imports
from filesystem import *
from factories import *


# -- if not imported but run as main module, test functionality --


def test_markdown_parser():
    m = markdownHeadingParser("Heya\n====\n\nImportant advisories\n---------\n\n\n###### - Seite 6 -\n",
                'k01', 'k0103.md')
    m.parse()
    for item in m.get_heading_list():
        print(item.get_markdown_link())
    print("Done.")

def test_file_walk():
    c = create_index('examples')
    c.walk()
    for key, value in c.get_index().items():
        print(key+' '+'\n  '.join([v.get_markdown_link() for v in value])+'\n')
    return c.get_index()

def test_index2markdown_TOC():
    c = create_index('examples')
    c.walk()
    idx = index2markdown_TOC(c.get_index(), 'de')
    print(idx.get_markdown_page())


def test_pagenumber_indexing():
    p=page_navigation('examples', 5, lang='de')
    p.iterate()


def test_image_descriptions():
    i = image_description('bilder/bla.jpg', '''
A cow on a meadow eating pink, already short gras and staring a bit stupidly. It
says in a balloon "moo". The balloon collides with the clouds. BTW, the
description is just that long to enforce outsourcing.
    ''')
    i.use_outsourced_descriptions( True ) # outsource image descriptions > 100
    i.set_outsourcing_path('k01/images.md')  # necessary for outsourcing!
    i.set_chapter_path('k01/k01.md')   # necessary for outsourcing! 
    i.set_title("a cow on a meadow")
    data = i.get_output()
    if(len(data) == 1):
        print('k01/k01.html:\n\n%s' % data[0])
    else:
        print('k01/k01.html:\n\n%s\n\n---------\n\nbilder.md:\n\n%s' % (data[0], data[1]))



if __name__ == '__main__':
    #test_markdown_parser()
    #test_file_walk()
    #test_index2markdown_TOC()
    #test_pagenumber_indexing()
    #test_image_linking()
    test_image_descriptions()
