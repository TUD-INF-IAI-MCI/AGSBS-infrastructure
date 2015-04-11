# Disabling the checkers above is discouraged, but encouraged for this file;
# pylint makes mistakes itself
#pylint: disable=line-too-long,abstract-class-little-used,no-init,too-few-public-methods
"""This file contains all helper functions and classes to represent a
mistake."""

import re, textwrap
import enum
from abc import ABCMeta, abstractmethod
from .. import datastructures

class MistakePriority(enum.IntEnum):
    critical = 1
    normal = 2
    pedantic = 3

class MistakeType(enum.Enum):
    """The mistake type determines the arguments and the environment in which to
    run the tests.

Note for this table: from datastructures import Heading as H

type                parameters      Explanation
full_file           (content, name) applied to a whole file
oneliner            (num, line)     applied to line, starting num = 1
need_headings       [H(), ...]      applied to all headings
need_headings_dir   {path : [H(),   applied to all headings in a directory
                     ...]
need_pagenumbers    (lnum, level,   applied to all page numbers of page
                 string)
need_pagenumbers_dir   see headings applied to all page numbers of directory"""
    full_file = 1
    oneliner = 2
    need_headings = 3
    need_headings_dir = 4
    need_pagenumbers = 5
    need_pagenumbers_dir = 6

class Mistake:
    """This class implements the actual mistake checker.

It has to be subclassed and the child needs to override the run method. It
should set the relevant properties in the constructor."""
    __metaclass__ = ABCMeta

    def __init__(self):
        self._type = MistakeType.full_file
        self._priority = MistakePriority.normal
        self.__apply = True
        self.__file_types = ["md"]
        super().__init__()

    def set_file_types(self, types):
        if not datastructures.is_list_alike(types):
            raise TypeError("List or tuple expected.")
        self.__file_types = types

    def get_file_types(self):
        """Return all file extensions which shall be checked."""
        return self.__file_types

    def should_be_run(self):
        """Can be set e.g. for oneliners which have already found an error."""
        return self.__apply

    def set_run(self, value):
        assert type(value) == bool
        self.__apply = value

    def get_type(self):
        return self._type

    def set_type(self, t):
        if(isinstance(t, MistakeType)):
            self._type = t
        else:
            raise TypeError("Argument must be of enum type MistakeType")

    def get_priority(self):
        return self._priority

    def set_priority(self, p):
        if(isinstance(p, MistakePriority)):
            self._priority = p
        else:
            raise TypeError("This method expects an argument of type enum.")

    def run(self, *args):
        if(not self.should_be_run):
            return
        return self.worker(*args)

    @abstractmethod
    def worker(self, *args):
        pass

    def error(self, msg, lnum=None, path=None):
        e = error_message()
        e.set_severity(self.get_priority())
        e.set_message(' '.join(msg.split()))
        if lnum:
            e.set_lnum(lnum)
        if path:
            e.set_path(path)
        return e

class onelinerMistake(Mistake):
    """Class to ease the creation of onliner checks further:
class myMistake(onelinerMistake):
    def __init__(self):
        onelinerMistake.__init__(self)
    def check(self, num, line):
        # ToDo: implement checks here
It'll save typing."""
    def __init__(self):
        Mistake.__init__(self)
        self.set_type(MistakeType.oneliner)
    def check(self, lnum, text):
        """The method to implement the actual  checker in."""
        pass

    def worker(self, *args):
        if(len(args) != 2):
            raise ValueError("For a mistake checker of type oneliner, exactly two arguments are required.")
        return self.check(args[0], args[1])


