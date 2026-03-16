# This file does NOT test pandoc, but MAGSBS.pandoc ;)
# pylint: disable=too-many-public-methods,import-error,too-few-public-methods,missing-docstring,unused-variable,multiple-imports,invalid-name
import os, shutil, tempfile, unittest, json, pandocfilters
from unittest import mock
from MAGSBS.config import MetaInfo
import MAGSBS.datastructures as datastructures
import MAGSBS.errors as errors
import MAGSBS.pandoc as pandoc

# these are the already normalized keys of the MetaInfo enum
META_DATA = {
    "Editor": "unique1",
    "SourceAuthor": "dummy",
    "WorkingGroup": "unique2",
    "Institution": "unique3",
    "Source": "unique4",
    "LectureTitle": "unique5",
    "SemesterOfEdit": "unique1990",
    "Language": "de",
    "path": "None",
}


def get_html_converter(meta_data=META_DATA, template=None):
    h = pandoc.output_formats.html.HtmlConverter(meta_data, language="de")
    if template:
        h.template_copy = template
    h.setup()
    return h


def get_epub_converter(meta_data=META_DATA):
    h = pandoc.output_formats.epub.EpubConverter(meta_data, language="de")
    h.setup()
    return h


def mkcache(file):
    return datastructures.FileCache(
        [
            (".", [os.path.dirname(file)], []),
            (os.path.dirname(file), [], [os.path.basename(file)]),
        ]
    )


class CleverTmpDir(tempfile.TemporaryDirectory):
    def __init__(self):
        self.cwd = os.getcwd()
        super().__init__()

    def __enter__(self):
        super().__enter__()
        os.chdir(self.name)

    def __exit__(self, a, b, c):
        os.chdir(self.cwd)
        super().__exit__(a, b, c)


