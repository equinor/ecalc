from datetime import datetime
from pathlib import Path

import pytest

from libecalc.common.time_utils import Period
from libecalc.common.units import Unit
from libecalc.common.utils.rates import RateType
from libecalc.common.variables import VariablesMap
from libecalc.core.result.emission import EmissionResult
from libecalc.dto.types import ConsumerUserDefinedCategoryType
from libecalc.expression import Expression
from libecalc.fixtures.cases import venting_emitters
from libecalc.fixtures.cases.ltp_export.utilities import get_consumption, get_sum_ltp_column
from libecalc.fixtures.cases.venting_emitters.venting_emitter_yaml import venting_emitter_yaml_factory
from libecalc.presentation.yaml.yaml_types.emitters.yaml_venting_emitter import (
    YamlDirectTypeEmitter,
    YamlOilTypeEmitter,
    YamlVentingEmission,
    YamlVentingType,
    YamlVentingVolume,
    YamlVentingVolumeEmission,
)
from libecalc.presentation.yaml.yaml_types.yaml_stream_conditions import (
    YamlEmissionRate,
    YamlEmissionRateUnits,
    YamlOilRateUnits,
    YamlOilVolumeRate,
)


def oil_values():
    return [10, 10, 10, 10]


def methane():
    return [0.005, 1.5, 3, 4]


@pytest.fixture
def variables_map(methane_values):
    return VariablesMap(
        variables={"TSC1;Methane_rate": methane(), "TSC1;Oil_rate": oil_values()},
        time_vector=[
            datetime(2000, 1, 1),
            datetime(2001, 1, 1),
            datetime(2002, 1, 1),
            datetime(2003, 1, 1),
            datetime(2004, 1, 1),
        ],
    )


