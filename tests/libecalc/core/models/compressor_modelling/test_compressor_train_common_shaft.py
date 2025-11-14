import numpy as np
import pytest

from libecalc.common.errors.exceptions import IllegalStateException
from libecalc.common.fixed_speed_pressure_control import FixedSpeedPressureControl
from libecalc.domain.process.compressor.core.train.compressor_train_common_shaft import CompressorTrainCommonShaft
from libecalc.domain.process.compressor.core.train.stage import CompressorTrainStage
from libecalc.domain.process.compressor.core.train.train_evaluation_input import CompressorTrainEvaluationInput
from libecalc.domain.process.core.results.compressor import CompressorTrainCommonShaftFailureStatus
from libecalc.domain.process.value_objects.chart.chart_area_flag import ChartAreaFlag
from libecalc.domain.process.value_objects.fluid_stream import FluidComposition
from libecalc.domain.process.value_objects.fluid_stream.fluid_model import FluidModel, EoSModel
from libecalc.infrastructure.neqsim_fluid_provider.neqsim_fluid_factory import NeqSimFluidFactory


class TestCompressorTrainCommonShaft:
    def test_evaluate_rate_ps_pd_downstream_choke_pressure_control(
        self, single_speed_compressor_train_common_shaft, fluid_model_medium, fluid_factory_medium
    ):
        compressor_train = single_speed_compressor_train_common_shaft(
            fluid_model=fluid_model_medium, pressure_control=FixedSpeedPressureControl.DOWNSTREAM_CHOKE
        )
        target_discharge_pressures = np.asarray([300.0, 310.0, 300.0, 300.0])
        suction_pressures = 4 * [80.0]
        compressor_train.set_evaluation_input(
            fluid_factory=fluid_factory_medium,
            rate=np.asarray([5800000.0, 5800000.0, 1000.0, 8189000.0]),
            suction_pressure=np.asarray(suction_pressures),
            discharge_pressure=target_discharge_pressures,
        )
        result = compressor_train.evaluate()
        np.testing.assert_almost_equal(
            result.outlet_stream_condition.pressure,
            [300.0, 305.0, 300.0, 216.9],
            decimal=1,
        )
        np.testing.assert_almost_equal(
            result.stage_results[-1].outlet_stream_condition.pressure, [305.0, 305.0, 367.7, 216.9], decimal=1
        )
        assert result.inlet_stream.pressure == pytest.approx(suction_pressures)

        assert result.failure_status == [
            CompressorTrainCommonShaftFailureStatus.NO_FAILURE,
            CompressorTrainCommonShaftFailureStatus.TARGET_DISCHARGE_PRESSURE_TOO_HIGH,
            CompressorTrainCommonShaftFailureStatus.NO_FAILURE,
            CompressorTrainCommonShaftFailureStatus.ABOVE_MAXIMUM_FLOW_RATE,
        ]
        energy_result = result.get_energy_result()
        assert energy_result.power.values == pytest.approx([14.54498, 14.54498, 16.05248, 14.6864], rel=0.0001)
        assert energy_result.is_valid == [True, False, True, False]

    def test_adjust_energy_constant_mw(
        self,
        single_speed_compressor_train_common_shaft,
        fluid_model_medium,
        fluid_factory_medium,
    ):
        target_discharge_pressures = np.asarray([300.0, 310.0, 300.0, 300.0])
        suction_pressures = 4 * [80.0]
        energy_usage_adjustment_constant = 10  # MW
        compressor_train = single_speed_compressor_train_common_shaft(
            fluid_model=fluid_model_medium, pressure_control=FixedSpeedPressureControl.DOWNSTREAM_CHOKE
        )

        compressor_train.set_evaluation_input(
            fluid_factory=fluid_factory_medium,
            rate=np.asarray([5800000.0, 5800000.0, 1000.0, 8189000.0]),
            suction_pressure=np.asarray(suction_pressures),
            discharge_pressure=target_discharge_pressures,
        )
        result_comparison = compressor_train.evaluate()

        compressor_train_adjusted = single_speed_compressor_train_common_shaft(
            fluid_model=fluid_model_medium,
            pressure_control=FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
            energy_usage_adjustment_constant=energy_usage_adjustment_constant,
        )

        compressor_train_adjusted.set_evaluation_input(
            fluid_factory=fluid_factory_medium,
            rate=np.asarray([5800000.0, 5800000.0, 1000.0, 8189000.0]),
            suction_pressure=np.asarray(suction_pressures),
            discharge_pressure=target_discharge_pressures,
        )
        result = compressor_train_adjusted.evaluate()

        np.testing.assert_allclose(
            np.asarray(result_comparison.get_energy_result().energy_usage.values) + energy_usage_adjustment_constant,
            result.get_energy_result().energy_usage.values,
        )

    def test_evaluate_rate_ps_pd_downstream_choke_pressure_control_and_maximum_discharge_pressure(
        self,
        single_speed_compressor_train_common_shaft,
        fluid_model_medium,
        fluid_factory_medium,
    ):
        # In the previous test, we see that the third point (index=2) have a floating discharge pressure 367.5
        # Now, the maximum discharge pressure is set to 350.0, thus for this point, the discharge pressure should be ~350
        # And the suction pressure and other relevant attributes in the result should have been changed accordingly
        target_discharge_pressures = np.asarray([300.0, 310.0, 300.0, 300.0])
        suction_pressures = 4 * [80.0]
        compressor_train = single_speed_compressor_train_common_shaft(
            fluid_model=fluid_model_medium,
            pressure_control=FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
            maximum_discharge_pressure=350.0,
        )
        compressor_train.set_evaluation_input(
            fluid_factory=fluid_factory_medium,
            rate=np.asarray([5800000.0, 5800000.0, 1000.0, 8189000.0]),
            suction_pressure=np.asarray(suction_pressures),
            discharge_pressure=target_discharge_pressures,
        )
        result = compressor_train.evaluate()
        np.testing.assert_almost_equal(
            result.outlet_stream_condition.pressure,
            [300.0, 305.0, 300.0, 216.9],
            decimal=1,
        )
        np.testing.assert_almost_equal(
            result.stage_results[-1].outlet_stream_condition.pressure,
            [305.0, 305.0, 350.0, 216.9],
            decimal=1,
        )

        np.testing.assert_almost_equal(result.inlet_stream_condition.pressure, [80.0, 80.0, 80.0, 80.0], decimal=1)
        np.testing.assert_almost_equal(
            result.stage_results[0].inlet_stream_condition.pressure, [80.0, 80.0, 75.8, 80.0], decimal=1
        )

        assert result.failure_status == [
            CompressorTrainCommonShaftFailureStatus.NO_FAILURE,
            CompressorTrainCommonShaftFailureStatus.TARGET_DISCHARGE_PRESSURE_TOO_HIGH,
            CompressorTrainCommonShaftFailureStatus.NO_FAILURE,
            CompressorTrainCommonShaftFailureStatus.ABOVE_MAXIMUM_FLOW_RATE,
        ]
        energy_result = result.get_energy_result()
        np.testing.assert_almost_equal(
            energy_result.power.values,
            [14.545, 14.545, 15.178, 14.686],
            decimal=3,
        )
        assert energy_result.is_valid == [True, False, True, False]

    @pytest.mark.slow
    def test_evaluate_rate_ps_pd_upstream_choke_pressure_control(
        self, single_speed_compressor_train_common_shaft, fluid_model_medium, fluid_factory_medium
    ):
        target_suction_pressures = np.asarray(5 * [80.0])
        suction_pressures_after_upstream_choking = np.asarray([79.34775, 80.0, 64.52168, 80.0, 49.11668])
        compressor_train = single_speed_compressor_train_common_shaft(
            fluid_model=fluid_model_medium, pressure_control=FixedSpeedPressureControl.UPSTREAM_CHOKE
        )
        compressor_train.set_evaluation_input(
            fluid_factory=fluid_factory_medium,
            rate=np.asarray([5800000.0, 5800000.0, 1000.0, 8000000.0, 5800000.0]),
            suction_pressure=target_suction_pressures,
            discharge_pressure=np.asarray([300.0, 310.0, 300.0, 250.0, 100.0]),
        )
        result = compressor_train.evaluate()
        np.testing.assert_almost_equal(
            suction_pressures_after_upstream_choking, result.stage_results[0].inlet_stream_condition.pressure, decimal=1
        )
        np.testing.assert_almost_equal(
            result.inlet_stream_condition.pressure,
            [80.0, 80.0, 80.0, 80.0, 80.0],
            decimal=1,
        )

        assert result.failure_status == [
            CompressorTrainCommonShaftFailureStatus.NO_FAILURE,
            CompressorTrainCommonShaftFailureStatus.TARGET_DISCHARGE_PRESSURE_TOO_HIGH,
            CompressorTrainCommonShaftFailureStatus.NO_FAILURE,
            CompressorTrainCommonShaftFailureStatus.ABOVE_MAXIMUM_FLOW_RATE,
            CompressorTrainCommonShaftFailureStatus.ABOVE_MAXIMUM_FLOW_RATE,
        ]
        assert result.get_energy_result().is_valid == [True, False, True, False, False]

    def test_evaluate_rate_ps_pd_asv_rate_control(
        self, single_speed_compressor_train_common_shaft, fluid_model_medium, fluid_factory_medium
    ):
        target_discharge_pressures = np.asarray([100, 300.0, 310.0, 300.0, 250.0])
        compressor_train = single_speed_compressor_train_common_shaft(
            fluid_model=fluid_model_medium, pressure_control=FixedSpeedPressureControl.INDIVIDUAL_ASV_RATE
        )
        compressor_train.set_evaluation_input(
            fluid_factory=fluid_factory_medium,
            rate=np.asarray([5800000.0, 5800000.0, 5800000.0, 1000.0, 8000000.0]),
            suction_pressure=np.asarray(5 * [80.0]),
            discharge_pressure=target_discharge_pressures,
        )
        result = compressor_train.evaluate()
        np.testing.assert_almost_equal(
            result.outlet_stream_condition.pressure,
            [167.0, 300.00, 305.0, 300.00, 220.4],
            decimal=1,
        )
        np.testing.assert_almost_equal(
            result.stage_results[-1].outlet_stream_condition.pressure,
            [167.0, 300.00, 305.0, 300.00, 220.4],
            decimal=1,
        )

        assert result.failure_status == [
            CompressorTrainCommonShaftFailureStatus.TARGET_DISCHARGE_PRESSURE_TOO_LOW,
            CompressorTrainCommonShaftFailureStatus.NO_FAILURE,
            CompressorTrainCommonShaftFailureStatus.TARGET_DISCHARGE_PRESSURE_TOO_HIGH,
            CompressorTrainCommonShaftFailureStatus.NO_FAILURE,
            CompressorTrainCommonShaftFailureStatus.ABOVE_MAXIMUM_FLOW_RATE,
        ]
        assert result.get_energy_result().is_valid == [False, True, False, True, False]

    def test_evaluate_rate_ps_pd_asv_pressure_control(
        self,
        single_speed_compressor_train_common_shaft,
        fluid_model_medium,
        compressor_stage_factory,
        single_speed_chart_curve_factory,
        chart_data_factory,
        fluid_factory_medium,
    ):
        target_discharge_pressures = np.asarray([300.0, 310.0, 300.0, 250.0, 200.0])

        first_stage = compressor_stage_factory(
            compressor_chart_data=chart_data_factory.from_curves(curves=[single_speed_chart_curve_factory()]),
            remove_liquid_after_cooling=True,
            pressure_drop_ahead_of_stage=0.0,
        )
        second_stage = compressor_stage_factory(
            compressor_chart_data=chart_data_factory.from_curves(
                curves=[
                    single_speed_chart_curve_factory(
                        rate=[x / 2 for x in first_stage.compressor.compressor_chart.curves[0].rate_actual_m3_hour]
                    )
                ]
            )
        )

        stages = [
            first_stage,
            second_stage,
        ]
        compressor_train = single_speed_compressor_train_common_shaft(
            fluid_model=fluid_model_medium,
            pressure_control=FixedSpeedPressureControl.INDIVIDUAL_ASV_PRESSURE,
            stages=stages,
        )

        compressor_train.set_evaluation_input(
            fluid_factory=fluid_factory_medium,
            rate=np.asarray([6800000.0, 6200000.0, 7000000.0, 8000000.0, 7000000.0]),
            suction_pressure=np.asarray([100, 100, 100, 110, 110], dtype=float),
            discharge_pressure=target_discharge_pressures,
        )
        result = compressor_train.evaluate()

        np.testing.assert_almost_equal(
            result.outlet_stream.pressure,
            [300.0, 310.0, 292.5, 240.4, 231.9],
            decimal=1,
        )
        assert result.failure_status == [
            CompressorTrainCommonShaftFailureStatus.NO_FAILURE,
            CompressorTrainCommonShaftFailureStatus.NO_FAILURE,
            CompressorTrainCommonShaftFailureStatus.TARGET_DISCHARGE_PRESSURE_TOO_HIGH,
            CompressorTrainCommonShaftFailureStatus.ABOVE_MAXIMUM_FLOW_RATE,
            CompressorTrainCommonShaftFailureStatus.TARGET_DISCHARGE_PRESSURE_TOO_LOW,
        ]
        assert result.get_energy_result().is_valid == [True, True, False, False, False]

    def test_evaluate_rate_ps_pd_common_asv(
        self, single_speed_compressor_train_common_shaft, fluid_model_medium, fluid_factory_medium
    ):
        target_discharge_pressures = np.asarray([200.0, 270.0, 350.0, 250.0])
        compressor_train = single_speed_compressor_train_common_shaft(
            fluid_model=fluid_model_medium, pressure_control=FixedSpeedPressureControl.COMMON_ASV
        )
        compressor_train.set_evaluation_input(
            rate=np.asarray([5800000.0, 5800000.0, 1000.0, 8000000.0]),
            suction_pressure=np.asarray(4 * [80.0]),
            discharge_pressure=target_discharge_pressures,
            fluid_factory=fluid_factory_medium,
        )
        result = compressor_train.evaluate()

        np.testing.assert_almost_equal(
            result.outlet_stream.pressure,
            [238.2, 270.0, 277.2, 220.4],
            decimal=1,
        )

        assert result.failure_status == [
            CompressorTrainCommonShaftFailureStatus.TARGET_DISCHARGE_PRESSURE_TOO_LOW,
            CompressorTrainCommonShaftFailureStatus.NO_FAILURE,
            CompressorTrainCommonShaftFailureStatus.TARGET_DISCHARGE_PRESSURE_TOO_HIGH,
            CompressorTrainCommonShaftFailureStatus.ABOVE_MAXIMUM_FLOW_RATE,
        ]
        assert result.get_energy_result().is_valid == [False, True, False, False]


