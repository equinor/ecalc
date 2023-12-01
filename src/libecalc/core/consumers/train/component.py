from dataclasses import dataclass
from typing import Dict, List, Union

from libecalc.common.graph import Graph
from libecalc.common.stream_conditions import StreamConditions
from libecalc.core.consumers.compressor import Compressor
from libecalc.core.consumers.pump import Pump
from libecalc.core.result import EcalcModelResult
from libecalc.dto.components import Stream

TurbineID = str
Consumer = Union[Pump, Compressor]
ConsumerID = str


@dataclass
class Turbine:
    name: str

    @property
    def id(self) -> TurbineID:
        return self.name


class ProcessFlowGraph:
    def __init__(self, consumers: List[Consumer], streams: List[Stream]):
        turbine_graph = Graph()  # TODO: PowerProviderGraph? this could be generators instead of turbines
        default_turbine = Turbine(name="common_turbine")
        turbine_graph.add_node(default_turbine)
        for consumer in consumers:
            turbine_graph.add_edge(from_id=consumer.id, to_id=default_turbine.id)
        self._turbine_graph = turbine_graph

        train_graph = Graph()

        for consumer in consumers:
            train_graph.add_node(consumer)

        for stream in streams:
            train_graph.add_edge(
                from_id=stream.from_component_id,
                to_id=stream.to_component_id,
                name=stream.stream_name,
            )

        self._train_graph = train_graph

    def get_inlet_streams(self, consumer_id: ConsumerID) -> List[Stream]:
        return [
            Stream(
                from_id=from_id,
                to_id=to_id,
                name=name,
            )
            for from_id, to_id, name in self._train_graph.graph.in_edges(consumer_id, data="name")
        ]

    def get_turbines(self) -> List[Turbine]:
        return [node for node in self._turbine_graph.nodes if isinstance(node, Turbine)]

    def get_consumers_for_turbine(self, turbine: Turbine) -> List[Consumer]:
        return [
            node
            for node in self._turbine_graph.nodes.values()
            if node.id in self._turbine_graph.get_predecessors(turbine.id)
        ]

    def get_turbine_for_consumer(self, consumer_id: ConsumerID) -> Turbine:
        return self._turbine_graph.get_node(self._turbine_graph.get_successor(consumer_id))

    def get_turbine(self, turbine_id: TurbineID) -> Turbine:
        return self._turbine_graph.get_node(turbine_id)

    def get_sorted_consumers(self) -> List[Consumer]:
        return [self._train_graph.get_node(node_id) for node_id in self._train_graph.sorted_node_ids]


class Train:
    def __init__(self, consumers: List[Consumer], streams: List[Stream]):
        self.process_flow_graph = ProcessFlowGraph(consumers, streams)

    def _group_consumers_by_turbine(self) -> Dict[TurbineID, List[Consumer]]:
        return {
            turbine.id: self.process_flow_graph.get_consumers_for_turbine(turbine)
            for turbine in self.process_flow_graph.get_turbines()
        }

    def evaluate_speeds(
        self,
        speeds: Dict[TurbineID, int],
        stream_conditions: Dict[ConsumerID, StreamConditions],
    ) -> Dict[ConsumerID, EcalcModelResult]:
        turbines = self.process_flow_graph.get_turbines()
        if len(turbines) != len(speeds):
            raise ValueError("Mismatch turbine,speed")

        results: Dict[ConsumerID, EcalcModelResult] = {}

        sorted_consumers = self.process_flow_graph.get_sorted_consumers()

        for i in range(len(sorted_consumers)):
            previous_consumer = sorted_consumers[i - 1] if i >= 1 else None
            current_consumer = sorted_consumers[i]
            inlet_streams = self.process_flow_graph.get_inlet_streams(current_consumer.id)
            stream_conditions = [stream_conditions[inlet_stream.stream_name] for inlet_stream in inlet_streams]

            # TODO: need to make sure other outlet streams are subtracted, and that -1 is the correct outlet stream
            previous_consumer_outlet_stream = results[previous_consumer.id].component_result.streams[-1]

            stream_conditions = [previous_consumer_outlet_stream, *stream_conditions]
            turbine = self.process_flow_graph.get_turbine_for_consumer(current_consumer.id)
            speed = speeds[turbine.id]

            # TODO: should we mix within consumer or here, outside consumer?
            #  There's really only one stream into a consumer, but it also makes sense to track the different streams.
            #  Maybe the stream object itself can keep track of the streams it consists of?
            #  I.e. when mixed keep the history?
            results[current_consumer.id] = current_consumer.evaluate_with_speed(stream_conditions, speed)
        return results

    def evaluate(self, stream_conditions: List[StreamConditions]):
        stream_conditions_map = {stream_condition.name: stream_condition for stream_condition in stream_conditions}

        consumers_by_turbine = self._group_consumers_by_turbine()

        # get supported speeds for compressors by looking at which turbine they are connected to
        available_speeds_per_turbine: Dict[TurbineID, List[int]] = {}
        for turbine_id, consumers_for_turbine in consumers_by_turbine.items():
            speeds_per_consumer = [consumer.get_supported_speeds() for consumer in consumers_for_turbine]

            # Intersect all speeds to get available speeds for shaft
            available_speeds_for_turbine = sorted(
                set.intersection(*[set(speeds_for_consumer) for speeds_for_consumer in speeds_per_consumer])
            )
            available_speeds_per_turbine[turbine_id] = available_speeds_for_turbine

        min_speeds = {
            turbine_id: turbine_speeds[0] for turbine_id, turbine_speeds in available_speeds_per_turbine.items()
        }
        max_speeds = {
            turbine_id: turbine_speeds[-1] for turbine_id, turbine_speeds in available_speeds_per_turbine.items()
        }

        self.evaluate_speeds(min_speeds, stream_conditions_map)
        self.evaluate_speeds(max_speeds, stream_conditions_map)

        # evaluate max and min speed to check if solution exists, if not use ASV
        # ASV can reduce pressure, if we don't achieve high enough pressure when running max speed the conditions are
        # unsolvable.

        # Notes:
        # Don't support sampled in train, compressors should have a chart, and can therefore provide supported speeds.
        # Sampled can be used as a single Compressor, if it is actually a train that is modelled then that knowledge is
        # not contained in the eCalc model. That can be handled by meta-data.
