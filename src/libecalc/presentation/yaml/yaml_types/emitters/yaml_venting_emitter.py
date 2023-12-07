from datetime import datetime
from typing import Dict, Optional

from pydantic import Field, ValidationError
from pydantic.class_validators import validator

from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period, define_time_model_for_period
from libecalc.common.utils.rates import RateType
from libecalc.dto.base import ComponentType
from libecalc.expression import Expression
from libecalc.expression.expression import ExpressionType
from libecalc.presentation.yaml.validation.yaml_validators import (
    ComponentNameStr,
    EmissionNameStr,
    convert_expression,
    validate_temporal_model,
)

# from libecalc.presentation.yaml.validation_errors import (
#     DtoValidationError
# )
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
    regularity: Dict[datetime, Expression] = Field(
        ...,
        title="REGULARITY",
        description="Regularity",
    )

    _validate_regularity_temporal_model = validator("regularity", allow_reuse=True)(validate_temporal_model)
    _default_emission_rate = validator("emission_rate", allow_reuse=True)(convert_expression)


class YamlTemporalEmitterModel:
    def __init__(self, target_period: Period):
        self._target_period = target_period

    @staticmethod
    def create_model(model: Dict, regularity: Dict[datetime, Expression]):
        emission_rate = model.get(EcalcYamlKeywords.installation_venting_emitter_emission_rate)
        emission_rate_type = model.get(EcalcYamlKeywords.venting_emitter_rate_type) or RateType.STREAM_DAY
        try:
            return YamlEmitterModel(
                emission_rate=emission_rate,
                regularity=regularity,
                emission_rate_type=emission_rate_type,
            )
        except ValidationError as e:
            raise ValueError(e) from e  # Got circular import issues with DtoValidationError...

    def get_model(
        self, data: Optional[Dict], regularity: Dict[datetime, Expression]
    ) -> Dict[YamlDefaultDatetime, YamlEmitterModel]:
        time_adjusted_model = define_time_model_for_period(data, target_period=self._target_period)
        return {
            YamlDefaultDatetime.date_to_datetime(start_date): self.create_model(model, regularity=regularity)
            for start_date, model in time_adjusted_model.items()
        }


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

    @property
    def temporal_emission_rate_model(self):
        return TemporalModel(
            {start_time: emitter_model.emission_rate for start_time, emitter_model in self.emitter_model.items()}
        )

    @property
    def temporal_regularity_model(self):
        return TemporalModel(
            {
                regularity_time: regularity
                for model_time, emitter_model in self.emitter_model.items()
                for regularity_time, regularity in emitter_model.regularity.items()
            }
        )

    _validate_emitter_model_temporal_model = validator("emitter_model", allow_reuse=True)(validate_temporal_model)
