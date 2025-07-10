import operator
from collections.abc import Iterable
from datetime import datetime
from functools import reduce
from typing import Self

from libecalc.application.graph_result import GraphResult
from libecalc.common.time_utils import Frequency, Period, Periods
from libecalc.common.units import Unit
from libecalc.common.utils.rates import TimeSeriesFloat, TimeSeriesStreamDayRate
from libecalc.common.variables import ExpressionEvaluator, VariablesMap
from libecalc.core.result import EcalcModelResult
from libecalc.core.result.emission import EmissionResult
from libecalc.domain.component_validation_error import DomainValidationException
from libecalc.domain.energy import ComponentEnergyContext, Emitter, EnergyComponent, EnergyModel
from libecalc.domain.infrastructure.energy_components.asset.asset import Asset
from libecalc.domain.installation import (
    Installation,
)
from libecalc.domain.resource import Resource
from libecalc.dto import ResultOptions
from libecalc.dto.component_graph import ComponentGraph
from libecalc.presentation.yaml.domain.category_service import CategoryService
from libecalc.presentation.yaml.domain.reference_service import ReferenceService
from libecalc.presentation.yaml.domain.time_series_collections import TimeSeriesCollections
from libecalc.presentation.yaml.domain.time_series_resource import TimeSeriesResource
from libecalc.presentation.yaml.mappers.component_mapper import EcalcModelMapper
from libecalc.presentation.yaml.mappers.create_references import create_references
from libecalc.presentation.yaml.mappers.variables_mapper import map_yaml_to_variables
from libecalc.presentation.yaml.mappers.variables_mapper.get_global_time_vector import (
    get_global_time_vector,
)
from libecalc.presentation.yaml.mappers.variables_mapper.variables_mapper import InvalidVariablesException
from libecalc.presentation.yaml.mappers.yaml_mapping_context import MappingContext
from libecalc.presentation.yaml.mappers.yaml_path import YamlPath
from libecalc.presentation.yaml.model_validation_exception import ModelValidationException
from libecalc.presentation.yaml.resource_service import ResourceService
from libecalc.presentation.yaml.validation_errors import (
    DataValidationError,
    DtoValidationError,
    Location,
    ModelValidationError,
)
from libecalc.presentation.yaml.yaml_models.yaml_model import YamlValidator
from libecalc.presentation.yaml.yaml_validation_context import (
    ModelContext,
    ModelName,
    YamlModelValidationContext,
    YamlModelValidationContextNames,
)

DEFAULT_START_TIME = datetime(1900, 1, 1)


