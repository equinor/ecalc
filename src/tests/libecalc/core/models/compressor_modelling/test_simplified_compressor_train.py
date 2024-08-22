from typing import List, Tuple

import numpy as np
import pytest
from numpy.typing import NDArray

from libecalc import dto
from libecalc.common.errors.exceptions import EcalcError
from libecalc.core.models.compressor.train.fluid import FluidStream
from libecalc.core.models.compressor.train.simplified_train import (
    CompressorTrainSimplifiedKnownStages,
    CompressorTrainSimplifiedUnknownStages,
)
from libecalc.core.models.compressor.train.stage import UndefinedCompressorStage
from libecalc.core.models.compressor.train.utils.enthalpy_calculations import (
    _calculate_head,
    _calculate_polytropic_exponent_expression_n_minus_1_over_n,
    calculate_enthalpy_change_head_iteration,
    calculate_polytropic_head_campbell,
)


@pytest.fixture
def rates():
    return np.asarray(
        [15478059.4, 14296851.66, 9001365.137, 7921594.316, 5857638.265, 4012786.153, 2920238.089, 2398857.123]
    )


@pytest.fixture
def suction_pressures():
    return np.asarray([36.0, 31.0, 21.0, 19.0, 18.0, 18.0, 18.0, 18.0])


@pytest.fixture
def discharge_pressures():
    return np.asarray([250.0, 250.0, 200, 200, 200, 200, 200, 200])


@pytest.fixture
def simplified_compressor_train_unknown_stages_dto(
    rich_fluid, variable_speed_compressor_chart_dto
) -> dto.CompressorTrainSimplifiedWithUnknownStages:
    """Note: Not all attributes are used in the model yet."""
    return dto.CompressorTrainSimplifiedWithUnknownStages(
        fluid_model=rich_fluid,
        stage=dto.CompressorStage(
            compressor_chart=variable_speed_compressor_chart_dto,
            inlet_temperature_kelvin=303.15,
            pressure_drop_before_stage=0,
            remove_liquid_after_cooling=True,
        ),
        energy_usage_adjustment_constant=0,
        energy_usage_adjustment_factor=1,
        maximum_pressure_ratio_per_stage=3.5,
    )


@pytest.fixture
def simplified_compressor_train_unknown_stages_generic_compressor_from_input_dto(
    medium_fluid,
) -> dto.CompressorTrainSimplifiedWithUnknownStages:
    """Note: Not all attributes are used in the model yet."""
    return dto.CompressorTrainSimplifiedWithUnknownStages(
        fluid_model=medium_fluid,
        stage=dto.CompressorStage(
            compressor_chart=dto.GenericChartFromInput(polytropic_efficiency_fraction=0.75),
            inlet_temperature_kelvin=303.15,
            pressure_drop_before_stage=0,
            remove_liquid_after_cooling=True,
        ),
        energy_usage_adjustment_constant=0,
        energy_usage_adjustment_factor=1,
        maximum_pressure_ratio_per_stage=3.5,
    )


@pytest.fixture
def simplified_compressor_train_known_stages_dto(
    medium_fluid, variable_speed_compressor_chart_dto
) -> dto.CompressorTrainSimplifiedWithKnownStages:
    """Note: Not all attributes are used in the model yet."""
    return dto.CompressorTrainSimplifiedWithKnownStages(
        fluid_model=medium_fluid,
        stages=[
            dto.CompressorStage(
                inlet_temperature_kelvin=303.15,
                compressor_chart=variable_speed_compressor_chart_dto,
                remove_liquid_after_cooling=True,
                pressure_drop_before_stage=0,
                control_margin=0,
            )
        ],
        energy_usage_adjustment_constant=0,
        energy_usage_adjustment_factor=1,
    )


@pytest.fixture
def simplified_compressor_train_with_known_stages_dto(medium_fluid_dto) -> dto.CompressorTrainSimplifiedWithKnownStages:
    """Note: Not all attributes are used in the model yet."""
    return dto.CompressorTrainSimplifiedWithKnownStages(
        fluid_model=medium_fluid_dto,
        stages=[
            dto.CompressorStage(
                inlet_temperature_kelvin=303.15,
                compressor_chart=dto.GenericChartFromDesignPoint(
                    polytropic_efficiency_fraction=0.75,
                    design_rate_actual_m3_per_hour=15848.089397866604,
                    design_polytropic_head_J_per_kg=135478.5333104937,
                ),
                remove_liquid_after_cooling=True,
                pressure_drop_before_stage=0,
                control_margin=0,
            ),
            dto.CompressorStage(
                inlet_temperature_kelvin=303.15,
                compressor_chart=dto.GenericChartFromDesignPoint(
                    polytropic_efficiency_fraction=0.75,
                    design_rate_actual_m3_per_hour=4539.170738284835,
                    design_polytropic_head_J_per_kg=116082.08687178302,
                ),
                remove_liquid_after_cooling=True,
                pressure_drop_before_stage=0,
                control_margin=0,
            ),
        ],
        energy_usage_adjustment_constant=0,
        energy_usage_adjustment_factor=1,
    )


