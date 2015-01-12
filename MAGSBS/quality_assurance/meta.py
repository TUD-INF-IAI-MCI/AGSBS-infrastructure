"""This file contains all helper functions and classes to represent a
mistake."""

import re
import enum
from MAGSBS.datastructures import is_list_alike

def HeadingExtractor(text):
    headings = []
    paragraph_begun = True
    previous_line_heading = False
    previous_line = ''
    for num, line in enumerate(text.split('\n')):
        if(line.strip() == ''):
            paragraph_begun = True
            previous_line_heading = False
        else:
            if(not paragraph_begun): # happens on the second line of a paragraph
                if(line.startswith('---')):
                    previous_line_heading = True
                    headings.append((num, 2, previous_line)) # heading level 2
                elif(line.startswith('===')):
                    previous_line_heading = True
                    headings.append((num, 1, previous_line)) # heading level 2
                    continue
            if(line.startswith("#")):
                if(paragraph_begun):
                    level = 0
                    while(line.startswith("#") or line.startswith(" ")):
                        if(line[0] == "#"): level += 1
                        line = line[1:]
                    while(line.endswith("#") or line.endswith(" ")):
                        line = line[:-1]

                    headings.append((num+1, level, line))
                    previous_line_heading = True
            paragraph_begun = False # one line of text ends "paragraph begun"
        previous_line = line[:]
    return headings


def pageNumberExtractor(data):
    """Iterate over lines and extract all those starting with ||. The page
    number and the rest of the line is returned as a tuple."""
    numbers = []
    rgx = re.compile(r"^\|\|\s*-\s*(.+?)\s*-")
    for num, line in enumerate(data.split('\n')):
        result = rgx.search(line)
        if(result):
            numbers.append((num+1, result.groups()[0]))
    return numbers

class MistakePriority(enum.Enum):
    critical = 1
    normal = 2
    pedantic = 3

class MistakeType(enum.Enum):
    """The mistake type determines the arguments and the environment in which to
    run the tests.

type                parameters      Explanation
full_file           (content, name) applied to a whole file
oneliner            (num, line)     applied to line, starting num = 1
need_headings       (lnum, level,   applied to all headings
                     title)
need_headings_dir   [(path, [lnum,  applied to all headings in a directory
                     level, title]))
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
    """Convenience class which saves the actual method and the type of
    mistake."""
    def __init__(self):
        self._type = MistakeType.full_file
        self._priority = MistakePriority.normal
        self.__apply = True
        self.__file_types = ["md"]
    def set_file_types(self, types):
        if(not is_list_alike(types)):
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
    def get_type(self): return self._type
    def set_type(self, t):
        if(isinstance(t, MistakeType)):
            self._type = t
        else:
            raise TypeError("Argument must be of enum type MistakeType")
    def get_priority(self): return self._priority
    def set_priority(self, p):
        if(isinstance(p, MistakePriority)):
            self._priority = p
        else:
            raise TypeError("This method expects an argument of type enum.")

    def run(self, *args):
        if(not self.should_be_run):
            return
        return self.worker(*args)
    def worker(self, *args):
        raise NotImplementedError("The method run must be overriden by a child class.")

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
    def worker(self, *args):
        if(len(args) != 2):
            raise ValueError("For a mistake checker of type oneliner, exactly two arguments are required.")
        return self.check(args[0], args[1])



