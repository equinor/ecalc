from datetime import datetime
from typing import Literal, Optional, Union

from pydantic import ConfigDict, Field

from libecalc.common.component_type import ComponentType
from libecalc.common.consumption_type import ConsumptionType
from libecalc.common.time_utils import Period, define_time_model_for_period
from libecalc.domain.infrastructure.energy_components.compressor.component_dto import CompressorComponent
from libecalc.dto import FuelType
from libecalc.expression import Expression
from libecalc.presentation.yaml.domain.reference_service import ReferenceService
from libecalc.presentation.yaml.yaml_types.components.yaml_base import (
    YamlConsumerBase,
)
from libecalc.presentation.yaml.yaml_types.models import YamlCompressorWithTurbine
from libecalc.presentation.yaml.yaml_types.models.model_reference_validation import (
    CompressorV2ModelReference,
)
from libecalc.presentation.yaml.yaml_types.yaml_temporal_model import YamlTemporalModel

CompressorModel = Union[YamlCompressorWithTurbine]


class YamlCompressor(YamlConsumerBase):
    model_config = ConfigDict(title="Compressor")

    component_type: Literal[ComponentType.COMPRESSOR_V2] = Field(
        ...,
        title="TYPE",
        description="The type of the component",
        alias="TYPE",
    )

    energy_usage_model: YamlTemporalModel[CompressorV2ModelReference]

    def to_dto(
        self,
        consumes: ConsumptionType,
        regularity: dict[datetime, Expression],
        target_period: Period,
        references: ReferenceService,
        category: str,
        fuel: Optional[dict[datetime, FuelType]],
    ):
        return CompressorComponent(
            consumes=consumes,
            regularity=regularity,
            name=self.name,
            user_defined_category=define_time_model_for_period(self.category or category, target_period=target_period),
            fuel=fuel,
            energy_usage_model={
                timestep: references.get_compressor_model(reference)
                for timestep, reference in define_time_model_for_period(
                    self.energy_usage_model, target_period=target_period
                ).items()
            },
        )
