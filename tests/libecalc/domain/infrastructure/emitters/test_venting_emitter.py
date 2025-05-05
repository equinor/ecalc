from datetime import datetime

from libecalc.common.component_type import ComponentType
from libecalc.common.units import Unit
from libecalc.common.utils.rates import RateType
from libecalc.common.variables import VariablesMap
from libecalc.domain.infrastructure.emitters.venting_emitter import (
    VentingEmission,
    EmissionRate,
    DirectVentingEmitter,
    VentingType,
    OilVolumeRate,
    VentingVolumeEmission,
    VentingVolume,
    OilVentingEmitter,
)
from libecalc.expression import Expression


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


def test_oil_venting_emitter_with_condition():
    oil_volume_values = [20, 200]

    expression_evaluator = VariablesMap(
        variables={"oil_volume": oil_volume_values},
        time_vector=[
            datetime(2022, 1, 1),
            datetime(2023, 1, 1),
            datetime(2024, 1, 1),
        ],
    )
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

    emitter = OilVentingEmitter(
        name="TestOilEmitter",
        emitter_type=VentingType.OIL_VOLUME,
        expression_evaluator=expression_evaluator,
        component_type=ComponentType.VENTING_EMITTER,
        user_defined_category={},
        regularity={},
        volume=volume,
    )

    # First period does not meet the condition (> 100), so it should be 0
    # Emission factor (0.1) applied to oil rates, assuming that the factor converts the
    # oil volume to kilo/day
    expected_result = Unit.KILO_PER_DAY.to(Unit.TONS_PER_DAY)([0, 20])
    result = emitter.get_emissions()

    assert result["CH4"].values == expected_result
