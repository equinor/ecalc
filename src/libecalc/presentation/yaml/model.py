import operator
from collections.abc import Iterable
from datetime import datetime
from functools import reduce
from typing import Any, Self, assert_never
from uuid import UUID

import numpy as np

from libecalc.application.graph_result import GraphResult
from libecalc.common.component_type import ComponentType
from libecalc.common.time_utils import Frequency, Period, Periods
from libecalc.common.units import Unit
from libecalc.common.utils.rates import TimeSeriesBoolean, TimeSeriesFloat, TimeSeriesStreamDayRate
from libecalc.common.variables import ExpressionEvaluator, VariablesMap
from libecalc.core.result import ComponentResult, CompressorResult
from libecalc.core.result.results import ConsumerSystemResult, PumpResult
from libecalc.domain.ecalc_component import EcalcComponent
from libecalc.domain.energy import ComponentEnergyContext, Emitter, EnergyComponent, EnergyModel
from libecalc.domain.infrastructure.energy_components.asset.asset import Asset
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function import ConsumerFunctionResult
from libecalc.domain.infrastructure.energy_components.legacy_consumer.system.results import (
    ConsumerSystemConsumerFunctionResult,
    SystemComponentResultWithName,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.system.types import (
    ConsumerSystemFlowRate,
    ConsumerSystemFluidDensity,
    ConsumerSystemPressure,
)
from libecalc.domain.installation import (
    Installation,
)
from libecalc.domain.process.compressor.core.base import CompressorWithTurbineModel
from libecalc.domain.process.compressor.core.sampled import CompressorModelSampled
from libecalc.domain.process.compressor.core.train.base import CompressorTrainModel
from libecalc.domain.process.core.results import CompressorTrainResult, PumpModelResult
from libecalc.domain.process.evaluation_input import (
    CompressorEvaluationInput,
    CompressorSampledEvaluationInput,
    PumpEvaluationInput,
)
from libecalc.domain.process.pump.pump import PumpModel
from libecalc.domain.time_series_power_loss_factor import TimeSeriesPowerLossFactor
from libecalc.dto import ResultOptions
from libecalc.dto.component_graph import ComponentGraph
from libecalc.presentation.yaml.domain.category_service import CategoryService
from libecalc.presentation.yaml.domain.default_process_service import DefaultProcessService
from libecalc.presentation.yaml.domain.ecalc_components import (
    CompressorProcessSystemComponent,
    CompressorSampledComponent,
    PumpProcessSystemComponent,
)
from libecalc.presentation.yaml.domain.reference_service import ReferenceService
from libecalc.presentation.yaml.domain.time_series_collections import TimeSeriesCollections
from libecalc.presentation.yaml.domain.time_series_resource import TimeSeriesResource
from libecalc.presentation.yaml.mappers.component_mapper import EcalcModelMapper
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
    Location,
    ModelValidationError,
)
from libecalc.presentation.yaml.yaml_models.yaml_model import YamlValidator
from libecalc.presentation.yaml.yaml_reference_service import YamlReferenceService
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
        consumer_results: dict[str, ComponentResult],
        component_id: str,
    ):
        self._energy_model = energy_model
        self._consumer_results = consumer_results
        self._component_id = component_id

    def _get_consumers_of_current(self) -> list[ComponentResult]:
        return [
            self._consumer_results[consumer.id] for consumer in self._energy_model.get_consumers(self._component_id)
        ]

    def get_power_requirement(self) -> TimeSeriesFloat | None:
        consumer_results = self._get_consumers_of_current()
        consumer_power_usage = [consumer.power for consumer in consumer_results if consumer.power is not None]

        if len(consumer_power_usage) < 1:
            return None

        if len(consumer_power_usage) == 1:
            return consumer_power_usage[0]

        return reduce(operator.add, consumer_power_usage)

    def get_fuel_usage(self) -> TimeSeriesStreamDayRate | None:
        energy_usage = self._consumer_results[self._component_id].energy_usage
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
        self._graph: ComponentGraph | None = None
        self._input: Asset | None = None
        self._consumer_results: dict[str, ComponentResult] = {}
        self._emission_results: dict[str, dict[str, TimeSeriesStreamDayRate]] = {}

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

    def _get_reference_service(self) -> ReferenceService:
        return YamlReferenceService(configuration=self._configuration)

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

            reference_service = self._get_reference_service()

            # Is validated, first step, must be set before calling get_graph
            self._is_validated = True
            # Validate and create the graph used for evaluating the energy model
            model_mapper = EcalcModelMapper(
                resources=facility_resources,
                references=reference_service,
                target_period=self.period,
                expression_evaluator=self._variables,
                mapping_context=self._mapping_context,
                configuration=self._configuration,
            )

            self._input = model_mapper.from_yaml_to_domain()

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

    def _get_context(self, component_id: str) -> ComponentEnergyContext:
        return Context(
            energy_model=self,
            consumer_results=self._consumer_results,
            component_id=component_id,
        )

    def evaluate_energy_usage(self):
        energy_components = self.get_energy_components()

        # Set evaluation inputs for consumer systems (compressor and pump systems).
        self._set_evaluation_inputs_for_consumer_systems()

        # Evaluate process systems (compressor trains and pumps).
        process_system_results = self._evaluate_process_systems()

        # Evaluate all sampled compressors.
        compressors_sampled_results = self._evaluate_compressors_sampled()

        all_model_results = {**process_system_results, **compressors_sampled_results}

        # Get consumer energy results from model evaluations
        consumer_results_from_models = self.get_consumer_energy_results_from_domain_models(
            model_results=all_model_results
        )

        for energy_component in energy_components:
            if hasattr(energy_component, "evaluate_energy_usage"):
                context = self._get_context(energy_component.id)

                if consumer_results_from_models.get(energy_component.get_id()) is not None:
                    # For compressors and pumps, get the consumer result from the model evaluation
                    consumer_result = consumer_results_from_models.get(energy_component.get_id())
                    energy_component._consumer_result = consumer_result
                else:
                    # For other energy components (e.g. direct consumer function, tabular consumer function, consumer systems) evaluate energy usage using consumer functions
                    consumer_result = energy_component.evaluate_energy_usage(context=context)

                self._consumer_results[energy_component.id] = consumer_result

    def evaluate_emissions(self) -> dict[str, dict[str, TimeSeriesStreamDayRate]]:
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

    def get_validity(self, component_id: str) -> TimeSeriesBoolean:
        assert self._graph is not None
        component = self._graph.get_node(component_id)
        if isinstance(component, Installation | Asset):
            # Aggregate for asset and installation
            validity = []

            # recursively since Genset both has its own is_valid while also having 'children'
            children = self._graph.get_successors(component_id, recursively=isinstance(component, Installation))
            assert len(children) > 0
            for child_id in children:
                validity.append(self.get_validity(child_id))

            return reduce(lambda acc, current: acc * current, validity)

        if component_id in self._consumer_results:
            return self._consumer_results[component_id].is_valid
        else:
            # VentingEmitter does not have validity/consumer_result
            periods = self._variables.periods
            return TimeSeriesBoolean(periods=periods, values=[True] * len(periods), unit=Unit.NONE)

    def get_installations(self) -> list[Installation]:
        assert self._input is not None
        return self._input.installations

    def get_category_service(self) -> CategoryService:
        return self._mapping_context

    def get_process_service(self) -> DefaultProcessService:
        return self._mapping_context._process_service

    def _evaluate_compressor_process_systems(self) -> dict[UUID, CompressorTrainResult]:
        process_service = self.get_process_service()
        compressor_process_systems = process_service.get_compressor_process_systems()
        evaluation_inputs = process_service.get_evaluation_inputs()

        evaluated_systems = {}
        for id, process_system in compressor_process_systems.items():
            evaluation_input = evaluation_inputs.get(id)
            assert isinstance(evaluation_input, CompressorEvaluationInput)
            assert isinstance(process_system, CompressorTrainModel | CompressorWithTurbineModel)
            evaluation_input.apply_to_model(process_system)
            model_result = process_system.evaluate()
            evaluated_systems[id] = model_result
        return evaluated_systems

    def _evaluate_pump_process_systems(self) -> dict[UUID, PumpModelResult]:
        process_service = self.get_process_service()
        pump_process_systems = process_service.get_pump_process_systems()
        evaluation_inputs = process_service.get_evaluation_inputs()

        evaluated_systems = {}
        for id, process_system in pump_process_systems.items():
            evaluation_input = evaluation_inputs.get(id)
            assert isinstance(evaluation_input, PumpEvaluationInput)
            assert isinstance(process_system, PumpModel)
            evaluation_input.apply_to_model(process_system)
            model_result = process_system.evaluate()
            evaluated_systems[id] = model_result
        return evaluated_systems

    def _evaluate_compressors_sampled(self) -> dict[UUID, CompressorTrainResult]:
        process_service = self.get_process_service()
        compressors_sampled = process_service.get_compressors_sampled()
        evaluation_inputs = process_service.get_evaluation_inputs()

        evaluated_compressors_sampled = {}
        for id, compressor_sampled in compressors_sampled.items():
            evaluation_input = evaluation_inputs.get(id)
            assert isinstance(evaluation_input, CompressorSampledEvaluationInput)
            assert isinstance(compressor_sampled, CompressorModelSampled | CompressorWithTurbineModel)
            evaluation_input.apply_to_model(compressor_sampled)
            model_result = compressor_sampled.evaluate()
            evaluated_compressors_sampled[id] = model_result
        return evaluated_compressors_sampled

    def _evaluate_process_systems(self) -> dict[UUID, CompressorTrainResult | PumpModelResult]:
        """
        Evaluates domain process systems and returns a mapping: model_id -> evaluated_result.
        """
        compressor_system_results = self._evaluate_compressor_process_systems()
        pump_system_results = self._evaluate_pump_process_systems()
        process_system_results = {**compressor_system_results, **pump_system_results}

        return process_system_results

    def _set_evaluation_inputs_for_consumer_systems(self):
        """
        For each registered consumer system, determine and set evaluation_input
        for all compressors and pumps in the system, so they can be evaluated
        uniformly with other components.
        """
        process_service = self.get_process_service()

        # Map from UUID to id for all energy components
        uuid_to_id = {component.get_id(): component.id for component in self.get_energy_components()}

        for system_id, model_ids in process_service.get_consumer_system_to_component_ids().items():
            component_id = process_service.get_consumer_system_to_consumer_map()[system_id]
            consumer_name = uuid_to_id[component_id]

            # Get consumer containing the consumer system consumer functions
            energy_component = self._get_graph().get_node(node_id=consumer_name)
            temporal_model = energy_component.energy_usage_model
            consumer_systems = temporal_model.get_models()
            periods = temporal_model.get_periods()

            # Get the period for which this consumer system is evaluated (based on process service mapping)
            actual_period = process_service.get_consumer_system_to_period_map().get(system_id)

            for consumer_system, period in zip(consumer_systems, periods):
                # Only set evaluation input for the relevant consumer system period:
                # The period must match the actual period registered for the consumer system
                if period != actual_period:
                    continue
                system_operational_input = consumer_system.evaluate()
                process_service.register_consumer_system_operational_input(
                    system_id=system_id, operational_input=system_operational_input
                )

                for consumer_index, _consumer in enumerate(consumer_system.consumers):
                    model_id = model_ids[consumer_index]
                    model = process_service.get_model_by_id(model_id)
                    ecalc_component = process_service.get_ecalc_components()[model_id]
                    actual_operational_setting = system_operational_input.actual_operational_settings[consumer_index]

                    # Register evaluation input for all compressors and pumps in the consumer system
                    # Evaluation input is stored in process service using same id as the registered model
                    # In practice, this means that the input evaluation dictionary is updated with new entries here - mapped to correct model ids
                    self._register_consumer_system_evaluation_input_per_type(
                        process_service=process_service,
                        model=model,
                        model_id=model_id,
                        ecalc_component=ecalc_component,
                        power_loss_factor=consumer_system.power_loss_factor,
                        actual_operational_setting=actual_operational_setting,
                    )

    @staticmethod
    def _register_consumer_system_evaluation_input_per_type(
        process_service: DefaultProcessService,
        model: PumpModel | CompressorTrainModel | CompressorModelSampled | CompressorWithTurbineModel,
        model_id: UUID,
        ecalc_component: EcalcComponent,
        power_loss_factor: TimeSeriesPowerLossFactor,
        actual_operational_setting: dict[str, Any],
    ):
        def _common_inputs():
            return {
                "rate": ConsumerSystemFlowRate(rate=actual_operational_setting["rate"]),
                "suction_pressure": ConsumerSystemPressure(pressure=actual_operational_setting["suction_pressure"]),
                "discharge_pressure": ConsumerSystemPressure(pressure=actual_operational_setting["discharge_pressure"]),
                "power_loss_factor": power_loss_factor,
            }

        if isinstance(model, PumpModel):
            pump_evaluation_input = PumpEvaluationInput(
                **_common_inputs(),
                fluid_density=ConsumerSystemFluidDensity(density=actual_operational_setting["fluid_density"]),
            )
            component = PumpProcessSystemComponent(id=model_id, name=ecalc_component.name, type=ecalc_component.type)
            process_service.register_pump_process_system(
                ecalc_component=component, pump_process_system=model, evaluation_input=pump_evaluation_input
            )

        elif isinstance(model, CompressorTrainModel):
            assert isinstance(model, CompressorTrainModel)
            assert model._fluid_factory is not None
            compressor_evaluation_input = CompressorEvaluationInput(
                **_common_inputs(), fluid_factory=model._fluid_factory
            )
            component = CompressorProcessSystemComponent(
                id=model_id, name=ecalc_component.name, type=ecalc_component.type
            )
            process_service.register_compressor_process_system(
                ecalc_component=component,
                compressor_process_system=model,
                evaluation_input=compressor_evaluation_input,
            )
        elif isinstance(model, CompressorWithTurbineModel):
            if isinstance(model.compressor_model, CompressorTrainModel):
                assert model.compressor_model._fluid_factory is not None
                compressor_evaluation_input = CompressorEvaluationInput(
                    **_common_inputs(), fluid_factory=model.compressor_model._fluid_factory
                )
                component = CompressorProcessSystemComponent(
                    id=model_id, name=ecalc_component.name, type=ecalc_component.type
                )
                process_service.register_compressor_process_system(
                    ecalc_component=component,
                    compressor_process_system=model,
                    evaluation_input=compressor_evaluation_input,
                )
            else:
                sampled_evaluation_input = CompressorSampledEvaluationInput(**_common_inputs())
                component = CompressorSampledComponent(
                    id=model_id, name=ecalc_component.name, type=ecalc_component.type
                )
                process_service.register_compressor_sampled(
                    ecalc_component=component,
                    compressor_sampled=model,
                    evaluation_input=sampled_evaluation_input,
                )
        elif isinstance(model, CompressorModelSampled):
            sampled_evaluation_input = CompressorSampledEvaluationInput(**_common_inputs())
            component = CompressorSampledComponent(id=model_id, name=ecalc_component.name, type=ecalc_component.type)
            process_service.register_compressor_sampled(
                ecalc_component=component,
                compressor_sampled=model,
                evaluation_input=sampled_evaluation_input,
            )
        else:
            assert_never(model)

    def get_consumer_energy_results_from_domain_models(
        self, model_results: dict[UUID, Any]
    ) -> dict[UUID, CompressorResult | PumpResult | ConsumerSystemResult]:
        """
        Builds consumer energy results for each consumer based on evaluated models.

        For each consumer and period, retrieves the corresponding model result,
        constructs a ConsumerFunctionResult, and aggregates these into a CompressorResult
        per consumer. Returns a mapping from consumer UUID to CompressorResult.

        Args:
            model_results: Mapping from compressor model UUID to evaluated model.

        Returns:
            Dictionary mapping consumer UUID to consumer result, containing energy results
            for all periods.
        """
        process_service = self.get_process_service()
        allowed_model_result_types = (CompressorTrainResult, PumpModelResult)
        assert all(
            isinstance(model_result, allowed_model_result_types) for model_result in model_results.values()
        ), "All models must be of allowed types"

        # Map from UUID to id for all energy components
        uuid_to_id = {component.get_id(): component.id for component in self.get_energy_components()}

        # Construct ConsumerFunctionResult or ConsumerSystemConsumerFunctionResult objects for each consumer
        consumer_function_results: dict[UUID, list[ConsumerFunctionResult | ConsumerSystemConsumerFunctionResult]] = {}
        for (consumer_id, _period), model_ids in process_service.get_consumer_to_model_map().items():
            is_consumer_system = process_service.components_in_system(model_ids)
            if is_consumer_system:
                result = self._build_consumer_system_function_result(
                    process_service=process_service, model_ids=model_ids, model_results=model_results
                )
                consumer_function_results.setdefault(consumer_id, []).append(result)
            else:
                result = self._build_consumer_function_result(
                    process_service=process_service, model_id=model_ids[0], model_results=model_results
                )
                if result is not None:
                    consumer_function_results.setdefault(consumer_id, []).append(result)

        # Build result for each consumer
        consumer_results: dict[UUID, CompressorResult | PumpResult | ConsumerSystemResult] = {}
        for consumer_id, consumer_function_result in consumer_function_results.items():
            consumer_name = uuid_to_id.get(consumer_id)
            assert consumer_name is not None
            component_type = self._get_graph().get_node(node_id=consumer_name).component_type

            if component_type == ComponentType.PUMP:
                pump_model_results: list[ConsumerFunctionResult] = [
                    result for result in consumer_function_result if isinstance(result, ConsumerFunctionResult)
                ]
                consumer_result = PumpResult(
                    id=consumer_name,
                    periods=self.get_expression_evaluator().get_periods(),
                    results=pump_model_results,
                )
            elif component_type in [ComponentType.PUMP_SYSTEM, ComponentType.COMPRESSOR_SYSTEM]:
                consumer_system_results: list[ConsumerSystemConsumerFunctionResult] = [
                    result
                    for result in consumer_function_result
                    if isinstance(result, ConsumerSystemConsumerFunctionResult)
                ]
                consumer_result = ConsumerSystemResult(
                    id=consumer_name,
                    periods=self.get_expression_evaluator().get_periods(),
                    results=consumer_system_results,
                )
            else:
                compressor_model_results: list[ConsumerFunctionResult] = [
                    result for result in consumer_function_result if isinstance(result, ConsumerFunctionResult)
                ]
                consumer_result = CompressorResult(
                    id=consumer_name,
                    periods=self.get_expression_evaluator().get_periods(),
                    results=compressor_model_results,
                )

            consumer_results[consumer_id] = consumer_result
        return consumer_results

    @staticmethod
    def _build_consumer_system_function_result(
        process_service: DefaultProcessService, model_ids: list[UUID], model_results: dict[UUID, Any]
    ) -> ConsumerSystemConsumerFunctionResult:
        system_id = process_service.get_consumer_system_id_by_component_ids(component_ids=model_ids)
        consumer_system_operational_input = process_service.get_consumer_system_operational_input().get(system_id)
        component_results = [model_results[model_id] for model_id in model_ids]
        consumer_names = [process_service.get_ecalc_components().get(model_id).name for model_id in model_ids]
        consumer_results_with_name = [
            SystemComponentResultWithName(name=name, result=result)
            for name, result in zip(consumer_names, component_results)
        ]
        power_loss_factor = process_service.get_evaluation_inputs().get(model_ids[0]).power_loss_factor
        return ConsumerSystemConsumerFunctionResult(
            periods=consumer_system_operational_input.periods,
            operational_setting_used=consumer_system_operational_input.operational_setting_number_used_per_timestep,
            consumer_results=consumer_results_with_name,
            cross_over_used=np.asarray(consumer_system_operational_input.crossover_used),
            power_loss_factor=power_loss_factor,
        )

    @staticmethod
    def _build_consumer_function_result(
        process_service: DefaultProcessService, model_id: UUID, model_results: dict[UUID, Any]
    ) -> ConsumerFunctionResult | None:
        model_result = model_results.get(model_id)
        if model_result is not None:
            evaluation_input = process_service.get_evaluation_inputs().get(model_id)
            power_loss_factor = evaluation_input.power_loss_factor if evaluation_input else None
            return ConsumerFunctionResult(
                periods=evaluation_input.periods,
                energy_function_result=model_result,
                power_loss_factor=power_loss_factor,
            )
        return None