def test_simplified_compressor_train_known_stages(
    simplified_compressor_train_with_known_stages_dto, rates, suction_pressures, discharge_pressures
):
    compressor_train = CompressorTrainSimplifiedKnownStages(
        data_transfer_object=simplified_compressor_train_with_known_stages_dto,
    )
    compressor_train.evaluate_rate_ps_pd(
        rate=rates,
        suction_pressure=suction_pressures,
        discharge_pressure=discharge_pressures,
    )


def test_simplified_compressor_train_unknown_stages(simplified_compressor_train_unknown_stages_dto):
    compressor_train = CompressorTrainSimplifiedUnknownStages(
        data_transfer_object=simplified_compressor_train_unknown_stages_dto,
    )

    compressor_train.evaluate_rate_ps_pd(
        rate=np.linspace(start=1000, stop=10000, num=10),
        suction_pressure=np.linspace(start=10, stop=20, num=10),
        discharge_pressure=np.linspace(start=200, stop=400, num=10),
    )


def test_simplified_compressor_train_unknown_stages_with_constant_power_adjustment(
    simplified_compressor_train_unknown_stages_dto,
):
    compressor_train_energy_function = CompressorTrainSimplifiedUnknownStages(
        data_transfer_object=simplified_compressor_train_unknown_stages_dto,
    )
    result_comparison = compressor_train_energy_function.evaluate_rate_ps_pd(
        rate=np.linspace(start=1000, stop=10000, num=10),
        suction_pressure=np.linspace(start=10, stop=20, num=10),
        discharge_pressure=np.linspace(start=200, stop=400, num=10),
    )

    energy_usage_adjustment_constant = 10
    compressor_train_energy_function.data_transfer_object.energy_usage_adjustment_constant = (
        energy_usage_adjustment_constant
    )
    result = compressor_train_energy_function.evaluate_rate_ps_pd(
        rate=np.linspace(start=1000, stop=10000, num=10),
        suction_pressure=np.linspace(start=10, stop=20, num=10),
        discharge_pressure=np.linspace(start=200, stop=400, num=10),
    )

    np.testing.assert_allclose(
        np.asarray(result_comparison.energy_usage) + energy_usage_adjustment_constant, result.energy_usage
    )


def test_calculate_maximum_rate_given_outlet_pressure_all_calculation_points(
    simplified_compressor_train_known_stages_dto, medium_fluid_dto, caplog
):
    compressor_train = CompressorTrainSimplifiedKnownStages(
        data_transfer_object=simplified_compressor_train_known_stages_dto,
    )
    stage = compressor_train.stages[0]
    n_calculations_points = 5
    inlet_pressure = np.full(shape=n_calculations_points, fill_value=10)
    inlet_temperature_kelvin = np.full(shape=n_calculations_points, fill_value=288.15)
    pressure_ratios = [1, 2, 3, 4, 5, 10, 100, 1000]

    # These expected max rates are here just to assure stability in the results. They are not assured to be correct!
    approx_expected_max_rates = [1116990, 1358999, 1536193, 1052085, 1052085, 1052085, 1052085, 1052085]
    for pressure_ratio, approx_expected_max_rate in zip(pressure_ratios, approx_expected_max_rates):
        calculated_max_rate = (
            CompressorTrainSimplifiedKnownStages.calculate_maximum_rate_given_outlet_pressure_all_calculation_points(
                inlet_pressure=inlet_pressure,
                pressure_ratio=np.full(shape=n_calculations_points, fill_value=pressure_ratio),
                inlet_temperature_kelvin=inlet_temperature_kelvin,
                fluid=FluidStream(medium_fluid_dto),
                compressor_chart=stage.compressor_chart,
            )
        )
        np.testing.assert_almost_equal(calculated_max_rate, approx_expected_max_rate, decimal=0)

    caplog.set_level("CRITICAL")
    with pytest.raises(EcalcError):
        CompressorTrainSimplifiedKnownStages.calculate_maximum_rate_given_outlet_pressure_all_calculation_points(
            inlet_pressure=inlet_pressure,
            pressure_ratio=np.full(shape=n_calculations_points, fill_value=0.0),
            inlet_temperature_kelvin=inlet_temperature_kelvin,
            fluid=FluidStream(medium_fluid_dto),
            compressor_chart=stage.compressor_chart,
        )

    with pytest.raises(EcalcError):
        CompressorTrainSimplifiedKnownStages.calculate_maximum_rate_given_outlet_pressure_all_calculation_points(
            inlet_pressure=inlet_pressure,
            pressure_ratio=np.full(shape=n_calculations_points, fill_value=0.5),
            inlet_temperature_kelvin=inlet_temperature_kelvin,
            fluid=FluidStream(medium_fluid_dto),
            compressor_chart=stage.compressor_chart,
        )


