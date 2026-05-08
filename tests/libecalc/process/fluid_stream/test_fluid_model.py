import dataclasses

import pytest

from libecalc.process.fluid_stream.exceptions import (
    InvalidFluidCompositionException,
    NegativeComponentFractionException,
)
from libecalc.process.fluid_stream.fluid_model import EoSModel, FluidComposition, FluidModel


@pytest.fixture
def pure_methane() -> FluidComposition:
    return FluidComposition(methane=1.0)


@pytest.fixture
def natural_gas() -> FluidComposition:
    """Realistic natural gas composition (sums to ~1.0)."""
    return FluidComposition(
        methane=0.85,
        ethane=0.08,
        propane=0.04,
        n_butane=0.02,
        nitrogen=0.01,
    )


@pytest.fixture
def unnormalized() -> FluidComposition:
    """Composition that sums to 2.0 — useful for normalization tests."""
    return FluidComposition(methane=1.6, ethane=0.4)


class TestFluidCompositionConstruction:
    def test_default_construction_all_zeros(self):
        comp = FluidComposition()
        for _, val in comp.items():
            assert val == 0.0

    def test_partial_construction_leaves_rest_zero(self):
        comp = FluidComposition(methane=0.9, CO2=0.1)
        assert comp.methane == 0.9
        assert comp.CO2 == 0.1
        assert comp.ethane == 0.0

    def test_negative_component_raises(self):
        with pytest.raises(NegativeComponentFractionException):
            FluidComposition(methane=-0.1)

    def test_zero_component_is_valid(self):
        comp = FluidComposition(methane=0.0)
        assert comp.methane == 0.0

    # Demonstration only - because it is a value object and compare is defined by attributes
    def test_equality_by_value(self):
        assert FluidComposition(methane=1.0) == FluidComposition(methane=1.0)

    def test_inequality_on_different_values(self):
        assert FluidComposition(methane=1.0) != FluidComposition(methane=0.9, ethane=0.1)


class TestFluidCompositionFromDict:
    def test_valid_dict_constructs_correctly(self):
        comp = FluidComposition.from_dict({"methane": 0.9, "ethane": 0.1})
        assert comp.methane == pytest.approx(0.9)
        assert comp.ethane == pytest.approx(0.1)

    def test_empty_dict_uses_all_defaults(self):
        comp = FluidComposition.from_dict({})
        for _, val in comp.items():
            assert val == 0.0

    def test_unknown_component_raises(self):
        with pytest.raises(InvalidFluidCompositionException, match="Unknown component"):
            FluidComposition.from_dict({"methane": 0.9, "unobtanium": 0.1})

    def test_multiple_unknown_components_raises(self):
        with pytest.raises(InvalidFluidCompositionException, match="Unknown component"):
            FluidComposition.from_dict({"donalditt": 0.5, "tnt": 0.5})

    def test_typo_in_component_name_raises(self):
        """Common mistake: 'co2' instead of 'CO2'."""
        with pytest.raises(InvalidFluidCompositionException, match="Unknown component"):
            FluidComposition.from_dict({"co2": 0.1, "methane": 0.9})

    def test_dict_unpacking_unknown_raises_type_error(self):
        """Bare ** unpacking bypasses from_dict — documents the raw Python behaviour."""
        with pytest.raises(TypeError, match="unexpected keyword argument"):
            FluidComposition(**{"methane": 0.9, "unobtanium": 0.1})  # type: ignore[call-arg]


class TestFluidCompositionItems:
    def test_items_returns_all_fields(self, pure_methane):
        field_names = {f.name for f in dataclasses.fields(FluidComposition)}
        item_names = {name for name, _ in pure_methane.items()}
        assert field_names == item_names

    def test_items_values_match_fields(self, natural_gas):
        items_dict = dict(natural_gas.items())
        assert items_dict["methane"] == pytest.approx(0.85)
        assert items_dict["ethane"] == pytest.approx(0.08)

    def test_items_returns_list_of_tuples(self, pure_methane):
        result = pure_methane.items()
        assert isinstance(result, list)
        assert all(isinstance(item, tuple) and len(item) == 2 for item in result)


class TestFluidCompositionNormalized:
    def test_already_normalized_is_unchanged(self, natural_gas):
        normalized = natural_gas.normalized()
        total = sum(val for _, val in normalized.items())
        assert total == pytest.approx(1.0)

    def test_unnormalized_sums_to_one_after_normalize(self, unnormalized):
        normalized = unnormalized.normalized()
        total = sum(val for _, val in normalized.items())
        assert total == pytest.approx(1.0)

    def test_normalized_preserves_ratios(self, unnormalized):
        normalized = unnormalized.normalized()
        # methane was 1.6 / 2.0 = 0.8, ethane was 0.4 / 2.0 = 0.2
        assert normalized.methane == pytest.approx(0.8)
        assert normalized.ethane == pytest.approx(0.2)

    def test_normalized_returns_new_instance(self, natural_gas):
        normalized = natural_gas.normalized()
        assert normalized is not natural_gas

    def test_all_zero_raises(self):
        with pytest.raises(InvalidFluidCompositionException):
            FluidComposition().normalized()

    def test_pure_methane_normalized_is_one(self, pure_methane):
        normalized = pure_methane.normalized()
        assert normalized.methane == pytest.approx(1.0)


class TestFluidModel:
    def test_construction(self, pure_methane):
        model = FluidModel(eos_model=EoSModel.SRK, composition=pure_methane)
        assert model.eos_model == EoSModel.SRK
        assert model.composition == pure_methane

    def test_different_eos_models_not_equal(self, pure_methane):
        m1 = FluidModel(eos_model=EoSModel.SRK, composition=pure_methane)
        m2 = FluidModel(eos_model=EoSModel.PR, composition=pure_methane)
        assert m1 != m2
