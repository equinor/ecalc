from datetime import datetime

import pytest
from libecalc.common.units import Unit
from libecalc.common.utils.rates import RateType
from libecalc.core.result.emission import EmissionResult
from libecalc.dto.base import ConsumerUserDefinedCategoryType
from libecalc.expression import Expression
from libecalc.presentation.yaml.yaml_types.emitters.yaml_venting_emitter import (
    YamlVentingEmission,
    YamlVentingEmitter,
)
from libecalc.presentation.yaml.yaml_types.yaml_stream_conditions import YamlRate
from libecalc.presentation.yaml.yaml_types.yaml_variable import YamlDefaultDatetime


def test_venting_emitter(variables_map):
    emitter_name = "venting_emitter"

    venting_emitter = YamlVentingEmitter(
        name=emitter_name,
        user_defined_category={YamlDefaultDatetime(1900, 1, 1): ConsumerUserDefinedCategoryType.COLD_VENTING_FUGITIVE},
        emission=YamlVentingEmission(
            name="ch4",
            rate=YamlRate(
                value="TSC1;Methane_rate {*} 1.02",
                unit=Unit.KILO_PER_DAY,
                rate_type=RateType.STREAM_DAY,
            ),
        ),
    )

    regularity = {datetime(1900, 1, 1): Expression.setup_from_expression(1)}

    emission_rate = venting_emitter.get_emission_rate(variables_map=variables_map, regularity=regularity).to_unit(
        Unit.TONS_PER_DAY
    )

    emission_result = {
        venting_emitter.emission.name: EmissionResult(
            name=venting_emitter.emission.name,
            timesteps=variables_map.time_vector,
            rate=emission_rate,
        )
    }
    emissions_ch4 = emission_result["ch4"]

    # Two first time steps using emitter_emission_function
    assert emissions_ch4.rate.values == pytest.approx([5.1e-06, 0.00153, 0.00306, 0.00408])
