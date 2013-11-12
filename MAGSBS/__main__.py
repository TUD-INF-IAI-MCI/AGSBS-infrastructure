# -*- coding: utf-8 -*-

import os, sys, codecs, re
import collections

# internal imports
from filesystem import *
from factories import *


# -- if not imported but run as main module, test functionality --


def test_markdown_parser():
    m = markdownParser("Heya\n====\n\nImportant advisories\n---------\n\n\n###### - Seite 6 -\n")
    m.parse()
    for item in m.get_data():
        print(repr(item))
    print("Done.")

def test_file_walk():
    c = create_index('examples')
    c.walk()
    for key, value in c.get_index().items():
        print(key+repr(value)+'\n\n')
    return c.get_index()

def test_index2markdown_TOC():
    idx = test_file_walk()
    c = index2markdown_TOC(idx, 'de')
    print(c.get_markdown_page())

def test_pagenumber_indexing():
    p=page_navigation('examples', 5, lang='de')
    print("echo")
    p.iterate()

if __name__ == '__main__':
    #test_markdown_parser()
    #test_file_walk()
    #test_index2markdown_TOC()
    #test_index2markdown_TOC()
    test_pagenumber_indexing()
