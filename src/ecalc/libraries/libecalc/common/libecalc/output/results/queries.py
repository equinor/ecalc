import abc
from collections import defaultdict
from datetime import datetime
from typing import DefaultDict, Dict, List, Optional

import libecalc.dto
from libecalc.common.feature_flags import Feature
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Frequency, resample_time_steps
from libecalc.common.units import Unit
from libecalc.common.utils.rates import TimeSeriesVolumes
from libecalc.core.graph_result import GraphResult
from libecalc.core.result import GeneratorSetResult


class Query(abc.ABC):
    """a type of action....filter, aggregator etc...combine fields? etc.
    Different types of filters? ie aggregators etc...or whatever..
    it should know itself what to do...just add new ones...
    """

    @abc.abstractmethod
    def query(
        self,
        installation_graph: GraphResult,
        unit: Unit,
        frequency: Frequency,
    ) -> Optional[Dict[datetime, float]]:
        pass


class FuelQuery(Query):
    """Filter is:
        * Filter
        * Unit Converter
        * Aggregator.

    perhaps we should separate those somehow...or just call it an action....?!
    an action can have one or more of those...?! too complex...
    filter and aggregates...divide in 2 steps? 1. get stuff, then aggregate?

    Allow to filter on fuel name and/or fuel type,
    that aggregates on installation

    If a filter is not specified, it is interpreted as
    no filter; ie all are used in aggregation
    """

    def __init__(
        self,
        consumer_categories: Optional[List[str]] = None,
        installation_category: Optional[str] = None,
        fuel_type_category: Optional[str] = None,
    ):
        self.consumer_categories = consumer_categories
        self.installation_category = installation_category
        self.fuel_type_category = fuel_type_category

    def query(
        self,
        installation_graph: GraphResult,
        unit: Unit,
        frequency: Frequency,
    ) -> Optional[Dict[datetime, float]]:
        installation_dto = installation_graph.graph.get_component(installation_graph.graph.root)

        installation_time_steps = installation_graph.timesteps
        time_steps = resample_time_steps(
            frequency=frequency,
            time_steps=installation_time_steps,
        )

        aggregated_result: DefaultDict[datetime, float] = defaultdict(float)
        aggregated_result_volume = {}

        if self.installation_category is None or installation_dto.user_defined_category == self.installation_category:
            for fuel_consumer in installation_dto.fuel_consumers:
                temporal_category = TemporalModel(fuel_consumer.user_defined_category)
                for period, category in temporal_category.items():
                    if self.consumer_categories is None or category in self.consumer_categories:
                        fuel_consumer_result = installation_graph.get_energy_result(fuel_consumer.id)
                        fuel_volumes = fuel_consumer_result.energy_usage.for_period(period).to_volumes()

                        fuel_temporal_model = TemporalModel(fuel_consumer.fuel)
                        for timestep, fuel_volume in fuel_volumes.datapoints():
                            fuel_model = fuel_temporal_model.get_model(timestep)
                            fuel_category = fuel_model.user_defined_category

                            if fuel_volume is not None:
                                if self.fuel_type_category is None or fuel_category == self.fuel_type_category:
                                    aggregated_result[timestep] += fuel_volume

            if aggregated_result:
                sorted_result = dict(sorted(zip(aggregated_result.keys(), aggregated_result.values())))
                sorted_result = {**dict.fromkeys(installation_time_steps, 0.0), **sorted_result}
                date_keys = list(sorted_result.keys())
                #  Last timestep is removed in check above (fuel_volume is None). Needed back for re-indexing:
                # date_keys.append(installation_time_steps[-1])
                reindexed_result = (
                    TimeSeriesVolumes(timesteps=date_keys, values=list(sorted_result.values())[:-1], unit=unit)
                    .reindex(time_steps)
                    .fill_nan(0)
                )

                aggregated_result_volume = {
                    reindexed_result.timesteps[i]: reindexed_result.values[i] for i in range(len(reindexed_result))
                }
        return aggregated_result_volume if aggregated_result_volume else None


