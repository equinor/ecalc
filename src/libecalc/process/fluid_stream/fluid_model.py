from __future__ import annotations

import dataclasses
from enum import StrEnum

from libecalc.common.ddd import value_object
from libecalc.process.fluid_stream.constants import ThermodynamicConstants
from libecalc.process.fluid_stream.exceptions import (
    InvalidFluidCompositionException,
    NegativeComponentFractionException,
)


@value_object
class FluidModel:
    eos_model: EoSModel
    composition: FluidComposition


class EoSModel(StrEnum):
    SRK = "SRK"
    PR = "PR"
    GERG_SRK = "GERG_SRK"
    GERG_PR = "GERG_PR"


@value_object
class FluidComposition:
    water: float = 0.0
    nitrogen: float = 0.0
    CO2: float = 0.0
    methane: float = 0.0
    ethane: float = 0.0
    propane: float = 0.0
    i_butane: float = 0.0
    n_butane: float = 0.0
    i_pentane: float = 0.0
    n_pentane: float = 0.0
    n_hexane: float = 0.0

    def __post_init__(self):
        for key, val in dataclasses.asdict(self).items():
            if val < 0:
                raise NegativeComponentFractionException(component_name=key, fraction=val)

    def normalized(self) -> FluidComposition:
        """
        Returns a new FluidComposition instance with each component normalized so that
        the sum of all components equals 1.
        """
        data = dataclasses.asdict(self)
        total = sum(data.values())
        if total == 0:
            raise InvalidFluidCompositionException(reason="Total composition is 0; cannot normalize.")
        normalized_data = {key: value / total for key, value in data.items()}
        return FluidComposition(**normalized_data)

    @classmethod
    def from_dict(cls, data: dict[str, float]) -> FluidComposition:
        """Construct a FluidComposition from a dict of component name → mole fraction.

        Safe to use this than directly unpacking with **data, will also yield a more
        helpful description of which components that are valid

        TODO: Should we allow different casing, but set to correct case?

        Raises:
            InvalidFluidCompositionException: If the dict contains unknown component names.
        """
        valid_fields = {f.name for f in dataclasses.fields(cls)}
        unknown = set(data.keys()) - valid_fields
        if unknown:
            raise InvalidFluidCompositionException(
                reason=f"Unknown component(s): {sorted(unknown)}. Valid components are: {sorted(valid_fields)}"
            )
        return cls(**data)

    def items(self) -> list[tuple[str, float]]:
        """Return a list of component names and their values."""
        return list(dataclasses.asdict(self).items())

    @property
    def molar_mass_mixture(self) -> float:
        """Calculate the molar mass of a fluid mixture using component molecular weights.

        Returns:
            float: The molar mass of the mixture in kg/mol
        """
        normalized_composition: FluidComposition = self.normalized()
        molar_mass = 0.0
        for component, mole_fraction in normalized_composition.items():
            if mole_fraction > 0:  # Skip zero components
                molar_mass += mole_fraction * ThermodynamicConstants.get_component_molecular_weight(component)
        return molar_mass
