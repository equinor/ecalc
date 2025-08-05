from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from libecalc.domain.process.value_objects.fluid_stream.constants import ThermodynamicConstants


class FluidModel(BaseModel):
    eos_model: EoSModel
    composition: FluidComposition


class EoSModel(str, Enum):
    SRK = "SRK"
    PR = "PR"
    GERG_SRK = "GERG_SRK"
    GERG_PR = "GERG_PR"


class FluidComposition(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True, frozen=True)
    water: float = Field(0.0, ge=0.0)
    nitrogen: float = Field(0.0, ge=0.0)
    CO2: float = Field(0.0, ge=0.0)
    methane: float = Field(0.0, ge=0.0)
    ethane: float = Field(0.0, ge=0.0)
    propane: float = Field(0.0, ge=0.0)
    i_butane: float = Field(0.0, ge=0.0)
    n_butane: float = Field(0.0, ge=0.0)
    i_pentane: float = Field(0.0, ge=0.0)
    n_pentane: float = Field(0.0, ge=0.0)
    n_hexane: float = Field(0.0, ge=0.0)

    def normalized(self) -> FluidComposition:
        """
        Returns a new FluidComposition instance with each component normalized so that
        the sum of all components equals 1.
        """
        # Using model_dump() for Pydantic v2
        data = self.model_dump()
        total = sum(data.values())
        if total == 0:
            raise ValueError("Total composition is 0; cannot normalize.")
        normalized_data = {key: value / total for key, value in data.items()}
        return self.__class__(**normalized_data)

    def items(self) -> list[tuple[str, float]]:
        """Return a list of component names and their values."""
        return list(self.__dict__.items())

    @property
    def molar_mass_mixture(self) -> float:
        """Calculate the molar mass of a fluid mixture using component molecular weights.

        Returns:
            float: The molar mass of the mixture in kg/mol
        """
        normalized_composition = self.normalized()
        molar_mass = 0.0
        for component, mole_fraction in normalized_composition.items():
            if mole_fraction > 0:  # Skip zero components
                molar_mass += mole_fraction * ThermodynamicConstants.get_component_molecular_weight(component)
        return molar_mass
