from copy import deepcopy

import numpy as np
import pytest

from libecalc.domain.process.compressor import dto
from libecalc.common.errors.exceptions import IllegalStateException
from libecalc.common.fixed_speed_pressure_control import FixedSpeedPressureControl
from libecalc.domain.process.core.chart.chart_area_flag import ChartAreaFlag
from libecalc.domain.process.compressor.core.train.variable_speed_compressor_train_common_shaft import (
    VariableSpeedCompressorTrainCommonShaft,
)
from libecalc.domain.process.core.results.compressor import (
    CompressorTrainCommonShaftFailureStatus,
)


@pytest.fixture
def variable_speed_compressor_train_one_compressor(
    variable_speed_compressor_train_dto, variable_speed_compressor_train_stage_dto
) -> VariableSpeedCompressorTrainCommonShaft:
    """Train with only one compressor, and standard medium fluid, no liquid off take."""
    dto_copy = deepcopy(variable_speed_compressor_train_dto)
    dto_copy.stages = [variable_speed_compressor_train_stage_dto]
    return VariableSpeedCompressorTrainCommonShaft(data_transfer_object=dto_copy)


@pytest.fixture
def variable_speed_compressor_train_one_compressor_maximum_power(
    variable_speed_compressor_train_dto, variable_speed_compressor_train_stage_dto
) -> VariableSpeedCompressorTrainCommonShaft:
    """Train with only one compressor, and standard medium fluid, no liquid off take."""
    dto_copy = deepcopy(variable_speed_compressor_train_dto)
    dto_copy.stages = [variable_speed_compressor_train_stage_dto]
    dto_copy.maximum_power = 7.0

    return VariableSpeedCompressorTrainCommonShaft(data_transfer_object=dto_copy)


@pytest.fixture
def variable_speed_compressor_train_one_compressor_no_pressure_control(
    variable_speed_compressor_train_dto, variable_speed_compressor_train_stage_dto
) -> VariableSpeedCompressorTrainCommonShaft:
    """Train with only one compressor, and standard medium fluid, no liquid off take."""
    dto_copy = deepcopy(variable_speed_compressor_train_dto)
    dto_copy.stages = [variable_speed_compressor_train_stage_dto]
    dto_copy.pressure_control = None

    return VariableSpeedCompressorTrainCommonShaft(data_transfer_object=dto_copy)


@pytest.fixture
def variable_speed_compressor_train_one_compressor_asv_rate(
    variable_speed_compressor_train_dto, variable_speed_compressor_train_stage_dto
) -> VariableSpeedCompressorTrainCommonShaft:
    """Train with only one compressor, and standard medium fluid, no liquid off take."""
    dto_copy = deepcopy(variable_speed_compressor_train_dto)
    dto_copy.stages = [variable_speed_compressor_train_stage_dto]
    dto_copy.pressure_control = FixedSpeedPressureControl.INDIVIDUAL_ASV_RATE

    return VariableSpeedCompressorTrainCommonShaft(data_transfer_object=dto_copy)


@pytest.fixture
def variable_speed_compressor_train_two_compressors(
    variable_speed_compressor_train_dto, variable_speed_compressor_train_stage_dto
) -> VariableSpeedCompressorTrainCommonShaft:
    """Train with only two compressors, and standard medium fluid, no liquid off take."""
    dto_copy = deepcopy(variable_speed_compressor_train_dto)
    dto_copy.stages = [variable_speed_compressor_train_stage_dto] * 2

    return VariableSpeedCompressorTrainCommonShaft(data_transfer_object=dto_copy)


