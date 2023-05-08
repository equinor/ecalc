import math

from neqsim_ecalc_wrapper.thermo import NeqsimFluid


def test_gerg_model_against_unisim(medium_fluid_with_gerg: NeqsimFluid) -> None:
    low_pressure = medium_fluid_with_gerg.set_new_pressure_and_temperature(
        new_pressure_bara=5, new_temperature_kelvin=30 + 273.15
    )
    medium_pressure = medium_fluid_with_gerg.set_new_pressure_and_temperature(
        new_pressure_bara=100, new_temperature_kelvin=30 + 273.15
    )
    high_pressure = medium_fluid_with_gerg.set_new_pressure_and_temperature(
        new_pressure_bara=400, new_temperature_kelvin=30 + 273.15
    )

    very_high_pressure = medium_fluid_with_gerg.set_new_pressure_and_temperature(
        new_pressure_bara=800, new_temperature_kelvin=30 + 273.15
    )

    assert math.isclose(low_pressure.density, 3.9, rel_tol=0.01)
    assert math.isclose(low_pressure.z, 0.9883, rel_tol=0.01)

    assert math.isclose(medium_pressure.density, 98.06, rel_tol=0.01)
    assert math.isclose(medium_pressure.z, 0.7865, rel_tol=0.01)

    assert math.isclose(high_pressure.density, 300.6, rel_tol=0.01)
    assert math.isclose(high_pressure.z, 1.026, rel_tol=0.01)

    assert math.isclose(very_high_pressure.density, 373.9, rel_tol=0.01)
    assert math.isclose(very_high_pressure.z, 1.65, rel_tol=0.01)

    assert math.isclose(
        low_pressure.enthalpy_J_per_kg - medium_pressure.enthalpy_J_per_kg, 17634 - -93366, rel_tol=0.01
    )
    assert math.isclose(
        medium_pressure.enthalpy_J_per_kg - high_pressure.enthalpy_J_per_kg, -93366 - -219900, rel_tol=0.02
    )

    assert math.isclose(
        high_pressure.enthalpy_J_per_kg - very_high_pressure.enthalpy_J_per_kg, -219900 - -194900, rel_tol=0.02
    )
