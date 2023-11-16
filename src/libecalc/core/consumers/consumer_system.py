import itertools
import operator
from functools import reduce
from typing import Dict, List, Optional, Protocol, Tuple, TypeVar, Union

import networkx as nx

from libecalc.common.priority_optimizer import EvaluatorResult
from libecalc.common.utils.rates import (
    TimeSeriesInt,
)
from libecalc.core.consumers.compressor import Compressor
from libecalc.core.consumers.pump import Pump
from libecalc.core.result import ComponentResult, ConsumerSystemResult, EcalcModelResult
from libecalc.domain.stream_conditions import Rate, StreamConditions

Consumer = TypeVar("Consumer", bound=Union[Compressor, Pump])


class Crossover(Protocol):
    stream_name: Optional[str]
    from_component_id: str
    to_component_id: str


class SystemComponentConditions(Protocol):
    crossover: List[Crossover]


class ConsumerSystem:
    """
    A system of possibly interdependent consumers and or other consumer systems.

    The motivation behind this construct is to enable simple heuristic optimization of operations by for example
    switching equipment on or off depending on operational characteristics such as rate of liquid entering a system
    of compressors. E.g. we have 2 compressors and the rate drops to a level that can be handled by a single compressor
    for a period of time -> Turn of compressor #2, and vice versa.
    """

    def __init__(
        self, id: str, consumers: List[Union[Compressor, Pump]], component_conditions: SystemComponentConditions
    ):
        self.id = id
        self._consumers = consumers
        self._component_conditions = component_conditions

    def _get_stream_conditions_adjusted_for_crossover(
        self,
        stream_conditions: Dict[str, List[StreamConditions]],
    ) -> Dict[str, List[StreamConditions]]:
        """
        Calculate stream conditions for the current consumer, accounting for potential crossover from previous
        consumers.
        """
        sorted_consumers = ConsumerSystem._topologically_sort_consumers_by_crossover(
            crossover=self._component_conditions.crossover,
            consumers=self._consumers,
        )
        adjusted_stream_conditions: Dict[str, List[StreamConditions]] = {}

        crossover_streams_map: Dict[str, List[StreamConditions]] = {consumer.id: [] for consumer in self._consumers}
        crossover_definitions_map: Dict[str, Crossover] = {
            crossover_stream.from_component_id: crossover_stream
            for crossover_stream in self._component_conditions.crossover
        }

        for consumer in sorted_consumers:
            consumer_stream_conditions = stream_conditions[consumer.id]
            inlet_streams = consumer_stream_conditions[
                :-1
            ]  # TODO: TERRIBLE! We should support multiple outlet streams, we need to be able to check if a stream is inlet or outlet here.

            # Currently only implemented for one crossover out per consumer
            crossover_stream_definition = crossover_definitions_map.get(consumer.id)
            has_crossover_out = crossover_stream_definition is not None
            if has_crossover_out:
                # TODO: Mix inlet streams and check pressure? Is consumer a Compressor or Pump or should it actually be trains also? Currently it is trains also.
                max_rate = consumer.get_max_rate(
                    inlet_stream=inlet_streams[0],
                    target_pressure=consumer_stream_conditions[-1].pressure,
                )
                crossover_stream, inlet_streams = ConsumerSystem._get_crossover_stream(
                    max_rate,
                    inlet_streams,
                    crossover_stream_name=crossover_stream_definition.stream_name
                    if crossover_stream_definition.stream_name is not None
                    else f"crossover-{crossover_stream_definition.from_component_id}-{crossover_stream_definition.to_component_id}",
                )
                crossover_streams_map[crossover_stream_definition.to_component_id].append(crossover_stream)

            adjusted_stream_conditions[consumer.id] = [
                *inlet_streams,
                *crossover_streams_map[consumer.id],
                consumer_stream_conditions[-1],
            ]

        return adjusted_stream_conditions

    def evaluate_consumers(self, system_stream_conditions: Dict[str, List[StreamConditions]]) -> List[EvaluatorResult]:
        """
        Function to evaluate the consumers in the system given stream conditions for a single point in time

        Args:
            system_stream_conditions:

        Returns: list of evaluator results

        """
        adjusted_system_stream_conditions = self._get_stream_conditions_adjusted_for_crossover(
            stream_conditions=system_stream_conditions,
        )
        consumer_results_for_priority = [
            consumer.evaluate(adjusted_system_stream_conditions[consumer.id]) for consumer in self._consumers
        ]
        return [
            EvaluatorResult(
                id=consumer_result_for_priority.component_result.id,
                result=consumer_result_for_priority,
                is_valid=consumer_result_for_priority.component_result.is_valid.values[0],
            )
            for consumer_result_for_priority in consumer_results_for_priority
        ]

    @staticmethod
    def get_system_result(
        id: str,
        consumer_results: List[ComponentResult],
        operational_settings_used: TimeSeriesInt,
    ) -> EcalcModelResult:
        """
        Get system result based on consumer results

        Notes:
            - We use 1-indexed operational settings output. We should consider changing this to default 0-index, and
                only convert when presenting results to the end-user.
        """

        consumer_system_result = ConsumerSystemResult(
            id=id,
            is_valid=reduce(
                operator.mul,
                [consumer_result.is_valid for consumer_result in consumer_results],
            ),
            timesteps=sorted({*itertools.chain(*(consumer_result.timesteps for consumer_result in consumer_results))}),
            energy_usage=reduce(
                operator.add,
                [consumer_result.energy_usage for consumer_result in consumer_results],
            ),
            power=reduce(
                operator.add,
                [consumer_result.power for consumer_result in consumer_results if consumer_result.power is not None],
            ),
            operational_settings_results=None,
            operational_settings_used=operational_settings_used,
        )

        return EcalcModelResult(
            component_result=consumer_system_result,
            sub_components=consumer_results,
            models=[],
        )

    @staticmethod
    def _topologically_sort_consumers_by_crossover(
        crossover: List[Crossover], consumers: List[Consumer]
    ) -> List[Consumer]:
        """Topological sort of the graph created by crossover. This makes it possible for us to evaluate each
        consumer with the correct rate directly.

        Parameters
        ----------
        crossover: list of crossover stream definitions
        consumers

        -------
        List of topological sorted consumers
        """
        graph = nx.DiGraph()
        for consumer in consumers:
            graph.add_node(consumer.id)

        for crossover_stream in crossover:
            graph.add_edge(crossover_stream.from_component_id, crossover_stream.to_component_id)

        consumers_by_id = {consumer.id: consumer for consumer in consumers}

        return [consumers_by_id[consumer_id] for consumer_id in nx.topological_sort(graph)]

    @staticmethod
    def _get_crossover_stream(
        max_rate: float, inlet_streams: List[StreamConditions], crossover_stream_name: str
    ) -> Tuple[StreamConditions, List[StreamConditions]]:
        """
        This function is run over a single consumer only, and is normally run in a for loop
        across all "dependent" consumers in the consumer system, such as here, in a consumer system.


        Args:
            max_rate: a list of max rates for one consumer, for each relevant timestep
            inlet_streams: list of incoming streams to this consumer. Usually this will have an outer list of length 1, since the consumer
            will only have 1 incoming rate. However, due to potential incoming crossover stream, and due to multistream outer length may be > 1. Length of the outer list is
            1 (standard incoming stream) at index 0, + nr of crossover streams + nr of additional incoming streams (multi stream)

        Returns:    1. the additional crossover stream that is required if the total incoming
        streams exceeds the max rate capacity for the consumer in question.
                    2. the streams within capacity of the given consumer
        """
        # Get total rate across all input rates for this consumer (incl already crossovers from other consumers, if any)
        total_stream = StreamConditions.mix_all(inlet_streams)

        # If we exceed total rate, we need to calculate exceeding rate, and return that as (potential) crossover rate to
        # another consumer
        crossover_stream = total_stream.copy(
            update={
                "rate": Rate(
                    value=total_stream.rate.value - max_rate if total_stream.rate.value > max_rate else 0,
                    unit=total_stream.rate.unit,
                ),
                "name": crossover_stream_name,
            },
        )

        streams_within_capacity = []
        left_over_crossover_stream = crossover_stream.copy()
        for inlet_stream in reversed(inlet_streams):
            # Inlet streams will have the requested streams first, then crossover streams. By reversing the list we
            # pass through the crossover rates first, then if needed, we reduce the requested inlet streams to capacity.
            rate_diff = inlet_stream.rate.value - left_over_crossover_stream.rate.value

            left_over_crossover_stream = left_over_crossover_stream.copy(
                update={
                    "rate": Rate(
                        value=abs(rate_diff) if rate_diff < 0 else 0, unit=left_over_crossover_stream.rate.unit
                    ),
                }
            )
            streams_within_capacity.append(
                inlet_stream.copy(
                    update={
                        "rate": Rate(value=rate_diff if rate_diff >= 0 else 0, unit=inlet_stream.rate.unit),
                    }
                )
            )
        return crossover_stream, list(reversed(streams_within_capacity))
