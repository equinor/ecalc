from datetime import datetime
from typing import Self, assert_never

from libecalc.common.errors.exceptions import InvalidResourceException
from libecalc.domain.resource import Resource
from libecalc.dto.types import InterpolationType
from libecalc.presentation.yaml.domain.time_series import TimeSeries
from libecalc.presentation.yaml.domain.time_series_exceptions import TimeSeriesNotFound
from libecalc.presentation.yaml.domain.time_series_provider import TimeSeriesProvider
from libecalc.presentation.yaml.domain.time_series_resource import TimeSeriesResource
from libecalc.presentation.yaml.model_validation_exception import ModelValidationException
from libecalc.presentation.yaml.validation_errors import Location, ModelValidationError
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords
from libecalc.presentation.yaml.yaml_types.time_series.yaml_time_series import (
    YamlDefaultTimeSeriesCollection,
    YamlMiscellaneousTimeSeriesCollection,
    YamlTimeSeriesCollection,
)


class TimeSeriesCollection(TimeSeriesProvider):
    """
    TimeSeriesCollection is a collection of time series (TimeSeriesResource) and common properties for all the time
    series in the collection.
    """

    def __init__(
        self,
        name: str,
        resource: TimeSeriesResource,
        interpolation: InterpolationType,
        extrapolation: bool,
        influence_time_vector: bool,
    ):
        self.name = name
        self._resource = resource
        self._interpolation = interpolation
        self._extrapolation = extrapolation
        self._influence_time_vector = influence_time_vector

    def should_influence_time_vector(self) -> bool:
        return self._influence_time_vector

    def get_time_vector(self) -> list[datetime]:
        return self._resource.get_time_vector()

    def get_time_series_references(self) -> list[str]:
        return self._resource.get_headers()

    def get_time_series(self, time_series_id: str) -> TimeSeries:
        try:
            return TimeSeries(
                reference_id=f"{self.name};{time_series_id}",
                time_vector=self.get_time_vector(),
                series=self._resource.get_column(time_series_id),
                extrapolate=self._extrapolation,
                interpolation_type=self._interpolation,
            ).sort()
        except InvalidResourceException as e:
            raise TimeSeriesNotFound(
                f"Unable to find time series with reference '{time_series_id}' in collection '{self.name}'"
            ) from e

    @classmethod
    def from_yaml(cls, resource: Resource, yaml_collection: YamlTimeSeriesCollection) -> Self:
        try:
            if not isinstance(resource, TimeSeriesResource):
                time_series_resource = TimeSeriesResource(resource).validate()
            else:
                time_series_resource = resource.validate()

            if isinstance(yaml_collection, YamlDefaultTimeSeriesCollection):
                interpolation = InterpolationType.RIGHT
                extrapolation = False
            elif isinstance(yaml_collection, YamlMiscellaneousTimeSeriesCollection):
                interpolation = InterpolationType[yaml_collection.interpolation_type]
                extrapolation = yaml_collection.extrapolation if yaml_collection.extrapolation is not None else False
            else:
                assert_never(yaml_collection)
            return cls(
                name=yaml_collection.name,
                resource=time_series_resource,
                interpolation=interpolation,
                extrapolation=extrapolation,
                influence_time_vector=yaml_collection.influence_time_vector,
            )

        except InvalidResourceException as e:
            # Catch validation when initializing TimeSeriesResource
            raise ModelValidationException(
                errors=[
                    ModelValidationError(
                        data=yaml_collection.model_dump(),
                        location=Location(keys=[EcalcYamlKeywords.file]),
                        message=str(e),
                        file_context=None,
                    )
                ],
            ) from e
