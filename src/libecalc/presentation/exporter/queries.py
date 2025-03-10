import abc
from collections import defaultdict

from libecalc.common.decorators.feature_flags import Feature
from libecalc.common.time_utils import Frequency, Period, Periods, resample_periods
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
    ) -> dict[Period, float] | None:
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
        consumer_categories: list[str] | None = None,
        installation_category: str | None = None,
        fuel_type_category: str | None = None,
    ):
        self.consumer_categories = consumer_categories
        self.installation_category = installation_category
        self.fuel_type_category = fuel_type_category

    def query(
        self,
        installation_graph: Exportable,
        unit: Unit,
        frequency: Frequency,
    ) -> dict[Period, float] | None:
        if self.installation_category is not None and self.installation_category != installation_graph.get_category():
            return None

        aggregated_result: defaultdict[Period, float] = defaultdict(float)
        for attribute in installation_graph.get_fuel_consumption():
            meta = attribute.get_meta()
            if self.fuel_type_category is not None and meta.fuel_category != self.fuel_type_category:
                continue

            if self.consumer_categories is not None and meta.consumer_category not in self.consumer_categories:
                continue

            for period, fuel_volume in attribute.datapoints():
                aggregated_result[period] += fuel_volume

        if aggregated_result:
            sorted_result = dict(
                sorted(zip(aggregated_result.keys(), aggregated_result.values()))
            )  # Sort tuple with datetime and values, basically means sort on date since dates are unique?
            sorted_result = {
                **dict.fromkeys(installation_graph.get_periods(), 0.0),
                **sorted_result,
            }  # Fill missing periods with zeroes, also keep sort?
            period_keys = list(sorted_result.keys())
            resampled_results = (
                TimeSeriesVolumes(periods=Periods(period_keys), values=list(sorted_result.values()), unit=unit)
                .resample(freq=frequency)
                .fill_nan(0)
            )
            return {
                resampled_results.periods.periods[i]: resampled_results.values[i] for i in range(len(resampled_results))
            }
        return None


class StorageVolumeQuery(Query):
    def __init__(
        self,
        installation_category: str | None = None,
        consumer_categories: list[str] | None = None,
    ):
        self.installation_category = installation_category
        self.consumer_categories = consumer_categories

    def query(
        self,
        installation_graph: Exportable,
        unit: Unit,
        frequency: Frequency,
    ) -> dict[Period, float] | None:
        if self.installation_category is not None and self.installation_category != installation_graph.get_category():
            return None

        aggregated_result: defaultdict[Period, float] = defaultdict(float)
        for attribute in installation_graph.get_storage_volumes(unit):
            meta = attribute.get_meta()

            if self.consumer_categories is not None and meta.consumer_category not in self.consumer_categories:
                continue

            for period, fuel_volume in attribute.datapoints():
                aggregated_result[period] += fuel_volume

        if aggregated_result:
            sorted_result = dict(dict(sorted(zip(aggregated_result.keys(), aggregated_result.values()))).items())
            sorted_result = {**dict.fromkeys(installation_graph.get_periods(), 0.0), **sorted_result}
            period_keys = list(sorted_result.keys())
            resampled_results = (
                TimeSeriesVolumes(periods=Periods(period_keys), values=list(sorted_result.values()), unit=unit)
                .resample(freq=frequency)
                .fill_nan(0)
            )
            return {
                resampled_results.periods.periods[i]: resampled_results.values[i] for i in range(len(resampled_results))
            }
        return None


class EmissionQuery(Query):
    def __init__(
        self,
        installation_category: str | None = None,
        consumer_categories: list[str] | None = None,
        fuel_type_category: str | None = None,
        emission_type: str | None = None,
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
    ) -> dict[Period, float] | None:
        if self.installation_category is not None and self.installation_category != installation_graph.get_category():
            return None

        aggregated_result: defaultdict[Period, float] = defaultdict(float)
        for attribute in installation_graph.get_emissions(unit):
            meta = attribute.get_meta()
            if self.fuel_type_category is not None and meta.fuel_category != self.fuel_type_category:
                continue

            if self.consumer_categories is not None and meta.consumer_category not in self.consumer_categories:
                continue

            if self.emission_type is not None and meta.emission_type != self.emission_type:
                continue

            for period, emission_volume in attribute.datapoints():
                aggregated_result[period] += emission_volume

        if aggregated_result:
            sorted_result = dict(dict(sorted(zip(aggregated_result.keys(), aggregated_result.values()))).items())
            sorted_result = {**dict.fromkeys(installation_graph.get_periods(), 0.0), **sorted_result}
            period_keys = list(sorted_result.keys())

            resampled_result = (
                TimeSeriesVolumes(periods=Periods(period_keys), values=list(sorted_result.values()), unit=unit)
                .resample(freq=frequency)
                .to_unit(Unit.KILO)
                .to_unit(unit)
                .fill_nan(0)
            )

            return {
                resampled_result.periods.periods[i]: resampled_result.values[i] for i in range(len(resampled_result))
            }
        return None


