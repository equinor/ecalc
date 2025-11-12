import numpy as np
import pytest
from pytest import approx

from ecalc_neqsim_wrapper.thermo import STANDARD_PRESSURE_BARA, STANDARD_TEMPERATURE_KELVIN
from libecalc.common.units import Unit
from libecalc.domain.process.compressor.core.train.simplified_train.simplified_train import CompressorTrainSimplified
from libecalc.domain.process.compressor.core.train.utils.enthalpy_calculations import (
    calculate_enthalpy_change_head_iteration,
)
from libecalc.domain.process.value_objects.fluid_stream.fluid_model import EoSModel, FluidComposition, FluidModel
from libecalc.infrastructure.neqsim_fluid_provider.neqsim_fluid_factory import NeqSimFluidFactory


@pytest.fixture
def unisim_test_data():
    """A test dataset from UniSim."""

    class Data:
        pass

    eos_model = EoSModel.SRK  # Without Lee-Kesler, EOS used for density, default binary coefficients
    composition = FluidComposition(
        nitrogen=20.1144855057,
        CO2=124.0132106862,
        methane=2674.1347020545,
        ethane=314.2057395578,
        propane=158.2739490708,
        i_butane=19.4049633148,
        n_butane=36.0026629855,
        i_pentane=9.6324615860,
        n_pentane=10.1845634277,
    )
    fluid_factory = NeqSimFluidFactory(
        fluid_model=FluidModel(
            eos_model=eos_model,
            composition=composition,
        )
    )
    train_fluid_stream = fluid_factory.create_stream_from_mass_rate(
        pressure_bara=STANDARD_PRESSURE_BARA,
        temperature_kelvin=STANDARD_TEMPERATURE_KELVIN,
        mass_rate_kg_per_h=1.0,  # Default mass rate for the factory stream
    )
    fluid_thermo_system = fluid_factory.create_thermo_system(
        pressure_bara=STANDARD_PRESSURE_BARA,
        temperature_kelvin=STANDARD_TEMPERATURE_KELVIN,
    )
    external_software_density_at_std_cond = 0.8824

    input_stream_data = Data()
    input_stream_data.fluid_thermo_system = fluid_thermo_system
    input_stream_data.fluid_factory = fluid_factory
    input_stream_data.train_fluid_stream = train_fluid_stream
    input_stream_data.temperatures = Unit.CELSIUS.to(Unit.KELVIN)(np.asarray([30.0, 30.0, 30, 15, 50, 50]))
    input_stream_data.pressures = np.asarray([18.0, 30.0, 40, 40, 115, 200])  # bar
    input_stream_data.mass_rate = np.asarray([70000.0, 70000.0, 120000, 120000, 120000, 120000])  # kg/hr
    input_stream_data.actual_volume_rate = np.asarray(
        [4488.636, 2604.429, 3255.251, 3013.698, 1096.047, 632.988]
    )  # Am3/h
    input_stream_data.z_factor = np.asarray([0.9523, 0.9210, 0.8953, 0.8720, 0.8130, 0.8166])
    input_stream_data.density = np.asarray([15.59, 26.88, 36.86, 39.82, 109.5, 189.6])

    output_stream_data = Data()
    output_stream_data.temperatures = Unit.CELSIUS.to(Unit.KELVIN)(
        np.asarray([111.8, 64.87, 145.8, 127.9, 161.5, 102.6])
    )
    output_stream_data.pressures = np.asarray([45.0, 45.0, 140, 140, 400, 400])  # bar
    output_stream_data.mass_rate = np.asarray([70000.0, 70000.0, 120000, 120000, 120000, 120000])  # kg/hr
    output_stream_data.actual_volume_rate = np.asarray(
        [2297.721, 1948.580, 1376.213, 1292.506, 581.682, 488.200]
    )  # Am3/h
    output_stream_data.z_factor = np.asarray([0.9599, 0.9260, 0.9585, 0.9405, 1.116, 1.083])
    output_stream_data.density = np.asarray([30.46, 35.92, 87.20, 92.84, 206.3, 245.8])

    compressor_data = Data()
    compressor_data.polytropic_heads_kJ_per_kg = np.asarray([119.9, 47.96, 165, 153.8, 177.3, 91.28])  # m
    compressor_data.polytropic_efficiency = 0.75
    compressor_data.power = np.asarray(
        [3.109, 1.244, 7.335, 6.834, 7.881, 4.057]
    )  # MW (With Lee-Kesler, the last value is 3.873)

    pressure_ratio = output_stream_data.pressures / input_stream_data.pressures
    output_data = Data()
    output_data.fluid_thermo_system = fluid_thermo_system
    output_data.fluid_factory = fluid_factory
    output_data.external_software_density_at_std_cond = external_software_density_at_std_cond
    output_data.input_stream_data = input_stream_data
    output_data.output_stream_data = output_stream_data
    output_data.compressor_data = compressor_data
    output_data.pressure_ratio = pressure_ratio
    return output_data


