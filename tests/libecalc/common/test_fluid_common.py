import pytest

from libecalc.common.fluid import FluidComposition


def test_fluid_composition_normalized():
    # Dynamically build a dictionary with each field set to 1.0,
    # so the test is agnostic to the number and names of components.
    init_data = {field: 1.0 for field in FluidComposition.model_fields}
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
