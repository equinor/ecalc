from datetime import datetime

import pytest
from libecalc import dto
from libecalc.common.units import Unit
from libecalc.common.utils.rates import RateType
from libecalc.core.result.emission import EmissionResult
from libecalc.dto.base import ConsumerUserDefinedCategoryType
from libecalc.expression import Expression
from libecalc.presentation.yaml.yaml_types.emitters.yaml_venting_emitter import (
    YamlVentingEmission,
    YamlVentingEmitter,
    YamlVentingType,
)
from libecalc.presentation.yaml.yaml_types.yaml_stream_conditions import (
    YamlEmissionRate,
)


@pytest.fixture
def variables_map(methane_values):
    return dto.VariablesMap(
        variables={"TSC1;Methane_rate": methane_values},
        time_vector=[
            datetime(2000, 1, 1, 0, 0),
            datetime(2001, 1, 1, 0, 0),
            datetime(2002, 1, 1),
            datetime(2003, 1, 1, 0, 0),
        ],
    )


def test_venting_emitter(variables_map):
    emitter_name = "venting_emitter"

    venting_emitter = YamlVentingEmitter(
        name=emitter_name,
        type=YamlVentingType.DIRECT_EMISSION,
        category=ConsumerUserDefinedCategoryType.COLD_VENTING_FUGITIVE,
        emissions=[
            YamlVentingEmission(
                name="ch4",
                rate=YamlEmissionRate(
                    value="TSC1;Methane_rate {*} 1.02",
                    unit=Unit.KILO_PER_DAY,
                    type=RateType.STREAM_DAY,
                ),
            )
        ],
    )

    regularity = {datetime(1900, 1, 1): Expression.setup_from_expression(1)}

    emission_rate = venting_emitter.get_emission_rate(variables_map=variables_map, regularity=regularity)[
        "ch4"
    ].to_unit(Unit.TONS_PER_DAY)

    emission_result = {
        venting_emitter.emissions[0].name: EmissionResult(
            name=venting_emitter.emissions[0].name,
            timesteps=variables_map.time_vector,
            rate=emission_rate,
        )
    }
    emissions_ch4 = emission_result["ch4"]

    # Two first time steps using emitter_emission_function
    assert emissions_ch4.rate.values == pytest.approx([5.1e-06, 0.00153, 0.00306, 0.00408])
