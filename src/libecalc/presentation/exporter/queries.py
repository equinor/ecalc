import abc
from collections import defaultdict
from datetime import datetime
from typing import DefaultDict, Dict, List, Optional

from libecalc.common.decorators.feature_flags import Feature
from libecalc.common.time_utils import Frequency, resample_time_steps
from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    TimeSeriesFloat,
    TimeSeriesVolumes,
)
from libecalc.presentation.exporter.domain.exportable import Exportable


class Query(abc.ABC):
    """a type of action....filter, aggregator etc...combine fields? etc.
    Different types of filters? ie aggregators etc...or whatever..
    it should know itself what to do...just add new ones...
    """

    @abc.abstractmethod
    def query(
        self,
        installation_graph: Exportable,
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
        installation_graph: Exportable,
        unit: Unit,
        frequency: Frequency,
    ) -> Optional[Dict[datetime, float]]:
        if self.installation_category is not None and self.installation_category != installation_graph.get_category():
            return None

        aggregated_result: DefaultDict[datetime, float] = defaultdict(float)
        for attribute in installation_graph.get_fuel_consumption():
            meta = attribute.get_meta()
            if self.fuel_type_category is not None and meta.fuel_category != self.fuel_type_category:
                continue

            if self.consumer_categories is not None and meta.consumer_category not in self.consumer_categories:
                continue

            for timestep, fuel_volume in attribute.datapoints():
                aggregated_result[timestep] += fuel_volume

        if aggregated_result:
            sorted_result = dict(
                sorted(zip(aggregated_result.keys(), aggregated_result.values()))
            )  # Sort tuple with datetime and values, basically means sort on date since dates are unique?
            sorted_result = {
                **dict.fromkeys(installation_graph.get_timesteps(), 0.0),
                **sorted_result,
            }  # Fill missing timesteps with zeroes, also keep sort?
            date_keys = list(sorted_result.keys())
            reindexed_result = (
                TimeSeriesVolumes(timesteps=date_keys, values=list(sorted_result.values())[:-1], unit=unit)
                .reindex(resample_time_steps(time_steps=installation_graph.get_timesteps(), frequency=frequency))
                .fill_nan(0)
            )

            return {reindexed_result.timesteps[i]: reindexed_result.values[i] for i in range(len(reindexed_result))}
        return None


class StorageVolumeQuery(Query):
    def __init__(
        self,
        installation_category: Optional[str] = None,
        consumer_categories: Optional[List[str]] = None,
    ):
        self.installation_category = installation_category
        self.consumer_categories = consumer_categories

    def query(
        self,
        installation_graph: Exportable,
        unit: Unit,
        frequency: Frequency,
    ) -> Optional[Dict[datetime, float]]:
        if self.installation_category is not None and self.installation_category != installation_graph.get_category():
            return None

        aggregated_result: DefaultDict[datetime, float] = defaultdict(float)
        for attribute in installation_graph.get_storage_volumes(unit):
            meta = attribute.get_meta()

            if self.consumer_categories is not None and meta.consumer_category not in self.consumer_categories:
                continue

            for timestep, fuel_volume in attribute.datapoints():
                aggregated_result[timestep] += fuel_volume

        if aggregated_result:
            sorted_result = dict(dict(sorted(zip(aggregated_result.keys(), aggregated_result.values()))).items())
            sorted_result = {**dict.fromkeys(installation_graph.get_timesteps(), 0.0), **sorted_result}
            date_keys = list(sorted_result.keys())

            reindexed_result = (
                TimeSeriesVolumes(timesteps=date_keys, values=list(sorted_result.values())[:-1], unit=unit)
                .reindex(resample_time_steps(time_steps=installation_graph.get_timesteps(), frequency=frequency))
                .fill_nan(0)
            )

            return {reindexed_result.timesteps[i]: reindexed_result.values[i] for i in range(len(reindexed_result))}

        return None


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
        installation_graph: Exportable,
        unit: Unit,
        frequency: Frequency,
    ) -> Optional[Dict[datetime, float]]:
        if self.installation_category is not None and self.installation_category != installation_graph.get_category():
            return None

        aggregated_result: DefaultDict[datetime, float] = defaultdict(float)
        for attribute in installation_graph.get_emissions(unit):
            meta = attribute.get_meta()
            if self.fuel_type_category is not None and meta.fuel_category != self.fuel_type_category:
                continue

            if self.consumer_categories is not None and meta.consumer_category not in self.consumer_categories:
                continue

            if self.emission_type is not None and meta.emission_type != self.emission_type:
                continue

            for timestep, emission_volume in attribute.datapoints():
                aggregated_result[timestep] += emission_volume

        if aggregated_result:
            sorted_result = dict(dict(sorted(zip(aggregated_result.keys(), aggregated_result.values()))).items())
            sorted_result = {**dict.fromkeys(installation_graph.get_timesteps(), 0.0), **sorted_result}
            date_keys = list(sorted_result.keys())

            reindexed_result = (
                TimeSeriesVolumes(timesteps=date_keys, values=list(sorted_result.values())[:-1], unit=unit)
                .to_unit(Unit.KILO)
                .to_unit(unit)
                .reindex(resample_time_steps(time_steps=installation_graph.get_timesteps(), frequency=frequency))
                .fill_nan(0)
            )

            return {reindexed_result.timesteps[i]: reindexed_result.values[i] for i in range(len(reindexed_result))}

        return None


