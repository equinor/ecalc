import pytest

from ecalc_neqsim_wrapper.thermo import STANDARD_PRESSURE_BARA, STANDARD_TEMPERATURE_KELVIN
from libecalc.process.fluid_stream.fluid_model import EoSModel, FluidComposition, FluidModel
from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_pipeline.process_error import NoGasPhaseError


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
    assert outlet_stream.mass_rate_kg_per_h < inlet_stream.mass_rate_kg_per_h


def test_liquid_remover_passthrough_when_no_liquid(fluid_service, liquid_remover_factory):
    composition = FluidComposition(nitrogen=3, CO2=1, methane=80, ethane=10, propane=6)
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


def test_liquid_remover_passthrough_supercritical_co2(fluid_service, liquid_remover_factory):
    """Pure CO2 above critical point: NeqSim reports vapor_fraction=0,
    but the EoS critical point check detects supercritical and prevents mass loss."""
    composition = FluidComposition(CO2=1.0)
    fluid_model = FluidModel(eos_model=EoSModel.SRK, composition=composition)

    fluid = fluid_service.create_fluid(
        fluid_model=fluid_model,
        pressure_bara=350.0,
        temperature_kelvin=308.15,
    )
    inlet_stream = FluidStream.from_standard_rate(
        standard_rate_m3_per_day=100000,
        fluid_model=fluid.fluid_model,
        fluid_properties=fluid.properties,
    )

    # NeqSim mislabels supercritical CO2 as liquid
    assert inlet_stream.vapor_fraction_molar <= 0.0001

    remover = liquid_remover_factory()
    outlet_stream = remover.propagate_stream(inlet_stream)

    # Mass fully conserved
    assert outlet_stream.mass_rate_kg_per_h == inlet_stream.mass_rate_kg_per_h


def test_liquid_remover_passthrough_subcritical_co2_vapor(fluid_service, liquid_remover_factory):
    """CO2 below critical pressure: should be all vapor, passes through."""
    composition = FluidComposition(CO2=1.0)
    fluid_model = FluidModel(eos_model=EoSModel.SRK, composition=composition)

    fluid = fluid_service.create_fluid(
        fluid_model=fluid_model,
        pressure_bara=50.0,
        temperature_kelvin=293.15,
    )
    inlet_stream = FluidStream.from_standard_rate(
        standard_rate_m3_per_day=100000,
        fluid_model=fluid.fluid_model,
        fluid_properties=fluid.properties,
    )

    remover = liquid_remover_factory()
    outlet_stream = remover.propagate_stream(inlet_stream)

    # Pure CO2 at these conditions is single-phase, mass conserved
    assert outlet_stream.mass_rate_kg_per_h == inlet_stream.mass_rate_kg_per_h


def test_liquid_remover_raises_for_genuine_liquid(fluid_service, liquid_remover_factory):
    """Water at ambient conditions is genuinely liquid (not supercritical).
    The LiquidRemover raises NoGasPhaseError — no gas to extract."""
    composition = FluidComposition(water=1.0)
    fluid_model = FluidModel(eos_model=EoSModel.SRK, composition=composition)

    fluid = fluid_service.create_fluid(
        fluid_model=fluid_model,
        pressure_bara=10.0,
        temperature_kelvin=293.15,
    )
    inlet_stream = FluidStream.from_standard_rate(
        standard_rate_m3_per_day=100000,
        fluid_model=fluid.fluid_model,
        fluid_properties=fluid.properties,
    )

    assert inlet_stream.vapor_fraction_molar <= 0.0001

    remover = liquid_remover_factory()
    with pytest.raises(NoGasPhaseError):
        remover.propagate_stream(inlet_stream)


def test_liquid_remover_passthrough_supercritical_co2_mixture(fluid_service, liquid_remover_factory):
    """CO2-dominant mixture above its EoS-computed critical point.
    Exercises the critical point calculation across multiple components."""
    composition = FluidComposition(CO2=95.0, methane=5.0)
    fluid_model = FluidModel(eos_model=EoSModel.SRK, composition=composition)

    # EoS critical point ≈ 297 K, 72 bar
    # At 310 K, 100 bar → above both → supercritical
    fluid = fluid_service.create_fluid(
        fluid_model=fluid_model,
        pressure_bara=100.0,
        temperature_kelvin=310.0,
    )
    inlet_stream = FluidStream.from_standard_rate(
        standard_rate_m3_per_day=100000,
        fluid_model=fluid.fluid_model,
        fluid_properties=fluid.properties,
    )

    remover = liquid_remover_factory()
    outlet_stream = remover.propagate_stream(inlet_stream)

    assert outlet_stream.mass_rate_kg_per_h == inlet_stream.mass_rate_kg_per_h


def test_liquid_remover_raises_on_non_positive_inlet_molar_mass(fluid_service, liquid_remover_factory):
    """The assertion guarding against degenerate streams with zero molar mass is still active."""
    from unittest.mock import MagicMock

    from libecalc.process.process_units.liquid_remover import LiquidRemover

    inlet_stream = MagicMock()
    inlet_stream.vapor_fraction_molar = 0.5
    inlet_stream.fluid.molar_mass = 0.0

    mock_fluid_service = MagicMock()
    remover = LiquidRemover(fluid_service=mock_fluid_service)

    with pytest.raises(AssertionError, match="non-positive molar mass"):
        remover.propagate_stream(inlet_stream)