class TestCalculateSingleSpeedCompressorStage:
    def test_rate_below_minimum_chart_rate(self, single_speed_compressor_train_stage, fluid_factory_medium):
        mass_rate_kg_per_hour = 85500.0
        inlet_pressure_train_bara = 80.0

        inlet_stream = fluid_factory_medium.create_stream_from_mass_rate(
            pressure_bara=inlet_pressure_train_bara,
            temperature_kelvin=single_speed_compressor_train_stage.inlet_temperature_kelvin,
            mass_rate_kg_per_h=mass_rate_kg_per_hour,
        )

        # stage.mass_rate_kg_per_hour = mass_rate_kg_per_hour
        speed = single_speed_compressor_train_stage.compressor.compressor_chart.curves[0].speed
        result = single_speed_compressor_train_stage.evaluate(
            inlet_stream_stage=inlet_stream,
            speed=speed,
        )
        # Stability check
        assert result.inlet_actual_rate_m3_per_hour == pytest.approx(1148.7960837804026)
        assert result.inlet_actual_rate_asv_corrected_m3_per_hour == 1735.0
        assert result.chart_area_flag == ChartAreaFlag.BELOW_MINIMUM_FLOW_RATE
        assert result.power_megawatt == pytest.approx(4.83, rel=0.001)
        assert result.outlet_stream.pressure_bara == pytest.approx(173.36, rel=0.001)
        assert result.outlet_stream.temperature_kelvin == pytest.approx(374.71, rel=0.001)
        assert result.outlet_stream.density == pytest.approx(117.14, rel=0.001)

    def test_rate_within_chart_curve_range(self, single_speed_compressor_train_stage, fluid_factory_medium):
        mass_rate_kg_per_hour = 200000.0
        # stage.mass_rate_kg_per_hour = mass_rate_kg_per_hour
        inlet_pressure_train_bara = 80.0

        inlet_stream = fluid_factory_medium.create_stream_from_mass_rate(
            pressure_bara=inlet_pressure_train_bara,
            temperature_kelvin=single_speed_compressor_train_stage.inlet_temperature_kelvin,
            mass_rate_kg_per_h=mass_rate_kg_per_hour,
        )
        speed = single_speed_compressor_train_stage.compressor.compressor_chart.curves[0].speed
        result = single_speed_compressor_train_stage.evaluate(
            inlet_stream_stage=inlet_stream,
            speed=speed,
        )
        # Stability check
        assert result.inlet_actual_rate_m3_per_hour == pytest.approx(2687.242301240708)
        assert result.inlet_actual_rate_asv_corrected_m3_per_hour == pytest.approx(2687.242301240708)
        assert result.chart_area_flag == ChartAreaFlag.INTERNAL_POINT
        assert result.power_megawatt == pytest.approx(5.407217436940095)
        assert result.outlet_stream.pressure_bara == pytest.approx(140.1095, rel=0.00001)
        assert result.outlet_stream.temperature_kelvin == pytest.approx(355.6817, rel=0.00001)
        assert result.outlet_stream.density == pytest.approx(103.1506, rel=0.00001)


