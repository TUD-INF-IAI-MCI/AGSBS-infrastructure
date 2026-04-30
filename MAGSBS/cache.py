import copy
import os
from typing import Any, Dict, Optional

from .pandoc import contentfilter

PandocAst = Dict[str, Any]


class DocumentCache:
    """Cache Pandoc JSON ASTs by document path."""

    def __init__(self) -> None:
        self._store: Dict[str, PandocAst] = {}

    @staticmethod
    def _normalize_path(path: str) -> str:
        return os.path.abspath(path)

    def add(self, path: str, ast: PandocAst) -> None:
        self._store[self._normalize_path(path)] = ast

    def get(self, path: str) -> Optional[PandocAst]:
        return self._store.get(self._normalize_path(path))

    def get_or_load(self, path: str) -> Optional[PandocAst]:
        normalized_path = self._normalize_path(path)
        if normalized_path not in self._store:
            self._store[normalized_path] = contentfilter.file2json_ast(normalized_path)
        return self.get(normalized_path)

    def get_copy(self, path: str) -> Optional[PandocAst]:
        ast = self.get_or_load(path)
        if ast is None:
            return None
        return copy.deepcopy(ast)
