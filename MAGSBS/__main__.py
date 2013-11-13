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

if __name__ == '__main__':
    #test_markdown_parser()
    #test_file_walk()
    #test_index2markdown_TOC()
    test_pagenumber_indexing()
