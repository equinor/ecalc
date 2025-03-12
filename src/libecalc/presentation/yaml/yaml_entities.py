from dataclasses import dataclass
from enum import Enum
from typing import TextIO, get_args

from libecalc.common.errors.exceptions import ColumnNotFoundException, HeaderNotFoundException
from libecalc.domain.process.dto.base import EnergyModel
from libecalc.domain.process.dto.compressor.base import CompressorModelTypes
from libecalc.domain.process.dto.generator_set import GeneratorSetSampled
from libecalc.domain.process.dto.tabulated import TabulatedData
from libecalc.domain.process.pump.pump import PumpModelDTO
from libecalc.dto import FuelType
from libecalc.presentation.yaml.domain.reference_service import InvalidReferenceException, ReferenceService
from libecalc.presentation.yaml.resource import Resource


@dataclass
class MemoryResource(Resource):
    """
    Resource object where the data is already read and parsed.
    """

    headers: list[str]
    data: list[list[float | int | str]]

    def get_headers(self) -> list[str]:
        return self.headers

    def get_column(self, header: str) -> list[float | int | str]:
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

    def get_compressor_model(self, reference: str) -> CompressorModelTypes:
        model = self._get_model_reference(reference, "compressor model")
        if not isinstance(model, get_args(CompressorModelTypes)):
            raise InvalidReferenceException("compressor model", reference)
        return model  # noqa

    def get_pump_model(self, reference: str) -> PumpModelDTO:
        model = self._get_model_reference(reference, "compressor model")
        if not isinstance(model, PumpModelDTO):
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
