from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Set, Type, Union

import pandas as pd
from pydantic import Field, model_validator

from libecalc.common.errors.exceptions import (
    DifferentLengthsError,
    IncompatibleDataError,
    MissingKeyError,
    ProgrammingError,
)
from libecalc.common.math.math_utils import MathUtil
from libecalc.common.time_utils import Frequency
from libecalc.common.units import Unit
from libecalc.dto.result.base import EcalcResultBaseModel


@dataclass
class DataSeries:
    name: str
    title: str

    values: List[Union[str, float]]


@dataclass
class QueryResult:
    """TODO: Generic result...can e.g. be datetime...or string?
    enough data in order to correctly format the results....

    TODO: provide more info e.g. on hierarchy etc? can also be done by having id and link to yaml...
    """

    name: str
    title: str

    unit: Unit  # Needed! in order to know how to handler further....parse

    values: Dict[datetime, float]
    # TODO: split? we will at this level always have one time vector..?!


@dataclass
class GroupedQueryResult:
    group_name: str
    query_results: List[QueryResult]


@dataclass
class FilteredResult:
    data_series: List[DataSeries]
    query_results: List[GroupedQueryResult]
    time_vector: List[datetime]


class TimeSteps(EcalcResultBaseModel):
    """The relevant timesteps for the associated values. Must have a fixed frequency."""

    values: List[datetime]
    frequency: Frequency


class TimeSeries(EcalcResultBaseModel):
    """A timeseries of values with corresponding unit."""

    values: Dict[datetime, float]
    title: str
    unit: Unit

    def fit_to_timesteps(self, timesteps: List[datetime]) -> "TimeSeries":
        """
        Fit TimeSeries to timesteps
        Args:
            timesteps:

        Returns:

        """

        if not set(timesteps).issubset(set(self.values.keys())):
            raise ProgrammingError("Provided timesteps must be a subset of the current timesteps.")

        return TimeSeries(
            values={timestep: value for timestep, value in self.values.items() if timestep in timesteps},
            title=self.title,
            unit=self.unit,
        )


class TSVPrognosis(EcalcResultBaseModel):
    """The LongTermPrognosis (LTP) and ShortTermPrognosis (STP) - all the corresponding predefined timeseries for a regular timevector.
    Corresponds to _one_ installation.
    """

    time_steps: TimeSteps
    time_series_collection: Dict[str, TimeSeries]

    @model_validator(mode="after")
    def check_equal_lengths_of_timeseries(self):
        time_steps, time_series_collection = (
            self.time_steps,
            self.time_series_collection,
        )

        nr_of_timesteps = len(time_steps.values)
        lengths_timeseries = {
            time_series_name: len(time_series.values)
            for time_series_name, time_series in time_series_collection.items()
        }

        same_time_steps = all(nr_of_timesteps == length_timeseries for length_timeseries in lengths_timeseries.values())

        if not same_time_steps:
            raise IncompatibleDataError(
                f"Nr of timesteps in timeseries differ. Nr of timesteps are: {nr_of_timesteps} while the timeseries have the following lengths: {lengths_timeseries}"
            )

        return self

    def fit_to_timesteps(self, timesteps: List[datetime]) -> "TSVPrognosis":
        return TSVPrognosis(
            time_steps=TimeSteps(
                values=timesteps,
                frequency=self.time_steps.frequency,
            ),
            time_series_collection={
                time_series_name: time_series.fit_to_timesteps(timesteps)
                for time_series_name, time_series in self.time_series_collection.items()
            },
        )

    def __sub__(self, other: "TSVPrognosis") -> "TSVPrognosis":
        delta_time_series_collection: Dict[str, TimeSeries] = {}

        self_time_series_names = list(self.time_series_collection.keys())
        other_time_series_names = list(other.time_series_collection.keys())
        # TODO: decide what to do with order of columns
        # Use dict.fromkeys to keep some kind of order until we know how they should be ordered.
        # This will order the columns from self before other, in most cases both should contain all columns
        all_time_series_names = list(dict.fromkeys([*self_time_series_names, *other_time_series_names]))

        time_steps = self.time_steps.values
        for time_series_name in all_time_series_names:
            self_time_series = self.time_series_collection.get(time_series_name)
            other_time_series = other.time_series_collection.get(time_series_name)

            if self_time_series is None and other_time_series is None:
                raise ValueError("Can't compare two undefined columns")
            elif self_time_series is None:
                unit = other_time_series.unit
                title = other_time_series.title
                self_time_series_values = {time_step: 0.0 for time_step in time_steps}
                other_time_series_values = other_time_series.values
            elif other_time_series is None:
                unit = self_time_series.unit
                title = self_time_series.title
                other_time_series_values = {time_step: 0.0 for time_step in time_steps}
                self_time_series_values = self_time_series.values
            else:
                # self and other title,unit should be the same
                unit = self_time_series.unit
                title = self_time_series.title
                other_time_series_values = other_time_series.values
                self_time_series_values = self_time_series.values

            try:
                delta_time_series_collection[time_series_name] = TimeSeries(
                    title=title,
                    unit=unit,
                    values=MathUtil.elementwise_subtraction_by_key(self_time_series_values, other_time_series_values),
                )
            except DifferentLengthsError as dle:
                raise DifferentLengthsError(
                    f"Time series {time_series_name} in Reference (A) and Changed (B) model have different time steps, and Delta LTP/STP can therefore not be calculated. Details: "
                    + str(dle)
                ) from dle
            except MissingKeyError as mke:
                raise MissingKeyError(
                    f"Time series {time_series_name} in Reference (A) and Changed (B) model have different keys, and Delta LTP/STP can therefore not be calculated. Details: "
                    + str(mke)
                ) from mke

        return TSVPrognosis(time_steps=self.time_steps, time_series_collection=delta_time_series_collection)

    def to_dataframe(self) -> pd.DataFrame:
        timesteps = self.time_steps.values

        values_with_headers: Dict[str, Dict[datetime, Union[float, int]]] = defaultdict(dict)
        values_with_headers["forecastYear"] = {timestep: timestep.year for timestep in timesteps}
        values_with_headers["forecastMonth"] = {timestep: timestep.month for timestep in timesteps}

        values_with_headers.update(
            {
                time_series_name: time_series.values
                for time_series_name, time_series in self.time_series_collection.items()
            }
        )
        data_frame: pd.DataFrame = pd.DataFrame(data=values_with_headers, index=timesteps)

        return data_frame


