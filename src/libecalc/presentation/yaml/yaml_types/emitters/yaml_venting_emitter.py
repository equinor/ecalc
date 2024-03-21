import enum
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np
from pydantic import ConfigDict, Field, field_validator, model_validator
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
from libecalc.expression.expression import ExpressionType
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.yaml_category_field import (
    CategoryField,
)
from libecalc.presentation.yaml.yaml_types.yaml_stream_conditions import (
    YamlEmissionRate,
)


class YamlVentingType(enum.Enum):
    OIL_VOLUME = "OIL_VOLUME"
    DIRECT_EMISSION = "DIRECT_EMISSION"


class YamlVentingVolumeEmission(YamlBase):
    name: str = Field(
        ...,
        title="NAME",
        description="Name of emission",
    )
    emission_factor: ExpressionType = Field(
        None, title="EMISSION_FACTOR", description="Loading/storage volume-emission factor"
    )


class YamlVentingVolume(YamlBase):
    rate: YamlEmissionRate = Field(..., title="RATE", description="The oil loading/storage volume or volume/rate")
    emissions: List[YamlVentingVolumeEmission] = Field(
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


class YamlVentingEmitter(YamlBase):
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

    type: YamlVentingType = Field(
        ...,
        title="TYPE",
        description="Type of venting emitter",
    )

    emissions: Optional[List[YamlVentingEmission]] = Field(
        None,
        title="EMISSIONS",
        description="The emissions for the emitter of type DIRECT_EMISSION",
    )

    volume: Optional[YamlVentingVolume] = Field(
        None,
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

    @model_validator(mode="after")
    def check_types(self):
        if self.emissions is None and self.volume is None:
            if self.type == YamlVentingType.DIRECT_EMISSION:
                raise ValueError(
                    f"The keyword EMISSIONS is required for VENTING_EMITTERS of TYPE {YamlVentingType.DIRECT_EMISSION.name}"
                )
            if self.type == YamlVentingType.OIL_VOLUME:
                raise ValueError(
                    f"The keyword VOLUME is required for VENTING_EMITTERS of TYPE {YamlVentingType.OIL_VOLUME.name}"
                )
        return self

    def get_emission_rates(
        self, variables_map: VariablesMap, regularity: Dict[datetime, Expression]
    ) -> Dict[str, TimeSeriesStreamDayRate]:
        regularity_evaluated = TemporalExpression.evaluate(
            temporal_expression=TemporalModel(regularity),
            variables_map=variables_map,
        )

        if self.type == YamlVentingType.DIRECT_EMISSION:
            emissions = self._get_direct_type_emissions(variables_map=variables_map, regularity=regularity_evaluated)

        else:
            emissions = self._get_oil_type_emissions(variables_map=variables_map, regularity=regularity_evaluated)

        return emissions

    def _get_oil_type_emissions(
        self,
        variables_map: VariablesMap,
        regularity: List[float],
    ) -> Dict[str, TimeSeriesStreamDayRate]:
        oil_rates = (
            Expression.setup_from_expression(value=self.volume.rate.value)
            .evaluate(variables=variables_map.variables, fill_length=len(variables_map.time_vector))
            .tolist()
        )

        if self.volume.rate.type == RateType.CALENDAR_DAY:
            oil_rates = Rates.to_stream_day(
                calendar_day_rates=np.asarray(oil_rates),
                regularity=regularity,
            ).tolist()

        emissions = {}
        for emission in self.volume.emissions:
            factors = (
                Expression.setup_from_expression(value=emission.emission_factor)
                .evaluate(variables=variables_map.variables, fill_length=len(variables_map.time_vector))
                .tolist()
            )
            emissions[emission.name] = TimeSeriesStreamDayRate(
                timesteps=variables_map.time_vector,
                values=[oil_rate * factor for oil_rate, factor in zip(oil_rates, factors)],
                unit=self.volume.rate.unit,
            )
        return emissions

    def _get_direct_type_emissions(
        self, variables_map: VariablesMap, regularity: List[float]
    ) -> Dict[str, TimeSeriesStreamDayRate]:
        emissions = {}
        for emission in self.emissions:
            emission_rate = (
                Expression.setup_from_expression(value=emission.rate.value)
                .evaluate(variables=variables_map.variables, fill_length=len(variables_map.time_vector))
                .tolist()
            )

            if emission.rate.type == RateType.CALENDAR_DAY:
                emission_rate = Rates.to_stream_day(
                    calendar_day_rates=np.asarray(emission_rate), regularity=regularity
                ).tolist()
            emissions[emission.name] = TimeSeriesStreamDayRate(
                timesteps=variables_map.time_vector,
                values=emission_rate,
                unit=emission.rate.unit,
            )
        return emissions
