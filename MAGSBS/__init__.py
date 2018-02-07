from . import config
from . import datastructures
from . import errors
from . import factories
from . import filesystem
from . import master
from . import mparser
from . import pagenumbering
from . import roman
from . import quality_assurance
from . import pandoc
from . import toc

lang = "cs"
try:
    # set language
    pass
except Exception:
    lang = "en"

for file in ["config", "./quality_assurance/markdown"]:
    gettext_lang = gettext.translation(file, localedir=os.path.dirname(os.path.realpath(__file__)) + "/locale", languages=[lang])
    gettext_lang.install()

    

__all__ = ["pandoc", "quality_assurance", "filesystem", "mparser",
        "errors", "datastructures", "contentfilter", "config", "master",
        "factories", "toc"]
