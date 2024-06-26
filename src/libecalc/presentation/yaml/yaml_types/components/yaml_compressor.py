from datetime import datetime
from typing import Dict, Literal, Optional, Union

from pydantic import AfterValidator, ConfigDict, Field
from typing_extensions import Annotated

from libecalc import dto
from libecalc.common.time_utils import Period, define_time_model_for_period
from libecalc.dto.base import ComponentType
from libecalc.dto.components import CompressorComponent
from libecalc.dto.types import ConsumptionType
from libecalc.expression import Expression
from libecalc.presentation.yaml.mappers.utils import resolve_reference
from libecalc.presentation.yaml.yaml_entities import References
from libecalc.presentation.yaml.yaml_types.components.yaml_base import (
    YamlConsumerBase,
)
from libecalc.presentation.yaml.yaml_types.facility_model.yaml_facility_model import (
    YamlFacilityModelType,
)
from libecalc.presentation.yaml.yaml_types.models import YamlCompressorWithTurbine
from libecalc.presentation.yaml.yaml_types.models.model_reference import ModelName
from libecalc.presentation.yaml.yaml_types.models.model_reference_validation import (
    check_field_model_reference,
)
from libecalc.presentation.yaml.yaml_types.models.yaml_enums import YamlModelType
from libecalc.presentation.yaml.yaml_types.yaml_temporal_model import YamlTemporalModel

CompressorModel = Union[YamlCompressorWithTurbine]

ModelReference = Annotated[
    ModelName,
    AfterValidator(
        check_field_model_reference(
            allowed_types=[
                YamlFacilityModelType.TABULAR,
                YamlFacilityModelType.COMPRESSOR_TABULAR,
                YamlModelType.COMPRESSOR_CHART,
            ]
        )
    ),
]


class YamlCompressor(YamlConsumerBase):
    model_config = ConfigDict(title="Compressor")

    component_type: Literal[ComponentType.COMPRESSOR_V2] = Field(
        ...,
        title="TYPE",
        description="The type of the component",
        alias="TYPE",
    )

    energy_usage_model: YamlTemporalModel[ModelReference]

    def to_dto(
        self,
        consumes: ConsumptionType,
        regularity: Dict[datetime, Expression],
        target_period: Period,
        references: References,
        category: str,
        fuel: Optional[Dict[datetime, dto.types.FuelType]],
    ):
        return CompressorComponent(
            consumes=consumes,
            regularity=regularity,
            name=self.name,
            user_defined_category=define_time_model_for_period(self.category or category, target_period=target_period),
            fuel=fuel,
            energy_usage_model={
                timestep: resolve_reference(
                    value=reference,
                    references=references.models,
                )
                for timestep, reference in define_time_model_for_period(
                    self.energy_usage_model, target_period=target_period
                ).items()
            },
        )
