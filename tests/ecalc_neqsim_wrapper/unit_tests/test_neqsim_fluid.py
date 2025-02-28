import numpy as np
import pytest

from ecalc_neqsim_wrapper.thermo import NeqsimFluid, mix_neqsim_streams
from libecalc.common.fluid import EoSModel, FluidComposition


def test_gerg_properties(medium_fluid: NeqsimFluid, medium_fluid_with_gerg: NeqsimFluid) -> None:
    medium_fluid_np_ne = medium_fluid.set_new_pressure_and_enthalpy(
        new_pressure=20.0, new_enthalpy_joule_per_kg=medium_fluid.enthalpy_joule_per_kg + 10000
    )
    medium_fluid_with_gerg_np_ne = medium_fluid_with_gerg.set_new_pressure_and_enthalpy(
        new_pressure=20.0, new_enthalpy_joule_per_kg=medium_fluid_with_gerg.enthalpy_joule_per_kg + 10000
    )
    assert (
        medium_fluid_with_gerg_np_ne.enthalpy_joule_per_kg - medium_fluid_with_gerg.enthalpy_joule_per_kg
        == pytest.approx(10000)
    )
    assert medium_fluid_np_ne.enthalpy_joule_per_kg - medium_fluid.enthalpy_joule_per_kg == pytest.approx(10000)

    # Pinning properties to ensure stability:
    # Before flash
    assert np.isclose(medium_fluid_with_gerg.density, 0.8249053143219223)
    assert np.isclose(medium_fluid_with_gerg.z, 0.9971825132713872)
    assert np.isclose(medium_fluid_with_gerg.enthalpy_joule_per_kg, -21220.02998198086)
    assert np.isclose(medium_fluid_with_gerg._gerg_properties.kappa, 1.2719274851916846)

    # After flash
    assert np.isclose(medium_fluid_with_gerg_np_ne.density, 16.182809350995125)
    assert np.isclose(medium_fluid_with_gerg_np_ne.z, 0.9532768832922157)
    assert np.isclose(medium_fluid_with_gerg_np_ne.enthalpy_joule_per_kg, -11220.029982279037)
    assert np.isclose(medium_fluid_with_gerg_np_ne._gerg_properties.kappa, 1.2451895327851366)


def test_fluid_volume(heavy_fluid: NeqsimFluid) -> None:
    volume = heavy_fluid.volume
    assert isinstance(volume, float)
    assert np.isclose(volume, 30602.92725199961)  # Ensure stability in estimate


def test_fluid_density(heavy_fluid: NeqsimFluid) -> None:
    density = heavy_fluid.density
    assert isinstance(density, float)
    assert np.isclose(density, 0.9077408554479557)  # Ensure stability in estimate


def test_fluid_molar_mass(heavy_fluid: NeqsimFluid) -> None:
    molar_mass = heavy_fluid.molar_mass
    assert isinstance(molar_mass, float)
    assert np.isclose(molar_mass, 0.021386817219231927)  # Ensure stability in estimate


def test_fluid_z(heavy_fluid: NeqsimFluid) -> None:
    z = heavy_fluid.z
    assert isinstance(z, float)
    assert np.isclose(z, 0.9964957687029184)  # Ensure stability in estimate


def test_fluid_enthalpy_J_per_kg(heavy_fluid: NeqsimFluid) -> None:
    enthalpy_J_per_kg = heavy_fluid.enthalpy_joule_per_kg
    assert isinstance(enthalpy_J_per_kg, float)
    assert np.isclose(enthalpy_J_per_kg, 27371.14615258956)  # Ensure stability in estimate


def test_fluid_kappa(heavy_fluid: NeqsimFluid) -> None:
    kappa = heavy_fluid.kappa
    assert isinstance(kappa, float)
    assert np.isclose(kappa, 1.2502874504879609)  # Ensure stability in estimate


def test_fluid_temperature_kelvin(heavy_fluid: NeqsimFluid) -> None:
    temperature_kelvin = heavy_fluid.temperature_kelvin
    assert isinstance(temperature_kelvin, float)
    assert np.isclose(temperature_kelvin, 288.15)  # Ensure stability in estimate


