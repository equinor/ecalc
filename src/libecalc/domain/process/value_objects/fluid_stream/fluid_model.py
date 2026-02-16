from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from libecalc.domain.process.value_objects.fluid_stream.constants import ThermodynamicConstants


# @dataclass(frozen=True)
class FluidModel(BaseModel):
    model_config = ConfigDict(frozen=True)  # TODO: Extra fields needed?

    eos_model: EoSModel
    composition: FluidComposition

    def __repr__(self) -> str:
        return f"FluidModel(eos_model={self.eos_model}, composition={self.composition})"

    def __str__(self) -> str:
        return self.__repr__()

    def __sub__(self, other: FluidModel) -> DeltaFluidModel:
        if not isinstance(other, FluidModel):
            raise TypeError(f"Unsupported operand type(s) for -: 'FluidModel' and '{type(other).__name__}'")

        if self.eos_model != other.eos_model:
            raise ValueError(
                f"Cannot subtract FluidModels with different EoS models: {self.eos_model} vs {other.eos_model}"
            )

        return DeltaFluidModel(
            eos_model=self.eos_model,  # Assuming EoS model doesn't change, otherwise we would need to handle this case ... is both not relevant nor possible
            composition=self.composition - other.composition,
        )


# @dataclass(frozen=True)
class DeltaFluidModel(FluidModel):
    """Represents the change in fluid model (composition/EoS), calculated as outlet - inlet."""

    def __repr__(self) -> str:
        change_string = ", ".join(
            filter(
                None,
                [
                    str(self.composition),
                ],
            )
        )

        return "" if not change_string else f"DeltaFluidModel({change_string})"


# @dataclass(frozen=True)
class EoSModel(str, Enum):
    SRK = "SRK"
    PR = "PR"
    GERG_SRK = "GERG_SRK"
    GERG_PR = "GERG_PR"


# @dataclass(frozen=True)
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

    def __repr__(self) -> str:
        return (
            f"FluidComposition(water={self.water}, nitrogen={self.nitrogen}, CO2={self.CO2}, "
            f"methane={self.methane}, ethane={self.ethane}, propane={self.propane}, i_butane={self.i_butane}, n_butane={self.n_butane}, "
            f"i_pentane={self.i_pentane}, n_pentane={self.n_pentane}, n_hexane={self.n_hexane})"
        )

    def __str__(self) -> str:
        return self.__repr__()

    def __sub__(self, other: FluidComposition) -> DeltaFluidComposition:
        if not isinstance(other, FluidComposition):
            raise TypeError(f"Unsupported operand type(s) for -: 'FluidComposition' and '{type(other).__name__}'")

        return DeltaFluidComposition(
            water=self.water - other.water,
            nitrogen=self.nitrogen - other.nitrogen,
            CO2=self.CO2 - other.CO2,
            methane=self.methane - other.methane,
            ethane=self.ethane - other.ethane,
            propane=self.propane - other.propane,
            i_butane=self.i_butane - other.i_butane,
            n_butane=self.n_butane - other.n_butane,
            i_pentane=self.i_pentane - other.i_pentane,
            n_pentane=self.n_pentane - other.n_pentane,
            n_hexane=self.n_hexane - other.n_hexane,
        )


# @dataclass(frozen=True)
class DeltaFluidComposition(FluidComposition):
    """Represents the change in fluid composition, calculated as outlet - inlet."""

    def __repr__(self) -> str:
        water = f"water: {self.water}" if self.water != 0.0 else ""
        nitrogen = f"nitrogen: {self.nitrogen}" if self.nitrogen != 0.0 else ""
        CO2 = f"CO2: {self.CO2}" if self.CO2 != 0.0 else ""
        methane = f"methane: {self.methane}" if self.methane != 0.0 else ""
        ethane = f"ethane: {self.ethane}" if self.ethane != 0.0 else ""
        propane = f"propane: {self.propane}" if self.propane != 0.0 else ""
        i_butane = f"i_butane: {self.i_butane}" if self.i_butane != 0.0 else ""
        n_butane = f"n_butane: {self.n_butane}" if self.n_butane != 0.0 else ""
        i_pentane = f"i_pentane: {self.i_pentane}" if self.i_pentane != 0.0 else ""
        n_pentane = f"n_pentane: {self.n_pentane}" if self.n_pentane != 0.0 else ""
        n_hexane = f"n_hexane: {self.n_hexane}" if self.n_hexane != 0.0 else ""

        change_string = ", ".join(
            filter(
                None,
                [
                    water,
                    nitrogen,
                    CO2,
                    methane,
                    ethane,
                    propane,
                    i_butane,
                    n_butane,
                    i_pentane,
                    n_pentane,
                    n_hexane,
                ],
            )
        )

        return "" if not change_string else f"DeltaFluidComposition({change_string})"
