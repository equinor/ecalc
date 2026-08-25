import abc
from collections.abc import Iterable, Sequence
from typing import Protocol

from pydantic import BaseModel

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.presentation.yaml.mappers.yaml_path import YamlPath
from libecalc.presentation.yaml.yaml_types.facility_model.yaml_facility_model import (
    YamlCompressorTabularModel,
    YamlGeneratorSetModel,
    YamlPumpChartSingleSpeed,
    YamlPumpChartVariableSpeed,
    YamlTabularModel,
)
from libecalc.presentation.yaml.yaml_types.fuel_type.yaml_fuel_type import YamlFuelType
from libecalc.presentation.yaml.yaml_types.models import (
    YamlCompressorChart,
    YamlCompressorWithTurbine,
    YamlFluidModel,
    YamlTurbine,
)
from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_trains import (
    YamlSimplifiedVariableSpeedCompressorTrain,
    YamlSingleSpeedCompressorTrain,
    YamlVariableSpeedCompressorTrain,
    YamlVariableSpeedCompressorTrainMultipleStreamsAndPressures,
)


class InvalidReferenceException(EcalcValidationException):
    def __init__(self, reference_type: str, reference: str, available_references: Iterable[str] | None = None):
        self.reference_type = reference_type
        self.reference = reference
        self.available_references = list(available_references) if available_references is not None else None
        if self.available_references is not None:
            available_message = f"Available references: {', '.join(self.available_references)}"
        else:
            available_message = ""
        super().__init__(message=f"Invalid {reference_type} reference '{reference}'. {available_message}")


class ReferenceNotFoundError(InvalidReferenceException):
    """Raised when a reference string does not match any known named object."""

    def __init__(self, reference_type: str, reference: str, available_references: Iterable[str]):
        super().__init__(
            reference_type=reference_type,
            reference=reference,
            available_references=available_references,
        )


class ReferenceTypeError(InvalidReferenceException):
    """Raised when a reference resolves to an object of an unexpected type."""

    def __init__(self, reference_type: str, reference: str, available_references: Iterable[str] | None = None):
        super().__init__(
            reference_type=reference_type,
            reference=reference,
            available_references=available_references,
        )


YamlCompressorModel = (
    YamlSimplifiedVariableSpeedCompressorTrain
    | YamlVariableSpeedCompressorTrain
    | YamlSingleSpeedCompressorTrain
    | YamlCompressorWithTurbine
    | YamlVariableSpeedCompressorTrainMultipleStreamsAndPressures
    | YamlCompressorTabularModel
)


class ReferenceService(Protocol):
    @abc.abstractmethod
    def get_yaml_path(self, reference: str) -> YamlPath: ...

    @abc.abstractmethod
    def get_fluid(self, reference: str) -> YamlFluidModel: ...

    @abc.abstractmethod
    def get_turbine(self, reference: str) -> YamlTurbine: ...

    @abc.abstractmethod
    def get_compressor_chart(self, reference: str) -> YamlCompressorChart: ...

    @abc.abstractmethod
    def get_fuel_reference(self, reference: str) -> YamlFuelType: ...

    @abc.abstractmethod
    def get_generator_set_model(self, reference: str) -> YamlGeneratorSetModel: ...

    @abc.abstractmethod
    def get_compressor_model(self, reference: str) -> YamlCompressorModel: ...

    @abc.abstractmethod
    def get_pump_model(self, reference: str) -> YamlPumpChartSingleSpeed | YamlPumpChartVariableSpeed: ...

    @abc.abstractmethod
    def get_tabulated_model(self, reference: str) -> YamlTabularModel: ...

    @abc.abstractmethod
    def get_references(self, obj: BaseModel) -> Sequence[str]: ...

    @abc.abstractmethod
    def get_reference(self, reference: str) -> BaseModel: ...
