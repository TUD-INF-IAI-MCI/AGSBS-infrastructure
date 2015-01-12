# This is free software licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2014 Sebastian Humenda <shumenda@gmx.de>

"""
This sub-module provides implementations for checking common lecture editing
errors.

In the Mistkerl class, the only one which should be used from outside, there is
a list of "mistakes". Mistkerl iterates through them and takes the appropriate
steps to run the mistake checks.

A mistake is a child of the Mistake class. It can set its priority and its type
(what it wants to see from the document) in its __init__-function. The common
run-function then implements the checking.

All mistakes take a list of arguments (which depends on the set type, see
MistakeType) and return a tuple with (line_number, detailed_error_text_German).

For the documentation of the mistake types, see the appropriate class."""

import re, os, sys
import codecs, collections
import MAGSBS.config as config
import MAGSBS.filesystem as filesystem
import MAGSBS.errors as errors

from .meta import *
from .latex import *
from .markdown import *

class Mistkerl():
    """Wrapper which wraps different levels of errors."""
    def __init__(self):
        self.__issues = [common_latex_errors, page_number_is_paragraph,
                heading_is_paragraph, level_one_heading, oldstyle_pagenumbering,
                itemize_is_paragraph, page_numbering_text_is_lowercase,
                page_string_but_no_page_number, page_string_varies,
                uniform_pagestrings, too_many_headings,
                LaTeXMatricesAreHardToRead, PageNumbersWithoutDashes]
        self.__cache_pnums = collections.OrderedDict()
        self.__cache_headings = collections.OrderedDict()
        self.__output = {}
        self.requested_level = MistakePriority.normal

    def get_issues(self, fname):
        """Instanciate issue classes and filter for file endings."""
        for issue in self.__issues:
            i = issue()
            if(self.get_priority().value >= i.get_priority().value):
                if(fname): # fname exists -> not a directory -> check for extension
                    ext = fname[fname.rfind(".")+1:]
                    if(ext in i.get_file_types()):
                        yield i
                else:
                    yield i
    def set_priority(self, p):
        assert type(p) == MistakePriority
        self.__priority = p
    def get_priority(self): return self.__priority
    def __format_out(self, data):
        if(data[0] == '-'):
            return data[1]
        else:
            return 'Zeile ' + str(data[0]) + ": " + data[1]

    def __append(self, path, value):
        if(value):
            if(not path in self.__output.keys()):
                self.__output[ path ] = []
            self.__output[ path ].append(self.__format_out(value))


    def run(self, path):
        """Take either a file and run checks or do the same for a directory
recursively."""
        last_dir = None
        fw = filesystem.FileWalker(path)
        fw.set_ignore_non_chapter_prefixed(False)
        fw.set_endings([".md","tex"])
        cwd = os.getcwd()
        for directoryname, dir_list, file_list in fw.walk():
            os.chdir(directoryname)
            if(not (last_dir == directoryname)):
                self.run_directory_filters(last_dir)
                last_dir = directoryname


            for file in file_list:
                file_path = os.path.join(directoryname, file)
                try:
                    text = codecs.open(file_path, "r", "utf-8").read()
                except UnicodeDecodeError:
                    self.__append(file_path, ('-','Datei ist nicht in UTF-8 kodiert, bitte waehle "UTF-8" als Zeichensatz im Editor.'))
                    continue
                text = text.replace('\r\n','\n').replace('\r','\n')
                self.__run_filters_on_file(file_path, text)
            os.chdir(cwd)
        # the last directory must be processed, even so there was no directory
        # change
        self.run_directory_filters(directoryname)
        return self.__output
 

    def __run_filters_on_file(self, file_path, text):
        """Execute all filters which operate on one file. Also exclue filters
        which do not match for the file ending."""
        # presort issues
        FullFile = [e for e in self.get_issues(file_path) \
                if e.get_type() == MistakeType.full_file]
        OneLiner = [e for e in self.get_issues(file_path)
                        if e.get_type() == MistakeType.oneliner]
        NeedPnums = [e for e in self.get_issues(file_path)
                    if e.get_type() == MistakeType.need_pagenumbers]
        NeedHeadings = [e for e in self.get_issues(file_path)
                        if e.get_type() == MistakeType.need_headings]

        overlong = False
        for issue in FullFile:
            self.__append(file_path, issue.run(text))
        for num, line in enumerate(text.split('\n')):
            if(num > 2500 and not overlong):
                overlong = True
                self.__append(file_path, ("-", "Die Datei ist zu lang. Um die "+
                    " Navigation zu erleichtern und die einfache Lesbarkeit zu"+
                    " gewährleisten sollten lange Kapitel mit mehr als 2500 " +
                    "Zeilen in mehrere Unterdateien nach dem Schema kxxyy.md "+
                    "der kleiner aufgeteilt werden."))
            for issue in OneLiner:
                if(issue.should_be_run()):
                    res = issue.run(num+1, line)
                    if(res):
                        self.__append(file_path, res)
                        issue.set_run(False)
        # cache headings and page numbers
        pnums = pageNumberExtractor(text)
        hdngs = HeadingExtractor(text)
        self.__cache_pnums[ file_path ] = pnums
        self.__cache_headings[ file_path ] = hdngs

        for issue in NeedPnums:
            self.__append(file_path, issue.run(pnums))
        for issue in NeedHeadings:
            self.__append(file_path, issue.run(hdngs))
                       
    def run_directory_filters(self, dname):
        """Run all filters depending on the output of a directory."""
        if(len(self.__cache_pnums) > 0):
            x = [e for e in self.get_issues(False) if e.get_type() == MistakeType.need_pagenumbers_dir]
            for issue in x:
                self.__append(dname, issue.run(self.__cache_pnums))
        if(len(self.__cache_headings) > 0):
            x = [e for e in self.get_issues(False) if e.get_type() == MistakeType.need_headings_dir]
            for issue in x:
                self.__append(dname, issue.run(self.__cache_headings))
        self.__cache_pnums.clear()
        self.__cache_headings.clear()