def test_venting_emitter(variables_map):
    emitter_name = "venting_emitter"

    venting_emitter = YamlDirectTypeEmitter(
        name=emitter_name,
        category=ConsumerUserDefinedCategoryType.COLD_VENTING_FUGITIVE,
        type=YamlVentingType.DIRECT_EMISSION.value,
        emissions=[
            YamlVentingEmission(
                name="ch4",
                rate=YamlEmissionRate(
                    value="TSC1;Methane_rate {*} 1.02",
                    unit=YamlEmissionRateUnits.KILO_PER_DAY,
                    type=RateType.STREAM_DAY,
                ),
            )
        ],
    )

    regularity = {datetime(1900, 1, 1): Expression.setup_from_expression(1)}

    emission_rate = venting_emitter.get_emissions(expression_evaluator=variables_map, regularity=regularity)[
        "ch4"
    ].to_unit(Unit.TONS_PER_DAY)

    emission_result = {
        venting_emitter.emissions[0].name: EmissionResult(
            name=venting_emitter.emissions[0].name,
            periods=variables_map.periods,
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
    regularity_expected = 1.0

    venting_emitter = YamlOilTypeEmitter(
        name=emitter_name,
        category=ConsumerUserDefinedCategoryType.LOADING,
        type=YamlVentingType.OIL_VOLUME.value,
        volume=YamlVentingVolume(
            rate=YamlOilVolumeRate(
                value="TSC1;Oil_rate",
                unit=YamlOilRateUnits.STANDARD_CUBIC_METER_PER_DAY,
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

    regularity = {Period(datetime(1900, 1, 1)): Expression.setup_from_expression(regularity_expected)}

    emission_rate = venting_emitter.get_emissions(expression_evaluator=variables_map, regularity=regularity)[
        "ch4"
    ].to_unit(Unit.TONS_PER_DAY)

    emission_result = {
        venting_emitter.volume.emissions[0].name: EmissionResult(
            name=venting_emitter.volume.emissions[0].name,
            periods=variables_map.periods,
            rate=emission_rate,
        )
    }
    emissions_ch4 = emission_result["ch4"]

    try:
        regularity_array = Expression.evaluate(
            regularity[Period(datetime(1900, 1, 1))], fill_length=1, variables=variables_map.variables
        )

        regularity_evaluated = float(regularity_array[0])

    except IndexError as e:
        raise IndexError("Failed to evaluate regularity: array index out of range.") from e

    assert regularity_evaluated == regularity_expected

    expected_result = [oil_value * regularity_evaluated * emission_factor / 1000 for oil_value in oil_values()]

    assert emissions_ch4.rate.values == expected_result


def test_no_emissions_direct(variables_map):
    """
    Check that error message is given if no emissions are specified for TYPE DIRECT_EMISSION.
    """
    emitter_name = "venting_emitter"

    with pytest.raises(ValueError) as exc:
        YamlDirectTypeEmitter(
            name=emitter_name,
            category=ConsumerUserDefinedCategoryType.COLD_VENTING_FUGITIVE,
            type=YamlVentingType.DIRECT_EMISSION.name,
        )

    assert "1 validation error for VentingEmitter\nEMISSIONS\n  Field required" in str(exc.value)


def test_no_volume_oil(variables_map):
    """
    Check that error message is given if no volume is specified for TYPE OIL_VOLUME.
    """
    emitter_name = "venting_emitter"

    with pytest.raises(ValueError) as exc:
        YamlOilTypeEmitter(
            name=emitter_name,
            category=ConsumerUserDefinedCategoryType.COLD_VENTING_FUGITIVE,
            type=YamlVentingType.OIL_VOLUME.name,
        )

    assert "1 validation error for VentingEmitter\nVOLUME\n  Field required" in str(exc.value)


def test_venting_emitters_direct_multiple_emissions_ltp():
    """
    Check that multiple emissions are calculated correctly for venting emitter of type DIRECT_EMISSION.
    """

    regularity = 0.2
    emission_rates = [10, 5]
    dto_case = venting_emitter_yaml_factory(
        emission_rates=emission_rates,
        regularity=regularity,
        units=[YamlEmissionRateUnits.KILO_PER_DAY, YamlEmissionRateUnits.KILO_PER_DAY],
        emission_names=["co2", "ch4"],
        rate_types=[RateType.STREAM_DAY],
        emission_keyword_name="EMISSIONS",
        categories=["COLD-VENTING-FUGITIVE"],
        names=["Venting emitter 1"],
        path=Path(venting_emitters.__path__[0]),
    )

    delta_days = [
        (time_j - time_i).days
        for time_i, time_j in zip(dto_case.variables.time_vector[:-1], dto_case.variables.time_vector[1:])
    ]

    ltp_result = get_consumption(
        model=dto_case.ecalc_model, variables=dto_case.variables, periods=dto_case.variables.get_periods()
    )

    ch4_emissions = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column="co2VentingMass")
    co2_emissions = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column="coldVentAndFugitivesCh4Mass")

    assert ch4_emissions == sum(emission_rates[0] * days * regularity / 1000 for days in delta_days)
    assert co2_emissions == sum(emission_rates[1] * days * regularity / 1000 for days in delta_days)


def test_venting_emitters_volume_multiple_emissions_ltp():
    """
    Check that multiple emissions are calculated correctly for venting emitter of type OIL_VOLUME.
    """

    regularity = 0.2
    emission_factors = [0.1, 0.1]
    oil_rates = [100]

    path = Path(venting_emitters.__path__[0])
    dto_case = venting_emitter_yaml_factory(
        regularity=regularity,
        units=[YamlEmissionRateUnits.KILO_PER_DAY, YamlEmissionRateUnits.KILO_PER_DAY],
        units_oil_rates=[YamlOilRateUnits.STANDARD_CUBIC_METER_PER_DAY, YamlOilRateUnits.STANDARD_CUBIC_METER_PER_DAY],
        emission_names=["ch4", "nmvoc"],
        emitter_types=["OIL_VOLUME"],
        rate_types=[RateType.CALENDAR_DAY],
        categories=["LOADING"],
        names=["Venting emitter 1"],
        emission_factors=emission_factors,
        oil_rates=oil_rates,
        path=path,
    )

    dto_case_stream_day = venting_emitter_yaml_factory(
        regularity=regularity,
        units=[YamlEmissionRateUnits.KILO_PER_DAY, YamlEmissionRateUnits.KILO_PER_DAY],
        units_oil_rates=[YamlOilRateUnits.STANDARD_CUBIC_METER_PER_DAY, YamlOilRateUnits.STANDARD_CUBIC_METER_PER_DAY],
        emission_names=["ch4", "nmvoc"],
        emitter_types=["OIL_VOLUME"],
        rate_types=[RateType.STREAM_DAY],
        categories=["LOADING"],
        names=["Venting emitter 1"],
        emission_factors=emission_factors,
        oil_rates=oil_rates,
        path=path,
    )

    delta_days = [
        (time_j - time_i).days
        for time_i, time_j in zip(dto_case.variables.time_vector[:-1], dto_case.variables.time_vector[1:])
    ]

    ltp_result = get_consumption(
        model=dto_case.ecalc_model, variables=dto_case.variables, periods=dto_case.variables.periods
    )

    ltp_result_stream_day = get_consumption(
        model=dto_case_stream_day.ecalc_model,
        variables=dto_case_stream_day.variables,
        periods=dto_case_stream_day.variables.periods,
    )

    ch4_emissions = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column="loadingNmvocMass")
    nmvoc_emissions = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column="loadingCh4Mass")
    oil_volume = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column="loadedAndStoredOil")

    oil_volume_stream_day = get_sum_ltp_column(
        ltp_result_stream_day, installation_nr=0, ltp_column="loadedAndStoredOil"
    )

    assert ch4_emissions == sum(oil_rates[0] * days * emission_factors[0] / 1000 for days in delta_days)
    assert nmvoc_emissions == sum(oil_rates[0] * days * emission_factors[1] / 1000 for days in delta_days)
    assert oil_volume == pytest.approx(sum(oil_rates[0] * days for days in delta_days), abs=1e-5)

    # Check that oil volume is including regularity correctly:
    # Oil volume (input rate in stream day) / oil volume (input rates calendar day) = regularity.
    # Given that the actual rate input values are the same.
    assert oil_volume_stream_day / oil_volume == regularity