class TestVariableSpeedCompressorTrainCommonShaftOneRateTwoPressures:
    def test_single_point_within_capacity_one_compressor(self, variable_speed_compressor_train_one_compressor):
        result = variable_speed_compressor_train_one_compressor.evaluate(
            rate=np.asarray([7000]),
            suction_pressure=np.asarray([30]),
            discharge_pressure=np.asarray([100.0]),
        )
        assert result.mass_rate_kg_per_hr[0] == pytest.approx(240.61266437085808)
        assert result.power[0] == pytest.approx(6.889951698413056)
        assert result.outlet_stream.pressure[0] == pytest.approx(100.00000000000007)
        assert result.inlet_stream.density_kg_per_m3[0] == pytest.approx(24.888039288426715)

    def test_points_above_and_below_maximum_power(self, variable_speed_compressor_train_one_compressor_maximum_power):
        result = variable_speed_compressor_train_one_compressor_maximum_power.evaluate(
            rate=np.asarray([3000000, 3500000]),
            suction_pressure=np.asarray([30, 30]),
            discharge_pressure=np.asarray([100.0, 100.0]),
        )
        assert result.is_valid[0]
        assert not result.is_valid[1]
        assert result.failure_status[0] == CompressorTrainCommonShaftFailureStatus.NO_FAILURE
        assert result.failure_status[1] == CompressorTrainCommonShaftFailureStatus.ABOVE_MAXIMUM_POWER

    def test_single_point_rate_too_high_no_pressure_control(
        self, variable_speed_compressor_train_one_compressor_no_pressure_control
    ):
        """When the rate is too high then the compressor normally will need to adjust the head up in order to be able to
        handle the high rate. This results in too high pressure and will normally be choked upstreams or downstreams.

        In some cases we don't have this mechanism, and we want the train to fail instead.
        """
        target_pressure = 35.0  # Low target discharge pressure normally forces downstream choke.
        result = variable_speed_compressor_train_one_compressor_no_pressure_control.evaluate(
            rate=np.asarray([7000]),
            suction_pressure=np.asarray([30]),
            discharge_pressure=np.asarray([target_pressure]),
        )
        assert not np.any(result.is_valid)
        assert not np.any(result.pressure_is_choked)
        assert result.failure_status[0] == CompressorTrainCommonShaftFailureStatus.TARGET_DISCHARGE_PRESSURE_TOO_LOW

    def test_single_point_recirculate_on_minimum_speed_curve_one_compressor(
        self, variable_speed_compressor_train_one_compressor_asv_rate
    ):
        result = variable_speed_compressor_train_one_compressor_asv_rate.evaluate(
            rate=np.asarray([1500000]),
            suction_pressure=np.asarray([30]),
            discharge_pressure=np.asarray([55.0]),
        )

        np.testing.assert_allclose(result.mass_rate_kg_per_hr[0], 51559.9, rtol=0.001)
        np.testing.assert_allclose(result.power[0], 2.5070, rtol=0.001)
        np.testing.assert_allclose(result.outlet_stream.pressure[0], 55.0, rtol=0.001)
        np.testing.assert_allclose(result.inlet_stream.density_kg_per_m3[0], 24.888, rtol=0.001)

    def test_zero_rate_zero_pressure(self, variable_speed_compressor_train_one_compressor):
        """We want to get a result object when rate is zero regardless of invalid/zero pressures. To ensure
        this we set pressure -> 1 when both rate and pressure is zero. This may happen when pressure is a function
        of rate.
        """
        result = variable_speed_compressor_train_one_compressor.evaluate(
            rate=np.array([0, 1, 1]),
            suction_pressure=np.array([0, 1, 1]),
            discharge_pressure=np.array([0, 2, 2]),
        )

        # Ensuring that first stage returns zero energy usage and no failure (zero rate should always be valid).
        assert result.is_valid == [True, True, True]
        assert result.failure_status == [
            CompressorTrainCommonShaftFailureStatus.NO_FAILURE,
            CompressorTrainCommonShaftFailureStatus.NO_FAILURE,
            CompressorTrainCommonShaftFailureStatus.NO_FAILURE,
        ]
        np.testing.assert_allclose(result.energy_usage, np.array([0.0, 0.092847, 0.092847]), rtol=0.0001)

        assert result.mass_rate_kg_per_hr[0] == 0
        assert result.power[0] == 0
        assert np.isnan(result.inlet_stream.pressure[0])
        assert np.isnan(result.outlet_stream.pressure[0])

    def test_non_zero_rate_and_zero_pressure(self, variable_speed_compressor_train_one_compressor):
        """We want to get a result object when rate is zero regardless of invalid/zero pressures. To ensure
        this we set pressure -> 1 when both rate and pressure is zero. This may happen when pressure is a function
        of rate.
        """
        result = variable_speed_compressor_train_one_compressor.evaluate(
            rate=np.array([0, 1, 1]), suction_pressure=np.array([0, 1, 0]), discharge_pressure=np.array([0, 0, 1])
        )

        # Result object generated but result marked as invalid when rates or pressures are altered by validation
        assert not all(result.is_valid)
        assert all(flag == ChartAreaFlag.NOT_CALCULATED for flag in result.stage_results[0].chart_area_flags)
        np.testing.assert_allclose(result.energy_usage, np.array([0, 0, 0]))

        np.testing.assert_allclose(result.mass_rate_kg_per_hr, 0)
        np.testing.assert_allclose(result.energy_usage, 0)
        np.testing.assert_allclose(result.power, 0)

    def test_single_point_within_capacity_one_compressor_add_constant(
        self,
        variable_speed_compressor_train_one_compressor,
    ):
        energy_usage_adjustment_constant = 10

        result_comparison = variable_speed_compressor_train_one_compressor.evaluate(
            rate=np.asarray([3000000]),
            suction_pressure=np.asarray([30]),
            discharge_pressure=np.asarray([100.0]),
        )

        variable_speed_compressor_train_one_compressor.data_transfer_object.energy_usage_adjustment_constant = (
            energy_usage_adjustment_constant
        )
        result = variable_speed_compressor_train_one_compressor.evaluate(
            rate=np.asarray([3000000]),
            suction_pressure=np.asarray([30]),
            discharge_pressure=np.asarray([100.0]),
        )

        np.testing.assert_allclose(
            np.asarray(result_comparison.energy_usage) + energy_usage_adjustment_constant,
            result.energy_usage,
            rtol=0.01,
        )

    def test_single_point_downstream_choke(
        self,
        variable_speed_compressor_train_one_compressor,
    ):
        # Testing internal point and ensure that choking is working correctly using DOWNSTREAM CHOKE (default)
        result = variable_speed_compressor_train_one_compressor.evaluate(
            rate=np.asarray([3000000]),
            suction_pressure=np.asarray([30]),
            discharge_pressure=np.asarray([40.0]),
        )

        assert result.outlet_stream.pressure[0] == 40
        np.testing.assert_allclose(result.stage_results[-1].outlet_stream_condition.pressure, 51, atol=1)
        assert all(result.is_valid)
        assert result.stage_results[0].chart_area_flags[0] == ChartAreaFlag.INTERNAL_POINT