class ElectricityGeneratedQuery(Query):
    """GenSet only (ie el producers)."""

    def __init__(self, installation_category: Optional[str] = None, producer_categories: Optional[List[str]] = None):
        self.installation_category = installation_category
        self.producer_categories = producer_categories

    def query(
        self,
        installation_graph: Exportable,
        unit: Unit,
        frequency: Frequency,
    ) -> Optional[Dict[datetime, float]]:
        if self.installation_category is not None and self.installation_category != installation_graph.get_category():
            return None

        aggregated_result: DefaultDict[datetime, float] = defaultdict(float)
        for attribute in installation_graph.get_electricity_production(unit):
            meta = attribute.get_meta()

            if self.producer_categories is not None and meta.producer_category not in self.producer_categories:
                continue

            for timestep, production_volume in attribute.datapoints():
                aggregated_result[timestep] += production_volume

        if aggregated_result:
            sorted_result = dict(dict(sorted(zip(aggregated_result.keys(), aggregated_result.values()))).items())
            sorted_result = {**dict.fromkeys(installation_graph.get_timesteps(), 0.0), **sorted_result}
            date_keys = list(sorted_result.keys())

            reindexed_result = (
                TimeSeriesVolumes(timesteps=date_keys, values=list(sorted_result.values())[:-1], unit=unit)
                .reindex(resample_time_steps(time_steps=installation_graph.get_timesteps(), frequency=frequency))
                .fill_nan(0)
            )

            return {reindexed_result.timesteps[i]: reindexed_result.values[i] for i in range(len(reindexed_result))}
        return None


class MaxUsageFromShoreQuery(Query):
    """GenSet only (ie el producers)."""

    def __init__(self, installation_category: Optional[str] = None, producer_categories: Optional[List[str]] = None):
        self.installation_category = installation_category
        self.producer_categories = producer_categories

    def query(
        self,
        installation_graph: Exportable,
        unit: Unit,
        frequency: Frequency,
    ) -> Optional[Dict[datetime, float]]:
        if self.installation_category is not None and self.installation_category != installation_graph.get_category():
            return None

        aggregated_result: DefaultDict[datetime, float] = defaultdict(float)
        for attribute in installation_graph.get_maximum_electricity_production(unit):
            meta = attribute.get_meta()

            if self.producer_categories is not None and meta.producer_category not in self.producer_categories:
                continue

            for timestep, production_volume in attribute.datapoints():
                aggregated_result[timestep] += production_volume

        if aggregated_result:
            sorted_result = dict(dict(sorted(zip(aggregated_result.keys(), aggregated_result.values()))).items())
            sorted_result = {**dict.fromkeys(installation_graph.get_timesteps(), 0.0), **sorted_result}
            date_keys = list(sorted_result.keys())

            # Max usage from shore is time series float (values), and contains one more item
            # than time steps for volumes. Number of values for max usage from shore should
            # be the same as number of volume-time steps, hence [:-1]
            reindexed_result = (
                TimeSeriesFloat(timesteps=date_keys, values=list(sorted_result.values()), unit=unit)
                .reindex(resample_time_steps(time_steps=installation_graph.get_timesteps(), frequency=frequency))
                .fill_nan(0)
            )[:-1]

            return {reindexed_result.timesteps[i]: reindexed_result.values[i] for i in range(len(reindexed_result))}
        return None


class PowerConsumptionQuery(Query):
    def __init__(
        self,
        consumer_categories: Optional[List[str]] = None,
        installation_category: Optional[str] = None,
        producer_categories: List[str] = None,
    ):
        self.consumer_categories = consumer_categories
        self.producer_categories = producer_categories
        self.installation_category = installation_category

    @Feature.experimental("New LTP power consumption calculation")
    def query(
        self,
        installation_graph: Exportable,
        unit: Unit,
        frequency: Frequency,
    ) -> Optional[Dict[datetime, float]]:
        if self.installation_category is not None and self.installation_category != installation_graph.get_category():
            return None

        aggregated_result: DefaultDict[datetime, float] = defaultdict(float)
        for attribute in installation_graph.get_power_consumption(unit):
            meta = attribute.get_meta()

            if self.producer_categories is not None and meta.producer_category not in self.producer_categories:
                continue

            if self.consumer_categories is not None and meta.consumer_category not in self.consumer_categories:
                continue

            for timestep, consumption_volume in attribute.datapoints():
                aggregated_result[timestep] += consumption_volume

        if aggregated_result:
            sorted_result = dict(dict(sorted(zip(aggregated_result.keys(), aggregated_result.values()))).items())
            sorted_result = {**dict.fromkeys(installation_graph.get_timesteps(), 0.0), **sorted_result}
            date_keys = list(sorted_result.keys())

            reindexed_result = (
                TimeSeriesVolumes(timesteps=date_keys, values=list(sorted_result.values())[:-1], unit=unit)
                .reindex(resample_time_steps(time_steps=installation_graph.get_timesteps(), frequency=frequency))
                .fill_nan(0)
            )

            return {reindexed_result.timesteps[i]: reindexed_result.values[i] for i in range(len(reindexed_result))}

        return None
