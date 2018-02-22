# This is free software licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2014-2017 Sebastian Humenda <shumenda@gmx.de>
# line-too-long is overridden, because error messages should be not broken up.
# Else it is strongly discouraged! Wild-card imports are here because we are
# importing the mistakes and it is cumbersome to add them to the imports every
# time a new one is written.
#pylint: disable=wildcard-import,unused-wildcard-import

"""
This sub-module provides implementations for checking common lecture editing
errors.

The Mistkerl class maintains a list of mistakes and iterates over these to spot
common errors. This is the only class which should be used from outside.

A mistake is a child of the Mistake class. It can set its priority and its type
(what it wants to see from the document) in its __init__-function. The common
run-function then implements the checking.

All mistakes take a list of arguments (which depends on the set type, see
MistakeType) and return a tuple with (line_number, detailed_error_text_German).

For the documentation of the mistake types, see the appropriate class."""

import os
import collections
from xml.etree import ElementTree as ET
from .. import config
from .. import errors
from .. import filesystem as filesystem
from .. import mparser
from .. import roman

from .all_formats import *
from .latex import *
from .markdown import *
from .meta import *

class Mistkerl():
    """Wrapper which wraps different levels of errors."""
    TOLERANT_PAGE_NUMBERING_PATTERN = re.compile(r'''
        # match any word or two-word phrase
        -\s*([a-z|A-Z]\s*[a-z|A-Z]*)\s+
        (\d+|%s)\s*- # arabic or roman numbers
        ''' % roman.roman_numeral_pattern_string.strip().lstrip('^').rstrip('$'),
        re.VERBOSE) # ^ strip begin and end-of-line matcher

    def __init__(self):
        self.__issues = [PageNumberIsParagraph, LevelOneHeading,
                ItemizeIsParagraph, ForgottenNumberInPageNumber,
                UniformPagestrings, TooManyHeadings,
                LaTeXMatricesShouldBeConstructeedUsingPmatrix,
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
                FreeStandingFormulasShouldBeDisplaymath,
                DetectEmptyImageDescriptions, DetectStrayingDollars,
                OnlyCorrectDirectoriesFound]
        self.__cache_pnums = collections.OrderedDict()
        self.__cached_headings = collections.OrderedDict()
        self.__output = []

    def get_issues(self, required_type, fname=None):
        """Instanciate issue classes and filter for their configured file
        extension."""
        extension = (os.path.splitext(fname)[1].replace('.', '') if fname else 'md')
        issues = (i for i in self.__issues
                if i.mistake_type == required_type)
        return list(i for i in (i() for i in issues) # instanciate
            if extension in i.get_file_types())

    def run(self, path):
        """Take either a file and run checks or do the same for a directory
        recursively."""
        file_tree = [(None, [], [])] # empty os.walk()-alike data structure
        if os.path.isfile(path):
            file_tree = [[os.path.dirname(path), [], [os.path.basename(path)]]]
            if not file_tree[0][0]: # no directory part extracted
                file_tree[0][0] = os.path.dirname(os.path.abspath(path))
        else:
            for issue in self.get_issues(MistakeType.lecture_root):
                self.__append_error(path, issue.run(path))
            fw = filesystem.FileWalker(path)
            fw.set_ignore_non_chapter_prefixed(False)
            fw.set_endings(["md","tex"])
            file_tree = fw.walk()
        last_dir = None
        directoryname = None
        for directoryname, _, file_list in file_tree:
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
                        paragraphs = mparser.rm_codeblocks(
                                mparser.file2paragraphs(f.read(), join_lines=True))
                except UnicodeDecodeError:
                    msg = _("Datei ist nicht in UTF-8 kodiert, bitte waehle \"UTF-8\" als Zeichensatz im Editor.")
                    e = ErrorMessage(msg, 1, file_path)
                    self.__append_error(path, e)
                    continue
                self.__run_filters_on_file(file_path, paragraphs)
        # the last directory must be processed, even though there was no directory
        # change
        self.run_directory_filters(directoryname)
        # sort output
        return self.__output

    def __append_error(self, path, err):
        """Add an error to the internal output dict."""
        if not err: return
        if not isinstance(err, ErrorMessage):
            raise TypeError("Errors may only be of type ErrorMessage, got '{}'"\
                    .format(str(err)))
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
        pnums = []
        try:
            pnums = mparser.extract_page_numbers_from_par(paragraphs,
                    regex=Mistkerl.TOLERANT_PAGE_NUMBERING_PATTERN)
            # if the file name does not end of any of the image description names,
            # it's a "proper" chapter and only for those the page number cache is relevant
            if not file_path.endswith("bilder.md"):
                self.__cache_pnums[file_path] = pnums
        except errors.FormattingError:
            pass # checkers are able to handle this case and will report
        hdngs = mparser.extract_headings_from_par(paragraphs)
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
                mistake = ErrorMessage(_("Die Konfiguration konnte nicht gelesen"
                    " werden: {}").format(e.args[0]), pos[0], path)
                mistake.pos_on_line = pos[1]
                self.__append_error(path, mistake)

    def check_for_overlong_files(self, file_path, paragraphs):
        if not paragraphs:
            return # ignore empty files
        last_par = next(reversed(paragraphs))
        if last_par > 2500:
            msg = _("Die Datei ist zu lang. Um die Navigation zu erleichtern und "
                "die einfache Lesbarkeit zu gewährleisten sollten lange Kapitel"
                " mit mehr als 2500 Zeilen in mehrere Unterdateien nach dem "
                "Schema kxxyy.md oder kleiner aufgeteilt werden.")
            return ErrorMessage(msg, last_par, file_path)