def test_fluid_density_at_standard_conditions(unisim_test_data):
    assert unisim_test_data.fluid_thermo_system.standard_density_gas_phase_after_flash == approx(
        unisim_test_data.external_software_density_at_std_cond, rel=1e-4
    )


def test_calculate_enthalpy_change_campbell_method(
    unisim_test_data,
):
    """Test the campbell method using a test case from UniSim."""
    suction_pressures = unisim_test_data.input_stream_data.pressures
    inlet_temperatures_kelvin = unisim_test_data.input_stream_data.temperatures
    mass_rates = unisim_test_data.input_stream_data.mass_rate
    inlet_streams = [
        unisim_test_data.fluid_factory.create_stream_from_mass_rate(
            pressure_bara=suction_pressure,
            temperature_kelvin=inlet_temperature,
            mass_rate_kg_per_h=mass_rate,
        )
        for suction_pressure, inlet_temperature, mass_rate in zip(
            suction_pressures, inlet_temperatures_kelvin, mass_rates
        )
    ]
    discharge_pressure = unisim_test_data.output_stream_data.pressures

    polytropic_enthalpy_change_joule_per_kg, _ = calculate_enthalpy_change_head_iteration(
        inlet_streams=inlet_streams,
        outlet_pressure=discharge_pressure,
        polytropic_efficiency_vs_rate_and_head_function=lambda x, y: np.full_like(x, fill_value=0.75),
    )

    expected_enthalpy_change_joule_per_kg = (unisim_test_data.compressor_data.polytropic_heads_kJ_per_kg / 0.75) * 1000
    np.testing.assert_allclose(
        polytropic_enthalpy_change_joule_per_kg, expected_enthalpy_change_joule_per_kg, rtol=0.03
    )


def test_simplified_compressor_train_compressor_stage_work(
    unisim_test_data, compressor_stage_factory, chart_data_factory
):
    """Integration test of Simplified Compressor Train one stage.

    Note: Consider to delete this test. We are testing enthalpy change only, but we use Simplified compressor train
        as a test proxy. See test_calculate_enthalpy_change_campbell_method above for what we actually test here...
    """

    stages = [
        compressor_stage_factory(
            inlet_temperature_kelvin=temperature,
            compressor_chart_data=chart_data_factory.from_design_point(
                efficiency=unisim_test_data.compressor_data.polytropic_efficiency,
                head=1,  # Dummy value
                rate=1,  # Dummy value
            ),
            remove_liquid_after_cooling=True,
        )
        for temperature in unisim_test_data.input_stream_data.temperatures
    ]

    results = []
    for suction_pressure, mass_rate, pressure_ratio, temperature, stage in zip(
        unisim_test_data.input_stream_data.pressures,
        unisim_test_data.input_stream_data.mass_rate,
        unisim_test_data.pressure_ratio,
        unisim_test_data.input_stream_data.temperatures,
        stages,
    ):
        inlet_stream = unisim_test_data.fluid_factory.create_stream_from_mass_rate(
            pressure_bara=suction_pressure,
            temperature_kelvin=temperature,
            mass_rate_kg_per_h=mass_rate,
        )
        result = stage.evaluate_given_target_pressure_ratio(
            target_pressure_ratio=pressure_ratio,
            inlet_stream=inlet_stream,
            adjust_for_chart=False,
        )
        results.append(result)

    # Check some inlet results (thermodynamic checks)
    np.testing.assert_allclose(
        actual=[time_step.inlet_pressure for time_step in results],
        desired=unisim_test_data.input_stream_data.pressures,
    )
    np.testing.assert_allclose(
        actual=[time_step.inlet_stream.density for time_step in results],
        desired=unisim_test_data.input_stream_data.density,
        rtol=0.02,
    )
    np.testing.assert_allclose(
        actual=[time_step.inlet_actual_rate_m3_per_hour for time_step in results],
        desired=unisim_test_data.input_stream_data.actual_volume_rate,
        rtol=0.02,
    )
    np.testing.assert_allclose(
        actual=[time_step.inlet_stream.z for time_step in results],
        desired=unisim_test_data.input_stream_data.z_factor,
        rtol=0.01,
    )

    # Check polytropic head and power (checking head/power calculations AND iteration of outlet z/kappa)
    np.testing.assert_allclose(
        actual=[time_step.polytropic_head_kJ_per_kg for time_step in results],
        desired=unisim_test_data.compressor_data.polytropic_heads_kJ_per_kg,
        rtol=0.03,
    )
    np.testing.assert_allclose(
        actual=[time_step.power_megawatt for time_step in results],
        desired=unisim_test_data.compressor_data.power,
        rtol=0.03,
    )
    np.testing.assert_allclose(
        actual=[time_step.outlet_stream.z for time_step in results],
        desired=unisim_test_data.output_stream_data.z_factor,
        rtol=0.01,
    )

    # Checking outlet stream results based on eCalc head/power/z/kappa calculations
    np.testing.assert_allclose(
        actual=[time_step.outlet_stream.density for time_step in results],
        desired=unisim_test_data.output_stream_data.density,
        rtol=0.02,
    )
    np.testing.assert_allclose(
        actual=[time_step.discharge_pressure for time_step in results],
        desired=unisim_test_data.output_stream_data.pressures,
        rtol=0.01,
    )
    np.testing.assert_allclose(
        actual=[time_step.outlet_stream.temperature_kelvin for time_step in results],
        desired=unisim_test_data.output_stream_data.temperatures,
        rtol=0.01,
    )


