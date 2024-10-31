from dataclasses import dataclass
from enum import Enum
from typing import TextIO, Union, get_args

from libecalc.common.errors.exceptions import ColumnNotFoundException, HeaderNotFoundException
from libecalc.dto import CompressorModel, EnergyModel, FuelType, GeneratorSetSampled, PumpModel, TabulatedData
from libecalc.presentation.yaml.domain.reference_service import InvalidReferenceException, ReferenceService
from libecalc.presentation.yaml.resource import Resource


@dataclass
class MemoryResource(Resource):
    """
    Resource object where the data is already read and parsed.
    """

    headers: list[str]
    data: list[list[Union[float, int, str]]]

    def get_headers(self) -> list[str]:
        return self.headers

    def get_column(self, header: str) -> list[Union[float, int, str]]:
        try:
            header_index = self.headers.index(header)
            return self.data[header_index]
        except ValueError as e:
            raise HeaderNotFoundException(header=header) from e
        except IndexError as e:
            # Should validate that header and columns are of equal length, but that is currently done elsewhere.
            raise ColumnNotFoundException(header=header) from e


@dataclass
class References(ReferenceService):
    models: dict[str, EnergyModel] = None
    fuel_types: dict[str, FuelType] = None

    def get_fuel_reference(self, reference: str) -> FuelType:
        try:
            return self.fuel_types[reference]
        except (KeyError, TypeError) as e:
            # KeyError: key does not exist
            # TypeError: fuel_types is None
            raise InvalidReferenceException("fuel", reference, self.fuel_types.keys()) from e

    def _get_model_reference(self, reference: str, reference_type_name: str) -> EnergyModel:
        try:
            return self.models[reference]
        except (KeyError, TypeError) as e:
            # KeyError: key does not exist
            # TypeError: fuel_types is None
            raise InvalidReferenceException(reference_type_name, reference, self.models.keys()) from e

    def get_generator_set_model(self, reference: str) -> GeneratorSetSampled:
        model = self._get_model_reference(reference, "generator set model")
        if not isinstance(model, GeneratorSetSampled):
            raise InvalidReferenceException("generator set model", reference)
        return model

    def get_compressor_model(self, reference: str) -> CompressorModel:
        model = self._get_model_reference(reference, "compressor model")
        if not isinstance(model, get_args(CompressorModel)):
            raise InvalidReferenceException("compressor model", reference)
        return model  # noqa

    def get_pump_model(self, reference: str) -> PumpModel:
        model = self._get_model_reference(reference, "compressor model")
        if not isinstance(model, PumpModel):
            raise InvalidReferenceException("pump model", reference)
        return model

    def get_tabulated_model(self, reference: str) -> TabulatedData:
        model = self._get_model_reference(reference, "tabulated")
        if not isinstance(model, TabulatedData):
            raise InvalidReferenceException("tabulated", reference)
        return model


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
