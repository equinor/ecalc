import itertools
from typing import Protocol, Self, TypeVar

from pydantic import BaseModel

from libecalc.common.list.list_utils import transpose
from libecalc.common.time_utils import Periods
from libecalc.common.utils.rates import TimeSeries


class TabularTimeSeries(Protocol):
    def model_copy(self, deep: bool = False) -> Self:
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
        merged_object = first.model_copy(deep=True)

        for key, value in first.__dict__.items():
            for other in others:
                accumulated_value = merged_object.__getattribute__(key)
                other_value = other.__getattribute__(key)
                if key == "periods":
                    merged_periods = sorted(itertools.chain(accumulated_value, other_value))
                    merged_object.__setattr__(key, Periods(merged_periods))
                elif isinstance(value, TimeSeries):
                    merged_object.__setattr__(key, accumulated_value.merge(other_value))
                elif isinstance(value, BaseModel):
                    merged_object.__setattr__(
                        key, cls.merge(*[obj.__getattribute__(key) for obj in objects_with_time_series])
                    )
                elif (
                    isinstance(value, list)
                    and len(value) > 0
                    and (isinstance(value[0], TimeSeries) or isinstance(value[0], BaseModel))
                ):
                    list_attributes = [obj.__getattribute__(key) for obj in objects_with_time_series]
                    transposed_list_attributes = transpose(list_attributes)
                    merged_list_attributes = []
                    if isinstance(value[0], TimeSeries):
                        for time_series_to_merge in transposed_list_attributes:
                            first_time_series, *others_time_series = time_series_to_merge
                            merged_time_series = first_time_series
                            for other_time_series in others_time_series:
                                merged_time_series = merged_time_series.merge(other_time_series)
                            merged_list_attributes.append(merged_time_series)
                    elif isinstance(value[0], BaseModel):
                        merged_list_attributes = [
                            cls.merge(*objs_to_merge) for objs_to_merge in transposed_list_attributes
                        ]

                    merged_object.__setattr__(key, merged_list_attributes)

        return merged_object
