from libecalc.presentation.yaml.yaml_types.yaml_stream_conditions import YamlStreamConditions

# PriorityID = str
# StreamID = str
# ConsumerID = str
#
# class YamlConsumerStreamConditions:
#     """Represents stream conditions for a specific consumer."""
#     def __init__(self, streams: dict[StreamID, YamlStreamConditions]):
#         self.streams = streams
#
#     def __repr__(self):
#         return f"YamlConsumerStreamConditions({self.streams})"
#
# class YamlConsumerStreamConditionsMap:
#     """Maps consumers to their respective stream conditions."""
#     def __init__(self, consumers: dict[ConsumerID, YamlConsumerStreamConditions]):
#         self.consumers = consumers
#
#     def __repr__(self):
#         return f"YamlConsumerStreamConditionsMap({self.consumers})"
#
# class YamlPriorities:
#     """Maps priority IDs to consumer stream condition maps."""
#     def __init__(self, priorities: dict[PriorityID, YamlConsumerStreamConditionsMap]):
#         self.priorities = priorities
#
#     def __repr__(self):
#         return f"YamlPriorities({self.priorities})"

PriorityID = str
StreamID = str
ConsumerID = str

YamlConsumerStreamConditions = dict[StreamID, YamlStreamConditions]
YamlConsumerStreamConditionsMap = dict[ConsumerID, YamlConsumerStreamConditions]
YamlPriorities = dict[PriorityID, YamlConsumerStreamConditionsMap]
