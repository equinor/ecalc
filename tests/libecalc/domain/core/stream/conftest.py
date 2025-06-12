import pytest

from libecalc.domain.process.entities.fluid_stream.fluid_composition import FluidComposition


@pytest.fixture
def medium_composition() -> FluidComposition:
    """Create a medium gas composition (19.4 kg/kmol) for testing.
    This matches the predefined MEDIUM_MW_19P4 composition."""
    return FluidComposition(
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


@pytest.fixture
def ultra_rich_composition() -> FluidComposition:
    """Create an ultra rich gas composition (24.6 kg/kmol) for testing.
    This matches the predefined ULTRA_RICH_MW_24P6 composition."""
    return FluidComposition(
        nitrogen=3.433045573,
        CO2=0.341296928,
        methane=62.50752861,
        ethane=15.64946798,
        propane=13.2202369,
        i_butane=1.606103192,
        n_butane=2.479421803,
        i_pentane=0.351335073,
        n_pentane=0.291106204,
        n_hexane=0.120457739,
    )