def test_calculate_single_speed_train(
    single_speed_compressor_train_common_shaft, fluid_model_medium, fluid_factory_medium
):
    mass_rate_kg_per_hour = 200000.0
    inlet_pressure_train_bara = 80.0

    compressor_train = single_speed_compressor_train_common_shaft(
        fluid_model=fluid_model_medium, pressure_control=FixedSpeedPressureControl.DOWNSTREAM_CHOKE
    )

    compressor_train.set_evaluation_input(
        fluid_factory=fluid_factory_medium, rate=1, suction_pressure=1, discharge_pressure=2
    )
    speed = compressor_train.stages[0].compressor.compressor_chart.curves[0].speed
    compressor_train.shaft.set_speed(speed)
    result = compressor_train.calculate_compressor_train(
        constraints=CompressorTrainEvaluationInput(
            rate=compressor_train._fluid_factory.mass_rate_to_standard_rate(mass_rate_kg_per_hour),
            suction_pressure=inlet_pressure_train_bara,
        )
    )

    # Stability tests
    assert result.power_megawatt == pytest.approx(14.51, rel=0.001)
    assert result.discharge_pressure == pytest.approx(304.10, rel=0.001)
    assert result.stage_results[0].outlet_stream.pressure_bara == pytest.approx(140.11, rel=0.001)
    assert result.stage_results[1].inlet_stream.pressure_bara == pytest.approx(140.11, rel=0.001)
    assert result.stage_results[0].chart_area_flag == ChartAreaFlag.INTERNAL_POINT
    assert result.stage_results[1].chart_area_flag == ChartAreaFlag.BELOW_MINIMUM_FLOW_RATE


