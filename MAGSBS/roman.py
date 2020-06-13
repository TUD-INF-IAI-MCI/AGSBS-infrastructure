"""Convert to and from Roman numerals

This program is part of "Dive Into Python", a free Python book for
experienced programmers.  Visit http://diveintopython.org/ for the
latest version.

It has been modified by Sebastian Humenda to run on Python3, 2017 and is licensed under the same
license.
"""

__author__ = "Mark Pilgrim (mark@diveintopython.org), Sebastian Humenda"
__version__ = "$Revision: 1.3 $"
__date__ = "$Date: 2004/05/05 21:57:19 $"
__copyright__ = "Copyright (c) 2001 Mark Pilgrim"
__license__ = "Python"

import re

# Define exceptions
class RomanError(Exception):
    pass


class OutOfRangeError(RomanError):
    pass


class NotIntegerError(RomanError):
    pass


class InvalidRomanNumeralError(RomanError):
    pass


# Define digit mapping
romanNumeralMap = (
    ("M", 1000),
    ("CM", 900),
    ("D", 500),
    ("CD", 400),
    ("C", 100),
    ("XC", 90),
    ("L", 50),
    ("XL", 40),
    ("X", 10),
    ("IX", 9),
    ("V", 5),
    ("IV", 4),
    ("I", 1),
)


def to_roman(n):
    """convert integer to Roman numeral"""
    if not (0 < n < 5000):
        raise OutOfRangeError("number out of range (must be 1..4999)")
    try:
        n = int(n)
    except ValueError:
        raise NotIntegerError("non-integers can not be converted")

    result = ""
    for numeral, integer in romanNumeralMap:
        while n >= integer:
            result += numeral
            n -= integer
    return result


# Define pattern to detect valid Roman numerals
roman_numeral_pattern_string = """^
    M{0,4}              # thousands - 0 to 4 M's
    (?:CM|CD|D?C{0,3})    # hundreds - 900 (CM), 400 (CD), 0-300 (0 to 3 C's),
                        #            or 500-800 (D, followed by 0 to 3 C's)
    (?:XC|XL|L?X{0,3})    # tens - 90 (XC), 40 (XL), 0-30 (0 to 3 X's),
                        #        or 50-80 (L, followed by 0 to 3 X's)
    (?:IX|IV|V?I{0,3})    # ones - 9 (IX), 4 (IV), 0-3 (0 to 3 I's),
                        #        or 5-8 (V, followed by 0 to 3 I's)
    $"""
roman_numeral_pattern = re.compile(roman_numeral_pattern_string, re.VERBOSE)


def from_roman(letters):
    """convert Roman numeral to integer"""
    if not letters:
        raise InvalidRomanNumeralError("Input can not be blank")
    if not roman_numeral_pattern.search(letters):
        raise InvalidRomanNumeralError("Invalid Roman numeral: %letters" % letters)

    result = 0
    index = 0
    for numeral, integer in romanNumeralMap:
        while letters[index : index + len(numeral)] == numeral:
            result += integer
            index += len(numeral)
    return result
