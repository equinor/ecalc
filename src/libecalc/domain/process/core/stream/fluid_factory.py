from libecalc.common.fluid import EoSModel, FluidComposition
from libecalc.domain.process.core.stream.fluid import Fluid
from libecalc.domain.process.core.stream.thermo_adapters import NeqSimThermodynamicAdapter


def create_fluid_with_neqsim_engine(composition: FluidComposition, eos_model: EoSModel | None = None) -> Fluid:
    """Create a fluid instance that uses the NeqSim engine"""
    if eos_model is None:
        eos_model = EoSModel.SRK  # Default to SRK if not specified
    engine = NeqSimThermodynamicAdapter()
    return Fluid(composition=composition, eos_model=eos_model, _thermodynamic_engine=engine)
