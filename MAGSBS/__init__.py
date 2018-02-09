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

# importing localization
import os
import gettext
# TODO: load lang if it this already exist, english otherwise
# TODO: implement for english
# TODO: do this for all files

lang = "cs"
try:
    # set language
    pass
except Exception:
    lang = "en"

for file in ["./quality_assurance/markdown"]:
    trans = gettext.translation(file, localedir=os.path.dirname(os.path.realpath(__file__)) + "/locale", languages=[lang])
    trans.install()



__all__ = ["pandoc", "quality_assurance", "filesystem", "mparser",
        "errors", "datastructures", "contentfilter", "config", "master",
        "factories", "toc"]
