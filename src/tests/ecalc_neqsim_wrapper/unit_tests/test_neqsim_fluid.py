import numpy as np
import pytest

from ecalc_neqsim_wrapper.thermo import NeqsimFluid


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
