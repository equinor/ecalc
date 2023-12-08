import itertools
import operator
from dataclasses import dataclass
from functools import reduce
from typing import Dict, List, Union

from scipy.interpolate import interp1d

from libecalc.common.graph import Graph
from libecalc.common.stream_conditions import StreamConditions
from libecalc.core.consumers.compressor import Compressor
from libecalc.core.consumers.pump import Pump
from libecalc.core.models.compressor.train.utils.numeric_methods import find_root
from libecalc.core.result import EcalcModelResult
from libecalc.core.result.results import TrainResult
from libecalc.dto.components import Stream

DriverID = str
Consumer = Union[Pump, Compressor]
ConsumerID = str


@dataclass
class DriverNode:
    """
    Driver includes turbine, electric motor. https://petrowiki.spe.org/Pump_drivers
    """

    name: str

    @property
    def id(self) -> DriverID:
        return self.name


class ProcessFlowGraph:
    def __init__(self, consumers: List[Consumer], streams: List[Stream]):
        driver_graph = Graph()
        default_driver = DriverNode(name="common_driver")
        driver_graph.add_node(default_driver)
        for consumer in consumers:
            driver_graph.add_edge(from_id=consumer.id, to_id=default_driver.id)
        self._driver_graph = driver_graph

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

    def get_drivers(self) -> List[DriverNode]:
        return [node for node in self._driver_graph.nodes if isinstance(node, DriverNode)]

    def get_consumers_for_driver(self, driver: DriverNode) -> List[Consumer]:
        return [
            node
            for node in self._driver_graph.nodes.values()
            if node.id in self._driver_graph.get_predecessors(driver.id)
        ]

    def get_driver_for_consumer(self, consumer_id: ConsumerID) -> DriverNode:
        return self._driver_graph.get_node(self._driver_graph.get_successor(consumer_id))

    def get_driver(self, driver_id: DriverID) -> DriverNode:
        return self._driver_graph.get_node(driver_id)

    def get_sorted_consumers(self) -> List[Consumer]:
        return [self._train_graph.get_node(node_id) for node_id in self._train_graph.sorted_node_ids]

    def get_last_consumer_in_train(self) -> Consumer:
        return self._train_graph.get_node(self._train_graph.sorted_node_ids[-1])


class Driver:
    def __init__(self, consumers: List[Consumer]):
        self._consumers = consumers

    @property
    def speeds(self) -> List[int]:
        speeds_per_consumer = [consumer.get_supported_speeds() for consumer in self._consumers]

        # Intersect all speeds to get available speeds for driver
        return sorted(set.intersection(*[set(speeds_for_consumer) for speeds_for_consumer in speeds_per_consumer]))

    @property
    def min_speed(self):
        return min(self.speeds)

    @property
    def max_speed(self):
        return max(self.speeds)

    def get_speed_from_factor(self, factor: float) -> int:
        """
        Return a speed based on the given factor. 0 means min speed, 1 means max speed.
        Args:
            factor: float between 0 and 1

        Returns: the speed
        """
        max_speed = self.max_speed
        normalized_speeds = [speed / max_speed for speed in self.speeds]
        return interp1d(normalized_speeds, self.speeds)(factor)


class ConsumerResultHelper:
    """
    Wrapper around consumer result (EcalcModelResult) to help get the info we need. This class exist to avoid having to
    change the return type of consumers until we know more about how the result should look.
    """

    def __init__(self, consumer_result: EcalcModelResult):
        self.consumer_result = consumer_result

    @property
    def outlet_stream(self) -> StreamConditions:
        """
        Get the 'unhandled' stream that should continue into the next stage in the train. A 'handled' stream is a user
        specified outlet stream. The 'unhandled' stream should equal the inlet stream subtracted by the user specified
        outlet streams.
        Returns: the in-train outlet stream
        """
        # TODO: need to make sure other outlet streams are subtracted, and that -1 is the correct outlet stream

        # Convert back to single timestep StreamConditions
        outlet_time_series_stream_conditions = self.consumer_result.component_result.streams[-1]
        return outlet_time_series_stream_conditions.for_timestep(outlet_time_series_stream_conditions.rate.timesteps[0])

    def is_valid(self) -> bool:
        # We only calculate one timestep, but that is not how the results are represented
        return self.consumer_result.component_result.is_valid.values[0]


class TrainResultHelper:
    def __init__(
        self,
        consumer_results: Dict[ConsumerID, ConsumerResultHelper],
        process_flow_graph: ProcessFlowGraph,
    ):
        self.consumer_results = consumer_results
        self._process_flow_graph = process_flow_graph

    @property
    def is_valid(self) -> bool:
        return all(consumer_result.is_valid for consumer_result in self.consumer_results.values())

    @property
    def outlet_stream(self) -> StreamConditions:
        """
        Get the outlet stream for the train
        Returns: train outlet stream

        """
        last_consumer = self._process_flow_graph.get_last_consumer_in_train()
        last_consumer_result = self.consumer_results[last_consumer.id]
        return last_consumer_result.outlet_stream


