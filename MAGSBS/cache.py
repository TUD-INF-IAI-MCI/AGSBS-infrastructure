import copy
import os
from typing import Any, Dict, Optional

from .pandoc import contentfilter

PandocAst = Dict[str, Any]


class DocumentCache:
    """Cache Pandoc JSON ASTs during one conversion run.

    Both table-of-contents generation and document conversion need to inspect
    the same Markdown files. Without this cache, Pandoc parses every file more
    than once. Documents are loaded lazily and stored in memory under their
    normalized absolute paths.

    The cached AST must remain unchanged. Content filters modify AST nodes in
    place, so callers that apply filters must use :meth:`get_copy`.
    """

    def __init__(self) -> None:
        self._store: Dict[str, PandocAst] = {}

    @staticmethod
    def _normalize_path(path: str) -> str:
        return os.path.abspath(path)

    def add(self, path: str, ast: PandocAst) -> None:
        """Store an AST under its normalized absolute document path."""
        self._store[self._normalize_path(path)] = ast

    def get(self, path: str) -> Optional[PandocAst]:
        """Return the cached AST; callers must treat it as read-only."""
        return self._store.get(self._normalize_path(path))

    def get_or_load(self, path: str) -> Optional[PandocAst]:
        """Return an AST, loading and caching it on the first access.

        The returned object is the cached AST and must not be modified.
        """
        normalized_path = self._normalize_path(path)
        if normalized_path not in self._store:
            self._store[normalized_path] = contentfilter.file2json_ast(normalized_path)
        return self.get(normalized_path)

    def get_copy(self, path: str) -> Optional[PandocAst]:
        """Return an independent AST copy for transformations and filters."""
        ast = self.get_or_load(path)
        if ast is None:
            return None
        return copy.deepcopy(ast)