def test_calculate_evaluate_rate_ps_pd_single_speed_train_with_max_rate(
    single_speed_compressor_train_common_shaft, fluid_model_medium, fluid_factory_medium
):
    rate = [300000]
    suction_pressure = [10]
    discharge_pressure = [40]

    compressor_train = single_speed_compressor_train_common_shaft(
        fluid_model=fluid_model_medium, pressure_control=FixedSpeedPressureControl.DOWNSTREAM_CHOKE
    )
    compressor_train.set_evaluation_input(
        fluid_factory=fluid_factory_medium,
        rate=np.asarray(rate),
        suction_pressure=np.asarray(suction_pressure),
        discharge_pressure=np.asarray(discharge_pressure),
    )
    result = compressor_train.evaluate()

    assert result.max_standard_rate[0] == pytest.approx(407354, rel=0.001)


def test_calculate_single_speed_train_zero_mass_rate(
    fluid_model_medium, single_speed_compressor_train_common_shaft, fluid_factory_medium
):
    """We want to get a result object when rate is zero"""
    compressor_train = single_speed_compressor_train_common_shaft(
        fluid_model=fluid_model_medium, pressure_control=FixedSpeedPressureControl.DOWNSTREAM_CHOKE
    )
    compressor_train.set_evaluation_input(
        fluid_factory=fluid_factory_medium,
        rate=np.array([0]),
        suction_pressure=np.array([1]),
        discharge_pressure=np.array([2]),
    )
    result = compressor_train.evaluate()

    # Ensuring that first stage returns zero energy usage and no failure.
    energy_result = result.get_energy_result()
    assert energy_result.is_valid == [True]
    assert energy_result.energy_usage.values == pytest.approx([0.0], rel=0.00001)
    assert energy_result.power.values[0] == 0

    assert np.isnan(result.mass_rate_kg_per_hr[0])
    assert np.isnan(result.inlet_stream.pressure[0])
    assert np.isnan(result.outlet_stream.pressure[0])