def test_fluid_streams(unisim_test_data):
    """Compare UniSim test case thermodynamic properties against eCalc (NeqSim)."""
    # Check outlet stream results given enthalpy change from external software
    inlet_streams = [
        unisim_test_data.fluid_factory.create_stream_from_mass_rate(
            pressure_bara=pressure,
            temperature_kelvin=temperature,
            mass_rate_kg_per_h=1,
        )
        for pressure, temperature in zip(
            unisim_test_data.input_stream_data.pressures,
            unisim_test_data.input_stream_data.temperatures,
        )
    ]

    compressor_data_enthalpy_change_joule_per_kg = (
        Unit.POLYTROPIC_HEAD_KILO_JOULE_PER_KG.to(Unit.POLYTROPIC_HEAD_JOULE_PER_KG)(
            unisim_test_data.compressor_data.polytropic_heads_kJ_per_kg
        )
        / unisim_test_data.compressor_data.polytropic_efficiency
    )

    outlet_streams_enthalpy = [
        s.create_stream_with_new_pressure_and_enthalpy_change(
            pressure_bara=unisim_test_data.output_stream_data.pressures[index],
            enthalpy_change_joule_per_kg=compressor_data_enthalpy_change_joule_per_kg[index],
        )
        for index, s in enumerate(inlet_streams)
    ]
    np.testing.assert_allclose(
        actual=[os.temperature_kelvin for os in outlet_streams_enthalpy],
        desired=unisim_test_data.output_stream_data.temperatures,
        rtol=0.01,
    )
    np.testing.assert_allclose(
        actual=[os.z for os in outlet_streams_enthalpy], desired=unisim_test_data.output_stream_data.z_factor, rtol=0.03
    )
    np.testing.assert_allclose(
        actual=[os.density for os in outlet_streams_enthalpy],
        desired=unisim_test_data.output_stream_data.density,
        rtol=0.02,
    )

    # Check outlet stream results given temperature change from external software
    outlet_streams_temperature = [
        unisim_test_data.fluid_factory.create_stream_from_mass_rate(
            pressure_bara=pressure,
            temperature_kelvin=temperature,
            mass_rate_kg_per_h=1,
        )
        for pressure, temperature in zip(
            unisim_test_data.output_stream_data.pressures,
            unisim_test_data.output_stream_data.temperatures,
        )
    ]

    np.testing.assert_allclose(
        actual=[os.temperature_kelvin for os in outlet_streams_temperature],
        desired=unisim_test_data.output_stream_data.temperatures,
        rtol=0.01,
    )
    np.testing.assert_allclose(
        actual=[os.z for os in outlet_streams_temperature],
        desired=unisim_test_data.output_stream_data.z_factor,
        rtol=0.02,
    )
    np.testing.assert_allclose(
        actual=[os.density for os in outlet_streams_temperature],
        desired=unisim_test_data.output_stream_data.density,
        rtol=0.02,
    )