class Context(ComponentEnergyContext):
    def __init__(
        self,
        energy_model: EnergyModel,
        consumer_results: dict[str, EcalcModelResult],
        component_id: str,
    ):
        self._energy_model = energy_model
        self._consumer_results = consumer_results
        self._component_id = component_id

    def get_power_requirement(self) -> TimeSeriesFloat | None:
        consumer_power_usage = [
            self._consumer_results[consumer.id].component_result.power
            for consumer in self._energy_model.get_consumers(self._component_id)
            if self._consumer_results[consumer.id].component_result.power is not None
        ]

        if len(consumer_power_usage) < 1:
            return None

        if len(consumer_power_usage) == 1:
            return consumer_power_usage[0]

        return reduce(operator.add, consumer_power_usage)

    def get_fuel_usage(self) -> TimeSeriesStreamDayRate | None:
        energy_usage = self._consumer_results[self._component_id].component_result.energy_usage
        if energy_usage.unit == Unit.MEGA_WATT:
            # energy usage is power usage, not fuel usage.
            return None
        return energy_usage


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
        configuration: YamlValidator,
        resource_service: ResourceService,
        output_frequency: Frequency,
    ) -> None:
        self._output_frequency = output_frequency
        self._configuration = configuration
        self._resource_service = resource_service

        self._is_validated = False
        self._graph = None
        self._input: Asset | None = None
        self._consumer_results: dict[str, EcalcModelResult] = {}
        self._emission_results: dict[str, dict[str, EmissionResult]] = {}

        self._time_series_collections: TimeSeriesCollections | None = None
        self._variables: VariablesMap | None = None
        self._mapping_context = MappingContext(target_period=self.period)

    def get_consumers(self, provider_id: str = None) -> list[EnergyComponent]:
        self.validate_for_run()
        return self._get_graph().get_consumers(provider_id)

    def get_energy_components(self) -> list[EnergyComponent]:
        self.validate_for_run()
        return self._get_graph().get_energy_components()

    def get_expression_evaluator(self) -> ExpressionEvaluator:
        return self.variables

    def _get_reference_service(self, facility_resources: dict[str, Resource]) -> ReferenceService:
        return create_references(self._configuration, facility_resources)

    @property
    def period(self) -> Period:
        return Period(
            start=self.start or DEFAULT_START_TIME,
            end=self.end or datetime.max,
        )

    @property
    def start(self) -> datetime | None:
        return self._configuration.start

    @property
    def end(self) -> datetime | None:
        return self._configuration.end

    def _get_time_series_collections(
        self, time_series_resources: dict[str, TimeSeriesResource]
    ) -> TimeSeriesCollections:
        if self._time_series_collections is not None:
            return self._time_series_collections

        time_series_collections = TimeSeriesCollections.create(
            time_series=self._configuration.time_series,
            resources=time_series_resources,
        )
        self._time_series_collections = time_series_collections
        return self._time_series_collections

    def _get_periods(self, time_series_time_vector: Iterable[datetime]) -> Periods:
        time_vector = get_global_time_vector(
            time_series_time_vector=time_series_time_vector,
            start=self._configuration.start,
            end=self._configuration.end,
            additional_dates=self._configuration.dates,
        )
        return Periods.create_periods(time_vector, include_before=False, include_after=False)

    @property
    def variables(self) -> VariablesMap:
        assert self._is_validated
        assert self._variables is not None
        return self._variables

    @property
    def result_options(self) -> ResultOptions:
        return ResultOptions(
            start=self._configuration.start,
            end=self._configuration.end,
            output_frequency=self._output_frequency,
        )

    def _get_graph(self) -> ComponentGraph:
        assert self._is_validated
        assert self._graph is not None
        return self._graph

    def _get_token_references(self, time_series_references: list[str]) -> list[str]:
        token_references = time_series_references
        for reference in self._configuration.variables:
            token_references.append(f"$var.{reference}")

        return token_references

    def _get_model_types(self) -> dict["ModelName", "ModelContext"]:
        models = [*self._configuration.models, *self._configuration.facility_inputs]
        model_types: dict[ModelName, ModelContext] = {}
        for model in models:
            if hasattr(model, "name"):
                model_types[model.name] = model
        return model_types

    def _get_validation_context(
        self, resource_names: set[str], token_references: list[str]
    ) -> YamlModelValidationContext:
        return {
            YamlModelValidationContextNames.model_name: self._configuration.name,  # type: ignore[misc]
            YamlModelValidationContextNames.resource_file_names: resource_names,
            YamlModelValidationContextNames.expression_tokens: token_references,
            YamlModelValidationContextNames.model_types: self._get_model_types(),
        }

    def validate_for_run(self) -> Self:
        if self._is_validated:
            return self

        time_series_resources, time_series_resource_errors = self._resource_service.get_time_series_resources()
        facility_resources, facility_resource_errors = self._resource_service.get_facility_resources()

        resource_errors = [*time_series_resource_errors, *facility_resource_errors]

        # Parse valid time series, combining yaml and resources
        time_series_collections = self._get_time_series_collections(time_series_resources=time_series_resources)

        configuration_validation_errors = []
        try:
            # Validate model, this will check the overall validity, i.e. fail if some time series or facility input is invalid
            resource_names = (
                time_series_resources.keys()
                | facility_resources.keys()
                | {
                    error.resource_name for error in resource_errors
                }  # Include resource names in errors to avoid "resource not found" in configuration.validate below
            )
            validation_context = self._get_validation_context(
                resource_names=resource_names,
                token_references=self._get_token_references(
                    time_series_references=time_series_collections.get_time_series_references()
                ),
            )
            self._configuration.validate(validation_context)
        except ModelValidationException as e:
            configuration_validation_errors = e.errors()

        if len(resource_errors) > 0 or len(configuration_validation_errors) > 0:
            resource_model_validation_errors = [
                ModelValidationError(
                    message=error.message,
                    file_context=error.file_context,
                    data=None,
                    location=Location([error.resource_name]),
                )
                for error in resource_errors
            ]
            raise ModelValidationException(errors=[*resource_model_validation_errors, *configuration_validation_errors])

        try:
            self._variables = map_yaml_to_variables(
                configuration=self._configuration,
                time_series_provider=time_series_collections,
                periods=self._get_periods(time_series_collections.get_time_vector()),
            )

            reference_service = self._get_reference_service(facility_resources=facility_resources)

            # Is validated, first step, must be set before calling get_graph
            self._is_validated = True
            # Validate and create the graph used for evaluating the energy model
            model_mapper = EcalcModelMapper(
                references=reference_service,
                target_period=self.period,
                expression_evaluator=self._variables,
                mapping_context=self._mapping_context,
            )

            self._input = model_mapper.from_yaml_to_domain(configuration=self._configuration)
            self._graph = self._input.get_graph()
            return self
        except InvalidVariablesException as e:
            variables_path = YamlPath(keys=("VARIABLES",))
            raise ModelValidationException(
                errors=[
                    ModelValidationError(
                        location=Location(keys=variables_path.keys),
                        message=str(e),
                        data=None,
                        file_context=self._configuration.get_file_context(variables_path.keys),
                    )
                ],
            ) from e
        except (
            DtoValidationError,
            DomainValidationException,
        ) as e:
            raise ModelValidationException(errors=e.errors()) from e  # type: ignore[arg-type]
        except DataValidationError as e:
            raise ModelValidationException(
                errors=[
                    ModelValidationError(
                        location=Location(keys=[""]),
                        message=str(e),
                        data=None,
                        file_context=None,
                    )
                ],
            ) from e

    def _get_context(self, component_id: str) -> ComponentEnergyContext:
        return Context(
            energy_model=self,
            consumer_results=self._consumer_results,
            component_id=component_id,
        )

    def evaluate_energy_usage(self) -> dict[str, EcalcModelResult]:
        energy_components = self.get_energy_components()

        for energy_component in energy_components:
            if hasattr(energy_component, "evaluate_energy_usage"):
                context = self._get_context(energy_component.id)
                self._consumer_results.update(energy_component.evaluate_energy_usage(context=context))

        return self._consumer_results

    def evaluate_emissions(self) -> dict[str, dict[str, EmissionResult]]:
        """
        Calculate emissions for fuel consumers and emitters

        Returns: a mapping from consumer_id to emissions
        """
        for energy_component in self.get_energy_components():
            if isinstance(energy_component, Emitter):
                emission_result = energy_component.evaluate_emissions(
                    energy_context=self._get_context(energy_component.id),
                    energy_model=self,
                )

                if emission_result is not None:
                    self._emission_results[energy_component.id] = emission_result

        return self._emission_results

    def get_graph_result(self) -> GraphResult:
        return GraphResult(
            graph=self._get_graph(),
            consumer_results=self._consumer_results,
            emission_results=self._emission_results,
            variables_map=self.variables,
        )

    def get_installations(self) -> list[Installation]:
        assert self._input is not None
        return self._input.installations

    def get_category_service(self) -> CategoryService:
        return self._mapping_context