def test_calculate_inlet_pressure_stages():
    inlet_pressure_first_stage = np.asarray([30, 50, 70.0])
    pressure_ratio_per_stage = np.asarray([1, 2, 3.0])
    stages_inlet_pressures = CompressorTrainSimplifiedKnownStages._calulate_inlet_pressure_stages(
        pressure_ratios_per_stage=pressure_ratio_per_stage,
        inlet_pressure=inlet_pressure_first_stage,
        number_of_stages=4,
    )
    np.testing.assert_almost_equal(
        stages_inlet_pressures,
        [
            inlet_pressure_first_stage,
            inlet_pressure_first_stage * pressure_ratio_per_stage,
            inlet_pressure_first_stage * np.power(pressure_ratio_per_stage, 2),
            inlet_pressure_first_stage * np.power(pressure_ratio_per_stage, 3),
        ],
    )


def test_compressor_train_simplified_known_stages_predefined_chart(
    simplified_compressor_train_known_stages_dto,
    rates,
    suction_pressures,
    discharge_pressures,
):
    compressor_train = CompressorTrainSimplifiedKnownStages(
        data_transfer_object=simplified_compressor_train_known_stages_dto
    )

    results = compressor_train.evaluate_rate_ps_pd(
        rate=rates / 5,
        suction_pressure=suction_pressures,
        discharge_pressure=discharge_pressures,
    )
    # Testing that the polytropic efficiency for the compressor in this compressor train model (with one compressor with
    # a predefined variable speed compressor chart) uses polytropic efficiency calculated from the chart input (and not
    # some hardcoded/fixed value)
    np.testing.assert_equal(
        results.stage_results[0].chart.curves[0].efficiency,
        compressor_train.stages[0].compressor_chart.minimum_speed_curve.efficiency_values,
    )


def test_compressor_train_simplified_known_stages_generic_chart(
    rates,
    suction_pressures,
    discharge_pressures,
    simplified_compressor_train_with_known_stages_dto,
    rich_fluid_dto,
    caplog,
):
    simplified_compressor_train_with_known_stages_dto.fluid_model = rich_fluid_dto
    simple_compressor_train_model = CompressorTrainSimplifiedKnownStages(
        data_transfer_object=simplified_compressor_train_with_known_stages_dto
    )
    results = simple_compressor_train_model.evaluate_rate_ps_pd(
        rate=rates,
        suction_pressure=suction_pressures,
        discharge_pressure=discharge_pressures,
    )

    assert len(results.stage_results) == 2
    np.testing.assert_allclose(
        results.power,
        [
            47.84035,
            48.67651,
            34.39074,
            32.022781,
            25.147764,
            24.23474,
            24.23474,
            24.23474,
        ],
    )

    maximum_rates = simple_compressor_train_model.get_max_standard_rate(
        suction_pressures=suction_pressures,
        discharge_pressures=discharge_pressures,
    )

    np.testing.assert_allclose(
        maximum_rates,
        [
            16571838.970157,
            14527144.905398,
            9148586.717274,
            8061504.543898,
            7443941.400856,
            7443941.400856,
            7443941.400856,
            7443941.400856,
        ],
        rtol=1e-3,
    )
    simple_compressor_train_model_extra_generic_stage_from_data = CompressorTrainSimplifiedKnownStages(
        simplified_compressor_train_with_known_stages_dto.model_copy(
            update={
                "stages": simplified_compressor_train_with_known_stages_dto.stages
                + [
                    dto.CompressorStage(
                        inlet_temperature_kelvin=303.15,
                        compressor_chart=dto.GenericChartFromInput(polytropic_efficiency_fraction=0.75),
                        remove_liquid_after_cooling=True,
                        pressure_drop_before_stage=0,
                        control_margin=0,
                    )
                ]
            }
        )
    )

    pressure_ratios_per_stage = simple_compressor_train_model.calculate_pressure_ratios_per_stage(
        suction_pressure=suction_pressures,
        discharge_pressure=discharge_pressures,
    )
    maximum_rates_extra_stage_chart_from_data = (
        simple_compressor_train_model_extra_generic_stage_from_data.get_max_standard_rate(
            suction_pressures=suction_pressures,
            discharge_pressures=discharge_pressures * pressure_ratios_per_stage,
        )
    )
    np.testing.assert_almost_equal(
        maximum_rates,
        maximum_rates_extra_stage_chart_from_data,
    )

    simple_compressor_train_model_only_generic_chart_from_data = CompressorTrainSimplifiedKnownStages(
        simplified_compressor_train_with_known_stages_dto.model_copy(
            update={
                "stages": [
                    dto.CompressorStage(
                        inlet_temperature_kelvin=303.15,
                        compressor_chart=dto.GenericChartFromInput(polytropic_efficiency_fraction=0.75),
                        remove_liquid_after_cooling=True,
                        pressure_drop_before_stage=0,
                        control_margin=0,
                    ),
                    dto.CompressorStage(
                        inlet_temperature_kelvin=313.15,
                        compressor_chart=dto.GenericChartFromInput(polytropic_efficiency_fraction=0.75),
                        remove_liquid_after_cooling=True,
                        pressure_drop_before_stage=0,
                        control_margin=0,
                    ),
                ]
            }
        )
    )

    max_standard_rate = simple_compressor_train_model_only_generic_chart_from_data.get_max_standard_rate(
        suction_pressures=suction_pressures,
        discharge_pressures=discharge_pressures * pressure_ratios_per_stage,
    )

    assert np.all(np.isnan(max_standard_rate))


