import math

import pytest

from ecalc_neqsim_wrapper.thermo import NeqsimFluid
from libecalc.process.fluid_stream.fluid_model import FluidComposition

INLET_FLUID_COMPOSITION = FluidComposition(
    nitrogen=6.78e-03,
    CO2=5.74e-03,
    methane=0.795667071,
    ethane=9.82e-02,
    propane=5.95e-02,
    i_butane=6.25e-03,
    n_butane=1.60e-02,
    i_pentane=3.23e-03,
    n_pentane=4.20e-03,
    n_hexane=9.11e-08,
    water=3.69e-03,
)

OUTLET_FLUID_COMPOSITION = FluidComposition(
    nitrogen=6.79e-03,
    CO2=5.75e-03,
    methane=0.797181663,
    ethane=0.098415785,
    propane=5.96e-02,
    i_butane=6.26e-03,
    n_butane=1.60e-02,
    i_pentane=3.24e-03,
    n_pentane=4.21e-03,
    n_hexane=9.13e-08,
    water=1.79e-03,
)


@pytest.fixture
def inlet_fluid() -> NeqsimFluid:
    """Inlet liquid to test liquids takeoff compared to UniSim.

    Inlet conditions before compressor:
        Pressure [kPa]	1700	kPa
        Temperature [C]	36	C
        Mass Density [kg/m3]	14,50851117	kg/m3
        Std. Gas Flow [STD_m3/h]	119650,326	Sm3/h

    Compressor outlet before cooling:
        Pressure [kPa]	4547,67395	kPa
        Temperature [C]	136,2978138	C
        Mass Density [kg/m3]	29,10805814	kg/m3

    Cooling and liquid takeoff:
        Delta P	220	kPa
        Temperature outlet[C]	38	C

    Final conditions:
        Pressure [kPa]	4327,67395	kPa
        Temperature [C]	38	C
        Mass Density [kg/m3]	39,93055581	kg/m3

    Final conditions:
        Pressure [kPa]	4327,67395	kPa
        Temperature [C]	38	C
        Mass Density [kg/m3]	39,93055581	kg/m3

    See outlet fluid below.
    """
    return NeqsimFluid.create_thermo_system(
        composition=INLET_FLUID_COMPOSITION, temperature_kelvin=36.0 + 273.15, pressure_bara=1700 / 100
    )


@pytest.fixture
def outlet_fluid() -> NeqsimFluid:
    """Inlet liquid to test liquids takeoff compared to UniSim. see inlet conditions above."""
    return NeqsimFluid.create_thermo_system(
        composition=OUTLET_FLUID_COMPOSITION, temperature_kelvin=38 + 273.15, pressure_bara=4327.67395 / 100
    )


def test_liquid_takeoff(inlet_fluid, outlet_fluid) -> None:
    """Integration testing compare against UniSim test case. See specifications above in inlet and outlet liquids.
    :param inlet_fluid:
    :param outlet_fluid:
    :return:
    """
    assert inlet_fluid.pressure_bara == 1700 / 100
    assert inlet_fluid.temperature_kelvin == 36.0 + 273.15
    assert math.isclose(inlet_fluid.density, 14.343437, rel_tol=0.01)  # 1 % tolerance

    fluid_after_compressor = inlet_fluid.set_new_pressure_and_temperature(
        new_pressure_bara=4547.67395 / 100,
        new_temperature_kelvin=136.298 + 273.15,  # kPa to bara  # Celsius to Kelvin
    )

    assert fluid_after_compressor.pressure_bara == 4547.67395 / 100
    assert fluid_after_compressor.temperature_kelvin == 136.298 + 273.15
    assert math.isclose(fluid_after_compressor.density, 29.10806, rel_tol=0.02)  # 2 % tolerance

    fluid_after_cooler = fluid_after_compressor.set_new_pressure_and_temperature(
        new_pressure_bara=4327.67395 / 100,  # kPa to bara
        new_temperature_kelvin=38 + 273.15,  # Celsius to Kelvin
    ).clone_gas_phase()

    assert fluid_after_cooler.pressure_bara == 4327.67395 / 100
    assert fluid_after_cooler.temperature_kelvin == 38 + 273.15

    fluid_after_liquid_takeoff = fluid_after_cooler.set_new_pressure_and_temperature(
        new_pressure_bara=4327.67395 / 100,  # kPa to bara
        new_temperature_kelvin=38 + 273.15,  # Celsius to Kelvin
    ).clone_gas_phase()

    assert fluid_after_liquid_takeoff.pressure_bara == 4327.67395 / 100
    assert fluid_after_liquid_takeoff.temperature_kelvin == 38 + 273.15
    assert math.isclose(fluid_after_liquid_takeoff.density, 39.93055581, rel_tol=0.03)  # 3 % tolerance

    """
    Asserting that the fluid after compressor, cooling and liquid takeoff is approximately the same
    as the fluid that we expect to get according to UniSim.
    """
    assert math.isclose(outlet_fluid.density, fluid_after_liquid_takeoff.density, rel_tol=0.01)
    assert math.isclose(outlet_fluid.pressure_bara, fluid_after_liquid_takeoff.pressure_bara, rel_tol=0.01)
    assert math.isclose(outlet_fluid.molar_mass, fluid_after_liquid_takeoff.molar_mass, rel_tol=0.01)
    assert math.isclose(
        outlet_fluid.enthalpy_joule_per_kg, fluid_after_liquid_takeoff.enthalpy_joule_per_kg, rel_tol=0.02
    )


# Propane-rich composition that is ~97% liquid at the probe (P, T) below.
DENSE_LIQUID_COMPOSITION = FluidComposition(
    water=0.003,
    nitrogen=2.447,
    CO2=0.64,
    methane=41.91,
    ethane=19.9,
    propane=24.29,
    i_butane=3.64,
    n_butane=5.40,
    i_pentane=0.83,
    n_pentane=0.68,
    n_hexane=0.26,
).normalized()


def test_clone_gas_phase_returns_initialized_properties() -> None:
    """clone_gas_phase() on a two-phase fluid must return properties matching a clean PT-flash of the gas-only composition."""
    two_phase = NeqsimFluid.create_thermo_system(
        composition=DENSE_LIQUID_COMPOSITION,
        temperature_kelvin=301.45,
        pressure_bara=91.476,
    )
    assert two_phase.vapor_fraction_molar < 0.1, (
        f"Test precondition: expected mostly-liquid state, got vap={two_phase.vapor_fraction_molar}"
    )

    gas_only = two_phase.clone_gas_phase()

    assert math.isclose(gas_only.vapor_fraction_molar, 1.0, rel_tol=1e-3)
    # Uninitialized systems return the sentinel kappa==1.0.
    assert gas_only.kappa > 1.02, f"Suspicious kappa (uninitialized?): {gas_only.kappa}"

    reference = NeqsimFluid.create_thermo_system(
        composition=gas_only.composition,
        temperature_kelvin=gas_only.temperature_kelvin,
        pressure_bara=gas_only.pressure_bara,
    )
    assert math.isclose(gas_only.kappa, reference.kappa, rel_tol=1e-3)
    assert math.isclose(gas_only.z, reference.z, rel_tol=1e-3)
    assert math.isclose(gas_only.density, reference.density, rel_tol=1e-3)
    assert math.isclose(gas_only.enthalpy_joule_per_kg, reference.enthalpy_joule_per_kg, rel_tol=1e-3)
