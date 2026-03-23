import enum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.models.model_reference import ModelName
from libecalc.presentation.yaml.yaml_types.models.yaml_enums import YamlModelType


class YamlEosModel(str, enum.Enum):
    SRK = "SRK"
    PR = "PR"
    GERG_SRK = "GERG_SRK"
    GERG_PR = "GERG_PR"


class YamlFluidModelType(str, enum.Enum):
    PREDEFINED = "PREDEFINED"
    COMPOSITION = "COMPOSITION"


class YamlPredefinedFluidType(str, enum.Enum):
    ULTRA_DRY = "ULTRA_DRY"
    DRY = "DRY"
    MEDIUM = "MEDIUM"
    RICH = "RICH"
    ULTRA_RICH = "ULTRA_RICH"


class YamlPredefinedFluidModel(YamlBase):
    """Fluid model using a predefined fluid type."""

    eos_model: YamlEosModel = Field(
        YamlEosModel.SRK,
        title="EOS_MODEL",
        description="Equation of state model. Supported models are SRK, PR, GERG_SRK, GERG_PR",
    )
    fluid_model_type: Literal[YamlFluidModelType.PREDEFINED] = Field(
        YamlFluidModelType.PREDEFINED,
        title="FLUID_MODEL_TYPE",
        description="Defines the fluid model type.",
    )
    gas_type: YamlPredefinedFluidType | None = Field(
        None,
        title="GAS_TYPE",
        description="Predefined gas type. Supported types are ULTRA_DRY, DRY, MEDIUM, RICH, ULTRA_RICH",
    )
    name: ModelName = Field(
        ...,
        description="Name of the model. See documentation for more information.",
        title="NAME",
    )
    type: Literal[YamlModelType.FLUID] = Field(
        YamlModelType.FLUID,
        title="TYPE",
        description="Defines the type of model.",
    )

    def to_dto(self):
        raise NotImplementedError


class YamlComposition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    CO2: float = Field(0.0, title="CO2", description="Mole fraction of CO2")
    ethane: float = Field(0.0, title="ethane", description="Mole fraction of ethane")
    i_butane: float = Field(0.0, title="i_butane", description="Mole fraction of i-butane")
    i_pentane: float = Field(0.0, title="i_pentane", description="Mole fraction of i-pentane")
    methane: float = Field(..., title="methane", description="Mole fraction of methane (required)")
    n_butane: float = Field(0.0, title="n_butane", description="Mole fraction of n-butane")
    n_hexane: float = Field(0.0, title="n_hexane", description="Mole fraction of n-hexane")
    n_pentane: float = Field(0.0, title="n_pentane", description="Mole fraction of n-pentane")
    nitrogen: float = Field(0.0, title="nitrogen", description="Mole fraction of nitrogen")
    propane: float = Field(0.0, title="propane", description="Mole fraction of propane")
    water: float = Field(0.0, title="water", description="Mole fraction of water")


class YamlCompositionFluidModel(YamlBase):
    """Fluid model defined by a custom composition."""

    composition: YamlComposition = Field(
        ...,
        description="Components in fluid and amount (relative to the others) in mole weights",
        title="COMPOSITION",
    )
    eos_model: YamlEosModel | None = Field(
        YamlEosModel.SRK,
        title="EOS_MODEL",
        description="Equation of state model. Supported models are SRK, PR, GERG_SRK, GERG_PR",
    )
    fluid_model_type: Literal[YamlFluidModelType.COMPOSITION] = Field(
        YamlFluidModelType.COMPOSITION,
        title="FLUID_MODEL_TYPE",
        description="Defines the fluid model type.",
    )
    name: ModelName = Field(
        ...,
        description="Name of the model. See documentation for more information.",
        title="NAME",
    )
    type: Literal[YamlModelType.FLUID] = Field(
        YamlModelType.FLUID,
        title="TYPE",
        description="Defines the type of model.",
    )

    def to_dto(self):
        raise NotImplementedError


YamlFluidModel = Annotated[
    Union[YamlPredefinedFluidModel, YamlCompositionFluidModel], Field(discriminator="fluid_model_type")
]
