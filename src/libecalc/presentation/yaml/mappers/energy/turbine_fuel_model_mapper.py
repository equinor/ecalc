from collections.abc import Mapping

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.domain.resource import Resource
from libecalc.energy.models.turbine_fuel_model import TurbineFuelModel
from libecalc.presentation.yaml.mappers.energy.curve_model_mapper import map_curve_model
from libecalc.presentation.yaml.yaml_types.energy.yaml_turbine_definition import YamlTurbineDefinition
from libecalc.presentation.yaml.yaml_types.yaml_data_or_file import YamlFile

LOAD_HEADER = "LOAD"
EFFICIENCY_HEADER = "EFFICIENCY"


def map_turbine_fuel_model(
    unit_name: str,
    definition: YamlTurbineDefinition,
    resources: Mapping[str, Resource],
    source_lower_heating_value: float | None,
    input_name: str,
) -> TurbineFuelModel:
    if source_lower_heating_value is None:
        raise EcalcValidationException(
            f"'{unit_name}': could not resolve a single LOWER_HEATING_VALUE from '{input_name}'. Set it on the "
            "fuel/diesel source this unit draws from, directly or through a chain of FUEL_GAS_MANIFOLDs that all "
            "agree on the same value."
        )
    curve = definition.curve
    return map_curve_model(
        unit_name=unit_name,
        curve=curve if isinstance(curve, YamlFile) else (curve.load, curve.efficiency),
        resources=resources,
        x_header=LOAD_HEADER,
        y_header=EFFICIENCY_HEADER,
        build=lambda loads, efficiencies: TurbineFuelModel(
            loads=loads, efficiencies=efficiencies, lower_heating_value=source_lower_heating_value
        ),
    )
