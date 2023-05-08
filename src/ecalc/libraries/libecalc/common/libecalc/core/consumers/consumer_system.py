import math
import operator
from abc import abstractmethod
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
from libecalc.dto import VariablesMap
from libecalc.dto.components import ConsumerComponent
from libecalc.dto.core_specs.compressor.operational_settings import (
    CompressorOperationalSettings,
)
from libecalc.dto.core_specs.pump.operational_settings import PumpOperationalSettings

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
    def __init__(self, id: str, consumers: List[ConsumerComponent]):
        self.id = id
        self._consumers = [create_consumer(consumer) for consumer in consumers]

    @staticmethod
    def _get_operational_settings_adjusted_for_crossover(
        operational_setting: SystemOperationalSettings,
        consumers: List[Consumer],
        variables_map: VariablesMap,
    ) -> Tuple[List[ConsumerOperationalSettings], List[Consumer]]:
        """Calculate operational settings for the current consumer, accounting for potential crossover from previous
        consumers.

        Todo: add unit test of this section. May consider to split this method since it is pretty big.
        """
        original_consumer_order_map = {consumer.id: consumer_index for consumer_index, consumer in enumerate(consumers)}
        sorted_consumers = ConsumerSystem._topologically_sort_consumers_by_crossover(
            crossover=operational_setting.crossover,
            consumers=consumers,
        )
        adjusted_operational_settings = []

        crossover_rates_map: Dict[int, List[List[float]]] = {
            consumer_index: [] for consumer_index in range(len(consumers))
        }

        # Converting from index 1 to index 0.
        crossover = [crossover_flow_to_index - 1 for crossover_flow_to_index in operational_setting.crossover]

        for consumer in sorted_consumers:
            consumer_index = original_consumer_order_map[consumer.id]
            consumer_operational_settings: ConsumerOperationalSettings = (
                operational_setting.get_consumer_operational_settings(
                    consumer_index, timesteps=variables_map.time_vector
                )
            )
            rates = [rate.values for rate in consumer_operational_settings.stream_day_rates]

            crossover_to = crossover[consumer_index]
            has_crossover_out = crossover_to >= 0
            if has_crossover_out:
                consumer = consumers[consumer_index]
                max_rate = consumer.get_max_rate(consumer_operational_settings)

                crossover_rate, rates = ConsumerSystem._get_crossover_rates(max_rate, rates)

                crossover_rates_map[crossover_to].append(list(crossover_rate))

            consumer_operational_settings.stream_day_rates = [
                TimeSeriesRate(
                    values=rate,
                    timesteps=variables_map.time_vector,
                    unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                )
                for rate in [*rates, *crossover_rates_map[consumer_index]]
            ]
            adjusted_operational_settings.append(consumer_operational_settings)
        return adjusted_operational_settings, sorted_consumers

    def evaluate(
        self,
        variables_map: VariablesMap,
        temporal_operational_settings: TemporalModel[List[SystemOperationalSettings]],
    ) -> EcalcModelResult:
        is_valid = TimeSeriesBoolean(
            timesteps=variables_map.time_vector, values=[False] * len(variables_map.time_vector), unit=Unit.NONE
        )
        energy_usage = TimeSeriesRate(
            timesteps=variables_map.time_vector,
            values=[0] * len(variables_map.time_vector),  # TODO: Initialize energy usage to NaN not zero 4084
            unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
            regularity=temporal_operational_settings.models[0].model[0].rates[0].regularity,
        )
        power = TimeSeriesRate(
            timesteps=variables_map.time_vector,
            values=[math.nan] * len(variables_map.time_vector),
            unit=Unit.MEGA_WATT,
            regularity=temporal_operational_settings.models[0].model[0].rates[0].regularity,
        )
        operational_settings_used = TimeSeriesInt(
            timesteps=variables_map.time_vector, values=[0] * len(variables_map.time_vector), unit=Unit.NONE
        )

        for period, operational_settings in temporal_operational_settings.items():
            variables_map_for_period = variables_map.get_subset_from_period(period)
            start_index, end_index = period.get_timestep_indices(variables_map.time_vector)

            for operational_setting_index, operational_setting in enumerate(operational_settings):
                (
                    adjusted_operational_settings,  # type: ignore[var-annotated]
                    sorted_consumers,
                ) = ConsumerSystem._get_operational_settings_adjusted_for_crossover(
                    operational_setting=operational_setting,
                    consumers=self._consumers,
                    variables_map=variables_map_for_period,
                )

                consumer_results = [
                    consumer.evaluate(adjusted_operational_setting)
                    for consumer, adjusted_operational_setting in zip(sorted_consumers, adjusted_operational_settings)
                ]

                is_operational_setting_valid = reduce(
                    operator.mul, [consumer_result.component_result.is_valid for consumer_result in consumer_results]
                )

                valid_indices_for_period = np.nonzero(is_operational_setting_valid.values)[0]
                if len(valid_indices_for_period) == 0:
                    # FIXME: Seems like valid indices is broken, always empty
                    continue
                valid_indices = [axis_indices + start_index for axis_indices in valid_indices_for_period]
                is_valid[valid_indices] = True

                energy_usage_for_period = reduce(
                    operator.add,
                    [consumer_result.component_result.energy_usage for consumer_result in consumer_results],
                )
                energy_usage[valid_indices] = energy_usage_for_period[valid_indices_for_period].values

                power_for_period = reduce(
                    operator.add,
                    [
                        (
                            consumer_result.component_result.power
                            or np.full_like(variables_map_for_period.time_vector, fill_value=0)
                        )
                        for consumer_result in consumer_results
                    ],
                    TimeSeriesRate(
                        timesteps=variables_map_for_period.time_vector,
                        values=[0] * variables_map_for_period.length,
                        unit=Unit.MEGA_WATT,
                        regularity=temporal_operational_settings.models[0].model[0].rates[0].regularity,
                    ),
                )
                power[valid_indices] = power_for_period[valid_indices_for_period].values

                operational_settings_used[valid_indices] = operational_setting_index + 1  # 1-based index

                if reduce(operator.mul, is_valid.values):
                    # quit as soon as all time-steps are valid. This means that we do not need to test all settings.
                    break

        consumer_result = ConsumerSystemResult(
            id=self.id,
            is_valid=is_valid,
            timesteps=variables_map.time_vector,
            energy_usage=energy_usage.to_calendar_day(),
            power=power,
            operational_settings_used=operational_settings_used,
        )

        # Fixme: We are missing model results for each operational setting tested....
        #    Since we will abandon model results, we could just output all single operational settings results
        #    into a big ball og mud in the models result?
        return EcalcModelResult(
            component_result=consumer_result,
            sub_components=[],  # Fixme: Add single consumer results and their model results in here.
            models=[],
        )

    @staticmethod
    def _topologically_sort_consumers_by_crossover(crossover: List[int], consumers: List[Consumer]) -> List[Consumer]:
        """Topological sort of the graph created by crossover. This makes it possible for us to evaluate each
        consumer with the correct rate directly.

        Parameters
        ----------
        crossover: list of indexes in consumers for crossover. 0 means no cross-over, 1 refers to first consumer etc.
        consumers

        Returns:
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
    def _get_crossover_rates(max_rate: List[float], rates: List[List[float]]) -> Tuple[np.ndarray, List[List[float]]]:
        total_rate = np.sum(rates, axis=0)
        crossover_rate = np.where(total_rate > max_rate, total_rate - max_rate, 0)
        rates_within_capacity = []
        left_over_crossover_rate = crossover_rate.copy()
        for rate in reversed(rates):
            # We handle the rates per stream backwards in order to forward inbound cross-overs first
            # if the compressor/pump in question (with inbound cross-over) is above capacity itself.
            diff = np.subtract(rate, left_over_crossover_rate)
            left_over_crossover_rate = np.where(diff < 0, diff, 0)
            rates_within_capacity.append(list(np.where(diff >= 0, diff, 0)))
        return crossover_rate, list(reversed(rates_within_capacity))
