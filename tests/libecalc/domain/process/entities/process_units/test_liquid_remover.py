from ecalc_neqsim_wrapper.thermo import STANDARD_PRESSURE_BARA, STANDARD_TEMPERATURE_KELVIN
from libecalc.domain.process.entities.process_units.liquid_remover import LiquidRemover
from libecalc.domain.process.value_objects.fluid_stream import FluidComposition
from libecalc.domain.process.value_objects.fluid_stream.fluid_model import EoSModel, FluidModel
from libecalc.domain.process.value_objects.fluid_stream.fluid_stream import FluidStream


def test_liquid_remover_removes_liquid(fluid_service):
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
    remover = LiquidRemover(fluid_service=fluid_service)
    outlet_stream = remover.propagate_stream(inlet_stream)

    assert inlet_stream.vapor_fraction_molar < 1.0
    assert outlet_stream.vapor_fraction_molar == 1.0