def test_compressor_train_simplified_unknown_stages(
    rates,
    suction_pressures,
    discharge_pressures,
    rich_fluid,
    simplified_compressor_train_unknown_stages_generic_compressor_from_input_dto,
    caplog,
):
    simplified_compressor_train_unknown_stages_generic_compressor_from_input_dto.fluid_model = rich_fluid
    simple_compressor_train_model = CompressorTrainSimplifiedUnknownStages(
        data_transfer_object=simplified_compressor_train_unknown_stages_generic_compressor_from_input_dto,
    )

    results = simple_compressor_train_model.evaluate_rate_ps_pd(
        rate=rates,
        suction_pressure=suction_pressures,
        discharge_pressure=discharge_pressures,
    )

    max_standard_rates = simple_compressor_train_model.get_max_standard_rate(
        suction_pressures=suction_pressures,
        discharge_pressures=discharge_pressures,
    )

    assert np.all(np.isnan(max_standard_rates))  # Undefined for unknown stages.
    assert len(results.stage_results) == 2

    np.testing.assert_allclose(
        results.power,
        [
            47.84,
            48.68,
            34.39,
            32.02,
            24.39,
            19.87,
            19.87,
            19.87,
        ],
        rtol=1e-3,
    )


def test_compressor_train_simplified_known_stages_no_indices_to_calulate(
    simplified_compressor_train_with_known_stages_dto, rich_fluid
):
    """Test that we still get a result if there are nothing to calculate, i.e. only rates <= 0."""
    simple_compressor_train_model = CompressorTrainSimplifiedKnownStages(
        data_transfer_object=simplified_compressor_train_with_known_stages_dto
    )
    results = simple_compressor_train_model.evaluate_rate_ps_pd(
        rate=np.array([0.0, 0.0, 0.0, 0.0]),
        suction_pressure=np.array([1.0, 1.0, 1.0, 0.0]),
        discharge_pressure=np.array([2.0, 4.0, 8.0, 3.0]),
    )
    assert np.all(np.asarray(results.energy_usage) == 0)


# Unit tests individual methods
def _span_variables(input_variables: List[NDArray[np.float64]]) -> Tuple:
    number_of_variables = len(input_variables)
    combo = np.asarray(np.meshgrid(*input_variables)).T.reshape(-1, number_of_variables)

    return tuple([combo[:, index] for index in range(number_of_variables)])


def test_calculate_polytropic_exponent_expression():
    # polytropic efficiency is a value between 0 and 1 ( > 0 )
    # heat capacity ratio (kappa) is typically around 1.2-1.4, span between 1 and 2 in test
    polytropic_efficiency, kappa = _span_variables(
        [np.linspace(start=0.0, stop=1.0, num=11)[1:], np.linspace(start=1.0, stop=2.0, num=10)]
    )

    calculated_polytropic_exponent_expression = _calculate_polytropic_exponent_expression_n_minus_1_over_n(
        polytropic_efficiency=polytropic_efficiency,
        kappa=kappa,
    )
    expected_polytropic_exponent_expression = (kappa - 1.0) / (kappa * polytropic_efficiency)
    np.testing.assert_almost_equal(
        calculated_polytropic_exponent_expression,
        expected_polytropic_exponent_expression,
    )


def test_calculate_head():
    (
        polytropic_exponent_expression_values,
        molar_mass_values,
        temperature_kelvin_values,
        pressure_ratio_values,
        z_values,
    ) = _span_variables(
        [
            np.linspace(0, 5.0, num=5)[1:],
            np.linspace(15.0, 100.0, num=4),
            np.linspace(273.0, 500.0, num=4),
            np.linspace(1.0, 5.0, num=4),
            np.linspace(0.5, 1.5, num=4),
        ]
    )

    calculated_head = _calculate_head(
        exponent_expression=polytropic_exponent_expression_values,
        molar_mass=molar_mass_values,
        temperature_kelvin=temperature_kelvin_values,
        pressure_ratio=pressure_ratio_values,
        z=z_values,
    )
    gas_constant = 8.314472
    expected_head = (
        z_values
        * temperature_kelvin_values
        * gas_constant
        / polytropic_exponent_expression_values
        / molar_mass_values
        * (np.power(pressure_ratio_values, polytropic_exponent_expression_values) - 1)
    )
    np.testing.assert_almost_equal(calculated_head, expected_head)


