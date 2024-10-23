import pytest
from pydantic import ValidationError

from libecalc import dto


def test_composition(caplog):
    composition_spec = {
        "nitrogen": 0.74373,
        "CO2": 2.415619,
        "methane": 85.60145,
        "ethane": 6.707826,
        "propane": 2.611471,
        "i_butane": 0.45077,
        "n_butane": 0.691702,
        "i_pentane": 0.210714,
        "n_pentane": 0.197937,
        "n_hexane": 0.368786,
    }
    composition = dto.FluidComposition.model_validate(composition_spec)

    assert all(x in composition.model_dump() for x in composition_spec)
    assert all(x in composition.model_dump().values() for x in composition_spec.values())

    # Composition with invalid component name
    with pytest.raises(ValidationError):
        caplog.set_level("CRITICAL")
        dto.FluidComposition.model_validate({"invalid": 0.74373, "CO2": 2.415619, "methane": 85.60145})