def test_calculate_single_speed_compressor_stage_given_target_discharge_pressure(
    single_speed_compressor_train_common_shaft,
    fluid_model_medium,
    fluid_factory_medium,
):
    inlet_pressure_train_bara = 80.0
    target_outlet_pressure = 130
    mass_rate_kg_per_hour = 200000.0
    compressor_train = single_speed_compressor_train_common_shaft(
        fluid_model=fluid_model_medium, pressure_control=FixedSpeedPressureControl.DOWNSTREAM_CHOKE
    )

    compressor_train.set_evaluation_input(
        fluid_factory=fluid_factory_medium, rate=1, suction_pressure=1, discharge_pressure=2
    )  # dummy values for rates and pressures, only need fluid factory

    stage: CompressorTrainStage = compressor_train.stages[0]
    inlet_stream_stage = compressor_train._fluid_factory.create_stream_from_mass_rate(
        pressure_bara=inlet_pressure_train_bara,
        temperature_kelvin=stage.inlet_temperature_kelvin,
        mass_rate_kg_per_h=mass_rate_kg_per_hour,
    )

    result = stage.evaluate_given_speed_and_target_discharge_pressure(
        inlet_stream_stage=inlet_stream_stage,
        target_discharge_pressure=target_outlet_pressure,
    )
    np.testing.assert_allclose(result.outlet_stream.pressure_bara, target_outlet_pressure, rtol=0.01)


def test_single_speed_compressor_train_vs_unisim_methane(single_speed_compressor_train_unisim_methane):
    compressor_train = single_speed_compressor_train_unisim_methane
    fluid_factory = NeqSimFluidFactory(FluidModel(composition=FluidComposition(methane=1.0), eos_model=EoSModel.SRK))
    compressor_train.set_evaluation_input(
        fluid_factory=fluid_factory,
        rate=np.asarray([5305771.971, 3890899.445, 6013208.233, 5305771.971, 5305771.971]),
        suction_pressure=np.asarray([40, 40, 40, 35, 60]),
        discharge_pressure=np.asarray([200, 200, 200, 200, 200]),  # Dummy values.
    )
    result = compressor_train.evaluate()

    expected_power = np.array([7.577819961, 6.440134787, 7.728668854, 6.687897402, 9.620088576])

    # Note: Given data was meter liquid column. We need to compare against kJ/kg
    # expected_head = Unit.POLYTROPIC_HEAD_METER_LIQUID_COLUMN.to(Unit.POLYTROPIC_HEAD_KILO_JOULE_PER_KG)(
    #     np.array([16129.34382, 15530.2335, 15595.82912, 17449.38821, 8944.004374])
    # )
    expected_efficiency = np.array([0.723876159, 0.7469255823, 0.7254063622, 0.7449794342, 0.7090675589])  # [-]
    expected_act_gas_rate = np.array([5305.395, 3890.623, 6012.781, 6115.773, 3422.705])  # [m3/h]
    expected_inlet_temperature = np.array([20, 20, 20, 20, 20]) + 273.15  # [K]
    expected_inlet_mass_rate = np.array([150000, 110000, 170000, 150000, 150000])  # [kg/h]
    expected_inlet_mass_density = np.array([28.27311, 28.27311, 28.27311, 24.52675, 43.82499])  # [kg/m3]
    expected_inlet_z = np.array([0.931221, 0.931221, 0.931221, 0.939278, 0.901147065266633])  # [-]
    # expected_inlet_kappa = np.array([1.44187, 1.44187, 1.44187, 1.42216, 1.52606])  # [-]
    # expected_outlet_mass_density = np.array([48.40811, 50.49946, 44.97294, 38.62820, 72.89670])  # [kg/m3]
    # expected_outlet_kappa = np.array([1.39929, 1.38925, 1.40124, 1.38569, 1.42486])  # [-]
    expected_outlet_temperature = np.array([103.43398, 115.16061, 95.05306341, 93.22515, 122.12128]) + 273.15  # [K]
    expected_outlet_pressure = np.array([91.33181, 98.96722, 82.60081, 70.74829, 146.64472])  # [bar]

    energy_result = result.get_energy_result()
    np.testing.assert_allclose(energy_result.power.values, expected_power, rtol=0.05)

    np.testing.assert_allclose(result.inlet_stream_condition.actual_rate_m3_per_hr, expected_act_gas_rate, rtol=0.05)
    np.testing.assert_allclose(result.inlet_stream.temperature_kelvin, expected_inlet_temperature, rtol=0.05)
    np.testing.assert_allclose(result.mass_rate_kg_per_hr, expected_inlet_mass_rate, rtol=0.05)
    np.testing.assert_allclose(result.inlet_stream.density_kg_per_m3, expected_inlet_mass_density, rtol=0.05)
    np.testing.assert_allclose(result.inlet_stream.z, expected_inlet_z, rtol=0.05)
    # np.testing.assert_allclose(result.inlet_kappa, expected_inlet_kappa, rtol=0.05)
    # np.testing.assert_allclose(result.outlet_density_kg_per_m3, expected_outlet_mass_density, rtol=0.05)
    # np.testing.assert_allclose(result.outlet_kappa, expected_outlet_kappa, rtol=0.16)
    np.testing.assert_allclose(result.outlet_stream.temperature_kelvin, expected_outlet_temperature, rtol=0.05)
    np.testing.assert_allclose(result.outlet_stream.pressure, expected_outlet_pressure, rtol=0.05)

    # np.testing.assert_allclose(result.polytropic_head_kJ_per_kg, expected_head, rtol=0.01)  # Test is failing
    np.testing.assert_allclose(result.stage_results[0].polytropic_efficiency, expected_efficiency, rtol=0.05)