def test_calculate_polytropic_head():
    # Calculations are already tested in test_calculate_polytropic_exponent_expression and test_calculate_head,
    # test a point to check
    polytropic_efficiency = np.asarray(0.75)
    kappa = np.asarray(1.2)
    molar_mass = np.asarray(30.0)
    pressure_ratio = np.asarray(3.5)
    z = np.asarray(0.8)
    temperature_kelvin = np.asarray(350.0)
    polytropic_exponent = _calculate_polytropic_exponent_expression_n_minus_1_over_n(
        polytropic_efficiency=polytropic_efficiency,
        kappa=kappa,
    )
    calculated_head = _calculate_head(
        exponent_expression=polytropic_exponent,
        molar_mass=molar_mass,
        temperature_kelvin=temperature_kelvin,
        pressure_ratio=pressure_ratio,
        z=z,
    )
    calculated_polytropic_head = calculate_polytropic_head_campbell(
        polytropic_efficiency=polytropic_efficiency,
        pressure_ratios=pressure_ratio,
        molar_mass=molar_mass,
        kappa=kappa,
        z=z,
        temperatures_kelvin=temperature_kelvin,
    )

    assert calculated_head == calculated_polytropic_head


def test_calculate_number_of_compressors_needed():
    total_maximum_pressure_ratio_span = np.linspace(1.1, 15.0, num=10)
    compressor_maximum_pressure_ratio_span = np.linspace(2.5, 4.5, num=5)
    (
        total_maximum_pressure_ratio_values,
        compressor_maximum_pressure_ratio_values,
    ) = _span_variables([total_maximum_pressure_ratio_span, compressor_maximum_pressure_ratio_span])

    calculated_number_of_stages = [
        CompressorTrainSimplifiedUnknownStages._calculate_number_of_compressors_needed(
            compressor_maximum_pressure_ratio=compressor_maximum_pressure_ratio,
            total_maximum_pressure_ratio=total_maximum_pressure_ratio,
        )
        for compressor_maximum_pressure_ratio, total_maximum_pressure_ratio in zip(
            compressor_maximum_pressure_ratio_values,
            total_maximum_pressure_ratio_values,
        )
    ]

    # Calculate the maximum total pressure for the number of stages found AND for one less stage
    # The maximum with one less stage, should have total maximum pressure ratio less than the maximum pressure ratio
    # values. The maximum with the number of stages calculated, should have a maximum pressure ratio larger than the
    # maximum pressure ratio values.
    total_maximum_pressure_ratio_one_compressor_short = np.power(
        compressor_maximum_pressure_ratio_values,
        np.asarray(calculated_number_of_stages) - 1,
    )
    total_maximum_pressure_ratio_sufficient_number_of_compressors = np.power(
        compressor_maximum_pressure_ratio_values, calculated_number_of_stages
    )
    assert np.all(total_maximum_pressure_ratio_one_compressor_short < total_maximum_pressure_ratio_values)
    assert np.all(total_maximum_pressure_ratio_values < total_maximum_pressure_ratio_sufficient_number_of_compressors)


def test_evaluate_compressor_simplified_valid_points(simplified_compressor_train_with_known_stages_dto, medium_fluid):
    design_head = 100000.0
    polytropic_efficiency = 0.75

    suction_pressures = np.asarray([50.0, 55.0, 53.0, 45.0, 55.0, 50.0, 45.0, 550])
    discharge_pressures = np.asarray([200.0, 178.2, 104.0, 101.0, 93.0, 392.0, 130.0, 750])
    inlet_temperature_kelvin = 313.15

    simplified_compressor_train_with_known_stages_dto.stages = [
        dto.CompressorStage(
            inlet_temperature_kelvin=inlet_temperature_kelvin,
            compressor_chart=dto.GenericChartFromDesignPoint(
                polytropic_efficiency_fraction=polytropic_efficiency,
                design_rate_actual_m3_per_hour=4000.0,
                design_polytropic_head_J_per_kg=design_head,
            ),
            remove_liquid_after_cooling=True,
            pressure_drop_before_stage=0,
            control_margin=0,
        ),
        dto.CompressorStage(
            inlet_temperature_kelvin=inlet_temperature_kelvin,
            compressor_chart=dto.GenericChartFromDesignPoint(
                polytropic_efficiency_fraction=polytropic_efficiency,
                design_rate_actual_m3_per_hour=2500.0,
                design_polytropic_head_J_per_kg=design_head,
            ),
            remove_liquid_after_cooling=True,
            pressure_drop_before_stage=0,
            control_margin=0,
        ),
    ]
    number_of_compressors = len(simplified_compressor_train_with_known_stages_dto.stages)
    pressure_ratios = discharge_pressures / suction_pressures
    maximum_pressure_ratio = max(pressure_ratios)

    compressor_train = CompressorTrainSimplifiedKnownStages(
        data_transfer_object=simplified_compressor_train_with_known_stages_dto,
    )
    compressor_results = compressor_train._evaluate_rate_ps_pd(
        discharge_pressure=discharge_pressures,
        rate=np.asarray([4376463, 2917642, 3209406, 4668227, 2334113, 4959991, 5835284, 5835284]),
        suction_pressure=suction_pressures,
    )

    assert maximum_pressure_ratio == max(discharge_pressures / suction_pressures)
    assert number_of_compressors == 2
    np.testing.assert_allclose(
        [result.stage_results[0].mass_rate_kg_per_hour for result in compressor_results],
        [150433, 100288, 110317, 160462, 80231, 170490, 200577, 200577],
        atol=1,
    )
    np.testing.assert_allclose(
        [result.power_megawatt for result in compressor_results],
        [10.0, 6.7, 3.8, 7.8, 3.5, np.nan, np.nan, 22.6],
        atol=0.1,
    )


