from typing import Any

from libecalc.dto import FuelType
from libecalc.presentation.yaml.domain.reference_service import ReferenceService, YamlCompressorModel
from libecalc.presentation.yaml.mappers.yaml_path import YamlPath
from libecalc.presentation.yaml.yaml_types.facility_model.yaml_facility_model import (
    YamlGeneratorSetModel,
    YamlPumpChartSingleSpeed,
    YamlPumpChartVariableSpeed,
    YamlTabularModel,
)
from libecalc.presentation.yaml.yaml_types.models import YamlCompressorChart, YamlFluidModel, YamlTurbine
from libecalc.presentation.yaml.yaml_types.process.yaml_process_pipeline import YamlProcessPipeline
from libecalc.presentation.yaml.yaml_types.process.yaml_process_units import YamlProcessUnit
from libecalc.presentation.yaml.yaml_types.streams.yaml_inlet_stream import YamlInletStream


class DirectReferenceService(ReferenceService):
    def __init__(self, references: dict[str, Any]):
        self._references = references

    def _resolve_reference(self, reference: str) -> Any:
        return self._references[reference]

    def get_yaml_path(self, reference: str) -> YamlPath:
        raise NotImplementedError()

    def get_fluid(self, reference: str) -> YamlFluidModel:
        raise NotImplementedError()

    def get_turbine(self, reference: str) -> YamlTurbine:
        raise NotImplementedError()

    def get_compressor_chart(self, reference: str) -> YamlCompressorChart:
        return self._resolve_reference(reference)

    def get_fuel_reference(self, reference: str) -> FuelType:
        raise NotImplementedError()

    def get_generator_set_model(self, reference: str) -> YamlGeneratorSetModel:
        raise NotImplementedError()

    def get_compressor_model(self, reference: str) -> YamlCompressorModel:
        raise NotImplementedError()

    def get_pump_model(self, reference: str) -> YamlPumpChartSingleSpeed | YamlPumpChartVariableSpeed:
        raise NotImplementedError()

    def get_tabulated_model(self, reference: str) -> YamlTabularModel:
        raise NotImplementedError()

    def get_process_pipeline(self, reference: str) -> YamlProcessPipeline:
        raise NotImplementedError()

    def get_process_unit(self, reference: str) -> YamlProcessUnit:
        raise NotImplementedError()

    def get_stream(self, reference: str) -> YamlInletStream:
        raise NotImplementedError()
