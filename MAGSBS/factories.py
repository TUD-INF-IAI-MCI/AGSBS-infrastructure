# This is free software, licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2016 Sebastian Humenda <shumenda |at| gmx |dot| de>
"""This (currently unrevised) module contains factory classes for factorizing
documents or parts of it from data read in other modules. The purpose is the
auto-generation of certain aspects of the generated material."""

import os
import sys
from . import datastructures
from . import config


#pylint: disable=too-many-instance-attributes
class ImageDescription():
    """
ImageDescription(image_path)


Store and format a picture description. It is important here to read all the
method's doc-strings to understand how this class works.

An example:

i = image_description('bilder/bla.jpg')
i.set_description('''
A cow on a meadow eating gras and staring a bit stupidly. It says "moo".
    ''')  # setting the description is optional
i.use_outsourced_descriptions(True) # outsource image descriptions
                                      # outsourced when length of alt attribut > 100
i.set_title("a cow on a meadow") # not necessary for images which are not outsourced
data = i.get_output()

data is either a dictionary with keys 'internal' and 'external', where
'external' is optional. 'internal' is meant to be embedded directly into the
edited text, i.e. into the chapter, 'external' is meant to be included in the
file containing outsourced image descriptions.
"""
    def __init__(self, image_path):
        self.__conf = config.confFactory().get_conf_instance( \
                os.path.split(image_path)[0])
        l10N = config.Translate()
        l10N.set_language(self.__conf['language'])
        self.__translate = _ = l10N.get_translation
        self.__image_path = image_path
        # replace \\ through / on windows
        if sys.platform.lower().startswith('win') and os.sep in image_path:
            self.__image_path = '/'.join(image_path.split(os.sep))
        self.__description = '\n'
        self.__title = None
        self.__outsource_descriptions = False
        # maximum length of image description before outsourcing it
        self.img_maxlength = 100
        self.__outsource_path = _('images') + '.' + self.__conf['format']

    def set_description(self, desc):
        """Set alternative image description."""
        self.__description = desc

    def set_title(self, title):
        """Set the title for an image description. Only use, when image is
        outsourced."""
        self.__title = title

    def get_title(self):
        return self.__title

    def set_outsource_descriptions(self, flag):
        """If set to True, descriptions are always outsourced."""
        self.__outsource_descriptions = flag

    def get_outsource_path(self):
        return self.__outsource_path

    def get_outsourcing_link(self):
        """Return the link for the case that the picture is excluded."""
        _ = self.__translate
        label = datastructures.gen_id( self.get_title() )
        link_text = _('external image description')
        return '[![%s](%s)](%s#%s)' % (link_text, self.__image_path,
                self.get_outsource_path(), label)

    def get_inline_description(self):
        """Generate markdown image with description."""
        desc = self.__description.replace('\n',' ').replace('\r',' ').replace(' ',' ')
        return '![%s](%s)' % (desc, self.__image_path)

    def __get_outsourced_title(self):
        _ = self.__translate
        if not self.__title:
            # generate one from path
            self.__title = _('image description of image').capitalize() + " " + \
                    os.path.split(self.__image_path)[1]
            return self.__title
        else:
            return self.__title

    def will_be_outsourced(self):
        """Determine, depending on the setting, whether description is
        outsourced. If outsourced is set, it will always return true, otherwise
        it'll depend on the description length."""
        if self.__outsource_descriptions:
            return True
        return (True if len(self.__description) > self.img_maxlength else False)

    def get_output(self):
        """Dispatcher function for get_inline_description and
    get_outsourcing_link; will be either a tuple of (link, content for
            outsourced description) or just a tuple with the image
    description/the reference to the image. It'll always return an outsourced
    description if set by set_outsource_descriptions(True) or will automatically
    exclude images longer than 100 characters."""
        if not self.will_be_outsourced():
            return {'internal' : self.get_inline_description()}
        title = self.__get_outsourced_title()
        external_text = '{}\n{}\n\n{}\n\n* * * * *\n'.format(
                title, '-' * len(title), self.__description)
        return {'internal': self.get_outsourcing_link(),
                'external': external_text}