def test_calculate_compressor_work(medium_fluid):
    polytropic_efficiency = 0.75
    # Test with predefined compressor (one stage)
    compressor_chart = dto.GenericChartFromDesignPoint(
        design_rate_actual_m3_per_hour=4000.0,
        design_polytropic_head_J_per_kg=100000.0,
        polytropic_efficiency_fraction=polytropic_efficiency,
    )
    # Test points relative to the chart
    # 1) internal point, 2) pure asv, 3) pure choke corr below minimum speed, 4) choke corr below stone wall
    # 5) both asv and below minimum speed, 6) above maximum speed/maximum head, 7) above maximum rate
    mass_rates = np.asarray([150000.0, 100000.0, 110000.0, 160000.0, 80000.0, 170000.0, 200000.0])
    inlet_pressures = np.asarray([50.0, 55.0, 53.0, 45.0, 55.0, 50.0, 45.0])
    pressure_ratios_per_stage = np.asarray([2.0, 1.8, 1.4, 1.5, 1.3, 2.8, 1.7])

    compressor_train = CompressorTrainSimplifiedKnownStages(
        data_transfer_object=dto.CompressorTrainSimplifiedWithKnownStages(
            fluid_model=medium_fluid,
            stages=[
                dto.CompressorStage(
                    compressor_chart=compressor_chart,
                    inlet_temperature_kelvin=313.15,
                    remove_liquid_after_cooling=True,
                    pressure_drop_before_stage=0,
                    control_margin=0,
                )
            ],
            energy_usage_adjustment_constant=0,
            energy_usage_adjustment_factor=1,
        )
    )
    compressor_result = compressor_train.calculate_compressor_stage_work_given_outlet_pressure(
        inlet_pressure=inlet_pressures,
        inlet_temperature_kelvin=np.full_like(inlet_pressures, fill_value=313.15),
        pressure_ratio=pressure_ratios_per_stage,
        mass_rate_kg_per_hour=mass_rates,
        stage=compressor_train.stages[0],
    )

    power_mw = np.array([x.power_megawatt for x in compressor_result])
    rate_exceeds_maximum = np.array([x.stage_results[0].rate_exceeds_maximum for x in compressor_result])
    head_exceeds_maximum = np.array([x.stage_results[0].head_exceeds_maximum for x in compressor_result])
    inlet_actual_rate_before_asv_m3_per_hr = np.array([x.inlet_actual_rate for x in compressor_result])
    inlet_actual_rate_m3_per_hr = np.array([x.inlet_actual_rate_asv_corrected_m3_per_hour for x in compressor_result])
    polytropic_enthalpy_change_before_choke_kJ_per_kg = np.array(
        [x.polytropic_enthalpy_change_before_choke_kilo_joule_per_kg for x in compressor_result]
    )
    polytropic_enthalpy_change_kJ_per_kg = np.array(
        [x.polytropic_enthalpy_change_kilo_joule_per_kg for x in compressor_result]
    )
    outlet_temperature_kelvin = np.array(
        [x.stage_results[-1].outlet_stream.temperature_kelvin for x in compressor_result]
    )
    outlet_actual_rate_m3_per_hr = np.array(
        [x.stage_results[-1].outlet_actual_rate_m3_per_hour for x in compressor_result]
    )
    assert np.isnan(power_mw[np.argwhere(rate_exceeds_maximum)[:, 0]]).all()
    assert np.isnan(power_mw[np.argwhere(head_exceeds_maximum)[:, 0]]).all()

    # Check a few results of the output stream as well as power
    np.testing.assert_allclose(
        outlet_temperature_kelvin,
        [
            377.5237431532266,
            367.36036152047734,
            347.6776025755494,
            356.73972174544724,
            349.03463256451977,
            410.51599645695023,
            367.8766501377052,
        ],
        rtol=1e-3,
    )
    np.testing.assert_allclose(
        outlet_actual_rate_m3_per_hr,
        [
            2257.169338038633,
            1461.7090831369323,
            2012.9181115835786,
            3358.410741224197,
            1531.7356831320449,
            2046.1618336487873,
            3838.387629719051,
        ],
        rtol=1e-3,
    )
    np.testing.assert_allclose(
        power_mw,
        [
            5.127098350537687,
            3.1608648363651213,
            2.0342922448691025,
            3.834917361557811,
            1.9028635989109357,
            np.nan,
            np.nan,
        ],
        rtol=1e-3,
    )

    # Check that all asv corrected rates are larger than or equal to input inlet rate
    assert np.all(inlet_actual_rate_before_asv_m3_per_hr <= inlet_actual_rate_m3_per_hr)
    # For points 1 and 4, asv corrected should be larger
    assert np.all(inlet_actual_rate_before_asv_m3_per_hr[[1, 4]] < inlet_actual_rate_m3_per_hr[[1, 4]])
    # For points 0, 2, 3, 5, 6 asv should be equal
    assert np.all(
        inlet_actual_rate_before_asv_m3_per_hr[[0, 2, 3, 5, 6]] == inlet_actual_rate_m3_per_hr[[0, 2, 3, 5, 6]]
    )
    # Check that all choke corrected head values are larger than or equal to head before potential choking
    assert (polytropic_enthalpy_change_before_choke_kJ_per_kg - 1e-5 <= polytropic_enthalpy_change_kJ_per_kg).all()
    # For points 2,3, 4 and 6, choke corrected should be larger
    assert np.all(
        polytropic_enthalpy_change_before_choke_kJ_per_kg[[2, 3, 4, 6]]
        < polytropic_enthalpy_change_kJ_per_kg[[2, 3, 4, 6]]
    )
    # For points 0, 1, 5, choke corrected should be equal
    np.testing.assert_allclose(
        polytropic_enthalpy_change_before_choke_kJ_per_kg[[0, 1, 5]], polytropic_enthalpy_change_kJ_per_kg[[0, 1, 5]]
    )

    # Not predefined compressors/charts, but estimated from data
    polytropic_efficiency = 0.75

    compressor_train = CompressorTrainSimplifiedKnownStages(
        data_transfer_object=dto.CompressorTrainSimplifiedWithKnownStages(
            fluid_model=medium_fluid,
            stages=[
                dto.CompressorStage(
                    inlet_temperature_kelvin=313.15,
                    compressor_chart=dto.GenericChartFromInput(polytropic_efficiency_fraction=polytropic_efficiency),
                    remove_liquid_after_cooling=True,
                    pressure_drop_before_stage=0,
                    control_margin=0,
                )
            ],
            calculate_max_rate=False,
            energy_usage_adjustment_constant=0,
            energy_usage_adjustment_factor=1,
        )
    )
    compressor_result_chart_from_input_data = compressor_train.calculate_compressor_stage_work_given_outlet_pressure(
        inlet_pressure=inlet_pressures,
        inlet_temperature_kelvin=np.full_like(mass_rates, fill_value=313.15),
        pressure_ratio=pressure_ratios_per_stage,
        mass_rate_kg_per_hour=mass_rates,
        stage=UndefinedCompressorStage(
            inlet_temperature_kelvin=313.15,
            polytropic_efficiency=polytropic_efficiency,
            remove_liquid_after_cooling=True,
        ),
    )

    # All points should now be valid!
    assert ~(np.isnan([x.power_megawatt for x in compressor_result_chart_from_input_data])).all()
    assert ~np.array([x.stage_results[0].rate_exceeds_maximum for x in compressor_result_chart_from_input_data]).all()
    assert ~np.array([x.stage_results[0].head_exceeds_maximum for x in compressor_result_chart_from_input_data]).all()


