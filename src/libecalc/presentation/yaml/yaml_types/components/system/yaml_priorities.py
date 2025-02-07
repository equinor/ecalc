from libecalc.domain.infrastructure.energy_components.base.component_dto import Priorities, SystemStreamConditions
from libecalc.presentation.yaml.yaml_types.yaml_stream_conditions import YamlStreamConditions

PriorityID = str
StreamID = str
ConsumerID = str

YamlConsumerStreamConditions = dict[StreamID, YamlStreamConditions]
YamlConsumerStreamConditionsMap = dict[ConsumerID, YamlConsumerStreamConditions]
YamlPriorities = dict[PriorityID, YamlConsumerStreamConditionsMap]


def to_dto(yaml_priorities: YamlPriorities) -> Priorities[SystemStreamConditions]:
    priorities: Priorities[SystemStreamConditions] = {}
    for priority_id, consumer_map in yaml_priorities.items():
        priorities[priority_id] = {}
        for consumer_id, stream_conditions in consumer_map.items():
            priorities[priority_id][consumer_id] = {
                stream_name: SystemStreamConditions(
                    rate=stream_conditions.rate,
                    pressure=stream_conditions.pressure,
                    fluid_density=stream_conditions.fluid_density,
                )
                for stream_name, stream_conditions in stream_conditions.items()
            }
    return priorities