class AssetTSVPrognosis(EcalcResultBaseModel):
    """An asset may have one or more installations, and each installation
    have their own LongTermPrognosis (LTP)/ShortTermPrognosis (STP).
    """

    tsv_prognoses: Dict[str, TSVPrognosis] = Field(default_factory=dict)

    @property
    def common_timesteps(self) -> Set[datetime]:
        """
        Get common timesteps for all tsv prognoses
        Returns: intersection of all timesteps

        """
        timesteps_sets = []
        for tsv_prognosis in self.tsv_prognoses.values():
            timesteps_sets.append(set(tsv_prognosis.time_steps.values))
        return set.intersection(*timesteps_sets)

    def add_tsv_prognosis(self, installation_name: str, long_term_prognosis: TSVPrognosis):
        self.tsv_prognoses[installation_name] = long_term_prognosis

    def get_tsv_prognosis(self, installation_name: str) -> TSVPrognosis:
        return self.tsv_prognoses.get(installation_name)

    def fit_to_timesteps(self, timesteps: List[datetime]) -> "AssetTSVPrognosis":
        return AssetTSVPrognosis(
            tsv_prognoses={
                installation_name: tsv_prognosis.fit_to_timesteps(timesteps)
                for installation_name, tsv_prognosis in self.tsv_prognoses.items()
            }
        )

    @classmethod
    def from_tsv_result(cls: Type["AssetTSVPrognosis"], filtered_result: FilteredResult) -> "AssetTSVPrognosis":
        asset_tsv_prognosis: cls = cls()

        for group in filtered_result.query_results:
            tsv_prognosis: TSVPrognosis = TSVPrognosis(
                time_steps=TimeSteps(frequency=Frequency.YEAR, values=filtered_result.time_vector),
                time_series_collection={
                    result.name: TimeSeries(title=result.title, values=result.values, unit=result.unit)
                    for result in group.query_results
                },
            )
            asset_tsv_prognosis.add_tsv_prognosis(group.group_name, tsv_prognosis)

        return asset_tsv_prognosis

    def to_dataframes(self) -> Dict[str, pd.DataFrame]:
        """We cannot represent AssetTSVPrognosis as _one_ dataframe, we need one per installation. The reason for this
        is that _the_same_ fields are aggregated at installation level, and each installation have the same fields/columns,
        and the name of these columns needs to be the same for each installation
        :return:
        """
        dataframes: Dict[str, pd.DataFrame] = {}
        for installation_name, tsv_prognosis in self.tsv_prognoses.items():
            dataframes[installation_name] = tsv_prognosis.to_dataframe()

        return dataframes

    @classmethod
    def delta_profile(cls, reference: "AssetTSVPrognosis", other: "AssetTSVPrognosis") -> "AssetTSVPrognosis":
        asset_delta_tsv_profile = AssetTSVPrognosis()

        timesteps = sorted(reference.common_timesteps.intersection(other.common_timesteps))

        reference = reference.fit_to_timesteps(timesteps)
        other = other.fit_to_timesteps(timesteps)

        for inst_name, other_tsv_prognosis in other.tsv_prognoses.items():
            asset_delta_tsv_profile.add_tsv_prognosis(
                inst_name, other_tsv_prognosis - reference.get_tsv_prognosis(inst_name)
            )

        return asset_delta_tsv_profile
