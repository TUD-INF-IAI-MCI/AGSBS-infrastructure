# vim:set expandtab sts=4 sw=4 ts=4 ft=python tw=0:
"""All mistake checkers regarding LaTeX, especially LaTeX equations, go in
here. Please note that they are also applied to *.md-files, since LaTeX can be
embedded there as well."""

import re
from .meta import FormulaMistake, OnelinerMistake, Mistake, MistakeType


class CasesSqueezedOnOneLine(FormulaMistake):
    r"""\begin{cases} ... lots of stuff \end{cases} is hard to read. There
    should be actual line breaks after \\\\."""
    def __init__(self):
        super().__init__()
        self.set_file_types(["md","tex"])

    def worker(self, *formulas):
        for pos, formula in formulas[0].items():
            if '\n' in formula:
                continue
            if r'\begin{cases}' in formula and r'\end{cases}' in formula:
                return self.error(("Die LaTeX-Umgebung zur Fallunterscheidung "
                    "(cases) sollte Zeilenumbrüche an den passenden Stellen "
                    "enthalten, um die Lesbarkeit zu gewährleisten."),
                    lnum=pos[0], pos=pos[1])



class LaTeXMatricesShouldBeConstructeedUsingPmatrix(FormulaMistake):
    """There are various ways to make matrices hard to read. Spot and report
    them."""
    def __init__(self):
        super().__init__()
        self.set_file_types(["md","tex"])
        self.pattern = re.compile(r".*(\left|\big|\Big)\(.*?begin{(array|matrix)")

    def worker(self, *args):
        for (line, pos), formula in args[0].items():
            if self.pattern.search(formula):
                return self.error(("Matrizen sollten, damit sie einfach lesbar "
                    "sind, nicht mit \\left\\(..., sondern einfach mit "
                    "\\begin{pmatrix}...  erzeugt werden. Dabei werden auch "
                    "Klammern automatisch gesetzt und es ist kürzer."),
                    lnum=line, pos=pos)

class LaTeXMatricesShouldHaveLineBreaks(FormulaMistake):
    def __init__(self):
        super().__init__()
        self.set_file_types(["md","tex"])
        self.pattern = re.compile(r"\\begin{.*?matrix}.*\\\\.*&")

    def worker(self, *args):
        for (line, pos), formula in args[0].items():
            if self.pattern.search(formula):
                return self.error(("Jede Zeile einer Matrix oder Tabelle sollte"
                    " zur besseren Lesbarkeit auf eine eigene Zeile gesetzt werden."),
                    lnum=line, pos=pos)


class LaTeXUmlautsUsed(OnelinerMistake):
    r"""Some people tend to use \"a etc. to display umlauts. That is hard to read."""
    def __init__(self):
        super().__init__()
        self.set_file_types(["tex"])
        # generate all permutations of umlauts with control sequences
        self.umlauts = ['\\"a', '{"a', '\\"u', '{u}', '\\"o', '"o', '\\3',
            '{"s}', '\\"s']

    def check(self, num, line):
        lower = line.lower()
        for token in self.umlauts:
            if token in lower:
                return super().error("Anstatt einen Umlaut zu schreiben, wurde "
                    "eine LaTeX-Kontrollsequenz verwendet. Das ist schwer "
                    "leserlich und kann außerdem einfach durch setzen des "
                    "Zeichensatzes umgangen werden.", num)


class DisplayMathShouldNotBeUsedWithinAParagraph(OnelinerMistake):
    """DisplayMath should not be used within a paragraph. That is against the
    idea of displaymath and will additionally result in incorrect
    formatting."""
    def __init__(self):
        super().__init__()
        self._pattern = re.compile(r'^.*?(\w+\s*\$\$.*\$\$|\$\$.*?\$\$\s*\w+).*')

    def check(self, num, line):
        if line:
            matched = self._pattern.search(line)
            if matched:
                return self.error("Formeln in einem Absatz (umgeben von Text), müssen mit einfachen $-Zeichen gesetzt werden, da sich die Formeln sonst in der Ausgabe nicht in den Text integrieren. $$ (display math) sollte für einzeln stehende Formeln verwendet werden.",
                    num, pos=matched.span()[1])

class SpacingInFormulaShouldBeDoneWithQuad(FormulaMistake):
    r"""Some people tend to use `\ \ \ \ ...` to format a bigger space within an equation. This is hard to read
    and hence \quad should be used."""
    def worker(self, *args):
        for (line, pos), formula in args[0].items():
            if r'\ \ \ \ ' in formula:
                return self.error(r"Leerräume in Formeln sollten mit \quad oder \qquad gekennzeichnet werden, da sie sonst mit Sprachausgabe schwer lesbar sind.",
                    lnum=line, pos=pos)

class UseProperCommandsForMathOperatorsAndFunctions(FormulaMistake):
    r"""\min, \max, ... should be marked up correctly."""
    def __init__(self):
        super().__init__()
        self.set_file_types(['md', 'tex'])
        self.opsandfuncs = ['sin','cos', 'max', 'min']

    def worker(self, *args):
        for (line, pos), formula in args[0].items():
            for mathop in self.opsandfuncs:
                if not mathop in formula:
                    continue
                if not ('\\' + mathop) in formula:
                    return self.error(("{0} sollte in LaTeX-Formeln "
                        "grundsätzlich als Befehl gesetzt werden, d.h. mittels "
                        "\\{0}. Nur so wird es in der Ausgabe korrekt "
                        "formatiert und ist gleichzeitig gut lesbar.").\
                            format(mathop), lnum=line, pos=pos)

class FormulasSpanningAParagraphShouldBeDisplayMath(Mistake):
    """This checker checks whether some formula was set with inline maths on a
    paragraph, but since it's a free standing one, should be rather formatted
    as display maths."""
    mistake_tyke = MistakeType.full_file
    def __init__(self):
        super().__init__()
        self.beginning = re.compile(r'^\s*\$(?!\$).+')
        self.ending = re.compile(r'.+\$(?!\$)\s*$')

    def worker(self, *args):
        for start_line, para in args[0].items():
            if self.beginning.search(para[0]) and self.ending.search(para[-1]):
                # count dollars to be sure that it's just one math env
                if sum(l.count('$') for l in para) < 3:
                    return self.error(("Eine Formel, die einzeln in einem Absatz "
                    "steht, wurde als eingebettete Formel mit einfachen $ gesetzt. "
                    "Stattdessen sollten doppelte Dollarzeichen verwendet werden,"
                    " da dies verhindert, dass LaTeX die Formel auf Zeilenhöhe "
                    "staucht."), lnum=start_line)

