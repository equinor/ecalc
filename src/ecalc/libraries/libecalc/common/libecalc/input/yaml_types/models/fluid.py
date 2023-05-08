import enum
from typing import Literal, Optional, Union

from libecalc.input.yaml_types import YamlBase
from libecalc.input.yaml_types.models.enums import ModelType
from pydantic import BaseModel, Extra, Field
from typing_extensions import Annotated


class EosModel(enum.Enum):
    SRK = "SRK"
    PR = "PR"
    GERG_SRK = "GERG_SRK"
    GERG_PR = "GERG_PR"


class FluidModelType(enum.Enum):
    PREDEFINED = "PREDEFINED"
    COMPOSITION = "COMPOSITION"


class PredefinedFluidType(enum.Enum):
    ULTRA_DRY = "ULTRA_DRY"
    DRY = "DRY"
    MEDIUM = "MEDIUM"
    RICH = "RICH"
    ULTRA_RICH = "ULTRA_RICH"


class PredefinedFluidModel(YamlBase):
    eos_model: EosModel = EosModel.SRK
    fluid_model_type: Literal[FluidModelType.PREDEFINED] = FluidModelType.PREDEFINED
    gas_type: PredefinedFluidType = None
    name: str = Field(
        ...,
        description="Name of the model. See documentation for more information.",
        title="NAME",
    )
    type: ModelType.FLUID

    def to_dto(self):
        raise NotImplementedError


class Composition(BaseModel):
    class Config:
        extra = Extra.forbid

    CO2: float = 0.0
    H2O: float = 0.0
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


class CompositionFluidModel(YamlBase):
    composition: Composition = Field(
        ...,
        description="Components in fluid and amount (relative to the others) in mole weights",
        title="COMPOSITION",
    )
    eos_model: Optional[EosModel] = EosModel.SRK
    fluid_model_type: Literal[FluidModelType.COMPOSITION] = FluidModelType.COMPOSITION
    name: Optional[str] = Field(
        None,
        description="Name of the model. See documentation for more information.",
        title="NAME",
    )
    type: Literal[ModelType.FLUID] = ModelType.FLUID

    def to_dto(self):
        raise NotImplementedError


FluidModel = Annotated[Union[PredefinedFluidModel, CompositionFluidModel], Field(discriminator="fluid_model_type")]
