from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from libecalc.common.fluid_stream_type import FluidStreamType
from libecalc.common.string.string_utils import to_camel_case
from libecalc.domain.process.core.stream.thermo_constants import ThermodynamicConstants


class EcalcBaseModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        alias_generator=to_camel_case,
        populate_by_name=True,
    )


class FluidComposition(EcalcBaseModel):
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


class FluidModel(EcalcBaseModel):
    eos_model: EoSModel
    composition: FluidComposition


class FluidStream(FluidModel):
    pressure_bara: float
    temperature_kelvin: float
    density_kg_per_m3: float
    kappa: float
    z: float

    @classmethod
    def from_fluid_domain_object(cls, fluid_stream) -> FluidStream:
        return cls(
            eos_model=fluid_stream.fluid_model.eos_model,
            composition=fluid_stream.fluid_model.composition,
            pressure_bara=fluid_stream.pressure_bara,
            temperature_kelvin=fluid_stream.temperature_kelvin,
            density_kg_per_m3=fluid_stream.density,
            kappa=fluid_stream.kappa,
            z=fluid_stream.z,
        )


class MultipleStreamsAndPressureStream(EcalcBaseModel):
    name: str
    typ: FluidStreamType
    fluid_model: FluidModel | None = None

    @model_validator(mode="after")
    def validate_stream(self):
        stream_name, stream_type, stream_fluid_model = (
            self.name,
            self.typ,
            self.fluid_model,
        )
        if stream_type == FluidStreamType.INGOING and not isinstance(stream_fluid_model, FluidModel):
            raise ValueError(f"Stream {stream_name} is of type {stream_type} and needs a fluid model to be defined")
        if stream_type == FluidStreamType.OUTGOING and isinstance(stream_fluid_model, FluidModel):
            raise ValueError(f"Stream {stream_name} is of type {stream_type} and should not have a fluid model defined")
        return self


class EoSModel(str, Enum):
    SRK = "SRK"
    PR = "PR"
    GERG_SRK = "GERG_SRK"
    GERG_PR = "GERG_PR"
