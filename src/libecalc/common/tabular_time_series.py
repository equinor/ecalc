import itertools
from typing import Protocol, TypeVar

from libecalc.common.utils.rates import TimeSeries
from typing_extensions import Self


class TabularTimeSeries(Protocol):
    def copy(self, deep: bool = False) -> Self:
        """
        Duplicate a model
        Args:
            deep: set to `True` to make a deep copy of the model

        Returns: new model instance

        """
        ...


ObjectWithTimeSeries = TypeVar("ObjectWithTimeSeries", bound=TabularTimeSeries)


class TabularTimeSeriesUtils:
    """
    Utility functions for objects containing TimeSeries
    """

    @classmethod
    def merge(cls, *objects_with_time_series: ObjectWithTimeSeries):
        """
        Merge objects containing TimeSeries. Other attributes will be copied from the first object.
        Args:
            *objects_with_time_series: list of objects to merge

        Returns: a merged object of the same type

        """
        # Verify that we are merging the same types
        if len({type(object_with_time_series) for object_with_time_series in objects_with_time_series}) != 1:
            raise ValueError("Can not merge objects of differing types.")

        first, *others = objects_with_time_series
        merged_object = first.copy(deep=True)

        for key, value in first.__dict__.items():
            for other in others:
                accumulated_value = merged_object.__getattribute__(key)
                other_value = other.__getattribute__(key)
                if key == "timesteps":
                    merged_timesteps = sorted(itertools.chain(accumulated_value, other_value))
                    merged_object.__setattr__(key, merged_timesteps)
                elif isinstance(value, TimeSeries):
                    merged_object.__setattr__(key, accumulated_value.merge(other_value))

        return merged_object
