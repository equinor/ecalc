import pytest

from libecalc.common.fluid import FluidComposition


def test_fluid_composition_normalized():
    # Dynamically build a dictionary with each field set to 1.0,
    # so the test is agnostic to the number and names of components.
    init_data = dict.fromkeys(FluidComposition.model_fields, 1.0)
    composition = FluidComposition(**init_data)

    normalized_composition = composition.normalized()
    data = normalized_composition.model_dump()
    total = sum(data.values())

    # Check that the total sum is 1 (within a tolerance)
    assert pytest.approx(total, rel=1e-4) == 1.0

    # Check that each normalized value is between 0 and 1
    for value in data.values():
        assert 0.0 <= value <= 1.0


def test_fluid_composition_normalized_zero_total():
    composition = FluidComposition()
    with pytest.raises(ValueError, match="Total composition is 0; cannot normalize."):
        composition.normalized()


def test_calculate_molar_mass_with_percent_composition():
    # MEDIUM_MW_19P4_COMPOSITION given in percent
    composition = FluidComposition(
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
    result = composition.calculate_avg_molar_mass()
    expected_molar_mass = 0.01944922662363117
    assert pytest.approx(expected_molar_mass, rel=1e-5) == result
