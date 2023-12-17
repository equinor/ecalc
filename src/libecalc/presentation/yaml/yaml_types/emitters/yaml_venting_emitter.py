from datetime import datetime
from typing import Dict

import numpy as np
from pydantic import Field
from pydantic.class_validators import validator

from libecalc.common.string.string_utils import generate_id
from libecalc.common.temporal_model import TemporalExpression, TemporalModel
from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    Rates,
    RateType,
    TimeSeriesStreamDayRate,
)
from libecalc.domain.venting_emitter import Emission, Rate, VentingEmitter
from libecalc.dto.base import ComponentType, ConsumerUserDefinedCategoryType
from libecalc.dto.variables import VariablesMap
from libecalc.expression import Expression
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.yaml_category_field import (
    CategoryField,
)
from libecalc.presentation.yaml.yaml_types.yaml_stream_conditions import YamlRate


class YamlVentingEmission(YamlBase):
    name: str = Field(
        ...,
        title="NAME",
        description="Name of emission",
    )

    rate: YamlRate = Field(..., title="RATE", description="The emission rate")


class YamlVentingEmitter(YamlBase):
    class Config:
        title = "VentingEmitter"

    component_type = ComponentType.VENTING_EMITTER

    name: str = Field(
        ...,
        title="NAME",
        description="Name of venting emitter",
    )

    emission: YamlVentingEmission = Field(
        ...,
        title="EMISSION",
        description="The emission",
    )

    category: ConsumerUserDefinedCategoryType = CategoryField(
        ...,
    )

    @property
    def id(self) -> str:
        return generate_id(self.name)

    @property
    def user_defined_category(self):
        return self.category

    def to_domain(self, variables_map: VariablesMap, regularity: Dict[datetime, Expression]) -> VentingEmitter:
        """
        Mapping from input YamlVentingEmitter to domain. Includes evaluating the rate expression.

        :param variables_map: map of all timeseries variables
        :param regularity: installation regularity
        :return: VentingEmitter domain object
        """
        rate = self.get_emission_rate(variables_map=variables_map, regularity=regularity).to_unit(Unit.TONS_PER_DAY)

        rate = Rate(
            value=rate,
            rate_type=self.emission.rate.type,
        )

        emission = Emission(
            name=self.emission.name,
            rate=rate,
        )

        venting_emitter = VentingEmitter(
            name=self.name,
            emission=emission,
            category=self.category,
            emitter_id=self.id,
            component_type=self.component_type,
        )

        return venting_emitter

    @validator("category", pre=True, always=True)
    def check_user_defined_category(cls, category, values):
        """Provide which value and context to make it easier for user to correct wrt mandatory changes."""
        if category is not None:
            if category not in list(ConsumerUserDefinedCategoryType):
                name = ""
                if values.get("name") is not None:
                    name = f"with the name {values.get('name')}"

                raise ValueError(
                    f"CATEGORY: {category} is not allowed for {cls.Config.title} {name}. Valid categories are: {[(consumer_user_defined_category.value) for consumer_user_defined_category in ConsumerUserDefinedCategoryType]}"
                )
        return category

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