class Train:
    def __init__(self, id: str, consumers: List[Consumer], streams: List[Stream]):
        self.id = id
        self.process_flow_graph = ProcessFlowGraph(consumers, streams)

    def _group_consumers_by_driver(self) -> Dict[DriverID, List[Consumer]]:
        return {
            driver.id: self.process_flow_graph.get_consumers_for_driver(driver)
            for driver in self.process_flow_graph.get_drivers()
        }

    def evaluate_speeds(
        self,
        speeds: Dict[DriverID, int],
        stream_conditions: Dict[ConsumerID, StreamConditions],
    ) -> TrainResultHelper:
        results: Dict[ConsumerID, ConsumerResultHelper] = {}

        sorted_consumers = self.process_flow_graph.get_sorted_consumers()

        for i in range(len(sorted_consumers)):
            previous_consumer = sorted_consumers[i - 1] if i >= 1 else None
            current_consumer = sorted_consumers[i]
            inlet_streams = self.process_flow_graph.get_inlet_streams(current_consumer.id)
            stream_conditions = [stream_conditions[inlet_stream.stream_name] for inlet_stream in inlet_streams]

            previous_consumer_outlet_stream = results[previous_consumer.id].outlet_stream

            stream_conditions = [previous_consumer_outlet_stream, *stream_conditions]
            driver = self.process_flow_graph.get_driver_for_consumer(current_consumer.id)
            speed = speeds[driver.id]

            # TODO: should we mix within consumer or here, outside consumer?
            #  There's really only one stream into a consumer, but it also makes sense to track the different streams.
            #  Maybe the stream object itself can keep track of the streams it consists of?
            #  I.e. when mixed keep the history?
            results[current_consumer.id] = ConsumerResultHelper(
                current_consumer.evaluate_with_speed(stream_conditions, speed)
            )
        return TrainResultHelper(results, process_flow_graph=self.process_flow_graph)

    def evaluate(self, stream_conditions: List[StreamConditions]):
        stream_conditions_map = {stream_condition.name: stream_condition for stream_condition in stream_conditions}

        consumers_by_driver = self._group_consumers_by_driver()
        driver_map = {driver_id: Driver(consumers) for driver_id, consumers in consumers_by_driver.items()}

        min_speeds = {driver_id: driver.min_speed for driver_id, driver in driver_map.items()}
        max_speeds = {driver_id: driver.max_speed for driver_id, driver in driver_map.items()}

        """
        Is this optimization (iterative problem?)? We are finding a solution, should we implement train as only
        evaluating specific scenarios, then wrap in a solver (or another name) that can figure out the
        conditions/scenario a train needs to run with to achieve the requested pressure. Makes sense if some external
        users want to figure out the conditions by using another method.
        """

        # check min and max speed for solution
        min_speed_result = self.evaluate_speeds(min_speeds, stream_conditions_map)
        max_speed_results = self.evaluate_speeds(max_speeds, stream_conditions_map)

        target_pressure = stream_conditions_map["outlet"].pressure

        if min_speed_result.outlet_stream.pressure <= target_pressure <= max_speed_results.outlet_stream.pressure:
            # A solution exists without pressure control
            results: Dict[float, TrainResultHelper] = {}

            def root_function(factor: float):
                speeds = {driver_id: driver.get_speed_from_factor(factor) for driver_id, driver in driver_map.items()}
                result = self.evaluate_speeds(speeds=speeds, stream_conditions=stream_conditions_map)
                results[factor] = result
                return result.outlet_stream.pressure - target_pressure

            root_factor = find_root(
                lower_bound=0,
                upper_bound=1,
                func=root_function,
            )

            train_result = results[root_factor]

            consumer_results = [
                consumer_result_helper.consumer_result.component_result
                for consumer_result_helper in train_result.consumer_results.values()
            ]

            return TrainResult(
                id=self.id,
                is_valid=reduce(
                    operator.mul,
                    [consumer_result.is_valid for consumer_result in consumer_results],
                ),
                timesteps=sorted(
                    {*itertools.chain(*(consumer_result.timesteps for consumer_result in consumer_results))}
                ),
                energy_usage=reduce(
                    operator.add,
                    [consumer_result.energy_usage for consumer_result in consumer_results],
                ),
                power=reduce(
                    operator.add,
                    [
                        consumer_result.power
                        for consumer_result in consumer_results
                        if consumer_result.power is not None
                    ],
                ),
            )
        else:
            raise NotImplementedError("Implement pressure control")

        # use find_root and driver.get_speed_from_factor to find a working speed.

        # evaluate max and min speed to check if solution exists, if not use ASV
        # ASV can reduce pressure, if we don't achieve high enough pressure when running max speed the conditions are
        # unsolvable.

        # Notes:
        # Don't support sampled in train, compressors should have a chart, and can therefore provide supported speeds.
        # Sampled can be used as a single Compressor, if it is actually a train that is modelled then that knowledge is
        # not contained in the eCalc model. That can be handled by meta-data.
