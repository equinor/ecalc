from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import YamlExpressionType
from libecalc.presentation.yaml.yaml_types.models.yaml_fluid import (
    YamlEosModel,
    YamlFluidModelType,
    YamlPredefinedFluidType,
)


class YamlFluidComposition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    water: YamlExpressionType = 0.0
    nitrogen: YamlExpressionType = 0.0
    CO2: YamlExpressionType = 0.0
    methane: YamlExpressionType
    ethane: YamlExpressionType = 0.0
    propane: YamlExpressionType = 0.0
    i_butane: YamlExpressionType = 0.0
    n_butane: YamlExpressionType = 0.0
    i_pentane: YamlExpressionType = 0.0
    n_pentane: YamlExpressionType = 0.0
    n_hexane: YamlExpressionType = 0.0


class YamlPredefinedFluidDefinition(YamlBase):
    type: Literal[YamlFluidModelType.PREDEFINED]
    eos_model: YamlEosModel = YamlEosModel.SRK
    gas_type: YamlPredefinedFluidType = YamlPredefinedFluidType.MEDIUM


class YamlCompositionFluidDefinition(YamlBase):
    type: Literal[YamlFluidModelType.COMPOSITION]
    eos_model: YamlEosModel = YamlEosModel.SRK
    composition: YamlFluidComposition


YamlFluidDefinition = Annotated[
    YamlPredefinedFluidDefinition | YamlCompositionFluidDefinition,
    Field(discriminator="type"),
]