class EmissionQuery(Query):
    def __init__(
        self,
        installation_category: Optional[str] = None,
        consumer_categories: Optional[List[str]] = None,
        fuel_type_category: Optional[str] = None,
        emission_type: Optional[str] = None,
    ):
        self.installation_category = installation_category
        self.consumer_categories = consumer_categories
        self.fuel_type_category = fuel_type_category
        self.emission_type = emission_type

    def query(
        self,
        installation_graph: GraphResult,
        unit: Unit,
        frequency: Frequency,
    ) -> Optional[Dict[datetime, float]]:
        installation_dto = installation_graph.graph.get_component(installation_graph.graph.root)

        installation_time_steps = installation_graph.timesteps
        time_steps = resample_time_steps(
            frequency=frequency,
            time_steps=installation_time_steps,
        )

        aggregated_result_volume = {}
        aggregated_result: Dict[datetime, float] = defaultdict(float)
        unit_in = None

        if self.installation_category is None or installation_dto.user_defined_category == self.installation_category:
            for fuel_consumer in installation_dto.fuel_consumers:
                temporal_category = TemporalModel(fuel_consumer.user_defined_category)
                for period, category in temporal_category.items():
                    if self.consumer_categories is None or category in self.consumer_categories:
                        fuel_temporal_model = TemporalModel(fuel_consumer.fuel)

                        emissions = installation_graph.get_emissions(fuel_consumer.id)

                        for emission in emissions.values():
                            emission_volumes = emission.rate.for_period(period).to_volumes()
                            unit_in = emission_volumes.unit
                            for timestep, emission_volume in emission_volumes.datapoints():
                                fuel_model = fuel_temporal_model.get_model(timestep)
                                fuel_category = fuel_model.user_defined_category

                                if self.fuel_type_category is None or fuel_category == self.fuel_type_category:
                                    if self.emission_type is None or emission.name == self.emission_type:
                                        aggregated_result[timestep] += emission_volume
            if aggregated_result:
                sorted_result = dict(dict(sorted(zip(aggregated_result.keys(), aggregated_result.values()))).items())
                sorted_result = {**dict.fromkeys(installation_time_steps, 0.0), **sorted_result}
                date_keys = list(sorted_result.keys())

                reindexed_result = (
                    TimeSeriesVolumes(timesteps=date_keys, values=list(sorted_result.values())[:-1], unit=unit_in)
                    .to_unit(Unit.KILO)
                    .to_unit(unit)
                    .reindex(time_steps)
                    .fill_nan(0)
                )

                aggregated_result_volume = {
                    reindexed_result.timesteps[i]: reindexed_result.values[i] for i in range(len(reindexed_result))
                }

            return aggregated_result_volume if aggregated_result_volume else None
        return None


class ElectricityGeneratedQuery(Query):
    """GenSet only (ie el producers)."""

    def __init__(self, installation_category: Optional[str] = None, producer_categories: Optional[List[str]] = None):
        self.installation_category = installation_category
        self.producer_categories = producer_categories

    def query(
        self,
        installation_graph: GraphResult,
        unit: Unit,
        frequency: Frequency,
    ) -> Optional[Dict[datetime, float]]:
        installation_dto = installation_graph.graph.get_component(installation_graph.graph.root)

        installation_time_steps = installation_graph.timesteps
        time_steps = resample_time_steps(
            frequency=frequency,
            time_steps=installation_time_steps,
        )

        aggregated_result: DefaultDict[datetime, float] = defaultdict(float)
        aggregated_result_volume = {}
        unit_in = None

        if self.installation_category is None or installation_dto.user_defined_category == self.installation_category:
            for fuel_consumer in installation_dto.fuel_consumers:
                if isinstance(fuel_consumer, libecalc.dto.GeneratorSet):
                    temporal_category = TemporalModel(fuel_consumer.user_defined_category)
                    for period, category in temporal_category.items():
                        if self.producer_categories is None or category in self.producer_categories:
                            fuel_consumer_result: GeneratorSetResult = installation_graph.get_energy_result(
                                fuel_consumer.id
                            )

                            cumulative_volumes_gwh = fuel_consumer_result.power.for_period(period).to_volumes()

                            unit_in = cumulative_volumes_gwh.unit

                            for timestep, cumulative_volume_gwh in cumulative_volumes_gwh.datapoints():
                                aggregated_result[timestep] += cumulative_volume_gwh

            if aggregated_result:
                sorted_result = dict(dict(sorted(zip(aggregated_result.keys(), aggregated_result.values()))).items())
                sorted_result = {**dict.fromkeys(installation_time_steps, 0.0), **sorted_result}
                date_keys = list(sorted_result.keys())

                reindexed_result = (
                    TimeSeriesVolumes(timesteps=date_keys, values=list(sorted_result.values())[:-1], unit=unit_in)
                    .to_unit(Unit.GIGA_WATT_HOURS)
                    .reindex(time_steps)
                    .fill_nan(0)
                )

                aggregated_result_volume = {
                    reindexed_result.timesteps[i]: reindexed_result.values[i] for i in range(len(reindexed_result))
                }
        return aggregated_result_volume if aggregated_result_volume else None


