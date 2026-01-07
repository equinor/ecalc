from ecalc_neqsim_wrapper.thermo import STANDARD_PRESSURE_BARA, STANDARD_TEMPERATURE_KELVIN
from libecalc.domain.process.entities.process_units.splitter.splitter import Splitter
from libecalc.domain.process.value_objects.fluid_stream import FluidComposition
from libecalc.domain.process.value_objects.fluid_stream.fluid_model import EoSModel, FluidModel
from libecalc.infrastructure.neqsim_fluid_provider.neqsim_fluid_factory import NeqSimFluidFactory


def test_splitter():
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
    inlet_stream = NeqSimFluidFactory(
        FluidModel(
            eos_model=EoSModel.SRK,
            composition=composition,
        )
    ).create_stream_from_standard_rate(
        pressure_bara=STANDARD_PRESSURE_BARA,
        temperature_kelvin=STANDARD_TEMPERATURE_KELVIN,
        standard_rate_m3_per_day=100000,
    )
    splitter = Splitter(
        number_of_outputs=2,
        rates_out_of_splitter=[50000],
    )
    outlet_streams = splitter.split_stream(inlet_stream)

    assert inlet_stream.standard_rate == 100000
    assert outlet_streams[0].standard_rate == 50000
    assert outlet_streams[1].standard_rate == 50000
