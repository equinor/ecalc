import pytest
from neqsim_ecalc_wrapper.thermo import NeqsimEoSModelType, NeqsimFluid

HEAVY_FLUID_COMPOSITION = {
    "nitrogen": 0.682785869,
    "CO2": 2.466921329,
    "methane": 79.57192993,
    "ethane": 5.153816223,
    "propane": 9.679747581,
    "i-butane": 0.691399336,
    "n-butane": 1.174334645,
    "i-pentane": 0.208390206,
    "n-pentane": 0.201853022,
    "n-hexane": 0.16881974,
}

MEDIUM_MW_19P4_COMPOSITION = {
    "nitrogen": 0.74373,
    "CO2": 2.415619,
    "methane": 85.60145,
    "ethane": 6.707826,
    "propane": 2.611471,
    "i-butane": 0.45077,
    "n-butane": 0.691702,
    "i-pentane": 0.210714,
    "n-pentane": 0.197937,
    "n-hexane": 0.368786,
}

LIGHT_FLUID_COMPOSITION = {"methane": 10.0, "ethane": 1.0, "propane": 0.1, "n-heptane": 10.1}


@pytest.fixture
def heavy_fluid() -> NeqsimFluid:
    return NeqsimFluid.create_thermo_system(composition=HEAVY_FLUID_COMPOSITION)


@pytest.fixture
def medium_fluid() -> NeqsimFluid:
    return NeqsimFluid.create_thermo_system(composition=MEDIUM_MW_19P4_COMPOSITION)


@pytest.fixture
def medium_fluid_with_gerg() -> NeqsimFluid:
    return NeqsimFluid.create_thermo_system(
        composition=MEDIUM_MW_19P4_COMPOSITION, eos_model=NeqsimEoSModelType.GERG_SRK
    )


@pytest.fixture
def light_fluid() -> NeqsimFluid:
    return NeqsimFluid.create_thermo_system(composition=LIGHT_FLUID_COMPOSITION)


@pytest.fixture
def heavy_fluid_with_water() -> NeqsimFluid:
    composition = HEAVY_FLUID_COMPOSITION.copy()
    composition["water"] = 0.15
    return NeqsimFluid.create_thermo_system(composition=composition)
