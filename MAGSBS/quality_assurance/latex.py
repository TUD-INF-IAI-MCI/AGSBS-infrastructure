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
        self.set_file_types(["md", "tex"])

    def worker(self, *formulas):
        for pos, formula in formulas[0].items():
            if '\n' in formula:
                continue
            if r'\begin{cases}' in formula and r'\end{cases}' in formula:
                return self.error(_("The LaTeX environment \"cases\" should "
                        "contain line breaks at suitable places to increase "
                        "readibility."), lnum=pos[0], pos=pos[1])



class LaTeXMatricesShouldBeConstructeedUsingPmatrix(FormulaMistake):
    """There are various ways to make matrices hard to read. Spot and report
    them."""
    PATTERN = re.compile(r".*(\\left|\\big|\\Big)(\(|\{).*?begin{(array|matrix)")
    def __init__(self):
        super().__init__()
        self.set_file_types(["md", "tex"])

    def worker(self, *args):
        for (line, pos), formula in args[0].items():
            if self.PATTERN.search(formula):
                return self.error(_("To increase readibility, matrices should "
                    "not be constructed using manual formatting commands, but "
                    "using \"\\begin{pmatrix}...\". This is also shorter."),
                    lnum=line, pos=pos)

class LaTeXMatricesShouldHaveLineBreaks(FormulaMistake):
    def __init__(self):
        super().__init__()
        self.set_file_types(["md", "tex"])
        self.pattern = re.compile(r"\\begin{.*?matrix}.*\\\\.*&")

    def worker(self, *args):
        for (line, pos), formula in args[0].items():
            if self.pattern.search(formula):
                return self.error(_("Each line of a matrix or table should "
                        "be written on one line, using a hard line break."),
                    lnum=line, pos=pos)


class LaTeXUmlautsUsed(FormulaMistake):
    r"""Some people tend to use \"a etc. to display umlauts. That is hard to
    read. Currently, only German umlauts are  considered."""
    UMLAUTS = ['\\"a', '{"a}', '\\"u', '{"u}', '\\"o', '"o', '\\3',
            '{"s}', '\\"s']

    def __init__(self):
        super().__init__()
        self.set_file_types(["tex", "md"])

    def worker(self, formulas):
        for pos, formula in formulas.items():
            formula = formula.lower()
            if any(t in formula for t in self.UMLAUTS):
                return super().error(_("Instead of using an actual umlaut, a "
                    "LaTeX control sequence was used. This is hard to read and "
                    "not required with this program."), lnum=pos[0], pos=pos[1])


class DisplayMathShouldNotBeUsedWithinAParagraph(OnelinerMistake):
    """DisplayMath should not be used within a paragraph. That is against the
    idea of displaymath and will additionally result in incorrect
    formatting."""
    PATTERN = re.compile(r'^.*?(\w+\s*\$\$.*\$\$|\$\$.*?\$\$\s*\w+).*')
    def check(self, num, line):
        if line:
            matched = self.PATTERN.search(line)
            if matched:
                return self.error(_("Formulas within a paragraph surrounded by "
                        "text have to be set with single dollars, because the "
                        "formulas don't integrate into the line otherwise. $$ "
                        "(displaymath) should be used in formulas standing on "
                        "their own in a paragraph."), num, pos=matched.span()[1])

class SpacingInFormulaShouldBeDoneWithQuad(FormulaMistake):
    r"""Some people tend to use `\ \ \ \ ...` to format a bigger space within
    an equation. This is hard to read and hence \quad should be used."""
    def worker(self, *args):
        for (line, pos), formula in args[0].items():
            if r'\ \ \ \ ' in formula:
                return self.error(_("Empty space in formulas should be set "
                        "with \\quad or \\qquad, because they are otherwise "
                        "hard to read with speech synthesis."),
                    lnum=line, pos=pos)

class UseProperCommandsForMathOperatorsAndFunctions(FormulaMistake):
    r"""\min, \max, ... should be marked up correctly."""
    OPSANDFUNCS = tuple(re.compile(r'\b%s\b' % op)
            for op in ('sin', 'cos', 'max', 'min', 'tan'))

    def __init__(self):
        super().__init__()
        self.set_file_types(['md', 'tex'])

    def worker(self, *args):
        has_backslash = lambda text, idx: (text[idx - 1] == '\\' if idx > 0
                else False)
        for (line, pos), formula in args[0].items():
            for mathop in self.OPSANDFUNCS:
                match = mathop.search(formula)
                if not match:
                    continue
                if not has_backslash(formula, match.span()[0]):
                    return self.error(_("'{0}' should be generally set using "
                        "the appropriate LaTeX command, namely using \\{0}. "
                        "This way it will be properly formatted in the output "
                        "and easily readable by screen readers.").format(
                        mathop.pattern.replace('\\b', '')), lnum=line, pos=pos)


class FreeStandingFormulasShouldBeDisplaymath(Mistake):
    """This checker checks whether some formula was set with inline maths on a
    paragraph, but since it's a free standing one, should be rather formatted
    as display maths."""
    mistake_tyke = MistakeType.full_file
    START = re.compile(r'^\s*\$(?!\$).+')
    END = re.compile(r'.+\$(?!\$)\s*$')

    def worker(self, *args):
        for start_line, para in args[0].items():
            if self.START.search(para[0]) and self.END.search(para[-1]):
                # count dollars to be sure that it's just one math env
                if sum(l.count('$') for l in para) == 2:
                    return self.error(_("A formula, occurring on a paragraph "
                            "on its own, has been set as an embedded formula "
                            "using single dollars. Instead double dollar signs "
                            "around the formula should be used, so that the "
                            "formula is not squeezed to the line height."),
                        lnum=start_line)