class FuelConsumerPowerConsumptionQuery(Query):
    def __init__(self, consumer_categories: Optional[List[str]] = None, installation_category: Optional[str] = None):
        self.consumer_categories = consumer_categories
        self.installation_category = installation_category

    def query(
        self,
        installation_graph: GraphResult,
        unit: Unit,
        frequency: Frequency,
    ) -> Optional[Dict[datetime, float]]:
        installation_dto = installation_graph.graph.get_component(installation_graph.graph.root)

        installation_time_steps = installation_graph.timesteps
        time_steps = resample_time_steps(
            frequency=frequency,
            time_steps=installation_time_steps,
        )
        fuel_consumers = installation_dto.fuel_consumers
        fuel_consumers = [
            fuel_consumer
            for fuel_consumer in fuel_consumers
            if not isinstance(fuel_consumer, libecalc.dto.GeneratorSet)
        ]

        aggregated_result: DefaultDict[datetime, float] = defaultdict(
            float
        )  # aggregate together over all fuel consumers with given category
        aggregated_result_volume = {}
        unit_in = None

        if self.installation_category is None or installation_dto.user_defined_category == self.installation_category:
            for fuel_consumer in fuel_consumers:
                temporal_category = TemporalModel(fuel_consumer.user_defined_category)
                for period, category in temporal_category.items():
                    if self.consumer_categories is None or category in self.consumer_categories:
                        fuel_consumer_result = installation_graph.get_energy_result(fuel_consumer.id)
                        time_vector = fuel_consumer_result.timesteps
                        shaft_power = fuel_consumer_result.power

                        if (
                            shaft_power is not None
                            and 0 < len(shaft_power) == len(time_vector)
                            and len(fuel_consumer_result.timesteps) == len(installation_graph.timesteps)
                        ):
                            cumulative_volumes_gwh = shaft_power.for_period(period).to_volumes()
                            unit_in = cumulative_volumes_gwh.unit

                            for timestep, cumulative_volume_gwh in cumulative_volumes_gwh.datapoints():
                                aggregated_result[timestep] += cumulative_volume_gwh
                        else:
                            raise NotImplementedError(
                                f"A combination of one or more compressors that do not support fuel to power conversion was used."
                                f"We are therefore unable to calculate correct power usage. Please only use compressors which support POWER conversion"
                                f"for fuel consumer {fuel_consumer.name}"
                            )

            if aggregated_result:
                sorted_result = dict(dict(sorted(zip(aggregated_result.keys(), aggregated_result.values()))).items())
                sorted_result = {**dict.fromkeys(installation_time_steps, 0.0), **sorted_result}
                date_keys = list(sorted_result.keys())

                reindexed_result = (
                    TimeSeriesVolumes(timesteps=date_keys, values=list(sorted_result.values())[:-1], unit=unit_in)
                    .to_unit(Unit.GIGA_WATT_HOURS)
                    .reindex(time_steps)
                    .fill_nan(0)
                )

                aggregated_result_volume = {
                    reindexed_result.timesteps[i]: reindexed_result.values[i] for i in range(len(reindexed_result))
                }

        return aggregated_result_volume if aggregated_result_volume else None


class ElConsumerPowerConsumptionQuery(Query):
    def __init__(self, consumer_categories: Optional[List[str]] = None, installation_category: Optional[str] = None):
        self.consumer_categories = consumer_categories
        self.installation_category = installation_category

    @Feature.experimental("New LTP power consumption calculation")
    def query(
        self,
        installation_graph: GraphResult,
        unit: Unit,
        frequency: Frequency,
    ) -> Optional[Dict[datetime, float]]:
        installation_dto = installation_graph.graph.get_component(installation_graph.graph.root)

        installation_time_steps = installation_graph.timesteps
        time_steps = resample_time_steps(
            frequency=frequency,
            time_steps=installation_time_steps,
        )

        aggregated_result: DefaultDict[datetime, float] = defaultdict(float)
        aggregated_result_volume = {}
        unit_in = None

        if self.installation_category is None or installation_dto.user_defined_category == self.installation_category:
            for fuel_consumer in installation_dto.fuel_consumers:
                if isinstance(fuel_consumer, libecalc.dto.GeneratorSet):
                    for electrical_consumer in fuel_consumer.consumers:
                        temporal_category = TemporalModel(electrical_consumer.user_defined_category)
                        for period, category in temporal_category.items():
                            if self.consumer_categories is None or category in self.consumer_categories:
                                electrical_consumer_result = installation_graph.get_energy_result(
                                    electrical_consumer.id
                                )
                                power = electrical_consumer_result.power
                                if power is not None:
                                    cumulative_volumes_gwh = power.for_period(period).to_volumes()
                                    unit_in = cumulative_volumes_gwh.unit

                                    for timestep, cumulative_volume_gwh in cumulative_volumes_gwh.datapoints():
                                        aggregated_result[timestep] += cumulative_volume_gwh

            if aggregated_result:
                sorted_result = dict(dict(sorted(zip(aggregated_result.keys(), aggregated_result.values()))).items())
                sorted_result = {**dict.fromkeys(installation_time_steps, 0.0), **sorted_result}
                date_keys = list(sorted_result.keys())

                reindexed_result = (
                    TimeSeriesVolumes(timesteps=date_keys, values=list(sorted_result.values())[:-1], unit=unit_in)
                    .to_unit(Unit.GIGA_WATT_HOURS)
                    .reindex(time_steps)
                    .fill_nan(0)
                )

                aggregated_result_volume = {
                    reindexed_result.timesteps[i]: reindexed_result.values[i] for i in range(len(reindexed_result))
                }

        return aggregated_result_volume if aggregated_result_volume else None
