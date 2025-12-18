from uuid import uuid4

import pytest

from ecalc_neqsim_wrapper.thermo import STANDARD_PRESSURE_BARA, STANDARD_TEMPERATURE_KELVIN
from libecalc.domain.process.entities.process_units.liquid_remover.liquid_remover import LiquidRemover
from libecalc.domain.process.value_objects.fluid_stream import FluidComposition
from libecalc.domain.process.value_objects.fluid_stream.fluid_model import FluidModel, EoSModel
from libecalc.infrastructure.neqsim_fluid_provider.neqsim_fluid_factory import NeqSimFluidFactory


def test_liquid_remover_removes_liquid():
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
    remover = LiquidRemover(unit_id=uuid4())
    outlet_stream = remover.remove_liquid(inlet_stream)

    assert inlet_stream.vapor_fraction_molar < 1.0
    assert outlet_stream.vapor_fraction_molar == 1.0
