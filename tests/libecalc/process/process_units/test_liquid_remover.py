from unittest.mock import MagicMock

import pytest

from ecalc_neqsim_wrapper.thermo import STANDARD_PRESSURE_BARA, STANDARD_TEMPERATURE_KELVIN
from libecalc.process.fluid_stream.fluid_model import EoSModel, FluidComposition, FluidModel
from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_units.liquid_remover import LiquidRemover


def test_liquid_remover_removes_liquid(fluid_service, liquid_remover_factory):
    composition = FluidComposition(
        nitrogen=3,
        CO2=1,
        methane=62,
        ethane=15,
        propane=13,
        i_butane=1,
        n_butane=2,
        i_pentane=1,
        n_pentane=1,
        n_hexane=1,
        water=25,
    )
    fluid_model = FluidModel(eos_model=EoSModel.SRK, composition=composition)
    fluid = fluid_service.create_fluid(
        fluid_model=fluid_model,
        pressure_bara=STANDARD_PRESSURE_BARA,
        temperature_kelvin=STANDARD_TEMPERATURE_KELVIN,
    )
    inlet_stream = FluidStream.from_standard_rate(
        standard_rate_m3_per_day=100000,
        fluid_model=fluid.fluid_model,
        fluid_properties=fluid.properties,
    )
    remover = liquid_remover_factory()
    outlet_stream = remover.propagate_stream(inlet_stream)

    assert inlet_stream.vapor_fraction_molar < 1.0
    assert outlet_stream.vapor_fraction_molar == 1.0

    expected_gas_mass_fraction = (
        inlet_stream.vapor_fraction_molar * outlet_stream.fluid.molar_mass / inlet_stream.fluid.molar_mass
    )
    expected_mass_rate = inlet_stream.mass_rate_kg_per_h * expected_gas_mass_fraction
    assert outlet_stream.mass_rate_kg_per_h < inlet_stream.mass_rate_kg_per_h
    assert outlet_stream.mass_rate_kg_per_h == expected_mass_rate


def test_liquid_remover_passthrough_when_no_liquid(fluid_service, liquid_remover_factory):
    composition = FluidComposition(
        nitrogen=3,
        CO2=1,
        methane=80,
        ethane=10,
        propane=6,
    )
    fluid_model = FluidModel(eos_model=EoSModel.SRK, composition=composition)
    fluid = fluid_service.create_fluid(
        fluid_model=fluid_model,
        pressure_bara=STANDARD_PRESSURE_BARA,
        temperature_kelvin=STANDARD_TEMPERATURE_KELVIN,
    )
    inlet_stream = FluidStream.from_standard_rate(
        standard_rate_m3_per_day=100000,
        fluid_model=fluid.fluid_model,
        fluid_properties=fluid.properties,
    )
    remover = liquid_remover_factory()
    outlet_stream = remover.propagate_stream(inlet_stream)

    assert inlet_stream.vapor_fraction_molar == 1.0
    assert outlet_stream.mass_rate_kg_per_h == inlet_stream.mass_rate_kg_per_h


def test_liquid_remover_raises_on_non_positive_inlet_molar_mass():
    inlet_stream = MagicMock()
    inlet_stream.vapor_fraction_molar = 0.5
    inlet_stream.fluid.molar_mass = 0.0

    fluid_service = MagicMock()
    remover = LiquidRemover(fluid_service=fluid_service)

    with pytest.raises(AssertionError, match="non-positive molar mass"):
        remover.propagate_stream(inlet_stream)
