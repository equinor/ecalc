import itertools
import operator
from abc import abstractmethod
from collections import defaultdict
from datetime import datetime
from functools import reduce
from typing import Dict, List, Protocol, Tuple, TypeVar, Union

import networkx as nx
import numpy as np
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    TimeSeriesBoolean,
    TimeSeriesInt,
    TimeSeriesRate,
)
from libecalc.core.consumers.base import BaseConsumer
from libecalc.core.consumers.compressor import Compressor
from libecalc.core.consumers.factory import create_consumer
from libecalc.core.consumers.pump import Pump
from libecalc.core.result import ConsumerSystemResult, EcalcModelResult
from libecalc.core.result.results import (
    CompressorResult,
    PumpResult,
)
from libecalc.dto import VariablesMap
from libecalc.dto.components import ConsumerComponent
from libecalc.dto.core_specs.compressor.operational_settings import (
    CompressorOperationalSettings,
)
from libecalc.dto.core_specs.pump.operational_settings import PumpOperationalSettings
from libecalc.dto.core_specs.system.operational_settings import (
    EvaluatedCompressorSystemOperationalSettings,
    EvaluatedPumpSystemOperationalSettings,
)
from numpy.typing import NDArray

Consumer = TypeVar("Consumer", bound=Union[Compressor, Pump])
ConsumerOperationalSettings = TypeVar(
    "ConsumerOperationalSettings", bound=Union[CompressorOperationalSettings, PumpOperationalSettings]
)


class SystemOperationalSettings(Protocol):
    crossover: List[int]

    @abstractmethod
    def get_consumer_operational_settings(
        self,
        consumer_index: int,
        timesteps: List[datetime],
    ) -> ConsumerOperationalSettings:  # type: ignore
        ...


