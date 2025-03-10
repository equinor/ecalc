from pydantic import ConfigDict, Field, model_validator

from libecalc.dto.types import ConsumerUserDefinedCategoryType
from libecalc.dto.utils.validators import ComponentNameStr
from libecalc.expression.expression import ExpressionType
from libecalc.presentation.yaml.ltp_validation import (
    validate_generator_set_power_from_shore,
)
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.legacy.yaml_electricity_consumer import (
    YamlElectricityConsumer,
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
    cable_loss: ExpressionType | None = Field(
        None, title="CABLE_LOSS", description="Cable loss from shore, fraction of from shore consumption"
    )
    max_usage_from_shore: ExpressionType | None = Field(
        None,
        title="MAX_USAGE_FROM_SHORE",
        description="The peak load/effect that is expected for one hour, per year (MW)",
    )
    consumers: list[YamlElectricityConsumer] = Field(
        ...,
        title="CONSUMERS",
        description="Consumers getting electrical power from the generator set.\n\n$ECALC_DOCS_KEYWORDS_URL/CONSUMERS",
    )

    @model_validator(mode="after")
    def check_power_from_shore(self):
        _check_power_from_shore_attributes = validate_generator_set_power_from_shore(
            cable_loss=self.cable_loss,
            max_usage_from_shore=self.max_usage_from_shore,
            category=self.category,
        )
        return self
