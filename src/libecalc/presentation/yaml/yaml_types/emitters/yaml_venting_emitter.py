import enum
from typing import Annotated, Literal, Union

from pydantic import (
    ConfigDict,
    Field,
    field_validator,
)
from pydantic_core.core_schema import ValidationInfo

from libecalc.common.component_type import ComponentType
from libecalc.common.string.string_utils import generate_id
from libecalc.dto.types import ConsumerUserDefinedCategoryType
from libecalc.dto.utils.validators import ComponentNameStr
from libecalc.expression.expression import ExpressionType
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.yaml_category_field import (
    CategoryField,
)
from libecalc.presentation.yaml.yaml_types.yaml_stream_conditions import (
    YamlEmissionRate,
    YamlOilVolumeRate,
)


class YamlVentingType(str, enum.Enum):
    OIL_VOLUME = "OIL_VOLUME"
    DIRECT_EMISSION = "DIRECT_EMISSION"


class YamlVentingVolumeEmission(YamlBase):
    name: str = Field(
        ...,
        title="NAME",
        description="Name of emission",
    )
    emission_factor: ExpressionType = Field(
        ..., title="EMISSION_FACTOR", description="Loading/storage volume-emission factor"
    )

    @field_validator("name", mode="before")
    def check_name(cls, name, info: ValidationInfo):
        """Make name case-insensitive"""
        return name.lower()


class YamlVentingVolume(YamlBase):
    rate: YamlOilVolumeRate = Field(..., title="RATE", description="The oil loading/storage volume or volume/rate")
    emissions: list[YamlVentingVolumeEmission] = Field(
        ...,
        title="EMISSIONS",
        description="The emission types and volume-emission-factors associated with oil loading/storage",
    )


class YamlVentingEmission(YamlBase):
    name: str = Field(
        ...,
        title="NAME",
        description="Name of emission",
    )
    rate: YamlEmissionRate = Field(..., title="RATE", description="The emission rate")

    @field_validator("name", mode="before")
    def check_name(cls, name, info: ValidationInfo):
        """Make name case-insensitive"""
        return name.lower()


class YamlDirectTypeEmitter(YamlBase):
    model_config = ConfigDict(title="VentingEmitter")

    @property
    def component_type(self):
        return ComponentType.VENTING_EMITTER

    @property
    def user_defined_category(self):
        return self.category

    @property
    def id(self) -> str:
        return generate_id(self.name)

    name: ComponentNameStr = Field(
        ...,
        title="NAME",
        description="Name of venting emitter",
    )

    category: ConsumerUserDefinedCategoryType = CategoryField(
        ...,
        validate_default=True,
    )

    type: Literal[YamlVentingType.DIRECT_EMISSION] = Field(
        title="TYPE",
        description="Type of venting emitter",
    )

    emissions: list[YamlVentingEmission] = Field(
        ...,
        title="EMISSIONS",
        description="The emissions for the emitter of type DIRECT_EMISSION",
    )

    @field_validator("category", mode="before")
    def check_user_defined_category(cls, category, info: ValidationInfo):
        """Provide which value and context to make it easier for user to correct wrt mandatory changes."""
        if category is not None:
            if category not in list(ConsumerUserDefinedCategoryType):
                name_context_string = ""
                if (name := info.data.get("name")) is not None:
                    name_context_string = f"with the name {name}"

                if info.config is not None and "title" in info.config:
                    entity_name = info.config["title"]
                else:
                    entity_name = str(cls)

                raise ValueError(
                    f"CATEGORY {category} is not allowed for {entity_name} {name_context_string}. Valid categories are: "
                    f"{', '.join(ConsumerUserDefinedCategoryType)}"
                )
        return category


class YamlOilTypeEmitter(YamlBase):
    model_config = ConfigDict(title="VentingEmitter")

    @property
    def component_type(self):
        return ComponentType.VENTING_EMITTER

    @property
    def user_defined_category(self):
        return self.category

    @property
    def id(self) -> str:
        return generate_id(self.name)

    name: ComponentNameStr = Field(
        ...,
        title="NAME",
        description="Name of venting emitter",
    )

    category: ConsumerUserDefinedCategoryType = CategoryField(
        ...,
        validate_default=True,
    )

    type: Literal[YamlVentingType.OIL_VOLUME] = Field(
        title="TYPE",
        description="Type of venting emitter",
    )

    volume: YamlVentingVolume = Field(
        ...,
        title="VOLUME",
        description="The volume rate and emissions for the emitter of type OIL_VOLUME",
    )

    @field_validator("category", mode="before")
    def check_user_defined_category(cls, category, info: ValidationInfo):
        """Provide which value and context to make it easier for user to correct wrt mandatory changes."""
        if category is not None:
            if category not in list(ConsumerUserDefinedCategoryType):
                name_context_string = ""
                if (name := info.data.get("name")) is not None:
                    name_context_string = f"with the name {name}"

                if info.config is not None and "title" in info.config:
                    entity_name = info.config["title"]
                else:
                    entity_name = str(cls)

                raise ValueError(
                    f"CATEGORY {category} is not allowed for {entity_name} {name_context_string}. Valid categories are: "
                    f"{', '.join(ConsumerUserDefinedCategoryType)}"
                )
        return category


YamlVentingEmitter = Annotated[Union[YamlOilTypeEmitter, YamlDirectTypeEmitter], Field(discriminator="type")]
