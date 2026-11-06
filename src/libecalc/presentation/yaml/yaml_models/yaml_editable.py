import abc
import datetime
from dataclasses import dataclass
from typing import Any

from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords
from libecalc.presentation.yaml.yaml_models.exceptions import YamlError

YamlPathElement = str | int | datetime.datetime
YamlPath = tuple[YamlPathElement, ...]


@dataclass(frozen=True)
class YamlReference:
    """A value in a yaml document together with the path to where it is located.

    The path uses keys as written in the yaml (original casing) and list indices, starting from the document root.
    """

    path: YamlPath
    value: Any


class YamlEditError(YamlError):
    def __init__(self, problem: str, path: YamlPath):
        self.path = path
        super().__init__(problem=f"{problem} (path: {_format_path(path)})")


class YamlEditable(abc.ABC):
    """Find and edit values in a yaml document by path."""

    @abc.abstractmethod
    def find_file_references(self) -> list[YamlReference]:
        """Find all file references (string values under FILE), anywhere in the document."""
        ...

    @abc.abstractmethod
    def edit(self, reference: YamlReference, new_value: Any) -> YamlReference:
        """Replace the value at reference.path with new_value.

        :raises YamlEditError: if the path does not exist, or the current value differs from reference.value
        :return: a reference to the same path with the new value
        """
        ...


class DataModelYamlEditor(YamlEditable):
    """Adapter over a nested dict/list yaml data model (plain dicts/lists or ruamel CommentedMap/CommentedSeq).

    Edits are applied in place on the wrapped data model, i.e. they are visible to the owner of the data model
    (and preserved formatting/comments for ruamel, since the containers are kept).
    """

    def __init__(self, datamodel: dict[str, Any]):
        self._datamodel = datamodel

    def find_file_references(self) -> list[YamlReference]:
        return [
            reference
            for reference in self._find_key_references(EcalcYamlKeywords.file)
            if isinstance(reference.value, str)
        ]

    def _find_key_references(self, key: str) -> list[YamlReference]:
        """Find all values stored under the given key (case-insensitive), anywhere in the document."""
        references: list[YamlReference] = []
        self._collect_key_references(node=self._datamodel, key=key.lower(), path=(), references=references)
        return references

    @classmethod
    def _collect_key_references(cls, node: Any, key: str, path: YamlPath, references: list[YamlReference]) -> None:
        if isinstance(node, dict):
            for node_key, value in node.items():
                child_path = (*path, node_key)
                if isinstance(node_key, str) and node_key.lower() == key:
                    references.append(YamlReference(path=child_path, value=value))
                else:
                    cls._collect_key_references(node=value, key=key, path=child_path, references=references)
        elif isinstance(node, list):
            for index, item in enumerate(node):
                cls._collect_key_references(node=item, key=key, path=(*path, index), references=references)

    def edit(self, reference: YamlReference, new_value: Any) -> YamlReference:
        if len(reference.path) == 0:
            raise YamlEditError("Cannot edit the document root", path=reference.path)

        parent = self._get_node(reference.path[:-1], full_path=reference.path)
        last = reference.path[-1]
        if not self._contains(parent, last):
            raise YamlEditError("Path does not exist", path=reference.path)

        current_value = parent[last]
        if current_value != reference.value:
            raise YamlEditError(
                f"Value has changed since reference was found, expected {reference.value!r}, got {current_value!r}",
                path=reference.path,
            )

        parent[last] = new_value
        return YamlReference(path=reference.path, value=new_value)

    def _get_node(self, path: YamlPath, full_path: YamlPath) -> Any:
        node: Any = self._datamodel
        for element in path:
            if not self._contains(node, element):
                raise YamlEditError("Path does not exist", path=full_path)
            node = node[element]
        return node

    @staticmethod
    def _contains(node: Any, element: YamlPathElement) -> bool:
        if isinstance(node, dict):
            return element in node
        if isinstance(node, list):
            return isinstance(element, int) and 0 <= element < len(node)
        return False


def _format_path(path: YamlPath) -> str:
    return ".".join(str(element) for element in path) if path else "<root>"