def test_find_and_calculate_for_compressor_shaft_speed_given_rate_ps_pd():
    func = VariableSpeedCompressorTrainCommonShaft.calculate_shaft_speed_given_rate_ps_pd
    assert func
    # Depends on test case with real data to make sense
    # Will be done after asset test case is established


def test_calculate_compressor_train_given_speed_invalid(variable_speed_compressor_train_dto):
    compressor_train = VariableSpeedCompressorTrainCommonShaft(
        data_transfer_object=variable_speed_compressor_train_dto,
    )

    with pytest.raises(IllegalStateException):
        _ = compressor_train.calculate_compressor_train_given_rate_ps_speed(
            speed=1,
            mass_rate_kg_per_hour=6000000.0,
            inlet_pressure_bara=50,
        )


def test_find_and_calculate_for_compressor_shaft_speed_given_rate_ps_pd_invalid_point(
    process_simulator_variable_compressor_data,
    medium_fluid,
):
    mass_rate_kg_per_hour = 6000000

    variable_speed_compressor_train = VariableSpeedCompressorTrainCommonShaft(
        data_transfer_object=dto.VariableSpeedCompressorTrain(
            stages=[
                dto.CompressorStage(
                    compressor_chart=process_simulator_variable_compressor_data.compressor_chart,
                    inlet_temperature_kelvin=293.15,
                    pressure_drop_before_stage=0.0,
                    remove_liquid_after_cooling=False,
                    control_margin=0,
                )
            ]
            * 2,
            energy_usage_adjustment_constant=0,
            energy_usage_adjustment_factor=1,
            fluid_model=medium_fluid,
            pressure_control=FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
        ),
    )

    # rate too large
    result = variable_speed_compressor_train.calculate_shaft_speed_given_rate_ps_pd(
        mass_rate_kg_per_hour=mass_rate_kg_per_hour,
        suction_pressure=20,
        target_discharge_pressure=400,
    )
    assert result.chart_area_status == ChartAreaFlag.ABOVE_MAXIMUM_FLOW_RATE

    # Target pressure too large, but rate still too high
    result = variable_speed_compressor_train.calculate_shaft_speed_given_rate_ps_pd(
        mass_rate_kg_per_hour=mass_rate_kg_per_hour,
        suction_pressure=20,
        target_discharge_pressure=1000,
    )
    assert result.failure_status == CompressorTrainCommonShaftFailureStatus.ABOVE_MAXIMUM_FLOW_RATE

    # Target pressure too low -> but still possible because of downstream choke. However, the rate is still too high.
    result = variable_speed_compressor_train.calculate_shaft_speed_given_rate_ps_pd(
        mass_rate_kg_per_hour=mass_rate_kg_per_hour,
        suction_pressure=20,
        target_discharge_pressure=1,
    )
    assert result.chart_area_status == ChartAreaFlag.ABOVE_MAXIMUM_FLOW_RATE
    assert not result.is_valid

    # Rate is too large, but point is below stonewall, i.e. rate is too large for resulting speed, but not too large
    # for maximum speed
    result = variable_speed_compressor_train.calculate_shaft_speed_given_rate_ps_pd(
        mass_rate_kg_per_hour=mass_rate_kg_per_hour,
        suction_pressure=20,
        target_discharge_pressure=600,
    )
    assert result.chart_area_status == ChartAreaFlag.ABOVE_MAXIMUM_FLOW_RATE

    # Point where rate is recirculating
    result = variable_speed_compressor_train.calculate_shaft_speed_given_rate_ps_pd(
        mass_rate_kg_per_hour=1,
        suction_pressure=20,
        target_discharge_pressure=400,
    )
    # Check that actual rate is equal to minimum rate for the speed
    assert result.stage_results[0].inlet_actual_rate_asv_corrected_m3_per_hour == pytest.approx(
        variable_speed_compressor_train.stages[0].compressor_chart.minimum_rate_as_function_of_speed(result.speed)
    )
    assert result.chart_area_status == ChartAreaFlag.BELOW_MINIMUM_FLOW_RATE