class ConsumerSystem(BaseConsumer):
    """
    A system of possibly interdependent consumers and or other consumer systems.

    The motivation behind this construct is to enable simple heuristic optimization of operations by for example
    switching equipment on or off depending on operational characteristics such as rate of liquid entering a system
    of compressors. E.g. we have 2 compressors and the rate drops to a level that can be handled by a single compressor
    for a period of time -> Turn of compressor #2, and vice versa.
    """

    def __init__(self, id: str, consumers: List[ConsumerComponent]):
        self.id = id
        self._consumers = [create_consumer(consumer) for consumer in consumers]

    def _get_operational_settings_adjusted_for_crossover(
        self,
        operational_setting: Union[
            SystemOperationalSettings,
            EvaluatedPumpSystemOperationalSettings,
            EvaluatedCompressorSystemOperationalSettings,
        ],
        variables_map: VariablesMap,
    ) -> List[ConsumerOperationalSettings]:
        """
        Calculate operational settings for the current consumer, accounting for potential crossover from previous
        consumers.
        """
        sorted_consumers = ConsumerSystem._topologically_sort_consumers_by_crossover(
            crossover=operational_setting.crossover,
            consumers=self._consumers,
        )
        adjusted_operational_settings = []

        crossover_rates_map: Dict[int, List[List[float]]] = {
            consumer_index: [] for consumer_index in range(len(self._consumers))
        }

        # Converting from index 1 to index 0.
        crossover = [crossover_flow_to_index - 1 for crossover_flow_to_index in operational_setting.crossover]

        for consumer in sorted_consumers:
            consumer_index = self._consumers.index(consumer)
            consumer_operational_settings: ConsumerOperationalSettings = (
                operational_setting.get_consumer_operational_settings(
                    consumer_index, timesteps=variables_map.time_vector
                )
            )
            rates = [rate.values for rate in consumer_operational_settings.stream_day_rates]

            crossover_to = crossover[consumer_index]
            has_crossover_out = crossover_to >= 0
            if has_crossover_out:
                consumer = self._consumers[consumer_index]
                max_rate = consumer.get_max_rate(consumer_operational_settings)

                crossover_rate, rates = ConsumerSystem._get_crossover_rates(max_rate, rates)

                crossover_rates_map[crossover_to].append(list(crossover_rate))

            # TODO: Assume regularity same for all now (false assumption, to be handled shortly)
            regularity = consumer_operational_settings.stream_day_rates[0].regularity
            consumer_operational_settings.stream_day_rates = [
                TimeSeriesRate(
                    values=rate,
                    timesteps=variables_map.time_vector,
                    unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                    regularity=regularity,
                )
                for rate in [*rates, *crossover_rates_map[consumer_index]]
            ]
            adjusted_operational_settings.append(consumer_operational_settings)

        # This is a hack to return operational settings in the original order of the consumers. This way we can
        # compare the results of Consumer System V1 and V2.
        return [adjusted_operational_settings[sorted_consumers.index(consumer)] for consumer in self._consumers]

    def evaluate(
        self,
        variables_map: VariablesMap,
        temporal_operational_settings: TemporalModel[
            List[
                Union[
                    SystemOperationalSettings,
                    EvaluatedPumpSystemOperationalSettings,
                    EvaluatedCompressorSystemOperationalSettings,
                ]
            ]
        ],
    ) -> EcalcModelResult:
        """
        Evaluating a consumer system that may be composed of both consumers and other consumer systems. It will default
        to the last operational setting if all settings fails.

        Notes:
            - We use 1-indexed operational settings output. We should consider changing this to default 0-index, and
                only convert when presenting results to the end-user.
        """
        is_valid = TimeSeriesBoolean(
            timesteps=variables_map.time_vector, values=[False] * len(variables_map.time_vector), unit=Unit.NONE
        )
        operational_settings_used = TimeSeriesInt(
            timesteps=variables_map.time_vector, values=[0] * len(variables_map.time_vector), unit=Unit.NONE
        )
        operational_settings_results: Dict[datetime, Dict[int, Dict[str, EcalcModelResult]]] = defaultdict(
            dict
        )  # map operational settings index and consumer id to consumer result.

        for timestep_index, timestep in enumerate(variables_map.time_vector):
            variables_map_for_timestep = variables_map.get_subset_for_timestep(timestep)
            operational_settings_results[timestep] = defaultdict(dict)

            operational_settings = temporal_operational_settings.get_model(timestep)
            for operational_setting_index, operational_setting in enumerate(operational_settings):
                operational_setting_for_timestep = operational_setting.for_timestep(timestep)
                adjusted_operational_settings: List[
                    ConsumerOperationalSettings
                ] = self._get_operational_settings_adjusted_for_crossover(
                    operational_setting=operational_setting_for_timestep,
                    variables_map=variables_map_for_timestep,
                )

                for consumer, adjusted_operational_setting in zip(self._consumers, adjusted_operational_settings):
                    consumer_result = consumer.evaluate(adjusted_operational_setting)
                    operational_settings_results[timestep][operational_setting_index][consumer.id] = consumer_result

                consumer_results = operational_settings_results[timestep][operational_setting_index].values()

                # Check if consumers are valid for this operational setting, should be valid for all consumers
                all_consumer_results_valid = reduce(
                    operator.mul, [consumer_result.component_result.is_valid for consumer_result in consumer_results]
                )
                all_consumer_results_valid_indices = np.nonzero(all_consumer_results_valid.values)[0]
                all_consumer_results_valid_indices_period_shifted = [
                    axis_indices + timestep_index for axis_indices in all_consumer_results_valid_indices
                ]

                # Remove already valid indices, so we don't overwrite operational setting used with the latest valid
                new_valid_indices = [
                    i for i in all_consumer_results_valid_indices_period_shifted if not is_valid.values[i]
                ]

                # Register the valid timesteps as valid and keep track of the operational setting used
                is_valid[new_valid_indices] = True
                operational_settings_used[new_valid_indices] = operational_setting_index

                if all(is_valid.values):
                    # quit as soon as all time-steps are valid. This means that we do not need to test all settings.
                    break
                elif operational_setting_index + 1 == len(operational_settings):
                    # If we are at the last operational_setting and not all indices are valid
                    invalid_indices = [i for i, x in enumerate(is_valid.values) if not x]
                    operational_settings_used[invalid_indices] = [operational_setting_index for _ in invalid_indices]

        # Avoid mistakes after this point by not using defaultdict
        operational_settings_results = dict(operational_settings_results)

        consumer_results = self.collect_consumer_results(operational_settings_used, operational_settings_results)

        # Change to 1-index operational_settings_used
        for index, value in enumerate(operational_settings_used.values):
            operational_settings_used[index] = value + 1

        consumer_system_result = ConsumerSystemResult(
            id=self.id,
            is_valid=is_valid,
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

    def collect_consumer_results(
        self,
        operational_settings_used: TimeSeriesInt,
        operational_settings_results: Dict[datetime, Dict[int, Dict[str, EcalcModelResult]]],
    ) -> List[Union[CompressorResult, PumpResult]]:
        """
        Merge consumer results into a single result per consumer based on the operational settings used. I.e. pick results
        from the correct operational setting result and merge into a single result per consumer.
        Args:
            operational_settings_used:
            operational_settings_results:

        Returns:

        """
        consumer_results: Dict[str, Union[CompressorResult, PumpResult]] = {}
        for consumer in self._consumers:
            for timestep_index, timestep in enumerate(operational_settings_used.timesteps):
                operational_setting_used = operational_settings_used.values[timestep_index]
                prev_result = consumer_results.get(consumer.id)
                consumer_result_subset = operational_settings_results[timestep][operational_setting_used][
                    consumer.id
                ].component_result

                if prev_result is None:
                    consumer_results[consumer.id] = consumer_result_subset
                else:
                    consumer_results[consumer.id] = prev_result.merge(consumer_result_subset)

        return list(consumer_results.values())

    @staticmethod
    def _topologically_sort_consumers_by_crossover(crossover: List[int], consumers: List[Consumer]) -> List[Consumer]:
        """Topological sort of the graph created by crossover. This makes it possible for us to evaluate each
        consumer with the correct rate directly.

        Parameters
        ----------
        crossover: list of indexes in consumers for crossover. 0 means no cross-over, 1 refers to first consumer etc.
        consumers

        -------
        List of topological sorted consumers
        """
        zero_indexed_crossover = [i - 1 for i in crossover]  # Use zero-index
        graph = nx.DiGraph()
        for consumer_index in range(len(consumers)):
            graph.add_node(consumer_index)

        for this, other in enumerate(zero_indexed_crossover):
            # No crossover (0) => -1 in zero-indexed crossover
            if other >= 0:
                graph.add_edge(this, other)

        return [consumers[consumer_index] for consumer_index in nx.topological_sort(graph)]

    @staticmethod
    def _get_crossover_rates(
        max_rate: List[float], rates: List[List[float]]
    ) -> Tuple[NDArray[np.float64], List[List[float]]]:
        """
        This function is run over a single consumer only, and is normally run in a for loop
        across all "dependent" consumers in the consumer system, such as here, in a consumer system.


        Args:
            max_rate: a list of max rates for one consumer, for each relevant timestep
            rates: list of list of the rates being sent in to this consumer. Usually this will have an outer list of length 1, since the consumer
            will only have 1 incoming rate. However, due to potential incoming crossover rate, and due to multistream outer length may be > 1. Length of the outer list is
            1 (standard incoming stream) at index 0, + nr of crossover streams + nr of additional incoming streams (multi stream)

        Returns:    1. the additional crossover rate that is required if the total incoming
        rate exceeds the max rate capacity for the consumer in question.
                    2. the rates within capacity of the given consumer
        """

        # Get total rate across all input rates for this consumer (incl already crossovers from other consumers, if any)
        total_rate = np.sum(rates, axis=0)

        # If we exceed total rate, we need to calculate exceeding rate, and return that as (potential) crossover rate to
        # another consumer
        crossover_rate = np.where(total_rate > max_rate, total_rate - max_rate, 0)

        rates_within_capacity = []
        left_over_crossover_rate = crossover_rate.copy()
        for rate in reversed(rates):
            # We handle the rates per stream backwards in order to forward inbound cross-overs first
            # if the compressor/pump in question (with inbound cross-over) is above capacity itself.
            diff = np.subtract(rate, left_over_crossover_rate)
            left_over_crossover_rate = np.where(diff < 0, np.absolute(diff), 0)
            rates_within_capacity.append(list(np.where(diff >= 0, diff, 0)))
        return crossover_rate, list(reversed(rates_within_capacity))
