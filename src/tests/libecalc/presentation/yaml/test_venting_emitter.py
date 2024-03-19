from datetime import datetime

import pytest
from libecalc import dto
from libecalc.common.units import Unit
from libecalc.common.utils.rates import RateType
from libecalc.core.result.emission import EmissionResult
from libecalc.dto.base import ConsumerUserDefinedCategoryType
from libecalc.expression import Expression
from libecalc.fixtures.cases.ltp_export.utilities import (
    get_consumption,
    get_sum_ltp_column,
)
from libecalc.fixtures.cases.venting_emitters.venting_emitter_yaml import (
    venting_emitter_yaml_factory,
)
from libecalc.presentation.yaml.yaml_types.emitters.yaml_venting_emitter import (
    YamlVentingEmission,
    YamlVentingEmitter,
    YamlVentingType,
    YamlVentingVolume,
    YamlVentingVolumeEmission,
)
from libecalc.presentation.yaml.yaml_types.yaml_stream_conditions import (
    YamlEmissionRate,
)


def oil_values():
    return [10, 10, 10, 10]


def methane():
    return [0.005, 1.5, 3, 4]


@pytest.fixture
def variables_map(methane_values):
    return dto.VariablesMap(
        variables={"TSC1;Methane_rate": methane(), "TSC1;Oil_rate": oil_values()},
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
        category=ConsumerUserDefinedCategoryType.COLD_VENTING_FUGITIVE,
        type=YamlVentingType.DIRECT_EMISSION,
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


def test_venting_emitter_oil_volume(variables_map):
    """
    Check that emissions related to oil loading/storage are correct. These emissions are
    calculated using a factor of input oil rates, i.e. the TYPE set to OIL_VOLUME.
    """
    emitter_name = "venting_emitter"
    emission_factor = 0.1

    venting_emitter = YamlVentingEmitter(
        name=emitter_name,
        category=ConsumerUserDefinedCategoryType.LOADING,
        type=YamlVentingType.OIL_VOLUME,
        volume=YamlVentingVolume(
            rate=YamlEmissionRate(
                value="TSC1;Oil_rate",
                unit=Unit.KILO_PER_DAY,
                type=RateType.STREAM_DAY,
            ),
            emissions=[
                YamlVentingVolumeEmission(
                    name="ch4",
                    emission_factor=emission_factor,
                )
            ],
        ),
    )

    regularity = {datetime(1900, 1, 1): Expression.setup_from_expression(1)}

    emission_rate = venting_emitter.get_emission_rate(variables_map=variables_map, regularity=regularity)[
        "ch4"
    ].to_unit(Unit.TONS_PER_DAY)

    emission_result = {
        venting_emitter.oil_volume.emissions[0].name: EmissionResult(
            name=venting_emitter.oil_volume.emissions[0].name,
            timesteps=variables_map.time_vector,
            rate=emission_rate,
        )
    }
    emissions_ch4 = emission_result["ch4"]

    regularity_evaluated = float(
        Expression.evaluate(regularity[datetime(1900, 1, 1)], fill_length=1, variables=variables_map.variables)
    )
    expected_result = [oil_value * regularity_evaluated * emission_factor / 1000 for oil_value in oil_values()]

    assert emissions_ch4.rate.values == expected_result


def test_no_emissions_direct(variables_map):
    """
    Check that error message is given if no emissions are specified for TYPE DIRECT_EMISSION.
    """
    emitter_name = "venting_emitter"

    with pytest.raises(ValueError) as exc:
        YamlVentingEmitter(
            name=emitter_name,
            category=ConsumerUserDefinedCategoryType.COLD_VENTING_FUGITIVE,
            type=YamlVentingType.DIRECT_EMISSION,
        )

    assert (
        f"The keyword EMISSIONS is required for VENTING_EMITTERS of TYPE {YamlVentingType.DIRECT_EMISSION.name}"
        in str(exc.value)
    )


def test_no_volume_oil(variables_map):
    """
    Check that error message is given if no volume is specified for TYPE OIL_VOLUME.
    """
    emitter_name = "venting_emitter"

    with pytest.raises(ValueError) as exc:
        YamlVentingEmitter(
            name=emitter_name,
            category=ConsumerUserDefinedCategoryType.COLD_VENTING_FUGITIVE,
            type=YamlVentingType.OIL_VOLUME,
        )

    assert f"The keyword VOLUME is required for VENTING_EMITTERS of TYPE {YamlVentingType.OIL_VOLUME.name}" in str(
        exc.value
    )


def test_venting_emitters_direct_multiple_emissions_ltp():
    """
    Check that multiple emissions are calculated correctly for venting emitter of type DIRECT_EMISSION.
    """

    time_vector = [
        datetime(2027, 1, 1),
        datetime(2028, 1, 1),
        datetime(2029, 1, 1),
    ]
    delta_days = [(time_j - time_i).days for time_i, time_j in zip(time_vector[:-1], time_vector[1:])]

    variables = dto.VariablesMap(time_vector=time_vector, variables={})
    regularity = 0.2
    emission_rates = [10, 5]
    venting_emitter_multiple_emissions = venting_emitter_yaml_factory(
        emission_rates=emission_rates,
        regularity=regularity,
        units=[Unit.KILO_PER_DAY, Unit.KILO_PER_DAY],
        emission_names=["co2", "ch4"],
        rate_types=[RateType.STREAM_DAY],
        emission_keyword_name="EMISSIONS",
        categories=["COLD-VENTING-FUGITIVE"],
        names=["Venting emitter 1"],
    )

    ltp_result = get_consumption(model=venting_emitter_multiple_emissions, variables=variables, time_vector=time_vector)

    ch4_emissions = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column_nr=0)
    co2_emissions = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column_nr=1)

    assert ch4_emissions == sum(emission_rates[0] * days * regularity / 1000 for days in delta_days)
    assert co2_emissions == sum(emission_rates[1] * days * regularity / 1000 for days in delta_days)


def test_venting_emitters_volume_multiple_emissions_ltp():
    """
    Check that multiple emissions are calculated correctly for venting emitter of type OIL_VOLUME.
    """
    time_vector = [
        datetime(2027, 1, 1),
        datetime(2028, 1, 1),
        datetime(2029, 1, 1),
    ]
    delta_days = [(time_j - time_i).days for time_i, time_j in zip(time_vector[:-1], time_vector[1:])]

    variables = dto.VariablesMap(time_vector=time_vector, variables={})
    regularity = 0.2
    emission_factors = [0.1, 0.1]
    oil_rates = [100]

    venting_emitter_multiple_emissions = venting_emitter_yaml_factory(
        regularity=regularity,
        units=[Unit.KILO_PER_DAY, Unit.KILO_PER_DAY],
        emission_names=["ch4", "nmvoc"],
        emitter_types=["OIL_VOLUME"],
        rate_types=[RateType.STREAM_DAY],
        categories=["LOADING"],
        names=["Venting emitter 1"],
        emission_factors=emission_factors,
        oil_rates=oil_rates,
    )

    ltp_result = get_consumption(model=venting_emitter_multiple_emissions, variables=variables, time_vector=time_vector)

    ch4_emissions = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column_nr=0)
    nmvoc_emissions = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column_nr=1)

    assert ch4_emissions == sum(oil_rates[0] * days * regularity * emission_factors[0] / 1000 for days in delta_days)
    assert nmvoc_emissions == sum(oil_rates[0] * days * regularity * emission_factors[1] / 1000 for days in delta_days)
