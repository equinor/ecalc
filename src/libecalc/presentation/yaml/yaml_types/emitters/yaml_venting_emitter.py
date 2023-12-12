from datetime import datetime
from typing import Dict

import numpy as np
from pydantic import Field

from libecalc.common.string.string_utils import generate_id
from libecalc.common.temporal_model import TemporalExpression, TemporalModel
from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    Rates,
    RateType,
    TimeSeriesStreamDayRate,
)
from libecalc.dto.base import ComponentType, ConsumerUserDefinedCategoryType
from libecalc.dto.variables import VariablesMap
from libecalc.expression import Expression
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.yaml_category_field import (
    CategoryField,
)
from libecalc.presentation.yaml.yaml_types.yaml_stream_conditions import YamlRate
from libecalc.presentation.yaml.yaml_types.yaml_temporal_model import YamlTemporalModel


class YamlVentingEmission(YamlBase):
    name: str = Field(
        ...,
        title="NAME",
        description="Name of emission",
    )

    rate: YamlRate = Field(..., title="RATE", description="The emission rate")


class YamlVentingEmitter(YamlBase):
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

    user_defined_category: YamlTemporalModel[ConsumerUserDefinedCategoryType] = CategoryField(
        ...,
    )

    @property
    def id(self) -> str:
        return generate_id(self.name)

    def get_emission_rate(
        self, variables_map: VariablesMap, regularity: Dict[datetime, Expression]
    ) -> TimeSeriesStreamDayRate:
        regularity_evaluated = TemporalExpression.evaluate(
            temporal_expression=TemporalModel(regularity),
            variables_map=variables_map,
        )

        emission_rate = Expression.setup_from_expression(value=self.emission.rate.value).evaluate(
            variables=variables_map.variables, fill_length=len(variables_map.time_vector)
        )

        emission_rate = Unit.to(self.emission.rate.unit, Unit.KILO_PER_DAY)(emission_rate).tolist()

        if self.emission.rate.rate_type == RateType.CALENDAR_DAY:
            emission_rate = Rates.to_stream_day(
                calendar_day_rates=np.asarray(emission_rate), regularity=regularity_evaluated
            ).tolist()

        return TimeSeriesStreamDayRate(
            timesteps=variables_map.time_vector,
            values=emission_rate,
            unit=self.emission.rate.unit,
        )
