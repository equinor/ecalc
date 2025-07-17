import pytest

from ecalc_neqsim_wrapper import NeqsimService
from ecalc_neqsim_wrapper.thermo import NeqsimFluid
from libecalc.domain.process.value_objects.fluid_stream.fluid_model import EoSModel, FluidComposition

HEAVY_FLUID_COMPOSITION = FluidComposition(
    nitrogen=0.682785869,
    CO2=2.466921329,
    methane=79.57192993,
    ethane=5.153816223,
    propane=9.679747581,
    i_butane=0.691399336,
    n_butane=1.174334645,
    i_pentane=0.208390206,
    n_pentane=0.201853022,
    n_hexane=0.16881974,
)

MEDIUM_MW_19P4_COMPOSITION = FluidComposition(
    nitrogen=0.74373,
    CO2=2.415619,
    methane=85.60145,
    ethane=6.707826,
    propane=2.611471,
    i_butane=0.45077,
    n_butane=0.691702,
    i_pentane=0.210714,
    n_pentane=0.197937,
    n_hexane=0.368786,
)

LIGHT_FLUID_COMPOSITION = FluidComposition(
    methane=10.0, ethane=1.0, propane=0.1, n_hexane=10.1
)  # Heptane not used in eCalc, only care about C1-C6


@pytest.fixture(autouse=True)
def with_neqsim_service():
    with NeqsimService() as neqsim_service:
        yield neqsim_service


@pytest.fixture
def heavy_fluid() -> NeqsimFluid:
    return NeqsimFluid.create_thermo_system(composition=HEAVY_FLUID_COMPOSITION)


@pytest.fixture
def medium_fluid() -> NeqsimFluid:
    return NeqsimFluid.create_thermo_system(composition=MEDIUM_MW_19P4_COMPOSITION)


@pytest.fixture
def medium_fluid_with_gerg() -> NeqsimFluid:
    return NeqsimFluid.create_thermo_system(composition=MEDIUM_MW_19P4_COMPOSITION, eos_model=EoSModel.GERG_SRK)


@pytest.fixture
def light_fluid() -> NeqsimFluid:
    return NeqsimFluid.create_thermo_system(composition=LIGHT_FLUID_COMPOSITION)


@pytest.fixture
def heavy_fluid_with_water() -> NeqsimFluid:
    composition = HEAVY_FLUID_COMPOSITION.model_copy()
    composition["water"] = 0.15
    return NeqsimFluid.create_thermo_system(composition=composition)