def test_points_above_and_below_maximum_power(
    single_speed_compressor_train_common_shaft, fluid_model_medium, fluid_factory_medium
):
    compressor_train = single_speed_compressor_train_common_shaft(
        fluid_model=fluid_model_medium, pressure_control=FixedSpeedPressureControl.DOWNSTREAM_CHOKE, maximum_power=4.5
    )
    compressor_train.set_evaluation_input(
        fluid_factory=fluid_factory_medium,
        rate=np.asarray([1800000, 2200000]),
        suction_pressure=np.asarray([30, 30]),
        discharge_pressure=np.asarray([80.0, 80.0]),
    )
    result = compressor_train.evaluate()
    energy_result = result.get_energy_result()
    is_valid = energy_result.is_valid
    assert is_valid[1]
    assert not is_valid[0]
    assert result.failure_status[1] == CompressorTrainCommonShaftFailureStatus.NO_FAILURE
    assert result.failure_status[0] == CompressorTrainCommonShaftFailureStatus.ABOVE_MAXIMUM_POWER


class TestCompressorTrainCommonShaftOneRateTwoPressures:
    def test_single_point_within_capacity_one_compressor(self, variable_speed_compressor_train, fluid_factory_medium):
        compressor_train = variable_speed_compressor_train()
        compressor_train.set_evaluation_input(
            fluid_factory=fluid_factory_medium,
            rate=np.asarray([7000]),
            suction_pressure=np.asarray([30]),
            discharge_pressure=np.asarray([100.0]),
        )
        result = compressor_train.evaluate()
        assert result.mass_rate_kg_per_hr[0] == pytest.approx(240.61266437085808)
        assert result.outlet_stream.pressure[0] == pytest.approx(100.00000000000007)
        assert result.inlet_stream.density_kg_per_m3[0] == pytest.approx(24.888039288426715)

        assert result.get_energy_result().power.values[0] == pytest.approx(6.889951698413056)

    def test_points_above_and_below_maximum_power(self, variable_speed_compressor_train, fluid_factory_medium):
        compressor_train = variable_speed_compressor_train(maximum_power=7.0)
        compressor_train.set_evaluation_input(
            fluid_factory=fluid_factory_medium,
            rate=np.asarray([3000000, 3500000]),
            suction_pressure=np.asarray([30, 30]),
            discharge_pressure=np.asarray([100.0, 100.0]),
        )
        result = compressor_train.evaluate()

        assert result.failure_status[0] == CompressorTrainCommonShaftFailureStatus.NO_FAILURE
        assert result.failure_status[1] == CompressorTrainCommonShaftFailureStatus.ABOVE_MAXIMUM_POWER

        is_valid = result.get_energy_result().is_valid
        assert is_valid[0]
        assert not is_valid[1]

    def test_single_point_rate_too_high_no_pressure_control(
        self, variable_speed_compressor_train, fluid_factory_medium
    ):
        """When the rate is too high then the compressor normally will need to adjust the head up in order to be able to
        handle the high rate. This results in too high pressure and will normally be choked upstreams or downstreams.

        In some cases we don't have this mechanism, and we want the train to fail instead.
        """
        target_pressure = 35.0  # Low target discharge pressure normally forces downstream choke.
        compressor_train = variable_speed_compressor_train(pressure_control=None)
        compressor_train.set_evaluation_input(
            fluid_factory=fluid_factory_medium,
            rate=np.asarray([7000]),
            suction_pressure=np.asarray([30]),
            discharge_pressure=np.asarray([target_pressure]),
        )
        result = compressor_train.evaluate()
        assert not np.any(result.pressure_is_choked)
        assert result.failure_status[0] == CompressorTrainCommonShaftFailureStatus.TARGET_DISCHARGE_PRESSURE_TOO_LOW

        assert not np.any(result.get_energy_result().is_valid)

    def test_single_point_recirculate_on_minimum_speed_curve_one_compressor(
        self, variable_speed_compressor_train, fluid_model_medium
    ):
        fluid_factory = NeqSimFluidFactory(fluid_model=fluid_model_medium)
        compressor_train = variable_speed_compressor_train(
            pressure_control=FixedSpeedPressureControl.INDIVIDUAL_ASV_RATE
        )
        compressor_train.set_evaluation_input(
            fluid_factory=fluid_factory,
            rate=np.asarray([1500000]),
            suction_pressure=np.asarray([30]),
            discharge_pressure=np.asarray([55.0]),
        )
        result = compressor_train.evaluate()

        np.testing.assert_allclose(result.mass_rate_kg_per_hr[0], 51559.9, rtol=0.001)
        np.testing.assert_allclose(result.outlet_stream.pressure[0], 55.0, rtol=0.001)
        np.testing.assert_allclose(result.inlet_stream.density_kg_per_m3[0], 24.888, rtol=0.001)

        np.testing.assert_allclose(result.get_energy_result().power.values[0], 2.5070, rtol=0.001)

    def test_zero_rate_zero_pressure(self, variable_speed_compressor_train, fluid_model_medium):
        """We want to get a result object when rate is zero regardless of invalid/zero pressures. To ensure
        this we set pressure -> 1 when both rate and pressure is zero. This may happen when pressure is a function
        of rate.
        """
        fluid_factory = NeqSimFluidFactory(fluid_model=fluid_model_medium)
        compressor_train = variable_speed_compressor_train()
        compressor_train.set_evaluation_input(
            fluid_factory=fluid_factory,
            rate=np.array([0, 1, 1]),
            suction_pressure=np.array([0, 1, 1]),
            discharge_pressure=np.array([0, 2, 2]),
        )
        result = compressor_train.evaluate()

        # Ensuring that first stage returns zero energy usage and no failure (zero rate should always be valid).
        assert result.failure_status == [
            CompressorTrainCommonShaftFailureStatus.NO_FAILURE,
            CompressorTrainCommonShaftFailureStatus.NO_FAILURE,
            CompressorTrainCommonShaftFailureStatus.NO_FAILURE,
        ]

        assert np.isnan(result.mass_rate_kg_per_hr[0])
        assert np.isnan(result.inlet_stream.pressure[0])
        assert np.isnan(result.outlet_stream.pressure[0])

        energy_result = result.get_energy_result()
        np.testing.assert_allclose(energy_result.energy_usage.values, np.array([0.0, 0.092847, 0.092847]), rtol=0.0001)
        assert energy_result.power.values[0] == 0
        assert energy_result.is_valid == [True, True, True]

    def test_single_point_within_capacity_one_compressor_add_constant(
        self, variable_speed_compressor_train, fluid_model_medium
    ):
        compressor_train = variable_speed_compressor_train()
        compressor_train_adjusted = variable_speed_compressor_train(energy_adjustment_constant=10)
        energy_usage_adjustment_constant = 10
        fluid_factory = NeqSimFluidFactory(fluid_model=fluid_model_medium)

        compressor_train.set_evaluation_input(
            fluid_factory=fluid_factory,
            rate=np.asarray([3000000]),
            suction_pressure=np.asarray([30]),
            discharge_pressure=np.asarray([100.0]),
        )
        result_comparison = compressor_train.evaluate()

        compressor_train_adjusted.set_evaluation_input(
            fluid_factory=fluid_factory,
            rate=np.asarray([3000000]),
            suction_pressure=np.asarray([30]),
            discharge_pressure=np.asarray([100.0]),
        )
        result = compressor_train_adjusted.evaluate()

        energy_result = result.get_energy_result()
        energy_result_comparison = result_comparison.get_energy_result()

        np.testing.assert_allclose(
            np.asarray(energy_result_comparison.energy_usage.values) + energy_usage_adjustment_constant,
            energy_result.energy_usage.values,
            rtol=0.01,
        )

    def test_single_point_downstream_choke(
        self,
        variable_speed_compressor_train,
        fluid_factory_medium,
    ):
        # Testing internal point and ensure that choking is working correctly using DOWNSTREAM CHOKE (default)
        compressor_train = variable_speed_compressor_train()
        compressor_train.set_evaluation_input(
            fluid_factory=fluid_factory_medium,
            rate=np.asarray([3000000]),
            suction_pressure=np.asarray([30]),
            discharge_pressure=np.asarray([40.0]),
        )
        result = compressor_train.evaluate()

        assert result.outlet_stream.pressure[0] == 40
        np.testing.assert_allclose(result.stage_results[-1].outlet_stream_condition.pressure, 51, atol=1)
        assert result.stage_results[0].chart_area_flags[0] == ChartAreaFlag.INTERNAL_POINT

        assert all(result.get_energy_result().is_valid)


