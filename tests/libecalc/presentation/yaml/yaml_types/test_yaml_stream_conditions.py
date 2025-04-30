from datetime import datetime

import pytest

from libecalc.common.component_type import ComponentType
from libecalc.common.units import Unit
from libecalc.common.utils.rates import RateType
from libecalc.common.variables import VariablesMap
from libecalc.domain.infrastructure.emitters.venting_emitter import (
    VentingEmission,
    EmissionRate,
    DirectVentingEmitter,
    VentingType,
)
from libecalc.expression import Expression
from libecalc.presentation.yaml.yaml_types.yaml_stream_conditions import YamlEmissionRate, YamlOilVolumeRate


def test_yaml_emission_rate_condition_and_conditions_mutual_exclusion():
    with pytest.raises(ValueError, match="Either CONDITION or CONDITIONS should be specified, not both."):
        YamlEmissionRate(value="10", condition="x > 5", conditions=["x > 5", "y < 10"])


def test_yaml_oil_volume_rate_condition_and_conditions_mutual_exclusion():
    with pytest.raises(ValueError, match="Either CONDITION or CONDITIONS should be specified, not both."):
        YamlEmissionRate(value="10", condition="x > 5", conditions=["x > 5", "y < 10"])


def test_direct_venting_emitter_with_condition():
    venting_emission_values = [10, 100]

    expression_evaluator = VariablesMap(
        variables={"venting_emissions": venting_emission_values},
        time_vector=[
            datetime(2022, 1, 1),
            datetime(2023, 1, 1),
            datetime(2024, 1, 1),
        ],
    )
    emissions = [
        VentingEmission(
            name="CO2",
            emission_rate=EmissionRate(
                value="venting_emissions",
                unit=Unit.KILO_PER_DAY,
                rate_type=RateType.STREAM_DAY,
                condition=Expression.setup_from_expression(value="venting_emissions > 50"),
            ),
        ),
    ]
    emitter = DirectVentingEmitter(
        name="TestEmitter",
        emitter_type=VentingType.DIRECT_EMISSION,
        expression_evaluator=expression_evaluator,
        component_type=ComponentType.VENTING_EMITTER,
        user_defined_category={},
        regularity={},
        emissions=emissions,
    )

    unit = emissions[0].emission_rate.unit

    # First period does not meet the condition (> 50), so it should be 0
    expected_result = unit.to(Unit.TONS_PER_DAY)([0, 100])

    result = emitter.get_emissions()
    assert result["CO2"].values == expected_result