def test_fluid_pressure_bara(heavy_fluid: NeqsimFluid) -> None:
    pressure_bara = heavy_fluid.pressure_bara
    assert isinstance(pressure_bara, float)
    assert np.isclose(pressure_bara, 1.01325)  # Ensure stability in estimate


def test_fluid_set_new_pressure_and_enthalpy(heavy_fluid: NeqsimFluid) -> None:
    """Testing the basic properties of enthalpy:

    H = U + pV

    Where
    H = enthalpy
    U = Internal energy
    p = pressure
    V = volume
    """
    fluid = heavy_fluid

    increase_enthalpy = fluid.set_new_pressure_and_enthalpy(
        new_pressure=fluid.pressure_bara, new_enthalpy_joule_per_kg=fluid.enthalpy_joule_per_kg * 2
    )

    decrease_enthalpy = fluid.set_new_pressure_and_enthalpy(
        new_pressure=fluid.pressure_bara, new_enthalpy_joule_per_kg=fluid.enthalpy_joule_per_kg / 2
    )

    increase_pressure = fluid.set_new_pressure_and_enthalpy(
        new_pressure=fluid.pressure_bara * 2, new_enthalpy_joule_per_kg=fluid.enthalpy_joule_per_kg
    )

    decrease_pressure = fluid.set_new_pressure_and_enthalpy(
        new_pressure=fluid.pressure_bara / 2, new_enthalpy_joule_per_kg=fluid.enthalpy_joule_per_kg
    )

    assert (
        increase_enthalpy.enthalpy_joule_per_kg > fluid.enthalpy_joule_per_kg > decrease_enthalpy.enthalpy_joule_per_kg
    )

    assert increase_pressure.pressure_bara > fluid.pressure_bara > decrease_pressure.pressure_bara

    assert increase_enthalpy.temperature_kelvin > fluid.temperature_kelvin > decrease_enthalpy.temperature_kelvin
    assert increase_pressure.temperature_kelvin > fluid.temperature_kelvin > decrease_pressure.temperature_kelvin


def test_fluid_set_new_pressure_and_temperature(heavy_fluid: NeqsimFluid) -> None:
    """Testing the basic properties of enthalpy:

    H = U + pV

    Where
    H = enthalpy
    U = Internal energy
    p = pressure
    V = volume
    """
    fluid = heavy_fluid

    increase_temperature = fluid.set_new_pressure_and_temperature(
        new_pressure_bara=fluid.pressure_bara, new_temperature_kelvin=fluid.temperature_kelvin * 2
    )

    decrease_temperature = fluid.set_new_pressure_and_temperature(
        new_pressure_bara=fluid.pressure_bara, new_temperature_kelvin=fluid.temperature_kelvin / 2
    )

    increase_pressure = fluid.set_new_pressure_and_temperature(
        new_pressure_bara=fluid.pressure_bara * 10, new_temperature_kelvin=fluid.temperature_kelvin
    )

    decrease_pressure = fluid.set_new_pressure_and_temperature(
        new_pressure_bara=fluid.pressure_bara / 10, new_temperature_kelvin=fluid.temperature_kelvin
    )

    assert increase_temperature.temperature_kelvin > fluid.temperature_kelvin > decrease_temperature.temperature_kelvin
    assert (
        increase_temperature.enthalpy_joule_per_kg
        > fluid.enthalpy_joule_per_kg
        > decrease_temperature.enthalpy_joule_per_kg
    )

    assert increase_pressure.pressure_bara > fluid.pressure_bara > decrease_pressure.pressure_bara


def test_fluid_remove_liquid(light_fluid: NeqsimFluid) -> None:
    fluid = light_fluid

    fluid_without_liquid = fluid.set_new_pressure_and_temperature(
        new_pressure_bara=10, new_temperature_kelvin=298.0, remove_liquid=True
    )
    assert fluid_without_liquid.volume < fluid.volume
    assert fluid_without_liquid.molar_mass < fluid.molar_mass
    assert fluid_without_liquid.pressure_bara > fluid.pressure_bara


