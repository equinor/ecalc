from abc import ABC, abstractmethod
from datetime import datetime
from functools import partial
from typing import Dict, Optional

from pydantic import Extra, Field
from pydantic.class_validators import validator
from pydantic.json import custom_pydantic_encoder

from libecalc.common.string.string_utils import generate_id, to_camel_case
from libecalc.dto.base import (
    ComponentType,
    ConsumerUserDefinedCategoryType,
    orjson_dumps,
)
from libecalc.expression import Expression
from libecalc.presentation.yaml.validation.yaml_validators import (
    ComponentNameStr,
    validate_temporal_model,
)
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.yaml_category_field import (
    CategoryField,
)
from libecalc.presentation.yaml.yaml_types.yaml_temporal_model import YamlTemporalModel
from libecalc.presentation.yaml.yaml_types.yaml_variable import YamlDefaultDatetime


class YamlEcalcBaseModel(YamlBase):
    class Config:
        extra = Extra.forbid
        alias_generator = to_camel_case
        allow_population_by_field_name = True
        json_dumps = orjson_dumps
        json_encoders = {
            datetime: lambda v: v.strftime("%Y-%m-%dT%H:%M:%S"),
            Expression: lambda e: str(e),
        }
        copy_on_model_validation = "deep"

    def json(self, date_format: Optional[str] = None, **kwargs) -> str:
        if date_format is None:
            return super().json(**kwargs)

        if kwargs.get("encoder") is None:
            # Override datetime encoder if not already overridden, use user specified date_format_option
            encoder = partial(
                custom_pydantic_encoder,
                {
                    datetime: lambda v: v.strftime(date_format),
                },
            )
        else:
            encoder = kwargs["encoder"]

        return super().json(**kwargs, encoder=encoder)  # Encoder becomes default, i.e. should handle unhandled types


class YamlComponent(YamlEcalcBaseModel, ABC):
    component_type: ComponentType

    @property
    @abstractmethod
    def id(self) -> str:
        ...


class YamlBaseComponent(YamlComponent, ABC):
    name: ComponentNameStr = Field(
        ...,
        title="NAME",
        description="Name of component",
    )

    regularity: Dict[YamlDefaultDatetime, Expression] = Field(
        ...,
        title="REGULARITY",
        description="Regularity",
    )
    _validate_base_temporal_model = validator("regularity", allow_reuse=True)(validate_temporal_model)


class YamlBaseEquipment(YamlBaseComponent, ABC):
    user_defined_category: YamlTemporalModel[ConsumerUserDefinedCategoryType] = CategoryField(
        ...,
    )

    @property
    def id(self) -> str:
        return generate_id(self.name)

    @validator("user_defined_category", pre=True, always=True)
    def check_user_defined_category(cls, user_defined_category, values):
        """Provide which value and context to make it easier for user to correct wrt mandatory changes."""
        if isinstance(user_defined_category, dict) and len(user_defined_category.values()) > 0:
            for user_category in user_defined_category.values():
                if user_category not in list(ConsumerUserDefinedCategoryType):
                    name = ""
                    if values.get("name") is not None:
                        name = f"with the name {values.get('name')}"

                    raise ValueError(
                        f"CATEGORY: {user_category} is not allowed for {cls.__name__} {name}. Valid categories are: {[(consumer_user_defined_category.value) for consumer_user_defined_category in ConsumerUserDefinedCategoryType]}"
                    )

        return user_defined_category