def test_calculate_enthalpy_change_head_iteration_and_outlet_stream(dry_fluid):
    (
        inlet_pressure_values,
        pressure_ratio_values,
        inlet_temperature_kelvin_values,
    ) = _span_variables(
        [np.linspace(10.0, 70.0, num=3), np.linspace(1.1, 5.0, num=3), np.linspace(300.0, 400.0, num=3)]
    )
    expected_enthalpy_change = [
        17165.70932758,
        230895.74851731,
        355729.95810979,
        16097.89323857,
        218638.62032295,
        342863.83168666,
        15184.99550521,
        212342.51428259,
        342127.88281624,
        20218.10110113,
        269720.78146496,
        413936.21938869,
        19606.37609504,
        264214.6646174,
        411503.93206297,
        19131.79183588,
        263066.99015241,
        418016.61020313,
        23221.06464442,
        307236.69517442,
        469773.65051616,
        22908.51413862,
        306273.37867871,
        474509.51275192,
        22704.75491024,
        308536.56502859,
        485931.1675868,
    ]
    expected_inlet_z = [
        0.9788040600374672,
        0.9788040600374672,
        0.9788040600374672,
        0.9181111786416455,
        0.9181111786416455,
        0.9181111786416455,
        0.8651156971635996,
        0.8651156971635996,
        0.8651156971635996,
        0.9888725578821254,
        0.9888725578821254,
        0.9888725578821254,
        0.9588377562295036,
        0.9588377562295036,
        0.9588377562295036,
        0.9349183542543573,
        0.9349183542543573,
        0.9349183542543573,
        0.9945543322185046,
        0.9945543322185046,
        0.9945543322185046,
        0.9808782514178426,
        0.9808782514178426,
        0.9808782514178426,
        0.9715102592626779,
        0.9715102592626779,
        0.9715102592626779,
    ]
    expected_outlet_z = [
        0.9790783202317882,
        0.9862619239163161,
        0.9947087074687762,
        0.9204426567669927,
        0.9715785182803748,
        1.0251572815654726,
        0.8714799117062179,
        0.9934101347412463,
        1.1054009885442733,
        0.9892011805265233,
        0.9966740973272696,
        1.0048955126981132,
        0.9608670082709349,
        1.004154453620488,
        1.0493043255390029,
        0.9396795075027707,
        1.0340935280215644,
        1.1249202801934195,
        0.9949097641604303,
        1.0024969970281834,
        1.0105180417623985,
        0.982747706739725,
        1.0217138145216378,
        1.061876446480986,
        0.9755099582570033,
        1.0555456899096032,
        1.1338963052693398,
    ]
    expected_inlet_kappa = [
        1.2670375983937072,
        1.2670375983937072,
        1.2670375983937072,
        1.2341234893402546,
        1.2341234893402546,
        1.2341234893402546,
        1.2026733845451791,
        1.2026733845451791,
        1.2026733845451791,
        1.2486932713593657,
        1.2486932713593657,
        1.2486932713593657,
        1.2301361868142462,
        1.2301361868142462,
        1.2301361868142462,
        1.2129635632351539,
        1.2129635632351539,
        1.2129635632351539,
        1.2296418285106454,
        1.2296418285106454,
        1.2296418285106454,
        1.218437877993173,
        1.218437877993173,
        1.218437877993173,
        1.2081830764957533,
        1.2081830764957533,
        1.2081830764957533,
    ]
    expected_outlet_kappa = [
        1.263145776633585,
        1.2200721530402499,
        1.2004165268549318,
        1.2305237354425138,
        1.1931437771461177,
        1.1776460655912142,
        1.2003229394326926,
        1.1778435565250387,
        1.1686777462372964,
        1.2446077262164887,
        1.2027841403439452,
        1.1850869165431854,
        1.2261418156907251,
        1.1862429060711157,
        1.1701178545566306,
        1.209445989072903,
        1.1758237873181443,
        1.1628923288697997,
        1.2256767853066637,
        1.187191564477486,
        1.171694970631198,
        1.2144686554156294,
        1.1763106363050397,
        1.1612904379919338,
        1.204400652997104,
        1.1689792717853782,
        1.155597777462001,
    ]

    fluid = FluidStream(dry_fluid)
    inlet_streams = fluid.get_fluid_streams(
        pressure_bara=inlet_pressure_values, temperature_kelvin=inlet_temperature_kelvin_values
    )

    outlet_pressure = inlet_pressure_values * pressure_ratio_values

    enthalpy_change_joule_per_kg, polytropic_efficiencies = calculate_enthalpy_change_head_iteration(
        molar_mass=fluid.molar_mass_kg_per_mol,
        polytropic_efficiency_vs_rate_and_head_function=lambda *args, **kwargs: 0.75,
        outlet_pressure=outlet_pressure,
        inlet_temperature_kelvin=inlet_temperature_kelvin_values,
        inlet_pressure=inlet_pressure_values,
        inlet_streams=inlet_streams,
        inlet_actual_rate_m3_per_hour=np.full_like(inlet_pressure_values, 1.0),
    )

    outlet_streams = [
        stream.set_new_pressure_and_enthalpy_change(new_pressure=pressure, enthalpy_change_joule_per_kg=enthalpy_change)
        for stream, pressure, enthalpy_change in zip(inlet_streams, outlet_pressure, enthalpy_change_joule_per_kg)
    ]

    np.testing.assert_allclose(expected_inlet_z, [s.z for s in inlet_streams])
    np.testing.assert_allclose(expected_outlet_z, [s.z for s in outlet_streams])
    np.testing.assert_allclose(expected_inlet_kappa, [s.kappa for s in inlet_streams])
    np.testing.assert_allclose(expected_outlet_kappa, [s.kappa for s in outlet_streams])
    np.testing.assert_allclose(expected_enthalpy_change, enthalpy_change_joule_per_kg)