def test_find_fixed_shaft_speed_given_constraints():
    func = CompressorTrainCommonShaft.find_fixed_shaft_speed_given_constraints
    assert func
    # Depends on test case with real data to make sense
    # Will be done after asset test case is established


def test_calculate_compressor_train_given_speed_invalid(variable_speed_compressor_train, fluid_factory_medium):
    compressor_train = variable_speed_compressor_train()
    compressor_train.set_evaluation_input(
        fluid_factory=fluid_factory_medium, rate=1, suction_pressure=1, discharge_pressure=2
    )  # dummy values for rates and pressures, only need fluid factory

    compressor_train.shaft.set_speed(1)
    with pytest.raises(IllegalStateException):
        _ = compressor_train.calculate_compressor_train(
            constraints=CompressorTrainEvaluationInput(
                suction_pressure=50,
                rate=compressor_train._fluid_factory.mass_rate_to_standard_rate(6000000.0),
            )
        )


def test_find_and_calculate_for_compressor_shaft_speed_given_rate_ps_pd_invalid_point(
    process_simulator_variable_compressor_chart,
    fluid_factory_medium,
    variable_speed_compressor_train,
    compressor_stages,
):
    mass_rate_kg_per_hour = 6000000

    compressor_train = variable_speed_compressor_train(
        stages=compressor_stages(
            inlet_temperature_kelvin=293.15,
            nr_stages=2,
            chart_data=process_simulator_variable_compressor_chart,
        )
    )

    compressor_train.set_evaluation_input(
        fluid_factory=fluid_factory_medium, rate=1, suction_pressure=1, discharge_pressure=2
    )  # dummy values for rates and pressures, only need fluid factory

    standard_rate = compressor_train._fluid_factory.mass_rate_to_standard_rate(mass_rate_kg_per_hour)
    # rate too large
    result = compressor_train.evaluate_given_constraints(
        constraints=CompressorTrainEvaluationInput(
            rate=standard_rate,
            suction_pressure=20,
            discharge_pressure=400,
        )
    )
    assert result.chart_area_status == ChartAreaFlag.ABOVE_MAXIMUM_FLOW_RATE

    # Target pressure too large, but rate still too high
    result = compressor_train.evaluate_given_constraints(
        constraints=CompressorTrainEvaluationInput(
            rate=standard_rate,
            suction_pressure=20,
            discharge_pressure=1000,
        )
    )
    assert result.failure_status == CompressorTrainCommonShaftFailureStatus.ABOVE_MAXIMUM_FLOW_RATE

    # Target pressure too low -> but still possible because of downstream choke. However, the rate is still too high.
    result = compressor_train.evaluate_given_constraints(
        constraints=CompressorTrainEvaluationInput(
            rate=standard_rate,
            suction_pressure=20,
            discharge_pressure=1,
        )
    )
    assert result.chart_area_status == ChartAreaFlag.ABOVE_MAXIMUM_FLOW_RATE
    assert not result.is_valid

    # Rate is too large, but point is below stonewall, i.e. rate is too large for resulting speed, but not too large
    # for maximum speed
    result = compressor_train.evaluate_given_constraints(
        constraints=CompressorTrainEvaluationInput(
            rate=standard_rate,
            suction_pressure=20,
            discharge_pressure=600,
        )
    )
    assert result.chart_area_status == ChartAreaFlag.ABOVE_MAXIMUM_FLOW_RATE

    # Point where rate is recirculating
    result = compressor_train.evaluate_given_constraints(
        constraints=CompressorTrainEvaluationInput(
            rate=1,
            suction_pressure=20,
            discharge_pressure=400,
        )
    )
    # Check that actual rate is equal to minimum rate for the speed
    assert result.stage_results[0].inlet_actual_rate_asv_corrected_m3_per_hour == pytest.approx(
        compressor_train.stages[0].compressor.compressor_chart.minimum_rate_as_function_of_speed(result.speed)
    )
    assert result.chart_area_status == ChartAreaFlag.BELOW_MINIMUM_FLOW_RATE


