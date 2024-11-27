from datetime import datetime
from functools import cached_property
from typing import Optional, Self

from typing_extensions import deprecated

from libecalc.application.energy.energy_component import EnergyComponent
from libecalc.application.energy.energy_model import EnergyModel
from libecalc.common.time_utils import Frequency, Period
from libecalc.common.variables import ExpressionEvaluator, VariablesMap
from libecalc.dto import ResultOptions
from libecalc.dto.component_graph import ComponentGraph
from libecalc.expression import Expression
from libecalc.presentation.yaml.configuration_service import ConfigurationService
from libecalc.presentation.yaml.domain.reference_service import ReferenceService
from libecalc.presentation.yaml.domain.time_series_collections import TimeSeriesCollections
from libecalc.presentation.yaml.mappers.component_mapper import EcalcModelMapper
from libecalc.presentation.yaml.mappers.create_references import create_references
from libecalc.presentation.yaml.mappers.variables_mapper import map_yaml_to_variables
from libecalc.presentation.yaml.mappers.variables_mapper.get_global_time_vector import get_global_time_vector
from libecalc.presentation.yaml.model_validation_exception import ModelValidationException
from libecalc.presentation.yaml.resource_service import ResourceService
from libecalc.presentation.yaml.validation_errors import DtoValidationError, Location, ModelValidationError
from libecalc.presentation.yaml.yaml_models.exceptions import DuplicateKeyError, YamlError
from libecalc.presentation.yaml.yaml_models.yaml_model import YamlValidator
from libecalc.presentation.yaml.yaml_validation_context import (
    ModelContext,
    ModelName,
    YamlModelValidationContext,
    YamlModelValidationContextNames,
)

DEFAULT_START_TIME = datetime(1900, 1, 1)


class YamlModel(EnergyModel):
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
        try:
            self._configuration = configuration_service.get_configuration()
        except YamlError as e:
            location = Location(keys=[])
            if isinstance(e, DuplicateKeyError):
                location = Location(keys=[e.key])
            raise ModelValidationException(
                errors=[
                    ModelValidationError(
                        location=location,
                        message=e.problem,
                        file_context=e.file_context,
                        data=None,
                    )
                ]
            ) from e
        self.resources = resource_service.get_resources(self._configuration)

        self._is_validated = False
        self._graph = None

    def get_regularity(self, component_id: str) -> dict[datetime, Expression]:
        graph = self.get_graph()
        installation_id = graph.get_parent_installation_id(component_id)
        installation = graph.get_node(installation_id)
        return installation.regularity

    def get_consumers(self, provider_id: str = None) -> list[EnergyComponent]:
        return self.get_graph().get_consumers(provider_id)

    def get_energy_components(self) -> list[EnergyComponent]:
        return self.get_graph().get_energy_components()

    def get_expression_evaluator(self) -> ExpressionEvaluator:
        return self.variables

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
        if self._is_validated and self._graph is not None:
            return self._graph

        # Allow creating the graph without validating since the model might be validated separately
        self._graph = self.dto.get_graph()
        return self._graph

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

            # Is validated, first step, must be set before calling get_graph
            self._is_validated = True

            # Validate and create the graph used for evaluating the energy model
            self.get_graph()
            return self
        except DtoValidationError as e:
            raise ModelValidationException(errors=e.errors()) from e
