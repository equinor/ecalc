from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, TextIO, Union

from libecalc import dto


@dataclass
class Resource:
    headers: List[str]
    data: List[List[Union[float, int, str]]]


Resources = Dict[str, Resource]


@dataclass
class References:
    models: Dict[str, dto.EnergyModel] = None
    fuel_types: Dict[str, dto.types.FuelType] = None


class YamlTimeseriesType(str, Enum):
    MISCELLANEOUS = "MISCELLANEOUS"
    DEFAULT = "DEFAULT"


@dataclass
class YamlTimeseriesResource:
    name: str
    typ: YamlTimeseriesType


@dataclass
class ResourceStream:
    name: str
    stream: TextIO

    # Implement read to make resource behave as a stream.
    def read(self, *args, **kwargs):
        return self.stream.read(*args, **kwargs)


def _create_node_class(cls):
    class node_class(cls):  # type: ignore
        def __init__(self, *args, **kwargs):
            cls.__init__(self, *args)
            self.start_mark = kwargs.get("start_mark")
            self.end_mark = kwargs.get("end_mark")

        def __new__(self, *args, **kwargs):
            return cls.__new__(self, *args)

    node_class.__name__ = "%s_node" % cls.__name__
    return node_class


YamlDict = _create_node_class(dict)
YamlList = _create_node_class(list)
