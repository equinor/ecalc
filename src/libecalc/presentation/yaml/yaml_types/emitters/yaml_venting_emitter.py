import enum
from datetime import datetime
from typing import Dict, List, Literal, Union

import numpy as np
from pydantic import (
    ConfigDict,
    Field,
    field_validator,
)
from pydantic_core.core_schema import ValidationInfo
from typing_extensions import Annotated

from libecalc.common.string.string_utils import generate_id
from libecalc.common.temporal_model import TemporalExpression, TemporalModel
from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    Rates,
    RateType,
    TimeSeriesFloat,
    TimeSeriesStreamDayRate,
)
from libecalc.dto.base import ComponentType, ConsumerUserDefinedCategoryType
from libecalc.dto.utils.validators import ComponentNameStr, convert_expression
from libecalc.dto.variables import VariablesMap
from libecalc.expression import Expression
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
        None, title="EMISSION_FACTOR", description="Loading/storage volume-emission factor"
    )


class YamlVentingVolume(YamlBase):
    rate: YamlOilVolumeRate = Field(..., title="RATE", description="The oil loading/storage volume or volume/rate")
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

    emissions: List[YamlVentingEmission] = Field(
        ...,
        title="EMISSIONS",
        description="The emissions for the emitter of type DIRECT_EMISSION",
    )

    def get_emissions(
        self, variables_map: VariablesMap, regularity: Dict[datetime, Expression]
    ) -> Dict[str, TimeSeriesStreamDayRate]:
        regularity_evaluated = TemporalExpression.evaluate(
            temporal_expression=TemporalModel(regularity),
            variables_map=variables_map,
        )

        emissions = {}
        for emission in self.emissions:
            emission_rate = (
                Expression.setup_from_expression(value=emission.rate.value)
                .evaluate(variables=variables_map.variables, fill_length=len(variables_map.time_vector))
                .tolist()
            )

            if emission.rate.type == RateType.CALENDAR_DAY:
                emission_rate = Rates.to_stream_day(
                    calendar_day_rates=np.asarray(emission_rate), regularity=regularity_evaluated
                ).tolist()

            emission_rate = Unit.to(emission.rate.unit, Unit.TONS_PER_DAY)(emission_rate)

            emissions[emission.name] = TimeSeriesStreamDayRate(
                timesteps=variables_map.time_vector,
                values=emission_rate,
                unit=Unit.TONS_PER_DAY,
            )
        return emissions

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

    def get_emissions(
        self,
        variables_map: VariablesMap,
        regularity: Dict[datetime, Expression],
    ) -> Dict[str, TimeSeriesStreamDayRate]:
        regularity_evaluated = TemporalExpression.evaluate(
            temporal_expression=TemporalModel(regularity),
            variables_map=variables_map,
        )

        oil_rates = (
            Expression.setup_from_expression(value=self.volume.rate.value)
            .evaluate(variables=variables_map.variables, fill_length=len(variables_map.time_vector))
            .tolist()
        )

        if self.volume.rate.type == RateType.CALENDAR_DAY:
            oil_rates = Rates.to_stream_day(
                calendar_day_rates=np.asarray(oil_rates),
                regularity=regularity_evaluated,
            ).tolist()

        emissions = {}
        for emission in self.volume.emissions:
            factors = (
                Expression.setup_from_expression(value=emission.emission_factor)
                .evaluate(variables=variables_map.variables, fill_length=len(variables_map.time_vector))
                .tolist()
            )
            oil_rates = Unit.to(self.volume.rate.unit, Unit.STANDARD_CUBIC_METER_PER_DAY)(oil_rates)
            emission_rate = [oil_rate * factor for oil_rate, factor in zip(oil_rates, factors)]

            # Emission factor is kg/Sm3 and oil rate/volume is Sm3/d. Hence, the emission rate is in kg/d:
            emission_rate = Unit.KILO_PER_DAY.to(Unit.TONS_PER_DAY)(emission_rate)

            emissions[emission.name] = TimeSeriesStreamDayRate(
                timesteps=variables_map.time_vector,
                values=emission_rate,
                unit=Unit.TONS_PER_DAY,
            )
        return emissions

    def get_oil_rates(
        self,
        variables_map: VariablesMap,
        regularity: TimeSeriesFloat,
    ) -> TimeSeriesStreamDayRate:
        oil_rates = Expression.evaluate(
            convert_expression(self.volume.rate.value),
            variables=variables_map.variables,
            fill_length=len(variables_map.time_vector),
        )

        if self.volume.rate.type == RateType.CALENDAR_DAY:
            oil_rates = Rates.to_stream_day(
                calendar_day_rates=np.asarray(oil_rates),
                regularity=regularity.values,
            ).tolist()

        oil_rates = self.volume.rate.unit.to(Unit.STANDARD_CUBIC_METER_PER_DAY)(oil_rates)

        return TimeSeriesStreamDayRate(
            timesteps=variables_map.time_vector,
            values=oil_rates,
            unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
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
