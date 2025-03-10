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
    eos_model: YamlEosModel = YamlEosModel.SRK
    fluid_model_type: Literal[YamlFluidModelType.PREDEFINED] = YamlFluidModelType.PREDEFINED
    gas_type: YamlPredefinedFluidType = None
    name: ModelName = Field(
        ...,
        description="Name of the model. See documentation for more information.",
        title="NAME",
    )
    type: Literal[YamlModelType.FLUID]

    def to_dto(self):
        raise NotImplementedError


class YamlComposition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    CO2: float = 0.0
    ethane: float = 0.0
    i_butane: float = 0.0
    i_pentane: float = 0.0
    methane: float
    n_butane: float = 0.0
    n_hexane: float = 0.0
    n_pentane: float = 0.0
    nitrogen: float = 0.0
    propane: float = 0.0
    water: float = 0.0


class YamlCompositionFluidModel(YamlBase):
    composition: YamlComposition = Field(
        ...,
        description="Components in fluid and amount (relative to the others) in mole weights",
        title="COMPOSITION",
    )
    eos_model: YamlEosModel | None = YamlEosModel.SRK
    fluid_model_type: Literal[YamlFluidModelType.COMPOSITION] = YamlFluidModelType.COMPOSITION
    name: ModelName = Field(
        ...,
        description="Name of the model. See documentation for more information.",
        title="NAME",
    )
    type: Literal[YamlModelType.FLUID] = YamlModelType.FLUID

    def to_dto(self):
        raise NotImplementedError


YamlFluidModel = Annotated[
    Union[YamlPredefinedFluidModel, YamlCompositionFluidModel], Field(discriminator="fluid_model_type")
]
