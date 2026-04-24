import os
import tempfile
import unittest
from unittest import mock

from MAGSBS.cache import DocumentCache


class TestDocumentCache(unittest.TestCase):
    def test_get_or_load_loads_document_only_once(self):
        ast = {"blocks": [], "meta": {}}
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "k01.md")
            with mock.patch(
                "MAGSBS.cache.contentfilter.file2json_ast", return_value=ast
            ) as file2json_ast:
                cache = DocumentCache()

                self.assertIs(cache.get_or_load(path), ast)
                self.assertIs(cache.get_or_load(path), ast)

                file2json_ast.assert_called_once_with(os.path.abspath(path))

    def test_get_copy_does_not_mutate_cached_ast(self):
        ast = {"blocks": [{"t": "Para", "c": []}], "meta": {}}
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "k01.md")
            cache = DocumentCache()
            cache.add(path, ast)

            ast_copy = cache.get_copy(path)
            ast_copy["blocks"].append({"t": "Para", "c": []})

            self.assertEqual(1, len(cache.get(path)["blocks"]))
