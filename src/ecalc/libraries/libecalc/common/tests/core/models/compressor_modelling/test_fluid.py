import itertools
from typing import List

import numpy as np
import pytest
from libecalc.common.units import UnitConstants
from libecalc.core.models.compressor.train.fluid import FluidStream


@pytest.fixture
def fluid_streams(dry_fluid, medium_fluid, rich_fluid) -> List[List[FluidStream]]:
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


def test_set_new_pressure_and_enthalpy_or_temperature(fluid_streams: List[List[FluidStream]]):
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
            344.4909047480005,
            357.8263792478509,
            384.6769711019459,
            457.42983576838066,
            353.64399093413545,
            368.21599484422575,
            395.76181264498234,
            466.31172113274334,
            296.5957445457387,
            313.5016383350938,
            346.6555589631875,
            430.45336250845924,
        ],
        [
            346.3579452315028,
            359.585895803585,
            386.2463042346924,
            458.6294172200485,
            354.53906167852375,
            369.59434425189016,
            397.55379271528335,
            468.1466709626877,
            296.6610721982785,
            313.6102644692811,
            346.9314579812098,
            431.3093404595682,
        ],
        [
            348.7434612227192,
            361.7666579102452,
            388.07509105966955,
            459.81787165852427,
            353.41184252688856,
            369.9137263308065,
            399.1548801703584,
            470.24437484497446,
            295.43007753887326,
            312.35585315980427,
            345.8005275981218,
            431.0868717573131,
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


@pytest.mark.parametrize(("new_pressure, enthalpy_change"), [(50,120e3), (100,180e3), (200, 400e3)])
def test_fluid_stream_flash(dry_fluid, new_pressure, enthalpy_change):
    """ Test calculating z from"""

    regular_fluid_stream = FluidStream(fluid_model=dry_fluid)
    ml_fluid_stream = FluidStream(fluid_model=dry_fluid,ml_backend=True)

    flashed_stream = regular_fluid_stream.set_new_pressure_and_enthalpy_change(new_pressure=new_pressure, enthalpy_change_joule_per_kg=enthalpy_change)
    flashed_ml_stream = ml_fluid_stream.set_new_pressure_and_enthalpy_change(new_pressure=new_pressure, enthalpy_change_joule_per_kg=enthalpy_change)

    assert flashed_ml_stream.pressure_bara == flashed_stream.pressure_bara
    assert flashed_ml_stream.enthalpy_joule_per_kg == pytest.approx(flashed_stream.enthalpy_joule_per_kg)
    assert flashed_ml_stream.temperature_kelvin == pytest.approx(flashed_stream.temperature_kelvin, 0.03)
    assert flashed_ml_stream.z == pytest.approx(flashed_stream.z, 0.03)
    assert flashed_ml_stream.kappa == pytest.approx(flashed_stream.kappa, 0.1)
    assert flashed_ml_stream.density == pytest.approx(flashed_stream.density, 0.02)


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