def test_variable_speed_compressor_train_vs_unisim_methane(variable_speed_compressor_train_unisim_methane):
    compressor_train = variable_speed_compressor_train_unisim_methane

    result = compressor_train.evaluate(
        rate=np.asarray([3537181, 5305772, 6720644, 5305772, 5305772]),
        suction_pressure=np.asarray([40, 40, 40, 40, 40]),
        discharge_pressure=np.asarray([100, 100, 100, 110, 70]),
    )

    expected_power = np.array(
        [6.64205229725697, 8.49608791013644, 11.1289812020102, 9.57095479322606, 5.15465592172343]
    )

    expected_efficiency = (
        np.array([72.3876159007002, 74.6925582292251, 72.5406362153829, 74.4979434232747, 70.9067558922266]) / 100
    )  # [-]
    expected_act_gas_rate = np.array(
        [3536.92985290962, 5305.39477936443, 6720.16672052827, 5305.39477936443, 5305.39477936443]
    )  # [m3/h]
    expected_inlet_temperature = np.array([20, 20, 20, 20, 20]) + 273.15  # [K]
    expected_inlet_mass_rate = np.array([100000, 150000, 190000, 150000, 150000])  # [kg/h]
    expected_inlet_mass_density = np.array([28.27311, 28.27311, 28.27311, 28.27311, 28.27311])  # [kg/m3]
    expected_inlet_z = np.array([0.931221, 0.931221, 0.931221, 0.931221, 0.931221])  # [-]
    # expected_inlet_kappa = np.array([1.44187, 1.44187, 1.44187, 1.44187, 1.44187])  # [-]
    expected_outlet_mass_density = np.array(
        [49.4096714224892, 51.4023341976981, 50.9927365350469, 54.6222268941276, 40.395808348514]
    )  # [kg/m3]
    # expected_outlet_kappa = np.array(
    #     [1.37453908352775, 1.39416716969814, 1.39009235743569, 1.38748506506009, 1.41110690143598]
    # )  # [-]
    expected_outlet_z = np.array(
        [0.979997063154205, 0.972313694183659, 0.973921602422692, 0.979185361636038, 0.953802181367592]
    )
    expected_outlet_temperature = (
        np.array([125.341812932287, 112.920750503461, 115.3793442863, 123.689153065012, 77.407746779584]) + 273.15
    )  # [K]
    expected_outlet_pressure = np.array([100, 100, 100, 110, 70])  # [bar]

    np.testing.assert_allclose(result.power, expected_power, rtol=0.07)
    np.testing.assert_allclose(result.inlet_stream.temperature_kelvin, expected_inlet_temperature, rtol=0.05)
    np.testing.assert_allclose(result.inlet_stream_condition.actual_rate_m3_per_hr, expected_act_gas_rate, rtol=0.05)
    np.testing.assert_allclose(result.mass_rate_kg_per_hr, expected_inlet_mass_rate, rtol=0.05)
    np.testing.assert_allclose(result.inlet_stream.density_kg_per_m3, expected_inlet_mass_density, rtol=0.05)
    np.testing.assert_allclose(result.inlet_stream.z, expected_inlet_z, rtol=0.05)
    # np.testing.assert_allclose(result.inlet_kappa, expected_inlet_kappa, rtol=0.12)
    np.testing.assert_allclose(result.outlet_stream.density_kg_per_m3, expected_outlet_mass_density, rtol=0.5)
    # np.testing.assert_allclose(result.outlet_kappa, expected_outlet_kappa, rtol=0.13)
    np.testing.assert_allclose(result.outlet_stream.z, expected_outlet_z, rtol=0.05)
    np.testing.assert_allclose(result.outlet_stream.temperature_kelvin, expected_outlet_temperature, rtol=0.05)
    np.testing.assert_allclose(result.outlet_stream.pressure, expected_outlet_pressure, rtol=0.06)
    np.testing.assert_allclose(result.stage_results[0].polytropic_efficiency, expected_efficiency, rtol=0.03)