def test_variable_speed_compressor_train_vs_unisim_methane(variable_speed_compressor_train_unisim_methane):
    compressor_train = variable_speed_compressor_train_unisim_methane
    fluid_factory = NeqSimFluidFactory(FluidModel(composition=FluidComposition(methane=1), eos_model=EoSModel.SRK))

    compressor_train.set_evaluation_input(
        fluid_factory=fluid_factory,
        rate=np.asarray([3537181, 5305772, 6720644, 5305772, 5305772]),
        suction_pressure=np.asarray([40, 40, 40, 40, 40]),
        discharge_pressure=np.asarray([100, 100, 100, 110, 70]),
    )
    result = compressor_train.evaluate()

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

    energy_result = result.get_energy_result()
    np.testing.assert_allclose(energy_result.power.values, expected_power, rtol=0.07)

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


def test_adjustment_constant_and_factor_one_compressor(variable_speed_compressor_train, fluid_factory_medium):
    adjustment_constant = 10
    adjustment_factor = 1.5

    compressor_train = variable_speed_compressor_train()
    compressor_train_adjusted = variable_speed_compressor_train(
        energy_adjustment_constant=adjustment_constant, energy_adjustment_factor=adjustment_factor
    )

    compressor_train.set_evaluation_input(
        fluid_factory=fluid_factory_medium,
        rate=np.asarray([7000]),
        suction_pressure=np.asarray([30]),
        discharge_pressure=np.asarray([100.0]),
    )
    result = compressor_train.evaluate()

    compressor_train_adjusted.set_evaluation_input(
        fluid_factory=fluid_factory_medium,
        rate=np.asarray([7000]),
        suction_pressure=np.asarray([30]),
        discharge_pressure=np.asarray([100.0]),
    )
    result_adjusted = compressor_train_adjusted.evaluate()

    energy_result_adjusted = result_adjusted.get_energy_result()
    energy_result = result.get_energy_result()

    assert energy_result_adjusted.power.values[0] == energy_result.power.values[0] * 1.5 + adjustment_constant


def test_get_max_standard_rate_with_and_without_maximum_power(variable_speed_compressor_train, fluid_factory_medium):
    compressor_train = variable_speed_compressor_train()
    compressor_train_max_power = variable_speed_compressor_train(maximum_power=7.0)

    compressor_train.set_evaluation_input(
        fluid_factory=fluid_factory_medium, rate=1, suction_pressure=30, discharge_pressure=100
    )
    compressor_train_max_power.set_evaluation_input(
        fluid_factory=fluid_factory_medium, rate=1, suction_pressure=30, discharge_pressure=100
    )

    max_standard_rate_without_maximum_power = compressor_train.get_max_standard_rate(
        suction_pressures=np.asarray([30]),
        discharge_pressures=np.asarray([100]),
    )
    max_standard_rate_with_maximum_power = compressor_train_max_power.get_max_standard_rate(
        suction_pressures=np.asarray([30]),
        discharge_pressures=np.asarray([100]),
    )
    compressor_train.set_evaluation_input(
        fluid_factory=fluid_factory_medium,
        rate=np.asarray([max_standard_rate_without_maximum_power], dtype=float),
        suction_pressure=np.asarray([30], dtype=float),
        discharge_pressure=np.asarray([100], dtype=float),
    )
    power_at_max_standard_rate_without_maximum_power = compressor_train.evaluate().get_energy_result().power.values

    compressor_train_max_power.set_evaluation_input(
        fluid_factory=fluid_factory_medium,
        rate=np.asarray([max_standard_rate_with_maximum_power], dtype=float),
        suction_pressure=np.asarray([30], dtype=float),
        discharge_pressure=np.asarray([100], dtype=float),
    )
    power_at_max_standard_rate_with_maximum_power = (
        compressor_train_max_power.evaluate().get_energy_result().power.values
    )

    assert max_standard_rate_without_maximum_power > max_standard_rate_with_maximum_power
    assert power_at_max_standard_rate_without_maximum_power > power_at_max_standard_rate_with_maximum_power
    assert power_at_max_standard_rate_with_maximum_power[0] < compressor_train_max_power.maximum_power