class ElectricityGeneratedQuery(Query):
    """GenSet only (ie el producers)."""

    def __init__(self, installation_category: str | None = None, producer_categories: list[str] | None = None):
        self.installation_category = installation_category
        self.producer_categories = producer_categories

    def query(
        self,
        installation_graph: Exportable,
        unit: Unit,
        frequency: Frequency,
    ) -> dict[Period, float] | None:
        if self.installation_category is not None and self.installation_category != installation_graph.get_category():
            return None

        aggregated_result: defaultdict[Period, float] = defaultdict(float)
        for attribute in installation_graph.get_electricity_production(unit):
            meta = attribute.get_meta()

            if self.producer_categories is not None and meta.producer_category not in self.producer_categories:
                continue

            for period, production_volume in attribute.datapoints():
                aggregated_result[period] += production_volume

        if aggregated_result:
            sorted_result = dict(dict(sorted(zip(aggregated_result.keys(), aggregated_result.values()))).items())
            sorted_result = {**dict.fromkeys(installation_graph.get_periods(), 0.0), **sorted_result}
            period_keys = list(sorted_result.keys())

            resampled_result = (
                TimeSeriesVolumes(periods=Periods(period_keys), values=list(sorted_result.values()), unit=unit)
                .resample(freq=frequency)
                .fill_nan(0)
            )

            return {
                resampled_result.periods.periods[i]: resampled_result.values[i] for i in range(len(resampled_result))
            }
        return None


class MaxUsageFromShoreQuery(Query):
    """GenSet only (ie el producers)."""

    def __init__(self, installation_category: str | None = None, producer_categories: list[str] | None = None):
        self.installation_category = installation_category
        self.producer_categories = producer_categories

    def query(
        self,
        installation_graph: Exportable,
        unit: Unit,
        frequency: Frequency,
    ) -> dict[Period, float] | None:
        if self.installation_category is not None and self.installation_category != installation_graph.get_category():
            return None

        aggregated_result: defaultdict[Period, float] = defaultdict(float)
        for attribute in installation_graph.get_maximum_electricity_production(unit):
            meta = attribute.get_meta()

            if self.producer_categories is not None and meta.producer_category not in self.producer_categories:
                continue

            for period, production_volume in attribute.datapoints():
                aggregated_result[period] += production_volume

        if aggregated_result:
            sorted_result = dict(dict(sorted(zip(aggregated_result.keys(), aggregated_result.values()))).items())
            sorted_result = {**dict.fromkeys(installation_graph.get_periods(), 0.0), **sorted_result}
            period_keys = list(sorted_result.keys())

            # Max usage from shore is time series float (values)
            # The maximum value with in each period in sorted_results should be found for the new periods
            return {
                period: TimeSeriesFloat(periods=Periods(period_keys), values=list(sorted_result.values()), unit=unit)
                .for_period(period)
                .max
                for period in resample_periods(periods=installation_graph.get_periods(), frequency=frequency)
            }
        return None


class PowerConsumptionQuery(Query):
    def __init__(
        self,
        consumer_categories: list[str] | None = None,
        installation_category: str | None = None,
        producer_categories: list[str] = None,
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
    ) -> dict[Period, float] | None:
        if self.installation_category is not None and self.installation_category != installation_graph.get_category():
            return None

        aggregated_result: defaultdict[Period, float] = defaultdict(float)
        for attribute in installation_graph.get_power_consumption(unit):
            meta = attribute.get_meta()

            if self.producer_categories is not None and meta.producer_category not in self.producer_categories:
                continue

            if self.consumer_categories is not None and meta.consumer_category not in self.consumer_categories:
                continue

            for period, consumption_volume in attribute.datapoints():
                aggregated_result[period] += consumption_volume

        if aggregated_result:
            sorted_result = dict(dict(sorted(zip(aggregated_result.keys(), aggregated_result.values()))).items())
            sorted_result = {**dict.fromkeys(installation_graph.get_periods(), 0.0), **sorted_result}
            period_keys = list(sorted_result.keys())

            resampled_result = (
                TimeSeriesVolumes(periods=Periods(period_keys), values=list(sorted_result.values()), unit=unit)
                .resample(freq=frequency)
                .fill_nan(0)
            )

            return {
                resampled_result.periods.periods[i]: resampled_result.values[i] for i in range(len(resampled_result))
            }

        return None
