# -*- coding: utf-8 -*-

"""Getting started:

# create index:
c = create_index('.')
c.walk()

# index 2 markdown:
md = index2markdown_TOC(c.get_data(), 'de')
my_fancy_page = c.get_markdown_page()
"""

import os, sys, codecs, re
import collections

# internal imports
#from filesystem import *
#from factories import *
import MAGSBS.filesystem
import MAGSBS.factories
import MAGSBS.pandoc
import MAGSBS.config
import MAGSBS.master
import MAGSBS.errors


#__all__ = ['config, 'pandoc']