class test_HTMLConverter(unittest.TestCase):
    def setUp(self):
        self.original_directory = os.getcwd()
        self.tmpdir = tempfile.mkdtemp()
        os.chdir(self.tmpdir)
        self.call_cleanup_on_me = None  # used for the OutputFormatters

    def tearDown(self):
        os.chdir(self.original_directory)
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        if self.call_cleanup_on_me:
            self.call_cleanup_on_me.cleanup()

    def test_that_css_information_is_in_template(self):
        self.assertTrue(".underline" in get_html_converter().template_copy)
        self.assertTrue(".frame" in get_html_converter().template_copy)

    def test_that_unsupported_formats_are_detected(self):
        with self.assertRaises(NotImplementedError):
            pandoc.converter.Pandoc().get_formatter_for_format("mp4")

    def test_that_all_meta_data_is_inserted_into_head(self):
        h = pandoc.converter.Pandoc().get_formatter_for_format("html")
        self.call_cleanup_on_me = h
        h.set_meta_data(META_DATA)
        data = h.get_template()
        for key, value in META_DATA.items():
            if key == "title" or key == "language" or key == "path":
                continue  # those don't need to be included
            self.assertTrue(
                value in data,
                "%s (key=%s) not found in the template\n%s" % (value, key, str(data)),
            )

    def test_that_setup_writes_template(self):
        h = get_html_converter()
        self.call_cleanup_on_me = h
        self.assertTrue(os.path.exists(h.template_path))

    def test_title_is_contained_in_document(self):
        with CleverTmpDir():
            path = os.path.join("k99", "k99.md")
            os.mkdir(os.path.dirname(path))
            with open(path, "w", encoding="utf-8") as file:
                file.write("It works!\n=======\n\nbla\nblub\n")
            h = get_html_converter()
            h.convert([path], cache=mkcache(path))
            with open(path.replace(".md", ".html")) as f:
                data = f.read()
            self.assertTrue("<title>It works!</title>" in data)

    def test_that_missing_key_raises_conf_error(self):
        meta = dict(META_DATA)
        meta.pop("SourceAuthor")
        self.assertRaises(errors.ConfigurationError, get_html_converter, meta)

    def test_that_language_is_set_in_body(self):
        meta = META_DATA.copy()
        meta["Language"] = "fr"
        with CleverTmpDir():
            path = os.path.join("k99", "k99.md")  # path within lecture
            os.mkdir(os.path.dirname(path))
            with open(path, "w") as file:
                file.write("It works!\n=========\n\nblah\nblub\n")
            h = get_html_converter(meta)
            h.convert([path], cache=mkcache(path))
            with open(path.replace(".md", ".html")) as f:
                data = f.read()
            bodypos = data.find("<body")
            self.assertTrue(
                '<body lang="fr"' in data or "<body lang='fr'" in data,
                repr(data[bodypos : bodypos + 250]),
            )

    def test_conentfilter_link_converter(self):
        """ast contains a link: 'target.md#target_id'.
        It should get converted to 'target.html#target_id'.
        """
        ast = {
            "blocks": [
                {"t": "Link", "c": [["", [], []], [], ["target.md#target_id", ""]],}
            ]
        }
        ast = pandocfilters.walk(
            ast, pandoc.contentfilter.html_link_converter, "html", None
        )
        self.assertTrue("target.html#target_id" in json.dumps(ast))

    def test_convert_formulas_falls_back_to_legacy_gladtex_formatter(self):
        long_formula = "x" * 150
        ast = {
            "blocks": [
                {"t": "Math", "c": [{"t": "InlineMath"}, long_formula]},
            ]
        }

        class DummyConverter:
            def __init__(self, *args, **kwargs):
                pass

            def set_replace_nonascii(self, flag):
                self.replace_nonascii = flag

            def convert_all(self, formulas):
                self.formulas = formulas

            def get_data_for(self, eqn, style):
                return {
                    "pos": {"depth": 0, "height": 10, "width": 10},
                    "formula": eqn,
                    "path": "bilder/eqn000.svg",
                    "displaymath": style,
                }

        class DummyLegacyFormatter:
            instances = []

            def __init__(self, base_path):
                self.base_path = base_path
                self.replace_nonascii = False
                self.exclude_long_formulas = False
                self.closed = False
                self._HtmlImageFormatter__exclusion_filepath = (
                    "outsourced-descriptions.html"
                )
                DummyLegacyFormatter.instances.append(self)

            def set_replace_nonascii(self, flag):
                self.replace_nonascii = flag

            def set_exclude_long_formulas(self, flag):
                self.exclude_long_formulas = flag

            def format(self, pos, formula, img_path, displaymath=False):
                return f"<img src='{img_path}' alt='{formula[:10]}' />"

            def close(self):
                self.closed = True

        def legacy_replace(formatter, blocks, formulas):
            eqn = formulas.pop(0)
            blocks[0].clear()
            blocks[0].update(
                {
                    "t": "RawInline",
                    "c": [
                        "html",
                        formatter.format(
                            eqn["pos"],
                            eqn["formula"],
                            eqn["path"],
                            eqn["displaymath"],
                        ),
                    ],
                }
            )

        with mock.patch.object(
            pandoc.contentfilter.gleetex.pandoc,
            "PandocAstImageFormatter",
            None,
        ), mock.patch.object(
            pandoc.contentfilter.gleetex.pandoc,
            "extract_formulas",
            return_value=[(None, False, long_formula)],
        ), mock.patch.object(
            pandoc.contentfilter.gleetex.pandoc,
            "replace_formulas_in_ast",
            side_effect=legacy_replace,
        ), mock.patch.object(
            pandoc.contentfilter.gleetex.cachedconverter,
            "CachedConverter",
            DummyConverter,
        ), mock.patch.object(
            pandoc.contentfilter.gleetex.htmlhandling,
            "HtmlImageFormatter",
            DummyLegacyFormatter,
            create=True,
        ):
            pandoc.contentfilter.convert_formulas("k01/k01.md", "bilder", ast)

        self.assertEqual(ast["blocks"][0]["t"], "RawInline")
        self.assertIn("bilder/eqn000.svg", ast["blocks"][0]["c"][1])
        self.assertTrue(DummyLegacyFormatter.instances[0].replace_nonascii)
        self.assertTrue(DummyLegacyFormatter.instances[0].exclude_long_formulas)
        self.assertTrue(DummyLegacyFormatter.instances[0].closed)
        self.assertEqual(
            DummyLegacyFormatter.instances[0]._HtmlImageFormatter__exclusion_filepath,
            "k01/excluded-descriptions.html",
        )

    def test_legacy_cachedconverter_uses_output_path_for_existing_eqn_files(self):
        class DummyCache:
            def contains(self, formula, displaymath):
                return False

        class BrokenCachedConverter:
            def __init__(self):
                self._CachedConverter__options = {"png": False}
                self._CachedConverter__img_dir = "bilder"
                self._CachedConverter__output_path = os.path.join(
                    os.getcwd(), "k01"
                )
                self._CachedConverter__cache = DummyCache()

            def _get_formulas_to_convert(self, formulas):
                file_ext = (
                    pandoc.contentfilter.gleetex.cachedconverter.Format.Png.value
                    if self._CachedConverter__options["png"]
                    else pandoc.contentfilter.gleetex.cachedconverter.Format.Svg.value
                )
                eqn_path = lambda x: os.path.join(
                    self._CachedConverter__img_dir, "eqn%03d.%s" % (x, file_ext)
                )
                abs_eqn_path = lambda x: os.path.join(
                    self._CachedConverter__img_dir, eqn_path(x)
                )
                formulas_to_convert = []
                file_name_count = 0
                for formula_count, (pos, dsp, formula) in enumerate(formulas):
                    while os.path.exists(abs_eqn_path(file_name_count)):
                        file_name_count += 1
                    formulas_to_convert.append(
                        (formula, pos, eqn_path(file_name_count), dsp, formula_count + 1)
                    )
                return formulas_to_convert

        with CleverTmpDir():
            os.makedirs(os.path.join("k01", "bilder"))
            for index in range(8):
                with open(
                    os.path.join("k01", "bilder", "eqn%03d.svg" % index), "w"
                ) as file:
                    file.write("placeholder")

            with mock.patch.object(
                pandoc.contentfilter.gleetex.cachedconverter,
                "CachedConverter",
                BrokenCachedConverter,
            ):
                pandoc.contentfilter._patch_legacy_cachedconverter()
                converter = BrokenCachedConverter()
                pipeline = converter._get_formulas_to_convert(
                    [((0, 0), False, "x+y")]
                )

            self.assertEqual("bilder/eqn008.svg", pipeline[0][2])


