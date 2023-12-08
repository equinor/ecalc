import pytest
from libecalc.common.units import Unit
from libecalc.core.result.emission import EmissionResult
from libecalc.dto.base import ConsumerUserDefinedCategoryType
from libecalc.presentation.yaml.yaml_types.emitters.yaml_venting_emitter import (
    YamlVentingEmitter,
)
from libecalc.presentation.yaml.yaml_types.yaml_variable import YamlDefaultDatetime


def test_venting_emitter(variables_map, temporal_emitter_model):
    emitter_name = "venting_emitter"

    venting_emitter = YamlVentingEmitter(
        name=emitter_name,
        emitter_model=temporal_emitter_model,
        user_defined_category={YamlDefaultDatetime(1900, 1, 1): ConsumerUserDefinedCategoryType.COLD_VENTING_FUGITIVE},
        emission_name="ch4",
    )

    emission_rate = venting_emitter.get_emission_rate(variables_map=variables_map).to_unit(Unit.TONS_PER_DAY)

    emission_result = {
        venting_emitter.emission_name: EmissionResult(
            name=venting_emitter.emission_name,
            timesteps=variables_map.time_vector,
            rate=emission_rate,
        )
    }
    emissions_ch4 = emission_result["ch4"]

    # Two first time steps using emitter_emission_function
    assert emissions_ch4.rate.values == pytest.approx([5.1e-06, 0.00153, 0.0033, 0.0044])
