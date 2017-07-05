# This file does NOT test pandoc, but MAGSBS.pandoc ;)
#pylint: disable=too-many-public-methods,import-error,too-few-public-methods,missing-docstring,unused-variable,multiple-imports
import os, shutil, tempfile, unittest, json
import MAGSBS.datastructures as datastructures
import MAGSBS.errors as errors
import MAGSBS.pandoc as pandoc

META_DATA = {'editor':'unique1', 'sourceAuthor':'dummy', 'workinggroup':'unique2',
        'institution':'unique3', 'source':'unique4', 'lecturetitle':'unique5',
        'semesterofedit':'unique1990',
        'language': 'de',
        'path': 'None'}

#pylint: disable=dangerous-default-value
def get_html_converter(meta_data=META_DATA, template=None):
    h = pandoc.HtmlConverter(meta_data, language='de')
    if meta_data:
        h.set_meta_data(meta_data)
    if template:
        h.template_copy = template
    h.setup()
    return h


class test_HTMLConverter(unittest.TestCase):
    def setUp(self):
        self.original_directory = os.getcwd()
        self.tmpdir = tempfile.mkdtemp()
        os.chdir(self.tmpdir)
        self.call_cleanup_on_me = None # used for the OutputFormatters

    def tearDown(self):
        os.chdir(self.original_directory)
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        if self.call_cleanup_on_me:
            self.call_cleanup_on_me.cleanup()


    def test_that_css_information_is_in_template(self):
        self.assertTrue('.underline' in get_html_converter().template_copy)
        self.assertTrue('.frame' in get_html_converter().template_copy)

    def test_that_unsupported_formats_are_detected(self):
        with self.assertRaises(NotImplementedError):
            pandoc.Pandoc().get_formatter_for_format('mp4')

    def test_that_all_meta_data_is_inserted_into_head(self):
        h = pandoc.Pandoc().get_formatter_for_format('html')
        self.call_cleanup_on_me = h
        h.set_meta_data(META_DATA)
        data = h.get_template()
        for key, value in META_DATA.items():
            if key == 'title' or key == 'language' or key == 'path':
                continue # those don't need to be included
            self.assertTrue(value in data,
                    "%s (key=%s) not found in the template\n%s" % \
                    (value, key, str(data)))

    def test_that_setup_writes_template(self):
        h = get_html_converter()
        self.call_cleanup_on_me = h
        self.assertTrue(os.path.exists(h.template_path))

    def test_title_is_contained_in_document(self):
        # example json document; title is "It works!"
        json_document = json.loads('{"blocks":[{"t":"Header","c":[1,["it-works",[],[]],[{"t":"Str","c":"It"},{"t":"Space"},{"t":"Str","c":"works!"}]]},{"t":"Para","c":[{"t":"Str","c":"blub"}]}],"pandoc-api-version":[1,17,0,4],"meta":{}}')

        h = get_html_converter()
        h.convert(json_document, 'It works!', 'foo.md')
        with open('foo.html') as f:
            data = f.read()
        self.assertTrue('<title>It works!</title>' in data)

    def test_that_unknown_keys_are_ignored(self):
        meta = dict(META_DATA)
        meta['malicious'] = 'evil'
        try:
            h = get_html_converter(meta)
        except errors.MAGSBS_error as e:
            self.fail("Did not expect an exception when supplying more keys than necessary, got one anyway: " + str(e))

    def test_that_missing_key_raises_conf_error(self):
        meta = dict(META_DATA)
        meta.pop('sourceAuthor')
        self.assertRaises(errors.ConfigurationError, get_html_converter, meta)

    def test_that_language_is_set_in_body(self):
        meta = META_DATA.copy()
        meta['language'] = 'fr'
        # example json document; title is "It works!"
        json_document = json.loads('{"blocks":[{"t":"Header","c":[1,["it-works",[],[]],[{"t":"Str","c":"It"},{"t":"Space"},{"t":"Str","c":"works!"}]]},{"t":"Para","c":[{"t":"Str","c":"blub"}]}],"pandoc-api-version":[1,17,0,4],"meta":{}}')
        h = get_html_converter(meta)
        h.convert(json_document, 'It works!', 'foo.md')
        with open('foo.html') as f:
            data = f.read()
        bodypos = data.find('<body')
        self.assertTrue('<body lang="fr"' in data or "<body lang='fr'" in data,
                repr(data[bodypos:bodypos+250]))


