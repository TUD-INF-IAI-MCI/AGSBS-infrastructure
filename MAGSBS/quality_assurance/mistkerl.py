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
from ..config import _
from ..mparser import headingExtractor, pageNumberExtractor

from .all_formats import *
from .latex import *
from .markdown import *
from .meta import *

class Mistkerl():
    """Wrapper which wraps different levels of errors."""
    def __init__(self):
        self.__issues = [PageNumberIsParagraph, LevelOneHeading,
                oldstyle_pagenumbering, ItemizeIsParagraph,
                PageNumberingTextIsLowercase, ForgottenNumberInPageNumber,
                UniformPagestrings, TooManyHeadings, LaTeXMatricesAreHardToRead,
                PageNumbersWithoutDashes, DoNotEmbedHTMLLineBreaks,
                EmbeddedHTMLComperators, PageNumberWordIsMispelled,
                HeadingOccursMultipleTimes,
                HeadingsUseEitherUnderliningOrHashes, CasesSqueezedOnOneLine,
                ConfigurationValuesAreAllSet, LaTeXUmlautsUsed,
                BrokenUmlautsFromPDFFiles]
        self.__cache_pnums = collections.OrderedDict()
        self.__cached_headings = collections.OrderedDict()
        self.__output = []
        self.__priority = MistakePriority.normal
        self.requested_level = MistakePriority.normal

    def get_issues(self, fname):
        """Instanciate issue classes and filter for file endings."""
        for issue in self.__issues:
            i = issue()
            if self.get_priority().value >= i.get_priority().value:
                if fname: # fname exists -> no directory -> check for extension
                    ext = fname[fname.rfind(".")+1:]
                    if ext in i.get_file_types():
                        yield i
                else:
                    yield i

    def set_priority(self, p):
        assert isinstance(p, MistakePriority)
        self.__priority = p

    def get_priority(self):
        return self.__priority

    def run(self, path):
        """Take either a file and run checks or do the same for a directory
recursively."""
        last_dir = None
        directoryname = None
        fw = filesystem.FileWalker(path)
        fw.set_ignore_non_chapter_prefixed(False)
        fw.set_endings(["md","tex", "dcxml"])
        cwd = os.getcwd()
        for directoryname, dir_list, file_list in fw.walk():
            os.chdir(directoryname)
            if last_dir is not directoryname:
                self.run_directory_filters(last_dir)
                last_dir = directoryname


            for file in file_list:
                file_path = os.path.join(directoryname, file)
                if file.endswith('dcxml'):
                    self.__handle_configuration(directoryname, file)
                    continue # do no more checks
                try:
                    paragraphs = filesystem.file2paragraphs( \
                            open(file, encoding="utf-8"), join_lines=True)
                except UnicodeDecodeError:
                    e = error_message()
                    e.set_severity(MistakePriority.critical)
                    e.set_path(file_path)
                    e.set_message('Datei ist nicht in UTF-8 kodiert, bitte waehle "UTF-8" als Zeichensatz im Editor.')
                    continue
                self.__run_filters_on_file(file_path, paragraphs)
            os.chdir(cwd)
        # the last directory must be processed, even so there was no directory
        # change
        self.run_directory_filters(directoryname)
        return self.__output

    def __append(self, path, err):
        """Add an error to the internal output dict."""
        if(not err): return
        if not isinstance(err, error_message):
            raise TypeError("Errors may only be of type error_message, got '%s'"
                    % str(err))
        if not err.get_path():
            err.set_path(path)
        self.__output.append(err)


    def __run_filters_on_file(self, file_path, paragraphs):
        """Execute all filters which operate on one file. Also exclue filters
        which do not match for the file ending."""
        # presort issues
        fullFile = [e for e in self.get_issues(file_path) \
                if e.get_type() == MistakeType.full_file]
        oneLiner = [e for e in self.get_issues(file_path)
                        if e.get_type() == MistakeType.oneliner]
        needPnums = [e for e in self.get_issues(file_path)
                    if e.get_type() == MistakeType.need_pagenumbers]
        needHeadings = [e for e in self.get_issues(file_path)
                if e.get_type() == MistakeType.need_headings]

        try:
            if next(reversed(paragraphs)) > 2500:
                e = error_message()
                e.set_severity(MistakePriority.normal)
                e.set_path(file_path)
                e.set_message("Die Datei ist zu lang. Um die "+
                    " Navigation zu erleichtern und die einfache Lesbarkeit zu"+
                    " gewährleisten sollten lange Kapitel mit mehr als 2500 " +
                    "Zeilen in mehrere Unterdateien nach dem Schema kxxyy.md" +
                    " oder kleiner aufgeteilt werden.")
                self.__append(file_path, e)
        except StopIteration:
            pass # empty file, that we need to except as well

        # ToDo: do not take full list of paragraphs, but rather one paragraph at
        # a time; so one-liners and paragraph-aware checkers in one loop, better
        # CPU cache usage
        for issue in fullFile:
            self.__append(file_path, issue.run(paragraphs))
        for start_line, paragraph in paragraphs.items():
            for lnum, line in enumerate(paragraph):
                for issue in oneLiner:
                    if issue.should_be_run():
                        res = issue.run(start_line+lnum, line)
                        if res:
                            self.__append(file_path, res)
                            issue.set_run(False)
        pnums = pageNumberExtractor(paragraphs)
        hdngs = headingExtractor(paragraphs)
        # cache headings and page numbers, but only if file is not an image
        # description file. In those this error category doesn't matter.
        if _('images') in file_path:
            self.__cache_pnums[ file_path ] = pnums
            self.__cached_headings[ file_path ] = hdngs

        for issue in needPnums:
            self.__append(file_path, issue.run(pnums))
        for issue in needHeadings:
            self.__append(file_path, issue.run(hdngs))

    def run_directory_filters(self, dname):
        """Run all filters depending on the output of a directory."""
        if(len(self.__cache_pnums) > 0):
            x = [e for e in self.get_issues(False) \
                    if e.get_type() == MistakeType.need_pagenumbers_dir]
            for issue in x:
                self.__append(dname, issue.run(self.__cache_pnums))
        if self.__cached_headings:
            x = [e for e in self.get_issues(False) if e.get_type() == MistakeType.need_headings_dir]
            for issue in x:
                self.__append(dname, issue.run(self.__cached_headings))
        self.__cache_pnums.clear()
        self.__cached_headings.clear()

    def __handle_configuration(self, directory, file):
        """Execute all checkers dealing with the configuration."""
        needConfiguration = [e for e in self.get_issues(file)
                if e.get_type() == MistakeType.need_configuration]
        for issue in needConfiguration:
            path = os.path.join(directory, file)
            self.__append(path, issue.run(file))

