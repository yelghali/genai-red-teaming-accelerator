"""Secret-safe helpers for loading strict YAML configuration documents."""

from __future__ import annotations

from pathlib import Path

import yaml
from yaml.constructor import ConstructorError
from yaml.nodes import MappingNode


class _UniqueKeySafeLoader(yaml.SafeLoader):
    """Load SafeLoader-compatible YAML while rejecting key shadowing."""

    def construct_mapping(self, node: MappingNode, deep: bool = False) -> dict[object, object]:
        self.flatten_mapping(node)
        mapping: dict[object, object] = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                duplicate = key in mapping
            except TypeError:
                raise ConstructorError(None, None, "unhashable mapping key", key_node.start_mark) from None
            if duplicate:
                raise ConstructorError(None, None, "duplicate mapping key", key_node.start_mark)
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


def load_yaml_document(path: Path, *, kind: str) -> object:
    """Load YAML without echoing source text through parser diagnostics."""
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"Could not read {kind} {path}: {exc}") from exc

    try:
        return yaml.load(content, Loader=_UniqueKeySafeLoader)
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        location = f" at line {mark.line + 1}, column {mark.column + 1}" if mark is not None else ""
        raise ValueError(f"Could not parse {kind} {path}{location}") from None
