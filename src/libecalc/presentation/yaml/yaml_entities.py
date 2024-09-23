from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, TextIO, Union

from libecalc.common.errors.exceptions import ColumnNotFoundException, HeaderNotFoundException
from libecalc.dto import EnergyModel, FuelType
from libecalc.presentation.yaml.resource import Resource


@dataclass
class MemoryResource(Resource):
    """
    Resource object where the data is already read and parsed.
    """

    headers: List[str]
    data: List[List[Union[float, int, str]]]

    def get_headers(self) -> List[str]:
        return self.headers

    def get_column(self, header: str) -> List[Union[float, int, str]]:
        try:
            header_index = self.headers.index(header)
            return self.data[header_index]
        except ValueError as e:
            raise HeaderNotFoundException(header=header) from e
        except IndexError as e:
            # Should validate that header and columns are of equal length, but that is currently done elsewhere.
            raise ColumnNotFoundException(header=header) from e


@dataclass
class References:
    models: Dict[str, EnergyModel] = None
    fuel_types: Dict[str, FuelType] = None


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

    node_class.__name__ = f"{cls.__name__}_node"
    return node_class


YamlDict = _create_node_class(dict)
YamlList = _create_node_class(list)