def test_mix_neqsim_streams():
    """Test the mix_neqsim_streams function with a focus on composition calculation."""
    stream1_composition = FluidComposition.model_validate(
        {
            "methane": 0.8,
            "ethane": 0.15,
            "propane": 0.05,
        }
    )

    stream2_composition = FluidComposition.model_validate(
        {
            "methane": 0.2,
            "ethane": 0.15,
            "propane": 0.6,
            "n_butane": 0.05,
        }
    )

    # Define stream properties
    mass_rate_1 = 100.0  # kg/h
    mass_rate_2 = 900.0  # kg/h
    pressure = 10.0  # bara
    temperature = 300.0  # K
    eos_model = EoSModel.SRK

    # Create NeqsimFluid objects to get molar masses
    fluid1 = NeqsimFluid.create_thermo_system(
        composition=stream1_composition,
        temperature_kelvin=temperature,
        pressure_bara=pressure,
        eos_model=eos_model,
    )
    fluid2 = NeqsimFluid.create_thermo_system(
        composition=stream2_composition,
        temperature_kelvin=temperature,
        pressure_bara=pressure,
        eos_model=eos_model,
    )

    # Calculate expected molar flow rates
    mol_per_hour_1 = mass_rate_1 / fluid1.molar_mass
    mol_per_hour_2 = mass_rate_2 / fluid2.molar_mass
    total_molar_flow = mol_per_hour_1 + mol_per_hour_2

    # Calculate expected composition manually
    expected_methane = (mol_per_hour_1 * 0.8 + mol_per_hour_2 * 0.2) / total_molar_flow
    expected_ethane = (mol_per_hour_1 * 0.15 + mol_per_hour_2 * 0.15) / total_molar_flow
    expected_propane = (mol_per_hour_1 * 0.05 + mol_per_hour_2 * 0.6) / total_molar_flow
    expected_n_butane = (mol_per_hour_1 * 0.0 + mol_per_hour_2 * 0.05) / total_molar_flow

    # Mix streams using the function
    mixed_composition, _ = mix_neqsim_streams(
        stream_composition_1=stream1_composition,
        stream_composition_2=stream2_composition,
        mass_rate_stream_1=mass_rate_1,
        mass_rate_stream_2=mass_rate_2,
        pressure=pressure,
        temperature=temperature,
        eos_model=eos_model,
    )

    # Check that the composition sums to 1.0 (within floating point precision)
    composition_sum = sum(mixed_composition.model_dump().values())
    assert np.isclose(composition_sum, 1.0), f"Composition sum is {composition_sum}, expected 1.0"

    # Check individual component fractions
    mixed_comp_dict = mixed_composition.model_dump()
    assert np.isclose(
        mixed_comp_dict["methane"], expected_methane
    ), f"Methane fraction is {mixed_comp_dict['methane']}, expected {expected_methane}"
    assert np.isclose(
        mixed_comp_dict["ethane"], expected_ethane
    ), f"Ethane fraction is {mixed_comp_dict['ethane']}, expected {expected_ethane}"
    assert np.isclose(
        mixed_comp_dict["propane"], expected_propane
    ), f"Propane fraction is {mixed_comp_dict['propane']}, expected {expected_propane}"
    assert np.isclose(
        mixed_comp_dict["n_butane"], expected_n_butane
    ), f"n-Butane fraction is {mixed_comp_dict['n_butane']}, expected {expected_n_butane}"

    # Print the results for reference
    print("\nTest mix_neqsim_streams results:")
    print(f"Stream 1 molar flow: {mol_per_hour_1:.2f} mol/h")
    print(f"Stream 2 molar flow: {mol_per_hour_2:.2f} mol/h")
    print(f"Total molar flow: {total_molar_flow:.2f} mol/h")
    print("\nExpected composition:")
    print(f"Methane: {expected_methane:.6f}")
    print(f"Ethane: {expected_ethane:.6f}")
    print(f"Propane: {expected_propane:.6f}")
    print(f"n-Butane: {expected_n_butane:.6f}")
    print("\nActual composition:")
    print(f"Methane: {mixed_comp_dict['methane']:.6f}")
    print(f"Ethane: {mixed_comp_dict['ethane']:.6f}")
    print(f"Propane: {mixed_comp_dict['propane']:.6f}")
    print(f"n-Butane: {mixed_comp_dict['n_butane']:.6f}")
