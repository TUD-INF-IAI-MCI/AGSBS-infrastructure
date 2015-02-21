# vim:set expandtab sts=4 sw=4 ts=4 ft=python tw=0:
"""All mistake checkers regarding LaTeX, especially LaTeX equations, go in
here. Please note that they are also applied to *.md-files, since LaTeX can be
embedded there as well."""

from .meta import MistakePriority, onelinerMistake
import re


class CasesSqueezedOnOneLine(onelinerMistake):
    r"""\begin{cases} ... lots of stuff \end{cases} is hard to read. There
    should be actual line breaks after \\\\."""
    def __init__(self):
        onelinerMistake.__init__(self)
        self.set_file_types(["md","tex"])
        self.set_priority(MistakePriority.pedantic)

    def check(self, num, line):
        if(line.find(r'\begin{cases}')>=0 and
                    line.find(r"\end{cases}")>=0):
            return self.error("Die LaTeX-Umgebung zur Fallunterscheidung (cases) sollte Zeilenumbrüche an den passenden Stellen enthalten, um die Lesbarkeit zu gewährleisten.", num)



class LaTeXMatricesAreHardToRead(onelinerMistake):
    """There are various ways to make matrices hard to read. Spot and report
    them."""
    def __init__(self):
        onelinerMistake.__init__(self)
        self.set_file_types(["md","tex"])
        self.set_priority(MistakePriority.normal)
        self.pat1 = re.compile(r"\\left\(.*?begin{(array|matrix)")
        self.pat2 = re.compile(r"\\begin{.*?matrix}.*\\\\.*&")

    def check(self, num, line):
        if(self.pat1.search(line)):
            return self.error(r"""Matrizen sollten, damit sie einfach lesbar
                    sind, nicht mit \left\(..., sondern einfach mit
                        \begin{pmatrix}...  erzeugt werden. Dabei werden auch
                        Klammern automatisch gesetzt und es ist kürzer.""", num)
        elif(self.pat2.search(line)):
            return self.error("Jede Zeile einer Matrix oder Tabelle sollte zur " +
                "besseren Lesbarkeit auf eine eigene Zeile gesetzt werden.", num)



