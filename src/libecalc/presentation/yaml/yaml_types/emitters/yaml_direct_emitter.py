from pydantic import Field

from libecalc.dto.base import ConsumerUserDefinedCategoryType
from libecalc.expression.expression import ExpressionType
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.yaml_category_field import (
    CategoryField,
)
from libecalc.presentation.yaml.yaml_types.yaml_temporal_model import YamlTemporalModel


class YamlEmitterModel(YamlBase):
    emission_rate: ExpressionType = Field(
        ...,
        title="EMISSION_RATE",
        description="Emission rate expression [kg/day]",
    )


class YamlDirectEmitter(YamlBase):
    name: str = Field(
        ...,
        title="NAME",
        description="Name of the emitter.\n\n$ECALC_DOCS_KEYWORDS_URL/NAME",
    )
    category: YamlTemporalModel[ConsumerUserDefinedCategoryType] = CategoryField(
        ...,
    )
    emission_name: str = Field(
        ...,
        title="EMISSION_NAME",
        description="Name of emission",
    )
    emitter_model: YamlTemporalModel[YamlEmitterModel] = Field(
        ..., title="EMITTER_MODEL", description="The emitter model.\n\n$ECALC_DOCS_KEYWORDS_URL/EMITTER_MODEL"
    )