def test_adjustment_constant_and_factor_one_compressor(variable_speed_compressor_train_one_compressor):
    compressor_train = variable_speed_compressor_train_one_compressor
    adjustment_constant = 10
    adjustment_factor = 1.5
    result = compressor_train.evaluate(
        rate=np.asarray([7000]),
        suction_pressure=np.asarray([30]),
        discharge_pressure=np.asarray([100.0]),
    )

    compressor_train.data_transfer_object.energy_usage_adjustment_factor = adjustment_factor
    compressor_train.data_transfer_object.energy_usage_adjustment_constant = adjustment_constant

    result_adjusted = compressor_train.evaluate(
        rate=np.asarray([7000]),
        suction_pressure=np.asarray([30]),
        discharge_pressure=np.asarray([100.0]),
    )
    assert result_adjusted.power[0] == result.power[0] * 1.5 + adjustment_constant


def test_get_max_standard_rate_with_and_without_maximum_power(
    variable_speed_compressor_train_one_compressor,
    variable_speed_compressor_train_one_compressor_maximum_power,
):
    max_standard_rate_without_maximum_power = variable_speed_compressor_train_one_compressor.get_max_standard_rate(
        suction_pressures=np.asarray([30], dtype=float),
        discharge_pressures=np.asarray([100], dtype=float),
    )
    max_standard_rate_with_maximum_power = (
        variable_speed_compressor_train_one_compressor_maximum_power.get_max_standard_rate(
            suction_pressures=np.asarray([30], dtype=float),
            discharge_pressures=np.asarray([100], dtype=float),
        )
    )
    power_at_max_standard_rate_without_maximum_power = variable_speed_compressor_train_one_compressor.evaluate(
        rate=np.asarray(max_standard_rate_without_maximum_power, dtype=float),
        suction_pressure=np.asarray([30], dtype=float),
        discharge_pressure=np.asarray([100], dtype=float),
    ).power
    power_at_max_standard_rate_with_maximum_power = (
        variable_speed_compressor_train_one_compressor_maximum_power.evaluate(
            rate=np.asarray(max_standard_rate_with_maximum_power, dtype=float),
            suction_pressure=np.asarray([30], dtype=float),
            discharge_pressure=np.asarray([100], dtype=float),
        ).power
    )

    assert max_standard_rate_without_maximum_power > max_standard_rate_with_maximum_power
    assert power_at_max_standard_rate_without_maximum_power > power_at_max_standard_rate_with_maximum_power
    assert (
        power_at_max_standard_rate_with_maximum_power[0]
        < variable_speed_compressor_train_one_compressor_maximum_power.maximum_power
    )
