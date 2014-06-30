# -*- coding: utf-8 -*-
# Copyright (c) 2014 Jens Voegler


DEFAULT_KATEPROJECT_FILE_TEMPLATE = """
{
 "name" : "%(projectName)s" ,
 "files": 
\t[{
 "filters": [ "*.md", "*.html", "*.jpg", "*.png", "*.dcxml"],
\t\t"directory": "%(projectDirectory)s"
\t }
\t]
}
"""
