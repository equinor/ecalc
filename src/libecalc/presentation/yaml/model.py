from datetime import datetime
from functools import cached_property
from typing import Optional, Self

from typing_extensions import deprecated

from libecalc.common.time_utils import Frequency, Period
from libecalc.common.variables import VariablesMap
from libecalc.dto import ResultOptions
from libecalc.dto.component_graph import ComponentGraph
from libecalc.presentation.yaml.configuration_service import ConfigurationService
from libecalc.presentation.yaml.domain.reference_service import ReferenceService
from libecalc.presentation.yaml.domain.time_series_collections import TimeSeriesCollections
from libecalc.presentation.yaml.mappers.component_mapper import EcalcModelMapper
from libecalc.presentation.yaml.mappers.create_references import create_references
from libecalc.presentation.yaml.mappers.variables_mapper import map_yaml_to_variables
from libecalc.presentation.yaml.mappers.variables_mapper.get_global_time_vector import get_global_time_vector
from libecalc.presentation.yaml.model_validation_exception import ModelValidationException
from libecalc.presentation.yaml.resource_service import ResourceService
from libecalc.presentation.yaml.validation_errors import DtoValidationError
from libecalc.presentation.yaml.yaml_models.yaml_model import YamlValidator
from libecalc.presentation.yaml.yaml_validation_context import (
    ModelContext,
    ModelName,
    YamlModelValidationContext,
    YamlModelValidationContextNames,
)

DEFAULT_START_TIME = datetime(1900, 1, 1)


class YamlModel:
    """
    Class representing both the yaml and the resources.

    We haven't defined a difference in naming between the YamlModel representing only the yaml file and this class,
    which also have information about the referenced resources.

    Maybe we could use 'configuration' for the single yaml file, that naming is already used a lot for the instantiation
    of that YamlModel class.

    configuration: the model configuration
    resources: the model 'input', kind of
    model: configuration + resources (input)
    """

    def __init__(
        self,
        configuration_service: ConfigurationService,
        resource_service: ResourceService,
        output_frequency: Frequency,
    ) -> None:
        self._output_frequency = output_frequency
        self._configuration = configuration_service.get_configuration()
        self.resources = resource_service.get_resources(self._configuration)

        self._is_validated = False

    def _get_reference_service(self) -> ReferenceService:
        return create_references(self._configuration, self.resources)

    @cached_property
    @deprecated(
        "Avoid using the dto objects directly, we want to remove them. get_graph() might be useful instead, although the nodes will change."
    )
    def dto(self):
        self.validate_for_run()
        model_mapper = EcalcModelMapper(
            references=self._get_reference_service(),
            target_period=self.period,
        )
        return model_mapper.from_yaml_to_dto(configuration=self._configuration)

    @property
    def period(self) -> Period:
        return Period(
            start=self.start or DEFAULT_START_TIME,
            end=self.end or datetime.max,
        )

    @property
    def start(self) -> Optional[datetime]:
        return self._configuration.start

    @property
    def end(self) -> Optional[datetime]:
        return self._configuration.end

    def _get_time_series_collections(self) -> TimeSeriesCollections:
        return TimeSeriesCollections(time_series=self._configuration.time_series, resources=self.resources)

    def _get_time_vector(self):
        return get_global_time_vector(
            time_series_time_vector=self._get_time_series_collections().get_time_vector(),
            start=self._configuration.start,
            end=self._configuration.end,
            frequency=self._output_frequency,
            additional_dates=self._configuration.dates,
        )

    @property
    def variables(self) -> VariablesMap:
        return map_yaml_to_variables(
            configuration=self._configuration,
            time_series_provider=self._get_time_series_collections(),
            global_time_vector=self._get_time_vector(),
        )

    @property
    def result_options(self) -> ResultOptions:
        return ResultOptions(
            start=self._configuration.start,
            end=self._configuration.end,
            output_frequency=self._output_frequency,
        )

    def get_graph(self) -> ComponentGraph:
        return self.dto.get_graph()

    def _get_token_references(self, yaml_model: YamlValidator) -> list[str]:
        token_references = self._get_time_series_collections().get_time_series_references()

        for reference in yaml_model.variables:
            token_references.append(f"$var.{reference}")

        return token_references

    @staticmethod
    def _get_model_types(yaml_model: YamlValidator) -> dict["ModelName", "ModelContext"]:
        models = [*yaml_model.models, *yaml_model.facility_inputs]
        model_types: dict[ModelName, ModelContext] = {}
        for model in models:
            if hasattr(model, "name"):
                model_types[model.name] = model
        return model_types

    def _get_validation_context(self, yaml_model: YamlValidator) -> YamlModelValidationContext:
        return {
            YamlModelValidationContextNames.resource_file_names: [name for name, resource in self.resources.items()],
            YamlModelValidationContextNames.expression_tokens: self._get_token_references(yaml_model=yaml_model),
            YamlModelValidationContextNames.model_types: self._get_model_types(yaml_model=yaml_model),
        }

    def validate_for_run(self) -> Self:
        if self._is_validated:
            return self

        try:
            # Validate model
            validation_context = self._get_validation_context(yaml_model=self._configuration)
            self._configuration.validate(validation_context)
            self._is_validated = True
            return self
        except DtoValidationError as e:
            raise ModelValidationException(errors=e.errors()) from e