class error_message(object):
    """Abstraction of an error message. It abstracts from the actual formatting
to be independent from a tty or GUI representation.

Usage:

e = error()
e.set_message("That's wrong.")
# line number, optional
e.set_number(666)
# automatically set when self.error() in Mistake sublcasses is used
e.set_severity(MistakePriority.normal)
# automatically set, but can be altered:
e.set_path("/dev/null")
"""
    def __init__(self):
        self.__msg = None
        self.__lnum = None
        self.__path = None
        self.__severity = None

    def set_severity(self, level):
        if(type(level) != MistakePriority):
            raise ValueError("Priority must be of type MistakePriority.")
        self.__severity = level

    def set_message(self, msg):
        if(type(msg) == str):
            self.__msg = msg
        else:
            self.__msg = str(msg)

    def set_lnum(self, lnum):
        if(type(lnum) != int):
            raise ValueError("Line number must be an integer.")
        self.__lnum = lnum

    def set_path(self, path):
        if(type(path) == str):
            self.__path = path
        else:
            self.__path = str(path)

    def is_valid(self):
        if(self.__path != None and self.__msg != None and
                self.__severity != None):
            return True
        else:
            return False

    def get_severity(self):
        return self.__severity

    def get_message(self):
        return self.__msg

    def get_path(self):
        return self.__path

    def get_lnum(self):
        return self.__lnum

class error_formatter(object):
    """Format an error message according to options set. One use case might be
the output on the command line.

Usage:

fmt = error_formatter()
fmt.set_with_blank_lines(False) # before/after path a blank line; default True
fmt.set_width(170) # output width of errors, default 80
fmt.set_itemize_sign("- ") # text before each of the errors; default: None
fmt.sort_critical_first(True) # sort not alphabetically using path, but by priority (default False)
fmt.suppress_paths(True) # do not show paths at all (useful if only one path examined); default False
"""
    def __init__(self):
        self.__x = 0
        self.__with_blank_lines = True
        self.__itemize_sign = ''
        self.__sort_critical_first = False
        self.__suppress_paths = False

    def set_with_blank_lines(self, flag):
        """Set whether there are blank lines between paths or not."""
        self.__with_blank_lines = flag

    def set_width(self, width):
        self.__x = width

    def set_itemize_sign(self, sign):
        self.__itemize_sign = sign[:]

    def suppress_paths(self, flag):
        self.__suppress_paths = flag

    def __severity_format(self, sev):
        translations = {'critical' : 'kritisch', 'pedantic' : 'pedantisch',
                'normal' : 'normal'}
        return translations[str(sev).split(".")[-1]]

    def sort_critical_first(self, flag):
        self.__sort_critical_first = flag

    def format_error(self, err):
        """Format an error according to the options set."""
        for attr in ['get_message', 'get_severity', 'get_path']:
            if not hasattr(err, attr):
                raise ValueError("Argument must provide method %s()." % attr)
        prefix = ''
        if self.__itemize_sign: prefix += self.__itemize_sign
        if err.get_lnum():
            prefix += 'Zeile %s' % err.get_lnum()
        if err.get_severity() == MistakePriority.critical:
            prefix += ' [%s]' % self.__severity_format(err.get_severity())
        width = (999999 if self.__x == 0 else self.__x - 1)
        wrapper = textwrap.TextWrapper(width)
        wrapper.initial_indent = prefix + ': '
        wrapper.subsequent_indent = '    '
        return '\n'.join(wrapper.wrap(err.get_message()))

    def __sort(self, errors):
        """Sorts given errors either alphabetical or using priority, if
self.sort_critical_first(True)."""
        if self.__sort_critical_first:
            return sorted(errors, key=error_message.get_severity)
        else:
            return sorted(errors, key=error_message.get_path)

    def format_errors(self, errors):
        errors = self.__sort(errors)
        last_path = None
        output = []
        for error in errors:
            if not self.__suppress_paths:
                if last_path != error.get_path():
                    # new path, new "section"; empty lines and path are printed
                    if output != [] and self.__with_blank_lines: output.append("\n")
                    output += [error.get_path(), '\n']
                    if self.__with_blank_lines: output.append("\n")
                    last_path = error.get_path()
            output.append(self.format_error(error))
            output.append("\n")
        return "".join(output)