################################################################################


class test_EPUBConverter(unittest.TestCase):
    def setUp(self):
        self.original_directory = os.getcwd()
        self.tmpdir = tempfile.mkdtemp()
        os.chdir(self.tmpdir)
        self.call_cleanup_on_me = None  # used for the OutputFormatters

    def tearDown(self):
        os.chdir(self.original_directory)
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        if self.call_cleanup_on_me:
            self.call_cleanup_on_me.cleanup()

    def test_that_setup_writes_css_template(self):
        h = get_epub_converter()
        self.call_cleanup_on_me = h
        self.assertTrue(os.path.exists(h.css_path))

    def test_conentfilter_link_converter(self):
        """ast contains a link: 'target.html#target_id'.
        It should get converted to 'ch003.xhtml#target_id'.
        meta contains the key 'target_id' with the chapter number '3' as value."""
        ast = {
            "blocks": [
                {"t": "Link", "c": [["", [], []], [], ["target.html#target_id", ""]],}
            ]
        }
        meta = {"ids": {"target_id": 3}}
        ast = pandocfilters.walk(
            ast, pandoc.contentfilter.epub_link_converter, "epub", meta
        )
        self.assertTrue("ch003.xhtml#target_id" in json.dumps(ast))

    def test_conentfilter_convert_header_ids(self):
        """meta conatins 'k03' which is used as prefix for IDs.
        ast contains a header with the id: 'header_id'.
        It should get converted to 'k03_header_id'.
        ast contains an image link with the id: 'image_id'.
        It should get converted to 'image_k03_image_id'."""
        ast = {
            "blocks": [
                {
                    "t": "Link",
                    "c": [
                        ["", [], []],
                        [
                            {
                                "t": "Image",
                                "c": [["", [], []], [], ["k02/bilder/image.png", ""],],
                            }
                        ],
                        ["image#image_id", ""],
                    ],
                },
                {"t": "Header", "c": [1, ["header_id", [], []], []]},
            ]
        }
        meta = "k03"
        ast = pandocfilters.walk(
            ast, pandoc.contentfilter.epub_convert_header_ids, "epub", meta
        )
        self.assertTrue("k03_header_id" in json.dumps(ast))
        self.assertTrue("image#image_k03_image_id" in json.dumps(ast))

    def test_conentfilter_convert_image_header_ids(self):
        """ast contains a header with the id: 'image_id'.
        It should get converted to 'image_image_id'.
        """
        ast = {"blocks": [{"t": "Header", "c": [1, ["image_id", [], []], []]}]}
        ast = pandocfilters.walk(
            ast, pandoc.contentfilter.epub_convert_image_header_ids, "epub", None,
        )
        self.assertTrue("image_image_id" in json.dumps(ast))

    def test_conentfilter_remove_images_from_toc(self):
        """ast contains a header with the id: 'header_id1', Level 1 and text 'Text'.
        It should get converted to
        '<p id=\\"header_id1\\" class=\\"header pagebreak\\" data-level=\\"1\\">Text</p>'.
        ast contains a header with the id: 'header_id2', Level 2 and text 'Text'.
        It should get converted to
        '<p id=\\"header_id2\\" class=\\"header\\" data-level=\\"2\\">Text</p>'."""
        ast = {
            "blocks": [
                {
                    "t": "Header",
                    "c": [1, ["header_id1", [], []], [{"t": "Str", "c": "Text"}],],
                },
                {
                    "t": "Header",
                    "c": [2, ["header_id2", [], []], [{"t": "Str", "c": "Text"}],],
                },
            ]
        }
        ast = pandocfilters.walk(
            ast, pandoc.contentfilter.epub_remove_images_from_toc, "epub", None
        )
        self.assertTrue(
            '<p id=\\"header_id2\\" class=\\"header\\" data-level=\\"2\\">Text</p>'
            in json.dumps(ast)
        )
        self.assertTrue(
            '<p id=\\"header_id1\\" class=\\"header pagebreak\\" data-level=\\"1\\">Text</p>'
            in json.dumps(ast)
        )

    def test_conentfilter_update_image_location(self):
        """meta conatins 'k03' which is used as prefix for URI.
        ast contains a image with path: 'image.png'.
        It should get converted to 'k03/image.png'."""
        ast = {"blocks": [{"t": "Image", "c": [["", [], []], [], ["image.png", ""]]}]}
        meta = "k03"
        ast = pandocfilters.walk(
            ast, pandoc.contentfilter.epub_update_image_location, "epub", meta
        )
        self.assertTrue("k03/image.png" in json.dumps(ast))

    def test_conentfilter_create_back_link_ids(self):
        """ast contains a link with the id: 'target_id'.
        It should get converted to 'target_id_back'."""
        ast = {
            "blocks": [
                {"t": "Link", "c": [["", [], []], [], ["target.html#target_id", ""]],}
            ]
        }
        ast = pandocfilters.walk(
            ast, pandoc.contentfilter.epub_create_back_link_ids, "epub", None
        )
        self.assertTrue("target_id_back" in json.dumps(ast))

    def test_conentfilter_create_back_links(self):
        """meta contains the key 'image_id_back' with the chapter number '3' as value.
        ast contains a RawBlock which includes the id in a paragraph: 'image_id'.
        The paragraph should contain the backlink with the target 'image_id_back'
        after the filter."""
        ast = {
            "blocks": [
                {
                    "t": "RawBlock",
                    "c": [
                        "html",
                        '<p id="image_id" class="header" data-level="2">Image</p>',
                    ],
                }
            ]
        }
        meta = {"ids": {"image_id_back": 3}}
        ast = pandocfilters.walk(
            ast, pandoc.contentfilter.epub_create_back_links, "epub", meta
        )
        self.assertTrue(
            '<a href=\\"ch003.xhtml#image_id_back\\">Image</a>' in json.dumps(ast)
        )

    def test_conentfilter_collect_ids(self):
        """meta contains '{'chapter': 1, 'ids': {}}'.
        'chapter' in meta should be increased to 2.
        'ids' should contain '{'image_id': 1, 'header_id': 2, 'target_id': 2}'
        after the filter."""
        ast = {
            "blocks": [
                {
                    "t": "RawBlock",
                    "c": [
                        "html",
                        '<p id="image_id" class="header" data-level="2">Image</p>',
                    ],
                },
                {"t": "Header", "c": [1, ["header_id", [], []], []]},
                {
                    "t": "Link",
                    "c": [["target_id", [], []], [], ["target.html#target_id", ""],],
                },
            ]
        }
        meta = {"chapter": 1, "ids": {}}
        ast = pandocfilters.walk(
            ast, pandoc.contentfilter.epub_collect_ids, "epub", meta
        )
        self.assertTrue(meta["chapter"] == 2)
        self.assertTrue("image_id" in meta["ids"] and meta["ids"]["image_id"] == 1)
        self.assertTrue("header_id" in meta["ids"] and meta["ids"]["header_id"] == 2)
        self.assertTrue("target_id" in meta["ids"] and meta["ids"]["target_id"] == 2)

    def test_conentfilter_unnumbered_toc(self):
        """ast contains a header with the id: 'header_id'.
        The class 'unnumbered' should be added to the ast.
        """
        ast = {"blocks": [{"t": "Header", "c": [1, ["header_id", [], []], []]}]}
        ast = pandocfilters.walk(
            ast, pandoc.contentfilter.epub_unnumbered_toc, "epub", None
        )
        self.assertTrue('["unnumbered"]' in json.dumps(ast))


