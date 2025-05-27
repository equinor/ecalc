from collections.abc import Iterable
from typing import Protocol

from libecalc.domain.infrastructure.energy_components.generator_set import GeneratorSetModel
from libecalc.domain.process.compressor.dto.model_types import CompressorModelTypes
from libecalc.domain.process.dto import TabulatedData
from libecalc.domain.process.pump.pump import PumpModelDTO
from libecalc.dto import FuelType


class InvalidReferenceException(Exception):
    def __init__(self, reference_type: str, reference: str, available_references: Iterable[str] = None):
        if available_references is not None:
            available_message = f"Available references: {', '.join(available_references)}"
        else:
            available_message = ""
        super().__init__(f"Invalid {reference_type} reference '{reference}'. {available_message}")


class ReferenceService(Protocol):
    def get_fuel_reference(self, reference: str) -> FuelType: ...

    def get_generator_set_model(self, reference: str) -> GeneratorSetModel: ...

    def get_compressor_model(self, reference: str) -> CompressorModelTypes: ...

    def get_pump_model(self, reference: str) -> PumpModelDTO: ...

    def get_tabulated_model(self, reference: str) -> TabulatedData: ...
