# This is free software licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2014 Sebastian Humenda <shumenda@gmx.de>
# line-too-long is overriden, because error messages should be not broken up.
# Else it is strongly discouraged! Wild-card imports are here because we are
# importing the mistakes and it is cumbersome to add them to the imports every
# time a new one is written.
#pylint: disable=line-too-long,wildcard-import,unused-wildcard-import

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

import os
import collections
from .. import filesystem as filesystem

from .meta import *
from .latex import *
from .markdown import *

class Mistkerl():
    """Wrapper which wraps different levels of errors."""
    def __init__(self):
        self.__issues = [common_latex_errors, page_number_is_paragraph,
                heading_is_paragraph, level_one_heading, oldstyle_pagenumbering,
                itemize_is_paragraph, page_numbering_text_is_lowercase,
                page_string_but_no_page_number, uniform_pagestrings,
                too_many_headings, LaTeXMatricesAreHardToRead,
                PageNumbersWithoutDashes, DoNotEmbedHTMLLineBreaks,
                EmbeddedHTMLComperators, pageNumberWordIsMispelled,
                headingOccursMultipleTimes]
        self.__cache_pnums = collections.OrderedDict()
        self.__cache_headings = collections.OrderedDict()
        self.__output = []
        self.__priority = MistakePriority.normal
        self.requested_level = MistakePriority.normal

    def get_issues(self, fname):
        """Instanciate issue classes and filter for file endings."""
        for issue in self.__issues:
            i = issue()
            if(self.get_priority().value >= i.get_priority().value):
                if(fname): # fname exists -> no directory -> check for extension
                    ext = fname[fname.rfind(".")+1:]
                    if(ext in i.get_file_types()):
                        yield i
                else:
                    yield i
    def set_priority(self, p):
        assert type(p) == MistakePriority
        self.__priority = p
    def get_priority(self): return self.__priority
    def run(self, path):
        """Take either a file and run checks or do the same for a directory
recursively."""
        last_dir = None
        directoryname = None
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
                    text = open(file, "r", encoding="utf-8").read()
                except UnicodeDecodeError:
                    e = error_message()
                    e.set_severity(MistakePriority.critical)
                    e.set_path(file_path)
                    e.set_message('Datei ist nicht in UTF-8 kodiert, bitte waehle "UTF-8" als Zeichensatz im Editor.')
                    continue
                text = text.replace('\r\n','\n').replace('\r','\n')
                self.__run_filters_on_file(file_path, text)
            os.chdir(cwd)
        # the last directory must be processed, even so there was no directory
        # change
        self.run_directory_filters(directoryname)
        return self.__output

    def __append(self, path, err):
        """Add an error to the internal output dict."""
        if(not err): return
        if(type(err) != error_message):
            raise TypeError("Errors may only be of type error_message, got '%s'"
                    % str(err))
        if not err.get_path():
            err.set_path(path)
        self.__output.append(err)


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
                e = error_message()
                e.set_severity(MistakePriority.normal)
                e.set_path(file_path)
                e.set_message("Die Datei ist zu lang. Um die "+
                    " Navigation zu erleichtern und die einfache Lesbarkeit zu"+
                    " gewährleisten sollten lange Kapitel mit mehr als 2500 " +
                    "Zeilen in mehrere Unterdateien nach dem Schema kxxyy.md" +
                    " oder kleiner aufgeteilt werden.")

                self.__append(file_path, e)
            for issue in OneLiner:
                if(issue.should_be_run()):
                    res = issue.run(num+1, line)
                    if(res):
                        self.__append(file_path, res)
                        issue.set_run(False)
        # cache headings and page numbers
        pnums = pageNumberExtractor(text)
        hdngs = headingExtractor(text)
        self.__cache_pnums[ file_path ] = pnums
        self.__cache_headings[ file_path ] = hdngs

        for issue in NeedPnums:
            self.__append(file_path, issue.run(pnums))
        for issue in NeedHeadings:
            self.__append(file_path, issue.run(hdngs))

    def run_directory_filters(self, dname):
        """Run all filters depending on the output of a directory."""
        if(len(self.__cache_pnums) > 0):
            x = [e for e in self.get_issues(False) \
                    if e.get_type() == MistakeType.need_pagenumbers_dir]
            for issue in x:
                self.__append(dname, issue.run(self.__cache_pnums))
        if(len(self.__cache_headings) > 0):
            x = [e for e in self.get_issues(False) if e.get_type() == MistakeType.need_headings_dir]
            for issue in x:
                self.__append(dname, issue.run(self.__cache_headings))
        self.__cache_pnums.clear()
        self.__cache_headings.clear()

