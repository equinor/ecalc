from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from libecalc.common.component_type import ComponentType
from libecalc.common.time_utils import Period, Periods
from libecalc.common.units import Unit
from libecalc.common.utils.rates import RateType
from libecalc.common.variables import VariablesMap
from libecalc.domain.infrastructure.emitters.venting_emitter import (
    DirectVentingEmitter,
    EmissionRate,
    OilVentingEmitter,
    OilVolumeRate,
    VentingEmission,
    VentingType,
    VentingVolume,
    VentingVolumeEmission,
)
from libecalc.domain.infrastructure.path_id import PathID
from libecalc.domain.regularity import Regularity
from libecalc.expression import Expression
from libecalc.presentation.yaml.mappers.consumer_function_mapper import _map_condition


@dataclass
class ConditionedModel:
    condition: str = None
    conditions: list[str] = None


def create_expression_evaluator(variable_name, values):
    return VariablesMap(
        variables={variable_name: values},
        periods=Periods.create_periods(
            [
                datetime(2022, 1, 1),
                datetime(2023, 1, 1),
                datetime(2024, 1, 1),
            ],
            include_before=False,
            include_after=False,
        ),
    )


def test_direct_venting_emitter_with_condition():
    expression_evaluator = create_expression_evaluator("venting_emissions", [10, 100])
    regularity = Regularity(expression_evaluator, target_period=Period(start=datetime(2022, 1, 1)), expression_input=1)

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
        id=uuid4(),
        path_id=PathID("TestEmitter"),
        emitter_type=VentingType.DIRECT_EMISSION,
        expression_evaluator=expression_evaluator,
        component_type=ComponentType.VENTING_EMITTER,
        user_defined_category={},
        regularity=regularity,
        emissions=emissions,
    )

    unit = emissions[0].emission_rate.unit

    # First period does not meet the condition (> 50), so it should be 0
    expected_result = unit.to(Unit.TONS_PER_DAY)([0, 100])
    result = emitter.get_emissions()

    assert result["CO2"].values == expected_result


def test_direct_venting_emitter_with_conditions():
    expression_evaluator = create_expression_evaluator("venting_emissions", [10, 100])
    regularity = Regularity(expression_evaluator, target_period=Period(start=datetime(2022, 1, 1)), expression_input=1)

    # Define multiple conditions
    conditions = [
        "venting_emissions > 50",
        "venting_emissions < 150",
    ]

    # Combine conditions using _map_condition
    combined_condition = _map_condition(ConditionedModel(conditions=conditions))

    emissions = [
        VentingEmission(
            name="CO2",
            emission_rate=EmissionRate(
                value="venting_emissions",
                unit=Unit.KILO_PER_DAY,
                rate_type=RateType.STREAM_DAY,
                condition=Expression.setup_from_expression(value=combined_condition),
            ),
        ),
    ]
    emitter = DirectVentingEmitter(
        id=uuid4(),
        path_id=PathID("TestEmitter"),
        emitter_type=VentingType.DIRECT_EMISSION,
        expression_evaluator=expression_evaluator,
        component_type=ComponentType.VENTING_EMITTER,
        user_defined_category={},
        regularity=regularity,
        emissions=emissions,
    )

    unit = emissions[0].emission_rate.unit

    # First period does not meet the conditions (> 50 and < 150), so it should be 0
    expected_result = unit.to(Unit.TONS_PER_DAY)([0, 100])
    result = emitter.get_emissions()

    assert result["CO2"].values == expected_result


def test_oil_venting_emitter_with_condition():
    expression_evaluator = create_expression_evaluator("oil_volume", [20, 200])

    oil_volume_rate = OilVolumeRate(
        value="oil_volume",
        unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
        rate_type=RateType.STREAM_DAY,
        condition=Expression.setup_from_expression(value="oil_volume > 100"),
    )
    emissions = [
        VentingVolumeEmission(
            name="CH4",
            emission_factor="0.1",  # Example emission factor
        ),
    ]
    volume = VentingVolume(oil_volume_rate=oil_volume_rate, emissions=emissions)

    regularity = Regularity(expression_evaluator=expression_evaluator, target_period=expression_evaluator.get_period())

    emitter = OilVentingEmitter(
        id=uuid4(),
        path_id=PathID("TestOilEmitter"),
        emitter_type=VentingType.OIL_VOLUME,
        expression_evaluator=expression_evaluator,
        component_type=ComponentType.VENTING_EMITTER,
        user_defined_category={},
        regularity=regularity,
        volume=volume,
    )

    # First period does not meet the condition (> 100), so it should be 0
    # Emission factor (0.1) applied to oil rates, assuming that the factor converts the
    # oil volume to kilo/day
    expected_result = Unit.KILO_PER_DAY.to(Unit.TONS_PER_DAY)([0, 20])
    result = emitter.get_emissions()

    assert result["CH4"].values == expected_result


def test_oil_venting_emitter_with_conditions():
    expression_evaluator = create_expression_evaluator("oil_volume", [20, 200])

    # Define multiple conditions
    conditions = [
        "oil_volume > 50",
        "oil_volume < 300",
    ]

    # Combine conditions using _map_condition
    combined_condition = _map_condition(ConditionedModel(conditions=conditions))

    oil_volume_rate = OilVolumeRate(
        value="oil_volume",
        unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
        rate_type=RateType.STREAM_DAY,
        condition=Expression.setup_from_expression(value=combined_condition),
    )
    emissions = [
        VentingVolumeEmission(
            name="CH4",
            emission_factor="0.1",  # Example emission factor
        ),
    ]
    volume = VentingVolume(oil_volume_rate=oil_volume_rate, emissions=emissions)
    regularity = Regularity(expression_evaluator=expression_evaluator, target_period=expression_evaluator.get_period())

    emitter = OilVentingEmitter(
        id=uuid4(),
        path_id=PathID("TestOilEmitter"),
        emitter_type=VentingType.OIL_VOLUME,
        expression_evaluator=expression_evaluator,
        component_type=ComponentType.VENTING_EMITTER,
        user_defined_category={},
        regularity=regularity,
        volume=volume,
    )

    # First period does not meet the conditions (> 50 and < 300), so it should be 0
    # Emission factor (0.1) applied to oil rates, assuming that the factor converts the
    # oil volume to kilo/day
    expected_result = Unit.KILO_PER_DAY.to(Unit.TONS_PER_DAY)([0, 20])
    result = emitter.get_emissions()

    assert result["CH4"].values == expected_result
