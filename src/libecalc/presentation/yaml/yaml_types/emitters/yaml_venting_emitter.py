from typing import Dict, Optional

import numpy as np
from pydantic import Field
from pydantic.class_validators import validator

from libecalc.common.temporal_model import TemporalExpression, TemporalModel
from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    Rates,
    RateType,
    TimeSeriesStreamDayRate,
)
from libecalc.dto.base import ComponentType
from libecalc.dto.variables import VariablesMap
from libecalc.expression import Expression
from libecalc.expression.expression import ExpressionType
from libecalc.presentation.yaml.validation.yaml_validators import (
    ComponentNameStr,
    EmissionNameStr,
    convert_expression,
    validate_temporal_model,
)
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords
from libecalc.presentation.yaml.yaml_types.components.yaml_category_field import (
    CategoryField,
)
from libecalc.presentation.yaml.yaml_types.yaml_temporal_model import YamlTemporalModel
from libecalc.presentation.yaml.yaml_types.yaml_to_core_base_models import (
    YamlBaseEquipment,
    YamlEcalcBaseModel,
)
from libecalc.presentation.yaml.yaml_types.yaml_variable import YamlDefaultDatetime


class YamlEmitterModel(YamlEcalcBaseModel):
    name: Optional[ComponentNameStr] = Field("", title="NAME", description="Name of emitter model")
    user_defined_category: Optional[str] = CategoryField(
        "",
    )

    emission_rate: ExpressionType = Field(
        ...,
        title="EMISSION_RATE",
        description="Emission rate expression [kg/day]",
    )
    emission_rate_type: RateType = Field(
        ...,
        title="EMISSION_RATE_TYPE",
        description="Emission rate type, calendar day or stream day",
    )
    regularity: Dict[YamlDefaultDatetime, Expression] = Field(
        ...,
        title="REGULARITY",
        description="Regularity",
    )

    _validate_regularity_temporal_model = validator("regularity", allow_reuse=True)(validate_temporal_model)
    _default_emission_rate = validator("emission_rate", allow_reuse=True)(convert_expression)


class YamlVentingEmitter(YamlBaseEquipment):
    component_type = ComponentType.VENTING_EMITTER

    emission_name: EmissionNameStr = Field(
        ...,
        title="EMISSION_NAME",
        description="Name of emission",
    )
    emitter_model: YamlTemporalModel[YamlEmitterModel] = Field(
        ..., title="EMITTER_MODEL", description="The emitter model.\n\n$ECALC_DOCS_KEYWORDS_URL/EMITTER_MODEL"
    )
    unit: Unit = Field(
        Unit.KILO_PER_DAY,
        title=EcalcYamlKeywords.emission_unit,
        description="Input unit for emission rate. Default is kg/day.",
    )

    def get_emission_rate(self, variables_map: VariablesMap) -> TimeSeriesStreamDayRate:
        emission_rate = []
        for period, model in TemporalModel(self.emitter_model).items():
            start_index, end_index = period.get_timestep_indices(variables_map.time_vector)
            variables_map_for_this_period = variables_map.get_subset(start_index=start_index, end_index=end_index)

            regularity_for_period_temporal = TemporalModel(dict(model.regularity.items()))
            emission_rate_for_period_temporal = TemporalModel({period.start: model.emission_rate})

            regularity_for_period = TemporalExpression.evaluate(
                temporal_expression=regularity_for_period_temporal,
                variables_map=variables_map_for_this_period,
            )
            emission_rate_for_period = TemporalExpression.evaluate(
                temporal_expression=emission_rate_for_period_temporal,
                variables_map=variables_map_for_this_period,
            )

            if model.emission_rate_type == RateType.CALENDAR_DAY:
                emission_rate_for_period = Rates.to_stream_day(
                    calendar_day_rates=np.asarray(emission_rate_for_period), regularity=regularity_for_period
                ).tolist()

            emission_rate.extend(emission_rate_for_period)

        return TimeSeriesStreamDayRate(
            timesteps=variables_map.time_vector,
            values=emission_rate,
            unit=self.unit,
        )

    _validate_emitter_model_temporal_model = validator("emitter_model", allow_reuse=True)(validate_temporal_model)
