# This is free software, licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2016 Sebastian Humenda <shumenda |at|gmx |dot| de>
"""
Link checker for MarkDown documents.

When linking to another file, the link has to use the target format extension
(i.e. .html) and hence that has to be considered when looking for broken links.
This link checker is hence tailored to MarkDown.

This link checker also checks for broken image references.

This link checker does not touch the file system. It requires a list of files
(as produced by os.walk()) and all links and images. Helper function extract
those for the link checker.
"""


"""
A common source of error are broken links. Normal link checkers won't work, 
since they are working on HTML files. It is hence necessary to parse all 
MarkDown links and implement the destination checks manually (to the 
resulting HTML files). As a plus, references within the document could be 
checked as well.

For checking IDs, it is a good idea to generate IDs of the target document. 
Headings get automatic IDs, which can be generated using datastructures.gen_id.
Furthermore, the user may create own anchors with <span id="foo"/> or the 
div equivalent.
"""

"""
Checking links in the markdown document
- a) parse the links
- b) test if they are corretly structured
- c) check external links
    - ca) test if the computer is online
    - cb) if online - test the reachability of the 
- d) check internal links (no need to be online, files should be on the disk)
    - da) check if files are generated
    - db) if they are - check all links given by markdown
"""


class LinkParser():
    # ToDo: document: files must be relative to document being checked
    # ToDo: how to thread ..? just check with os.path.exists()? needs base
    # directory
    # def __init__(self, links, images, files):
    def __init__(self, file_list):
        self.errors = []
        print(file_list)

    def target_exists(self, target_file_name):
        pass

    def extract_links(self, file_name):
        pass

class LinkStructureChecker():
    pass

class LinkOnlineChecker():
    pass

class RelativeUrlChecker():
    pass



