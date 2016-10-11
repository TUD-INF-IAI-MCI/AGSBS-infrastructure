# This is free software licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2016 Sebastian Humenda <shumenda@gmx.de>
# line-too-long is overridden, because error messages should be not broken up.
# Else it is strongly discouraged! Wild-card imports are here because we are
# importing the mistakes and it is cumbersome to add them to the imports every
# time a new one is written.
#pylint: disable=wildcard-import,unused-wildcard-import

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
from xml.etree import ElementTree as ET
from .. import filesystem as filesystem
from .. import config
from .. import mparser

from .all_formats import *
from .latex import *
from .markdown import *
from .meta import *

class Mistkerl():
    """Wrapper which wraps different levels of errors."""
    def __init__(self):
        self.__issues = [PageNumberIsParagraph, LevelOneHeading,
                oldstyle_pagenumbering, ItemizeIsParagraph,
                ForgottenNumberInPageNumber, UniformPagestrings,
                TooManyHeadings, LaTeXMatricesShouldBeConstructeedUsingPmatrix,
                LaTeXMatricesShouldHaveLineBreaks, PageNumbersWithoutDashes,
                DoNotEmbedHtml, EmbeddedHTMLComperators,
                PageNumberWordIsMispelled, HeadingOccursMultipleTimes,
                HeadingsUseEitherUnderliningOrHashes, CasesSqueezedOnOneLine,
                ConfigurationValuesAreAllSet, LaTeXUmlautsUsed,
                BrokenUmlautsFromPDFFiles,
                TextInItemizeShouldntStartWithItemizeCharacter,
                SpacingInFormulaShouldBeDoneWithQuad,
                BrokenImageLinksAreDetected,
                HyphensFromJustifiedTextWereRemoved,
                DisplayMathShouldNotBeUsedWithinAParagraph,
                UseProperCommandsForMathOperatorsAndFunctions,
                FormulasSpanningAParagraphShouldBeDisplayMath,
                DetectEmptyImageDescriptions, DetectStrayingDollars]
        self.__cache_pnums = collections.OrderedDict()
        self.__cached_headings = collections.OrderedDict()
        self.__output = []

    def get_issues(self, required_type, fname=None):
        """Instanciate issue classes and filter for file endings."""
        extension = (os.path.splitext(fname)[1] if fname else 'md').lstrip('.')
        issues = (i for i in self.__issues
                if i.mistake_type == required_type)
        return list(i for i in (i() for i in issues) # instanciate
            if extension in i.get_file_types())

    def run(self, path):
        """Take either a file and run checks or do the same for a directory
recursively."""
        last_dir = None
        directoryname = None
        fw = filesystem.FileWalker(path)
        fw.set_ignore_non_chapter_prefixed(False)
        fw.set_endings(["md","tex"])
        for directoryname, dir_list, file_list in fw.walk():
            if last_dir is not directoryname:
                self.run_directory_filters(last_dir)
                last_dir = directoryname
                # check configuration
                if os.path.exists(os.path.join(directoryname, config.CONF_FILE_NAME)):
                    self.__handle_configuration(directoryname,
                            config.CONF_FILE_NAME)
                    continue # do no more checks


            for file in file_list:
                file_path = os.path.join(directoryname, file)
                try:
                    with open(file_path, encoding="utf-8") as f:
                        paragraphs = mparser.remove_codeblocks(
                                mparser.file2paragraphs(f.read(), join_lines=True))
                except UnicodeDecodeError:
                    msg = 'Datei ist nicht in UTF-8 kodiert, bitte waehle "UTF-8" als Zeichensatz im Editor.'
                    e = ErrorMessage(msg, 1, file_path)
                    self.__append_error(path, e)
                    continue
                self.__run_filters_on_file(file_path, paragraphs)
        # the last directory must be processed, even so there was no directory
        # change
        self.run_directory_filters(directoryname)
        # sort output
        return self.__output

    def __append_error(self, path, err):
        """Add an error to the internal output dict."""
        if not err: return
        if not isinstance(err, ErrorMessage):
            raise TypeError("Errors may only be of type ErrorMessage, got '%s'"
                    % str(err))
        if not err.path:
            err.path = path
        if os.path.dirname(err.path) == '.':
            err.path = err.path[2:] # strip ./ or .\
        self.__output.append(err)


    def __run_filters_on_file(self, file_path, paragraphs):
        """Execute all filters which operate on one file. Also exclue filters
            which do not match for the file ending."""
        # check whether file is too long
        self.__append_error(file_path, self.check_for_overlong_files(file_path,
            paragraphs))

        for issue in self.get_issues(MistakeType.full_file, file_path):
            self.__append_error(file_path, issue.run(paragraphs))
        oneliners = self.get_issues(MistakeType.oneliner, file_path)
        for start_line, paragraph in paragraphs.items():
            for lnum, line in enumerate(paragraph):
                for issue in oneliners:
                    if issue.should_be_run():
                        res = issue.run(start_line+lnum, line)
                        if res:
                            self.__append_error(file_path, res)
                            issue.set_run(False)
            if not any(e.should_be_run() for e in oneliners):
                break # no oneliner left which needs to be executed
        pnums = mparser.extract_page_numbers_from_par(paragraphs)
        hdngs = mparser.extract_headings_from_par(paragraphs)
        # if the file name does not end of any of the image description names,
        # it's a "proper" chapter and only for those the cache is relevant
        if not file_path.endswith("bilder.md"):
            self.__cache_pnums[file_path] = pnums
        self.__cached_headings[file_path] = hdngs

        for issue in self.get_issues(MistakeType.pagenumbers, file_path):
            self.__append_error(file_path, issue.run(pnums))
        for issue in self.get_issues(MistakeType.headings, file_path):
            self.__append_error(file_path, issue.run(hdngs))
        # extract formulas and run checkers; file needs to be read again,
        # because the formula parser operates on a whole file
        formulas = mparser.parse_formulas(paragraphs)
        for issue in self.get_issues(MistakeType.formulas, file_path):
            self.__append_error(file_path, issue.run(formulas))

    def run_directory_filters(self, dname):
        """Run all filters depending on the output of a directory."""
        if self.__cache_pnums:
            x = self.get_issues(MistakeType.pagenumbers_dir)
            for issue in x:
                self.__append_error(dname, issue.run(self.__cache_pnums))
        if self.__cached_headings:
            x = self.get_issues(MistakeType.headings_dir)
            for issue in x:
                self.__append_error(dname, issue.run(self.__cached_headings))
        self.__cache_pnums.clear()
        self.__cached_headings.clear()

    def __handle_configuration(self, directory, file):
        """Execute all checkers dealing with the configuration."""
        needConfiguration = self.get_issues(MistakeType.configuration, file)
        for issue in needConfiguration:
            path = os.path.join(directory, file)
            try:
                self.__append_error(path, issue.run(path))
            except ET.ParseError as e:
                pos = e.position
                mistake = ErrorMessage(("Die Konfiguration konnte nicht gelesen"
                        " werden: ") + e.args[0], pos[0], path)
                mistake.pos_on_line = pos[1]
                self.__append_error(path, mistake)

    def check_for_overlong_files(self, file_path, paragraphs):
        if not paragraphs:
            return # ignore empty files
        last_par = next(reversed(paragraphs))
        if last_par > 2500:
            msg = ("Die Datei ist zu lang. Um die Navigation zu erleichtern und "
                "die einfache Lesbarkeit zu gewährleisten sollten lange Kapitel"
                " mit mehr als 2500 Zeilen in mehrere Unterdateien nach dem "
                "Schema kxxyy.md oder kleiner aufgeteilt werden.")
            e = ErrorMessage(msg, last_par, file_path)
            return e

