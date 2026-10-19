from unittest.mock import MagicMock, patch

import pytest

from ecalc_neqsim_wrapper.thermo import STANDARD_PRESSURE_BARA, STANDARD_TEMPERATURE_KELVIN
from libecalc.process.fluid_stream.constants import ThermodynamicConstants
from libecalc.process.fluid_stream.fluid_model import EoSModel, FluidComposition, FluidModel
from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_pipeline.process_error import LiquidAtInletError
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


WET_GAS_COMPOSITION = FluidComposition(
    water=0.365,
    nitrogen=1.785,
    CO2=0.269,
    methane=57.023,
    ethane=16.53,
    propane=15.884,
    i_butane=2.235,
    n_butane=3.821,
    i_pentane=0.784,
    n_pentane=0.783,
    n_hexane=0.521,
)


@pytest.mark.parametrize(
    ("pressure_bara", "temperature_kelvin", "expected_mass_fraction"),
    [
        # Aqueous and hydrocarbon liquid; the plain flash sees a vapor fraction of 1.0 at 100 bara
        (60.0, 298.15, 0.6825),
        (100.0, 298.15, 0.5073),
    ],
)
def test_liquid_remover_removes_aqueous_phase_together_with_hydrocarbon_liquid(
    pressure_bara, temperature_kelvin, expected_mass_fraction, fluid_service, liquid_remover_factory
):
    inlet_stream = fluid_service.create_stream_from_standard_rate(
        fluid_model=FluidModel(eos_model=EoSModel.PR, composition=WET_GAS_COMPOSITION),
        pressure_bara=pressure_bara,
        temperature_kelvin=temperature_kelvin,
        standard_rate_m3_per_day=1e6,
    )

    outlet_stream = liquid_remover_factory().propagate_stream(inlet_stream)

    assert outlet_stream.mass_rate_kg_per_h / inlet_stream.mass_rate_kg_per_h == pytest.approx(
        expected_mass_fraction, abs=1e-4
    )
    assert outlet_stream.vapor_fraction_molar >= ThermodynamicConstants.PURE_VAPOR_THRESHOLD
    reflashed = fluid_service.flash_pt(outlet_stream.fluid.fluid_model, pressure_bara, temperature_kelvin)
    assert reflashed.vapor_fraction_molar >= ThermodynamicConstants.PURE_VAPOR_THRESHOLD


def test_liquid_remover_removes_only_water_from_dense_hydrocarbon_phase(fluid_service, liquid_remover_factory):
    inlet_stream = fluid_service.create_stream_from_standard_rate(
        fluid_model=FluidModel(eos_model=EoSModel.PR, composition=WET_GAS_COMPOSITION),
        pressure_bara=300.0,
        temperature_kelvin=293.0,
        standard_rate_m3_per_day=1e6,
    )

    outlet_stream = liquid_remover_factory().propagate_stream(inlet_stream)

    assert outlet_stream.mass_rate_kg_per_h / inlet_stream.mass_rate_kg_per_h == pytest.approx(0.9976, abs=1e-4)
    assert outlet_stream.fluid.fluid_model.composition.water < inlet_stream.fluid.fluid_model.composition.water


def test_liquid_remover_removes_hydrocarbon_liquid_without_water(fluid_service, liquid_remover_factory):
    composition = FluidComposition(
        nitrogen=1,
        CO2=1,
        methane=60,
        ethane=15,
        propane=13,
        i_butane=1,
        n_butane=2,
        i_pentane=1,
        n_pentane=1,
        n_hexane=5,
    )
    inlet_stream = fluid_service.create_stream_from_standard_rate(
        fluid_model=FluidModel(eos_model=EoSModel.PR, composition=composition),
        pressure_bara=60.0,
        temperature_kelvin=260.0,
        standard_rate_m3_per_day=1e6,
    )

    outlet_stream = liquid_remover_factory().propagate_stream(inlet_stream)

    assert outlet_stream.mass_rate_kg_per_h < inlet_stream.mass_rate_kg_per_h
    assert outlet_stream.vapor_fraction_molar >= ThermodynamicConstants.PURE_VAPOR_THRESHOLD


def test_dense_hydrocarbon_phase_kept_by_liquid_remover_is_rejected_by_compressor(
    fluid_service, liquid_remover_factory, compressor_factory, variable_speed_compressor_chart_data
):
    inlet_stream = fluid_service.create_stream_from_standard_rate(
        fluid_model=FluidModel(eos_model=EoSModel.PR, composition=WET_GAS_COMPOSITION),
        pressure_bara=300.0,
        temperature_kelvin=293.0,
        standard_rate_m3_per_day=1e6,
    )
    outlet_stream = liquid_remover_factory().propagate_stream(inlet_stream)

    with pytest.raises(LiquidAtInletError):
        compressor_factory(variable_speed_compressor_chart_data).propagate_stream(outlet_stream)


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
    with patch.object(fluid_service, "_get_reference_fluid", wraps=fluid_service._get_reference_fluid) as get_ref:
        outlet_stream = remover.propagate_stream(inlet_stream)

    assert inlet_stream.vapor_fraction_molar == 1.0
    assert outlet_stream.mass_rate_kg_per_h == inlet_stream.mass_rate_kg_per_h
    # Water-free and already pure vapor: the no-flash shortcut should apply, not the multiphase flash.
    get_ref.assert_not_called()


def test_liquid_remover_raises_on_non_positive_inlet_molar_mass():
    inlet_stream = MagicMock()
    inlet_stream.vapor_fraction_molar = 0.5
    inlet_stream.fluid.molar_mass = 0.0

    fluid_service = MagicMock()
    remover = LiquidRemover(fluid_service=fluid_service)

    with pytest.raises(AssertionError, match="non-positive molar mass"):
        remover.propagate_stream(inlet_stream)