################################################################################


class TestNavbarGeneration(unittest.TestCase):
    def setUp(self):
        self.files = (
            (".", ("anh01", "v01", "k01"), ("index.html",)),
            ("anh01", [], ("anh01.md",)),
            ("k01", (), ("k01.md",)),
            ("v01", (), ("v01.md",)),
        )
        self.cache = datastructures.FileCache(self.files)
        self.pagenumbers = []
        for i in range(1, 50):
            self.pagenumbers.append(datastructures.PageNumber("Seite", i))

        # set up test directory
        self.original_directory = os.getcwd()
        self.tmpdir = tempfile.mkdtemp()
        os.chdir(self.tmpdir)
        for d, _, files in self.files:
            if not os.path.exists(d):
                os.mkdir(d)
            for f in files:
                with open(os.path.join(d, f), "w") as file:
                    file.write("\n")

    def tearDown(self):
        os.chdir(self.original_directory)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def gen_nav(self, path, cache=None, pnums=None, conf=None):
        h = get_html_converter()
        pnums = pnums if pnums else self.pagenumbers
        return h.generate_page_navigation(
            path, (cache if cache else self.cache), pnums, conf=conf
        )

    def test_that_navbar_is_generated(self):
        start, end = self.gen_nav("k01/k01.md")
        self.assertTrue(start != None and end != None)
        self.assertTrue(isinstance(start, str) and isinstance(end, str))

    def test_that_pnum_gap_is_used(self):
        conf = {MetaInfo.Language: "de", MetaInfo.PageNumberingGap: 10}
        start, end = self.gen_nav("k01/k01.md", conf=conf)
        self.assertTrue("[5]" not in start + end)  # links to page 5 don't exist
        self.assertTrue(
            "[10]" in start + end,  # links to page 10 do exist
            "page number 10 doesn't exist; got: " + repr(start),
        )

    def test_that_roman_numbers_work(self):
        h = get_html_converter()
        pnums = [
            datastructures.PageNumber("page", i, is_arabic=False) for i in range(1, 20)
        ]
        conf = {MetaInfo.Language: "de", MetaInfo.PageNumberingGap: 5}
        path = "k01/k01.md"  # that has been initilized in the setup method
        start, end = h.generate_page_navigation(path, self.cache, pnums, conf=conf)
        self.assertTrue(
            "[V]" in start + end,
            "Expected page number V in output, but couldn't be found: " + repr(start),
        )

    def test_that_language_is_used(self):
        conf = {MetaInfo.Language: "en", MetaInfo.PageNumberingGap: 5}
        start, end = map(str.lower, self.gen_nav("k01/k01.md", conf=conf))
        self.assertTrue("nhalt]" not in start + end)
        self.assertTrue("table of contents]" in start + end)

    def test_that_link_to_next_file_if_missing_is_omitted(self):
        start, end = self.gen_nav("anh01/anh01.md")
        self.assertTrue(
            "k01/k01.html" in start + end,
            "previous chapter k01/k01.md not found; navbar: " + repr(start),
        )
        chapter_navigation = None
        for chapter_navigation in start.split("\n"):
            if chapter_navigation.endswith("inhalt.html)"):
                break
        self.assertTrue(
            chapter_navigation != None,
            (
                "A link to the next chapter should not exist, since there is "
                "none. However something makes this test believe that there is "
                "actually another link. Here's the navigation bar: "
            )
            + repr(start),
        )
