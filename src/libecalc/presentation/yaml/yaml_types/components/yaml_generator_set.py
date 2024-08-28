from typing import List, Optional, Union

from pydantic import ConfigDict, Field, field_validator, model_validator
from pydantic_core.core_schema import ValidationInfo
from typing_extensions import Annotated

from libecalc.common.discriminator_fallback import DiscriminatorWithFallback
from libecalc.dto.base import ConsumerUserDefinedCategoryType
from libecalc.dto.utils.validators import ComponentNameStr
from libecalc.expression.expression import ExpressionType
from libecalc.presentation.yaml.ltp_validation import (
    validate_generator_set_power_from_shore,
)
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
from libecalc.presentation.yaml.yaml_types.models.model_reference_validation import (
    GeneratorSetModelReference,
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
    electricity2fuel: YamlTemporalModel[GeneratorSetModelReference] = Field(
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

    # def to_core(self, test):
    #
    #
    #     return self

    @model_validator(mode="after")
    def check_power_from_shore(self):
        _check_power_from_shore_attributes = validate_generator_set_power_from_shore(
            cable_loss=self.cable_loss,
            max_usage_from_shore=self.max_usage_from_shore,
            model_fields=self.model_fields,
            category=self.category,
        )
        test = 1
        return self

    # @field_validator("electricity2fuel", mode="after")
    # def validate_genset_temporal_model(self, value):
    #     validate_temporal_model(self.model_fields[value])
    #     return self
    #
    # @field_validator("fuel", mode="after")
    # def validate_fuel_temporal_model(self, value):
    #     validate_temporal_model(self.model_fields[value])
    #     return self

    @field_validator("category", mode="before")
    def check_mandatory_category_for_generator_set(cls, user_defined_category, info: ValidationInfo):
        """This could be handled automatically with Pydantic, but I want to inform the users in a better way, in
        particular since we introduced a breaking change for this to be mandatory for GeneratorSets in v7.2.
        """
        if user_defined_category is None or user_defined_category == "":
            raise ValueError(f"CATEGORY is mandatory and must be set for '{info.data.get('name', cls.__name__)}'")

        return user_defined_category
