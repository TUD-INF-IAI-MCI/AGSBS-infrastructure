"""All errors regarding LaTeX, especially LaTeX equations, go in here. Please
note that they are also applied to *.md-files, since LaTeX can be embedded there
as well."""

from .mistkerl import Mistake, MistakeType, \
                                MistakePriority, onelinerMistake


class common_latex_errors(Mistake):
    def __init__(self):
        Mistake.__init__(self)
        # full_file is automatic
        self.set_file_types([".md",".tex"])
    def worker(self, *args):
        if(len(args) < 1):
            raise TypeError("An argument with the file content to check is expected.")
        for num, line in enumerate(args[0].split('\n')):
            # check whether cases has no line break
            if(line.find(r'\begin{cases}')>=0 and
                    line.find(r"\end{cases}")>=0):
                return (num+1, "Die LaTeX-Umgebung zur Fallunterscheidung (cases) sollte Zeilenumbrüche an den passenden Stellen enthalten, um die Lesbarkeit zu gewährleisten.")
            # check whether cases environment is in $$ blah $$
            pos = line.find(r'\begin{cases}')
            if(pos >= 0):
                if(line[:pos].rfind('$$')>=0):
                    continue
                elif(line[:pos].rfind(r"\(")>=0 or line[:pos].rfind(r"\\[")>=0):
                    continue
                else:
                    return (num+1, "Die mathematische Umgebung zur Fallunterscheidung (\\begin{cases} ... \\end{cases}) sollte in Displaymath gesetzt werden, d.h. doppelte Dollarzeichen anstatt ein Einzelnes sollten diese Umgebung umschließen. Dies erhält den Zeilenumbruch für den grafischen Alternativtext.") 

class LaTeXMatricesAreHardToRead(onelinerMistake):
    """There are various ways to make matrices hard to read. Spot and report
    them."""
    def __init__(self):
        onelinerMistake.__init__(self)
        self.set_file_types(["md","tex"])
        self.pat1 = re.compile(r"\\left\(.*?begin{(array|matrix)")
        self.pat2 = re.compile(r"\\begin{.*?matrix}.*\\\\.*&")
    def check(self, num, line):
        if(self.pat1.search(line)):
            return (num, "Matrizen sollten, damit sie einfach lesbar sind, nicht "+
                "mit \\left\(..., sondern einfach mit \\begin{pmatrix}... " +
                    "erzeugt werden. Dabei werden auch Klammern automatisch " +
                    "gesetzt und es ist kürzer.")
        elif(self.pat2.search(line)):
            return (num, "Jede Zeile einer Matrix oder Tabelle sollte zur " +
                "besseren Lesbarkeit auf eine eigene Zeile gesetzt werden.")



