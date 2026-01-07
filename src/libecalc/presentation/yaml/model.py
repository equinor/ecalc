import operator
import uuid
from collections.abc import Iterable
from datetime import datetime
from functools import cached_property, reduce
from typing import Any, Self

from libecalc.common.component_type import ComponentType
from libecalc.common.time_utils import Period, Periods
from libecalc.common.units import Unit
from libecalc.common.utils.rates import TimeSeriesBoolean, TimeSeriesFloat, TimeSeriesInt, TimeSeriesStreamDayRate
from libecalc.common.variables import ExpressionEvaluator, VariablesMap
from libecalc.core.result import ComponentResult, CompressorResult
from libecalc.core.result.results import PumpResult
from libecalc.domain.component_validation_error import DomainValidationException
from libecalc.domain.energy import ComponentEnergyContext, Emitter, EnergyModel
from libecalc.domain.energy.energy_component import EnergyContainerID
from libecalc.domain.infrastructure.energy_components.asset.asset import Asset
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function import ConsumerFunctionResult
from libecalc.domain.installation import (
    ElectricityProducer,
    FuelConsumer,
    Installation,
    PowerConsumer,
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
from libecalc.domain.regularity import Regularity
from libecalc.dto.node_info import NodeInfo
from libecalc.presentation.yaml.domain.category_service import CategoryService
from libecalc.presentation.yaml.domain.default_process_service import DefaultProcessService
from libecalc.presentation.yaml.domain.energy_container_energy_model_builder import EnergyContainerEnergyModel
from libecalc.presentation.yaml.domain.reference_service import ReferenceService
from libecalc.presentation.yaml.domain.time_series_collections import TimeSeriesCollections
from libecalc.presentation.yaml.domain.time_series_resource import TimeSeriesResource
from libecalc.presentation.yaml.mappers.component_mapper import EcalcModelMapper
from libecalc.presentation.yaml.mappers.variables_mapper import map_yaml_to_variables
from libecalc.presentation.yaml.mappers.variables_mapper.get_global_time_vector import (
    InvalidEndDate,
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
        consumer_results: dict[EnergyContainerID, ComponentResult],
        component_id: EnergyContainerID,
    ):
        self._energy_model = energy_model
        self._consumer_results = consumer_results
        self._component_id = component_id

    def _get_consumers_of_current(self) -> list[ComponentResult]:
        return [
            self._consumer_results[consumer_id] for consumer_id in self._energy_model.get_consumers(self._component_id)
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
        configuration: YamlValidator,
        resource_service: ResourceService,
    ) -> None:
        self._configuration = configuration
        self._resource_service = resource_service

        self._is_validated = False
        self._input: Asset | None = None

        self._consumer_results: dict[EnergyContainerID, ComponentResult] = {}
        self._emission_results: dict[uuid.UUID, dict[str, TimeSeriesStreamDayRate]] = {}

        self._time_series_collections: TimeSeriesCollections | None = None
        self._variables: VariablesMap | None = None
        self._mapping_context = MappingContext(target_period=self.period)

        self._id = uuid.uuid4()  # ID used for "asset" energy container, which is the same as model?

    def get_emitter(self, container_id: uuid.UUID) -> Emitter | None:
        for installation in self.get_installations():
            for emitter in installation.get_emitters():
                if emitter.get_id() == container_id:
                    return emitter

        return None

    def get_electricity_producer(self, sub_container_id: EnergyContainerID) -> ElectricityProducer | None:
        for installation in self.get_installations():
            for electricity_producer in installation.get_electricity_producers():
                if electricity_producer.get_id() == sub_container_id:
                    return electricity_producer
        return None

    def get_fuel_consumer(self, container_id: EnergyContainerID) -> FuelConsumer | None:
        for installation in self.get_installations():
            for fuel_consumer in installation.get_fuel_consumers():
                if fuel_consumer.get_id() == container_id:
                    return fuel_consumer
        return None

    def get_power_consumer(self, container_id: EnergyContainerID) -> PowerConsumer | None:
        for installation in self.get_installations():
            for power_consumer in installation.get_power_consumers():
                if power_consumer.get_id() == container_id:
                    return power_consumer
        return None

    def get_regularity(self, container_id: EnergyContainerID) -> Regularity:
        return self._mapping_context.get_regularity(container_id)

    def get_container_result(self, sub_container_id):
        # Temporary, until we find a better way to represent these results
        return self._consumer_results[sub_container_id]

    def get_operational_settings_used(self, container_id) -> TimeSeriesInt:
        return self._consumer_results[container_id].operational_settings_used

    def get_name(self) -> str:
        return self._configuration.name

    @cached_property
    def _energy_model(self) -> EnergyModel:
        self.validate_for_run()
        return self._mapping_context.get_energy_container_energy_model_builder().build()

    def get_energy_model(self) -> EnergyModel:
        return self._energy_model

    def get_container_info(self, container_id: EnergyContainerID) -> NodeInfo:
        energy_component = self.get_energy_model().get_energy_container(container_id)
        return NodeInfo(
            id=energy_component.get_id(),
            name=energy_component.get_name(),
            component_type=energy_component.get_component_process_type(),
        )

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
        assert self._configuration.end is not None
        try:
            time_vector = get_global_time_vector(
                time_series_time_vector=time_series_time_vector,
                start=self._configuration.start,
                end=self._configuration.end,
                additional_dates=self._configuration.dates,
            )
            return Periods.create_periods(time_vector, include_before=False, include_after=False)
        except InvalidEndDate as e:
            location_keys = ("END",)
            raise ModelValidationException(
                errors=[
                    ModelValidationError(
                        message=str(e),
                        location=Location(keys=location_keys),
                        file_context=self._configuration.get_file_context(location_keys),
                    )
                ]
            ) from e
        except DomainValidationException as e:
            raise ModelValidationException(
                errors=[
                    ModelValidationError(
                        message=str(e),
                        location=Location(keys=""),
                        file_context=self._configuration.get_file_context(()),
                    )
                ]
            ) from e

    @property
    def variables(self) -> VariablesMap:
        assert self._is_validated
        assert self._variables is not None
        return self._variables

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

            self._input = model_mapper.from_yaml_to_domain(model_id=self._id, model_name=self._configuration.name)

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

    def _get_context(self, component_id: EnergyContainerID) -> ComponentEnergyContext:
        return Context(
            energy_model=self.get_energy_model(),
            consumer_results=self._consumer_results,
            component_id=component_id,
        )

    def evaluate_energy_usage(self):
        energy_components = self.get_energy_model().get_energy_components()

        # Evaluate process systems (compressor trains and pumps).
        process_system_results = self._evaluate_process_systems()

        # Evaluate all sampled compressors.
        compressors_sampled_results = self._evaluate_compressors_sampled()

        all_model_results = {**process_system_results, **compressors_sampled_results}

        # Get consumer energy results from model evaluations
        consumer_results_from_models = self.get_consumer_energy_results_from_domain_models(
            model_results=all_model_results
        )

        for energy_component_id in energy_components:
            energy_component = self.get_energy_model().get_energy_container(energy_component_id)
            if hasattr(energy_component, "evaluate_energy_usage"):
                context = self._get_context(energy_component.get_id())

                if consumer_results_from_models.get(energy_component.get_id()) is not None:
                    # For compressors and pumps, get the consumer result from the model evaluation
                    consumer_result = consumer_results_from_models.get(energy_component.get_id())
                    energy_component._consumer_result = consumer_result
                else:
                    # For other energy components (e.g. direct consumer function, tabular consumer function, consumer systems) evaluate energy usage using consumer functions
                    consumer_result = energy_component.evaluate_energy_usage(context=context)

                self._consumer_results[energy_component.get_id()] = consumer_result

    def evaluate_emissions(self):
        """
        Calculate emissions for fuel consumers and emitters

        Returns: a mapping from consumer_id to emissions
        """
        for energy_component_id in self.get_energy_model().get_energy_components():
            energy_component = self.get_energy_model().get_energy_container(energy_component_id)
            if isinstance(energy_component, Emitter):
                emission_result = energy_component.evaluate_emissions(
                    energy_context=self._get_context(energy_component.get_id()),
                )

                if emission_result is not None:
                    self._emission_results[energy_component.get_id()] = emission_result

    def get_validity(self, component_id: EnergyContainerID) -> TimeSeriesBoolean:
        energy_model = self.get_energy_model()
        component = energy_model.get_energy_container(component_id)
        if isinstance(component, Installation | Asset):
            # Aggregate for asset and installation
            validity = []

            # get_all_children instead of get_consumers/get_children since Genset both has its own is_valid while also having 'children'
            # TODO: There's a difference between a container and a provider, but we capture both in our EnergyModel. children vs consumer, installation vs genset. Installation is a container, genset is a provider
            assert isinstance(energy_model, EnergyContainerEnergyModel)
            children = energy_model.get_all_children(component_id)
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

    def _evaluate_compressor_process_systems(self) -> dict[uuid.UUID, CompressorTrainResult]:
        process_service = self.get_process_service()
        compressor_process_systems = process_service.compressor_process_systems

        evaluated_systems = {}
        for id, process_system in compressor_process_systems.items():
            evaluation_input = process_service.get_evaluation_input(model_id=id)
            assert isinstance(evaluation_input, CompressorEvaluationInput)
            assert isinstance(process_system, CompressorTrainModel | CompressorWithTurbineModel)
            evaluation_input.apply_to_model(process_system)
            model_result = process_system.evaluate()
            evaluated_systems[id] = model_result
        return evaluated_systems

    def _evaluate_pump_process_systems(self) -> dict[uuid.UUID, PumpModelResult]:
        process_service = self.get_process_service()
        pump_process_systems = process_service.pump_process_systems

        evaluated_systems = {}
        for id, process_system in pump_process_systems.items():
            evaluation_input = process_service.get_evaluation_input(model_id=id)
            assert isinstance(evaluation_input, PumpEvaluationInput)
            assert isinstance(process_system, PumpModel)
            evaluation_input.apply_to_model(process_system)
            model_result = process_system.evaluate()
            evaluated_systems[id] = model_result
        return evaluated_systems

    def _evaluate_compressors_sampled(self) -> dict[uuid.UUID, CompressorTrainResult]:
        process_service = self.get_process_service()
        compressors_sampled = process_service.compressors_sampled

        evaluated_compressors_sampled = {}
        for id, compressor_sampled in compressors_sampled.items():
            evaluation_input = process_service.get_evaluation_input(model_id=id)
            assert isinstance(evaluation_input, CompressorSampledEvaluationInput)
            assert isinstance(compressor_sampled, CompressorModelSampled | CompressorWithTurbineModel)
            evaluation_input.apply_to_model(compressor_sampled)
            model_result = compressor_sampled.evaluate()
            evaluated_compressors_sampled[id] = model_result
        return evaluated_compressors_sampled

    def _evaluate_process_systems(self) -> dict[uuid.UUID, CompressorTrainResult | PumpModelResult]:
        """
        Evaluates domain process systems and returns a mapping: model_id -> evaluated_result.
        """
        compressor_system_results = self._evaluate_compressor_process_systems()
        pump_system_results = self._evaluate_pump_process_systems()
        process_system_results = {**compressor_system_results, **pump_system_results}

        return process_system_results

    def get_consumer_energy_results_from_domain_models(
        self, model_results: dict[uuid.UUID, Any]
    ) -> dict[uuid.UUID, CompressorResult | PumpResult]:
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

        # Construct ConsumerFunctionResult objects for each consumer
        consumer_function_results: dict[uuid.UUID, list[ConsumerFunctionResult]] = {}
        for (consumer_id, _period), model_id in process_service.consumer_to_model_map.items():
            model_result = model_results.get(model_id)
            if model_result is not None:
                evaluation_input = process_service.get_evaluation_input(model_id=model_id)
                power_loss_factor = evaluation_input.power_loss_factor if evaluation_input else None
                consumer_function_results.setdefault(consumer_id, []).append(
                    ConsumerFunctionResult(
                        periods=evaluation_input.periods,
                        energy_function_result=model_result,
                        power_loss_factor=power_loss_factor,
                    )
                )

        # Build result for each consumer
        consumer_results: dict[uuid.UUID, CompressorResult | PumpResult] = {}
        for consumer_id, consumer_function_result in consumer_function_results.items():
            container_info = self.get_container_info(consumer_id)

            if container_info.component_type == ComponentType.PUMP:
                assert all(isinstance(result, ConsumerFunctionResult) for result in consumer_function_result)
                consumer_result = PumpResult(
                    id=container_info.name,
                    periods=self.get_expression_evaluator().get_periods(),
                    results=consumer_function_result,
                )
            else:
                assert all(isinstance(result, ConsumerFunctionResult) for result in consumer_function_result)
                consumer_result = CompressorResult(
                    id=container_info.name,
                    periods=self.get_expression_evaluator().get_periods(),
                    results=consumer_function_result,
                )

            consumer_results[consumer_id] = consumer_result
        return consumer_results
