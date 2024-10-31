from collections.abc import Iterable
from typing import Protocol

from libecalc.dto import CompressorModel, FuelType, GeneratorSetSampled, PumpModel, TabulatedData


class InvalidReferenceException(Exception):
    def __init__(self, reference_type: str, reference: str, available_references: Iterable[str] = None):
        if available_references is not None:
            available_message = f"Available references: {', '.join(available_references)}"
        else:
            available_message = ""
        super().__init__(f"Invalid {reference_type} reference '{reference}'. {available_message}")


class ReferenceService(Protocol):
    def get_fuel_reference(self, reference: str) -> FuelType: ...

    def get_generator_set_model(self, reference: str) -> GeneratorSetSampled: ...

    def get_compressor_model(self, reference: str) -> CompressorModel: ...

    def get_pump_model(self, reference: str) -> PumpModel: ...

    def get_tabulated_model(self, reference: str) -> TabulatedData: ...
