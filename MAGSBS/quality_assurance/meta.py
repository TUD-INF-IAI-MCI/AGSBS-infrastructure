# This is free software, licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2016 Sebastian Humenda <shumenda |at| gmx |dot| de>
# Disabling the checkers below is discouraged, but encouraged for this file;
# pylint makes mistakes itself
#pylint: disable=line-too-long,no-init,too-few-public-methods
"""This file contains all helper functions and classes to represent a
mistake."""

from abc import ABCMeta, abstractmethod
import enum

class MistakeType(enum.Enum):
    """The mistake type determines the arguments and the environment in which to
    run the tests.

Shortcuts for this table: par == paragraph, h == datastructures.Heading

type            parameters          Explanation
full_file       content             content: dict mapping from line number to
                                    paragraph (paragraph is list of lines)
oneliner        (num, line)         applied to line, starting num = 1
headings        [H(), ...]          applied to all headings
headings_dir    {path : [H(), …]    applied to all headings in a directory
pagenumbers     (lnum, level,       applied to all page numbers of page
                 string)
pagenumbers_dir see headings        applied to all page numbers of directory
configuration   (LectureMetaData    apply checks on the configuration
                 instance)
formulas        (path, formulas)    apply checks on the ordered list of formulas
                                    of `path`; for the format see mparser.parse_formulas
"""
    full_file = 1
    oneliner = 2
    headings = 3
    headings_dir = 4
    pagenumbers = 5
    pagenumbers_dir = 6
    configuration = 7
    formulas = 8

class Mistake:
    """This class implements the actual mistake checker.

It has to be subclassed and the child needs to override the run method. It
should set the relevant properties in the constructor."""
    __metaclass__ = ABCMeta
    mistake_type = MistakeType.full_file

    def __init__(self):
        self.__apply = True
        self.__file_types = ["md"]
        super().__init__()

    def set_file_types(self, types):
        # is it list-alike
        if not (hasattr(types, '__iter__') or hasattr(types, '__getitem__')):
            raise TypeError("List or tuple expected.")
        self.__file_types = types

    def get_file_types(self):
        """Return all file extensions which shall be checked."""
        return self.__file_types

    def should_be_run(self):
        """Can be set e.g. for oneliners which have already found an error."""
        return self.__apply

    def set_run(self, value):
        assert isinstance(value, bool)
        self.__apply = value


    def run(self, *args):
        if not self.should_be_run:
            return
        return self.worker(*args)

    @abstractmethod
    def worker(self, *args):
        pass

    def error(self, msg, lnum=None, path=None, pos=None):
        """Short hand to return an ErrorMessage object."""
        msg = ' '.join(msg.split())
        e = ErrorMessage(msg, lnum, path)
        if pos:
            e.pos_on_line = pos
        return e

class OnelinerMistake(Mistake):
    """Class to ease the creation of onliner checks further:
class myMistake(OnelinerMistake):
    def __init__(self):
        OnelinerMistake.__init__(self)
    def check(self, num, line):
        # ToDo: implement checks here
It'll save typing."""
    mistake_type = MistakeType.oneliner

    def __init__(self):
        Mistake.__init__(self)
    def check(self, lnum, text):
        """The method to implement the actual  checker in."""
        pass

    def worker(self, *args):
        if len(args) != 2:
            raise ValueError("For a mistake checker of type oneliner, exactly two arguments are required.")
        return self.check(args[0], args[1])


class FormulaMistake(Mistake):
    """This class simplifies the writing of LaTeX formula checkers.
    Example:
    class myMistake(OnelinerMistake): # note: class attribute mistake_type is automatically set
        def __init__(self):
            super().__init__()
        def check(self, formulas):
            # *implement checks here*
    When calling .error inside such a checker, a call might look like this:
        self.error("some_msg", lnum=some_line, pos=position_on_line)"""
    mistake_type = MistakeType.formulas

    @abstractmethod
    def worker(self, *args):
        pass



class ErrorMessage:
    """Simplistic data structure to ease the handling of error messages.
Usage:

e = ErrorMessage(message, linenumber, path)
e.pos_on_line = 52 # at which character the error was encountered
e.path = "foo.md" # usually set by the Mistkerl, but can be altered
assert hasattr(e, 'message') and hasattr(e, 'lineno')
"""
    def __init__(self, message, lineno, path):
        self.lineno = lineno
        self.message = message
        self.path = path
        self.pos_on_line = None


