import itertools

import numpy as np
import pytest

from libecalc.common.units import UnitConstants
from libecalc.domain.process.core.compressor.train.fluid import FluidStream


@pytest.fixture
def fluid_streams(dry_fluid, medium_fluid, rich_fluid) -> list[list[FluidStream]]:
    fluid_dry = FluidStream(dry_fluid)
    fluid_medium = FluidStream(medium_fluid)
    fluid_rich = FluidStream(rich_fluid)

    # Conditions
    inlet_pressures_bara = [15.0, 100.0, 400.0]
    inlet_temperatures_kelvin = [288.15, 303.15, 333.15, 413.15]

    # Create all combinations of temperature and pressure by using itertools.product.
    pressure_temperature_rate_array = np.array(list(itertools.product(inlet_pressures_bara, inlet_temperatures_kelvin)))

    streams = [
        fluid.get_fluid_streams(
            pressure_bara=pressure_temperature_rate_array[:, 0],
            temperature_kelvin=pressure_temperature_rate_array[:, 1],
        )
        for fluid in (fluid_dry, fluid_medium, fluid_rich)
    ]
    return streams


def test_set_new_pressure_and_enthalpy_or_temperature(fluid_streams: list[list[FluidStream]]):
    enthalpy_change_joule_per_kg = 100000.0
    pressure_increase_factor = 3.0

    inlet_enthalpies_all_fluids = [np.asarray([s.enthalpy_joule_per_kg for s in stream]) for stream in fluid_streams]

    new_enthalpies_all_fluids = [
        enthalpy_array + enthalpy_change_joule_per_kg for enthalpy_array in inlet_enthalpies_all_fluids
    ]

    inlet_pressures_all_fluids = [np.asarray([s.pressure_bara for s in streams]) for streams in fluid_streams]

    new_pressures_all_fluids = [
        pressure_array * pressure_increase_factor for pressure_array in inlet_pressures_all_fluids
    ]

    streams_with_new_pressure_and_enthalpy = [
        [
            s.set_new_pressure_and_enthalpy_change(
                enthalpy_change_joule_per_kg=enthalpy_change_joule_per_kg,
                new_pressure=new_pressure,
            )
            for s, new_pressure in zip(streams, new_pressures)
        ]
        for streams, new_pressures in zip(
            fluid_streams,
            new_pressures_all_fluids,
        )
    ]
    new_temperatures_all_fluids = [
        np.asarray([s.temperature_kelvin for s in streams]) for streams in streams_with_new_pressure_and_enthalpy
    ]

    # Test values for new temperatures after changing enthalpy and pressure, taken from these calculations
    expected_new_temperatures = [
        [
            344.47800111,
            357.81209332,
            384.66028792,
            457.40783481,
            353.63190929,
            368.202054,
            395.74471377,
            466.28818501,
            296.59449828,
            313.49978189,
            346.65233075,
            430.44646877,
        ],
        [
            346.34145995,
            359.56790323,
            386.22632078,
            458.60684954,
            354.52420492,
            369.57731606,
            397.53375933,
            468.12263053,
            296.65952396,
            313.60791615,
            346.92746694,
            431.3019393,
        ],
        [
            348.72789591,
            361.74975883,
            388.05650806,
            459.79736319,
            353.39889124,
            369.89850145,
            399.13664454,
            470.22243851,
            295.42887241,
            312.35396756,
            345.79719463,
            431.0803508,
        ],
    ]
    np.testing.assert_allclose(new_temperatures_all_fluids, expected_new_temperatures)

    # Check that setting temperature, gives the same enthalpy change

    streams_with_new_pressure_and_temperature = [
        [
            s.set_new_pressure_and_temperature(
                new_pressure_bara=new_pressure,
                new_temperature_kelvin=new_temperature,
            )
            for s, new_temperature, new_pressure in zip(streams, new_temperatures, new_pressures)
        ]
        for streams, new_temperatures, new_pressures in zip(
            fluid_streams,
            new_temperatures_all_fluids,
            new_pressures_all_fluids,
        )
    ]
    new_enthalpies_all_fluids_after_setting_new_temperature = [
        np.asarray([s.enthalpy_joule_per_kg for s in streams]) for streams in streams_with_new_pressure_and_temperature
    ]
    np.testing.assert_allclose(
        new_enthalpies_all_fluids_after_setting_new_temperature,
        new_enthalpies_all_fluids,
    )


def test_fluid_mixing(dry_fluid, rich_fluid):
    """Test mixing two fluids together, check that the order does not change"""

    dry_fluid_stream = FluidStream(fluid_model=dry_fluid)
    rich_fluid_stream = FluidStream(fluid_model=rich_fluid)

    mix_rich_into_dry = dry_fluid_stream.mix_in_stream(
        other_fluid_stream=rich_fluid_stream,
        self_mass_rate=1,
        other_mass_rate=1,
        pressure_bara=UnitConstants.STANDARD_PRESSURE_BARA,
        temperature_kelvin=270,
    )
    mix_dry_into_rich = rich_fluid_stream.mix_in_stream(
        other_fluid_stream=dry_fluid_stream,
        self_mass_rate=1,
        other_mass_rate=1,
        pressure_bara=UnitConstants.STANDARD_PRESSURE_BARA,
        temperature_kelvin=270,
    )

    assert (
        mix_rich_into_dry.standard_conditions_density == mix_dry_into_rich.standard_conditions_density
    )  # Order of mixing should not matter
    assert (
        mix_rich_into_dry.standard_conditions_density != mix_rich_into_dry.density
    )  # Check that the mixing conditions are set correctly, since we are not at standard conditions it should not be equal
    np.testing.assert_allclose(actual=mix_rich_into_dry.density, desired=0.888741, rtol=1e-5)
    np.testing.assert_allclose(actual=mix_dry_into_rich.standard_conditions_density, desired=0.832155, rtol=1e-5)