def test_venting_emitters_direct_uppercase_emissions_name():
    """
    Check emission names are case-insensitive for venting emitters of type DIRECT_EMISSION.
    """

    regularity = 0.2
    emission_rates = [10, 5]
    dto_case = venting_emitter_yaml_factory(
        emission_rates=emission_rates,
        regularity=regularity,
        units=[YamlEmissionRateUnits.KILO_PER_DAY, YamlEmissionRateUnits.KILO_PER_DAY],
        emission_names=["CO2", "nmVOC"],
        rate_types=[RateType.STREAM_DAY],
        emission_keyword_name="EMISSIONS",
        categories=["COLD-VENTING-FUGITIVE"],
        names=["Venting emitter 1"],
        path=Path(venting_emitters.__path__[0]),
    )

    assert dto_case.ecalc_model.installations[0].venting_emitters[0].emissions[0].name == "co2"
    assert dto_case.ecalc_model.installations[0].venting_emitters[0].emissions[1].name == "nmvoc"


def test_venting_emitters_volume_uppercase_emissions_name():
    """
    Check emission names are case-insensitive for venting emitters of type OIL_VOLUME.
    """

    regularity = 0.2
    emission_factors = [0.1, 0.1]
    oil_rates = [100]

    dto_case = venting_emitter_yaml_factory(
        regularity=regularity,
        units=[YamlEmissionRateUnits.KILO_PER_DAY, YamlEmissionRateUnits.KILO_PER_DAY],
        units_oil_rates=[YamlOilRateUnits.STANDARD_CUBIC_METER_PER_DAY, YamlOilRateUnits.STANDARD_CUBIC_METER_PER_DAY],
        emission_names=["CO2", "nmVOC"],
        emitter_types=["OIL_VOLUME"],
        rate_types=[RateType.CALENDAR_DAY],
        categories=["LOADING"],
        names=["Venting emitter 1"],
        emission_factors=emission_factors,
        oil_rates=oil_rates,
        path=Path(venting_emitters.__path__[0]),
    )

    assert dto_case.ecalc_model.installations[0].venting_emitters[0].volume.emissions[0].name == "co2"
    assert dto_case.ecalc_model.installations[0].venting_emitters[0].volume.emissions[1].name == "nmvoc"
