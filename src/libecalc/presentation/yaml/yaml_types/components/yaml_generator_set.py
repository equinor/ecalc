from typing import List, Optional, Union

from pydantic import ConfigDict, Field, model_validator
from typing_extensions import Annotated

from libecalc.common.discriminator_fallback import DiscriminatorWithFallback
from libecalc.dto.base import ConsumerUserDefinedCategoryType
from libecalc.dto.utils.validators import ComponentNameStr
from libecalc.expression.expression import ExpressionType
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.legacy.yaml_electricity_consumer import (
    YamlElectricityConsumer,
)
from libecalc.presentation.yaml.yaml_types.components.system.yaml_consumer_system import (
    YamlConsumerSystem,
)
from libecalc.presentation.yaml.yaml_types.components.yaml_category_field import (
    CategoryField,
)
from libecalc.presentation.yaml.yaml_types.yaml_temporal_model import YamlTemporalModel


class YamlGeneratorSet(YamlBase):
    model_config = ConfigDict(title="GeneratorSet")

    name: ComponentNameStr = Field(
        ...,
        title="NAME",
        description="Name of the generator set.\n\n$ECALC_DOCS_KEYWORDS_URL/NAME",
    )
    category: YamlTemporalModel[ConsumerUserDefinedCategoryType] = CategoryField(...)
    fuel: YamlTemporalModel[str] = Field(
        None,
        title="FUEL",
        description="The fuel used by the generator set." "\n\n$ECALC_DOCS_KEYWORDS_URL/FUEL",
    )
    electricity2fuel: YamlTemporalModel[str] = Field(
        ...,
        title="ELECTRICITY2FUEL",
        description="Specifies the correlation between the electric power delivered and the fuel burned by a "
        "generator set.\n\n$ECALC_DOCS_KEYWORDS_URL/ELECTRICITY2FUEL",
    )
    cable_loss: Optional[ExpressionType] = Field(
        None, title="CABLE_LOSS", description="Cable loss from shore, fraction of from shore consumption"
    )
    max_usage_from_shore: Optional[ExpressionType] = Field(
        None,
        title="MAX_USAGE_FROM_SHORE",
        description="The peak load/effect that is expected for one hour, per year (MW)",
    )
    consumers: List[
        Annotated[
            Union[
                YamlElectricityConsumer,
                YamlConsumerSystem,
            ],
            Field(discriminator="component_type"),
            DiscriminatorWithFallback("TYPE", "ELECTRICITY_CONSUMER"),
        ]
    ] = Field(
        ...,
        title="CONSUMERS",
        description="Consumers getting electrical power from the generator set.\n\n$ECALC_DOCS_KEYWORDS_URL/CONSUMERS",
    )

    @model_validator(mode="after")
    def check_power_from_shore(self):
        if self.cable_loss is not None or self.max_usage_from_shore is not None:
            if isinstance(self.category, ConsumerUserDefinedCategoryType):
                if self.category is not ConsumerUserDefinedCategoryType.POWER_FROM_SHORE:
                    raise ValueError(
                        f"{self.cable_loss.title} and {self.max_usage_from_shore.title} are only valid for the "
                        f"category {ConsumerUserDefinedCategoryType.POWER_FROM_SHORE}, not for "
                        f"{self.category}."
                    )
            else:
                if ConsumerUserDefinedCategoryType.POWER_FROM_SHORE not in self.category.values():
                    raise ValueError(
                        f"{self.cable_loss.title} and {self.max_usage_from_shore.title} are only valid for the "
                        f"category {ConsumerUserDefinedCategoryType.POWER_FROM_SHORE}."
                    )
        return self
