from datetime import datetime
from typing import Dict, Optional

import numpy as np
from pydantic import ConfigDict, Field, field_validator
from pydantic_core.core_schema import ValidationInfo

from libecalc.common.string.string_utils import generate_id
from libecalc.common.temporal_model import TemporalExpression, TemporalModel
from libecalc.common.utils.rates import (
    Rates,
    RateType,
    TimeSeriesStreamDayRate,
)
from libecalc.dto.base import ComponentType, ConsumerUserDefinedCategoryType
from libecalc.dto.utils.validators import ComponentNameStr
from libecalc.dto.variables import VariablesMap
from libecalc.expression import Expression
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.yaml_category_field import (
    CategoryField,
)
from libecalc.presentation.yaml.yaml_types.yaml_stream_conditions import (
    YamlEmissionRate,
)


class YamlVentingEmission(YamlBase):
    name: str = Field(
        ...,
        title="NAME",
        description="Name of emission",
    )
    emission_rate_to_volume_factor: Optional[float] = Field(
        None, title="FACTOR", description="Loading/storage volume-emission factor"
    )
    rate: YamlEmissionRate = Field(..., title="RATE", description="The emission rate")


class YamlVentingEmitter(YamlBase):
    model_config = ConfigDict(title="VentingEmitter")

    @property
    def component_type(self):
        return ComponentType.VENTING_EMITTER

    name: ComponentNameStr = Field(
        ...,
        title="NAME",
        description="Name of venting emitter",
    )

    category: ConsumerUserDefinedCategoryType = CategoryField(
        ...,
        validate_default=True,
    )

    emission: YamlVentingEmission = Field(
        ...,
        title="EMISSION",
        description="The emission",
    )

    @property
    def id(self) -> str:
        return generate_id(self.name)

    @property
    def user_defined_category(self):
        return self.category

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

    @field_validator("emission", mode="after")
    def check_volume_emission_factor(cls, emission, info: ValidationInfo):
        """Provide which value and context to make it easier for user to correct wrt mandatory changes."""
        category = info.data.get("category")
        name = ""

        if info.data.get("name") is not None:
            name = f"with the name {info.data.get('name')}"

        if emission.emission_rate_to_volume_factor is not None:
            if category not in [ConsumerUserDefinedCategoryType.LOADING, ConsumerUserDefinedCategoryType.STORAGE]:
                raise ValueError(
                    f"{cls.model_config['title']} {name}: It is not possible to specify FACTOR for CATEGORY {category}. "
                    f"The volume/emission factor in EMISSION is only allowed for the categories "
                    f"{ConsumerUserDefinedCategoryType.LOADING} and {ConsumerUserDefinedCategoryType.STORAGE}."
                )
        return emission

    def get_emission_rate(
        self, variables_map: VariablesMap, regularity: Dict[datetime, Expression]
    ) -> TimeSeriesStreamDayRate:
        regularity_evaluated = TemporalExpression.evaluate(
            temporal_expression=TemporalModel(regularity),
            variables_map=variables_map,
        )

        emission_rate = (
            Expression.setup_from_expression(value=self.emission.rate.value)
            .evaluate(variables=variables_map.variables, fill_length=len(variables_map.time_vector))
            .tolist()
        )

        # emission_rate = Unit.to(self.emission.rate.unit, Unit.KILO_PER_DAY)(emission_rate).tolist()

        if self.emission.rate.type == RateType.CALENDAR_DAY:
            emission_rate = Rates.to_stream_day(
                calendar_day_rates=np.asarray(emission_rate), regularity=regularity_evaluated
            ).tolist()

        return TimeSeriesStreamDayRate(
            timesteps=variables_map.time_vector,
            values=emission_rate,
            unit=self.emission.rate.unit,
        )
