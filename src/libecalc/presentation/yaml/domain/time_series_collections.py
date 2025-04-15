from datetime import datetime
from typing import Self

from libecalc.domain.resource import Resource
from libecalc.presentation.yaml.domain.time_series import TimeSeries
from libecalc.presentation.yaml.domain.time_series_collection import TimeSeriesCollection
from libecalc.presentation.yaml.domain.time_series_exceptions import TimeSeriesNotFound
from libecalc.presentation.yaml.domain.time_series_provider import TimeSeriesProvider
from libecalc.presentation.yaml.model_validation_exception import ModelValidationException
from libecalc.presentation.yaml.validation_errors import Location, ModelValidationError
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords
from libecalc.presentation.yaml.yaml_types.time_series.yaml_time_series import YamlTimeSeriesCollection


class TimeSeriesCollections(TimeSeriesProvider):
    """
    TimeSeriesCollections keeps several TimeSeriesCollection classes and can provide info about those, such as all time
    steps in all collections.
    """

    def __init__(self, time_series_collections: dict[str, TimeSeriesCollection]):
        self._time_series_collections = time_series_collections

    def get_time_series_references(self) -> list[str]:
        time_series_references = []
        for collection in self._time_series_collections.values():
            for time_series_reference in collection.get_time_series_references():
                time_series_references.append(f"{collection.name};{time_series_reference}")
        return time_series_references

    def get_time_series(self, time_series_id: str) -> TimeSeries:
        reference_id_parts = time_series_id.split(";")
        if len(reference_id_parts) != 2:
            raise TimeSeriesNotFound(time_series_id)
        [collection_id, time_series_id] = reference_id_parts

        if collection_id not in self._time_series_collections:
            raise TimeSeriesNotFound(time_series_id)

        return self._time_series_collections[collection_id].get_time_series(time_series_id)

    def get_time_vector(self) -> set[datetime]:
        time_vector: set[datetime] = set()
        for time_series_collection in self._time_series_collections.values():
            if time_series_collection.should_influence_time_vector():
                time_vector = time_vector.union(time_series_collection.get_time_vector())
        return time_vector

    @classmethod
    def create(
        cls,
        time_series: list[YamlTimeSeriesCollection],
        resources: dict[str, Resource],
        raise_on_error: bool,
    ) -> tuple[Self, list[ModelValidationError]]:
        time_series_collections: dict[str, TimeSeriesCollection] = {}
        errors: list[ModelValidationError] = []
        for time_series_collection in time_series:
            resource = resources.get(time_series_collection.file)
            if resource is None:
                errors.append(
                    ModelValidationError(
                        data=None,
                        location=Location(keys=[]),
                        message=f"There is no resource file '{time_series_collection.file}'",
                        file_context=None,
                    )
                )
                continue
            try:
                time_series_collections[time_series_collection.name] = TimeSeriesCollection.from_yaml(
                    resource=resource,
                    yaml_collection=time_series_collection,
                )
            except ModelValidationException as e:
                # Catch validation when initializing TimeSeriesResource
                errors.extend(
                    [
                        ModelValidationError(
                            data=error.data,
                            location=Location(
                                keys=[EcalcYamlKeywords.time_series, time_series_collection.name, *error.location.keys]
                            ),
                            message=error.message,
                            file_context=error.file_context,
                        )
                        for error in e.errors()
                    ]
                )
        if raise_on_error and len(errors) != 0:
            raise ModelValidationException(errors=errors)

        return cls(time_series_collections), errors
