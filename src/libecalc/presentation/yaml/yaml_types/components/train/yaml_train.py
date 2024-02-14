from datetime import datetime
from typing import Dict, Generic, List, Literal, Optional, TypeVar

from libecalc import dto
from libecalc.common.time_utils import Period
from libecalc.dto.base import ComponentType
from libecalc.dto.components import Stream, TrainComponent
from libecalc.dto.types import ConsumptionType
from libecalc.expression import Expression
from libecalc.presentation.yaml.yaml_entities import References
from libecalc.presentation.yaml.yaml_types.components.yaml_base import YamlConsumerBase
from libecalc.presentation.yaml.yaml_types.components.yaml_compressor import (
    YamlCompressor,
)
from libecalc.presentation.yaml.yaml_types.yaml_stream import YamlStream
from pydantic import Field

TYamlConsumer = TypeVar("TYamlConsumer", bound=YamlCompressor)


class YamlTrain(YamlConsumerBase, Generic[TYamlConsumer]):
    component_type: Literal[ComponentType.TRAIN_V2] = Field(
        ComponentType.TRAIN_V2,
        title="Type",
        description="The type of the component",
        alias="TYPE",
    )
    stages: List[TYamlConsumer]
    streams: List[YamlStream] = Field(default_factory=list, title="Streams", description="List of streams")

    def to_dto(
        self,
        consumes: ConsumptionType,
        regularity: Dict[datetime, Expression],
        target_period: Period,
        references: References,
        category: str,
        fuel: Optional[Dict[datetime, dto.types.FuelType]],
    ):
        stages = [
            consumer.to_dto(
                references=references,
                consumes=consumes,
                regularity=regularity,
                target_period=target_period,
                fuel=fuel,
                category=self.category or category,
            )
            for consumer in self.stages
        ]

        stage_name_to_id_map = {stage.name: stage.id for stage in stages}

        return TrainComponent(
            component_type=self.component_type,
            consumes=consumes,
            fuel=fuel,
            category=self.category or category,
            name=self.name,
            stages=stages,
            streams=[
                Stream(
                    stream_name=stream.name,
                    from_component_id=stage_name_to_id_map[stream.from_],
                    to_component_id=stage_name_to_id_map[stream.to],
                )
                for stream in self.streams
            ],
        )