################################################################################

class TestNavbarGeneration(unittest.TestCase):
    def setUp(self):
        self.files = (('.', ('anh01', 'v01', 'k01',), ('index.html',)),
                ('anh01', [], ('anh01.md',)),
                ('k01', (), ('k01.md',)),
                ('v01', (), ('v01.md',))
                )
        self.cache = datastructures.FileCache(self.files)
        self.pagenumbers = []
        for i in range(1,50):
            self.pagenumbers.append(datastructures.PageNumber('Seite', i))

        # set up test directory
        self.original_directory = os.getcwd()
        self.tmpdir = tempfile.mkdtemp()
        os.chdir(self.tmpdir)
        for d, _, files in self.files:
            if not os.path.exists(d):
                os.mkdir(d)
            for f in files:
                with open(os.path.join(d, f), 'w') as file:
                    file.write('\n')

    def tearDown(self):
        os.chdir(self.original_directory)
        shutil.rmtree(self.tmpdir, ignore_errors=True)



    def gen_nav(self, path, cache=None, pnums=None, conf=None):
        pnums = (pnums if pnums else self.pagenumbers)
        return pandoc.generate_page_navigation(path,
                (cache if cache else self.cache),
                pnums,
                conf=conf)


    def test_that_navbar_is_generated(self):
        start,end = self.gen_nav('k01/k01.md')
        self.assertTrue(start != None and end != None)
        self.assertTrue(isinstance(start, str) and isinstance(end, str))

    def test_that_pnum_gap_is_used(self):
        conf = {'language' : 'de',  'pageNumberingGap' : 10, 'format' : 'html'}
        start, end = self.gen_nav('k01/k01.md', conf=conf)
        self.assertTrue('[5]' not in start+end) # links to page 5 don't exist
        self.assertTrue('[10]' in start+end, # links to page 10 do exist
                "page number 10 doesn't exist; got: " + repr(start))

    def test_that_roman_numbers_work(self):
        pnums = [datastructures.PageNumber('page', i, is_arabic=False) for i in
                range(1, 20)]
        conf = {'language' : 'de',  'pageNumberingGap' : 5, 'format' : 'html'}
        path = 'k01/k01.md' # that has been initilized in the setup method
        start, end = pandoc.generate_page_navigation(path, self.cache, pnums, conf=conf)
        self.assertTrue('[V]' in start+end,
            "Expected page number V in output, but couldn't be found: " + repr(start))

    def test_that_language_is_used(self):
        conf = {'language' : 'en',  'pageNumberingGap' : 5, 'format' : 'html'}
        start, end = map(str.lower, self.gen_nav('k01/k01.md', conf=conf))
        self.assertTrue('nhalt]' not in start+end)
        self.assertTrue('table of contents]' in start+end)

    def test_that_link_to_next_file_if_missing_is_omitted(self):
        start, end = self.gen_nav('anh01/anh01.md')
        self.assertTrue('k01/k01.html' in start+end,
                "previous chapter k01/k01.md not found; navbar: " + repr(start))
        chapter_navigation = None
        for chapter_navigation in start.split('\n'):
            if chapter_navigation.endswith('inhalt.html)'):
                break
        self.assertTrue(chapter_navigation != None,
                ("A link to the next chapter should not exist, since there is "
                "none. However something makes this test believe that there is "
                "actually another link. Here's the navigation bar: ") +
                repr(start))

