"""Getting started:

# create index:
c = create_index('.')
c.walk()

# index 2 markdown:
md = index2markdown_TOC(c.get_data(), 'de')
my_fancy_page = c.get_markdown_page()
"""

from . import factories
from . import pandoc
from . import quality_assurance
from . import master

__all__ = ["pandoc", "quality_assurance", "filesystem", "mparser",
        "errors", "datastructures", "contentfilter", "config", "master",
        "factories"]
