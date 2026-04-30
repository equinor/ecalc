from collections.abc import Sequence
from typing import Literal, assert_never

from libecalc.common.errors.exceptions import InvalidResourceException
from libecalc.common.time_utils import Period
from libecalc.common.units import Unit
from libecalc.common.variables import ExpressionEvaluator
from libecalc.domain.component_validation_error import DomainValidationException
from libecalc.domain.process.value_objects.chart.chart import ChartData
from libecalc.domain.regularity import Regularity
from libecalc.domain.resource import Resources
from libecalc.expression.expression import ExpressionType
from libecalc.presentation.yaml.domain.expression_time_series_flow_rate import ExpressionTimeSeriesFlowRate
from libecalc.presentation.yaml.domain.reference_service import ReferenceService
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression
from libecalc.presentation.yaml.mappers.charts.user_defined_chart_data import UserDefinedChartData
from libecalc.presentation.yaml.mappers.consumer_function_mapper import handle_condition_list
from libecalc.presentation.yaml.mappers.fluid_mapper import (
    composition_fluid_model_mapper,
    predefined_fluid_model_mapper,
)
from libecalc.presentation.yaml.mappers.model import InvalidChartResourceException
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import YamlExpressionType
from libecalc.presentation.yaml.yaml_types.components.yaml_process_system import (
    YamlCompressor,
    YamlCompressorModelChart,
    YamlCompressorStageProcessSystem,
    YamlProcessSimulation,
    YamlSerialProcessSystem,
)
from libecalc.presentation.yaml.yaml_types.models import YamlFluidModel
from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_stages import YamlControlMarginUnits
from libecalc.presentation.yaml.yaml_types.models.yaml_fluid import YamlCompositionFluidModel, YamlPredefinedFluidModel
from libecalc.presentation.yaml.yaml_types.streams.yaml_inlet_stream import YamlInletStream, YamlInletStreamRate
from libecalc.presentation.yaml.yaml_types.yaml_data_or_file import YamlFile
from libecalc.process.fluid_stream.fluid_model import FluidModel
from libecalc.process.fluid_stream.fluid_service import FluidService
from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.fluid_stream.time_series_stream import TimeSeriesStream
from libecalc.process.process_pipeline.process_pipeline import (
    ProcessPipeline,
    ProcessPipelineId,
)
from libecalc.process.process_pipeline.process_unit import ProcessUnit, ProcessUnitId
from libecalc.process.process_simulation import (
    AntiSurgeConfig,
    CommonStreamDistributionConfig,
    CommonStreamSettings,
    Constraint,
    IndividualStreamDistributionConfig,
    PressureControlConfig,
    ProcessProblem,
    ProcessSimulation,
)
from libecalc.process.process_solver.anti_surge.anti_surge_strategy import AntiSurgeStrategy
from libecalc.process.process_solver.anti_surge.common_asv import CommonASVAntiSurgeStrategy
from libecalc.process.process_solver.anti_surge.individual_asv import IndividualASVAntiSurgeStrategy
from libecalc.process.process_solver.choke_configuration_handler import ChokeConfigurationHandler
from libecalc.process.process_solver.configuration import ConfigurationHandlerId
from libecalc.process.process_solver.configuration_handler import ConfigurationHandler
from libecalc.process.process_solver.feasibility_solver import FeasibilitySolver
from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process.process_solver.process_runner import ProcessRunner
from libecalc.process.process_solver.recirculation_loop import RecirculationLoop
from libecalc.process.process_solver.search_strategies import ScipyRootFindingStrategy
from libecalc.process.process_units.choke import Choke
from libecalc.process.process_units.compressor import Compressor
from libecalc.process.process_units.direct_mixer import DirectMixer
from libecalc.process.process_units.direct_splitter import DirectSplitter
from libecalc.process.process_units.liquid_remover import LiquidRemover
from libecalc.process.process_units.temperature_setter import TemperatureSetter
from libecalc.process.shaft import VariableSpeedShaft
from libecalc.process.stream_distribution.common_stream_distribution import (
    HasExcessRate,
    Overflow,
)
from libecalc.process.stream_distribution.priorities_stream_distribution import (
    HasValidity,
)


class StreamDistributionItem(HasExcessRate, HasValidity):
    """Connects a compressor train's solver to the stream distribution system."""

    def __init__(
        self,
        feasibility_solver: FeasibilitySolver,
        target_pressure: FloatConstraint,
    ):
        self._feasibility_solver = feasibility_solver
        self._target_pressure = target_pressure

    def is_valid(self, inlet_stream: FluidStream) -> bool:
        """Can the train operate at these inlet conditions?"""
        return self.get_excess_rate(inlet_stream) == 0.0

    def get_excess_rate(self, inlet_stream: FluidStream) -> float:
        """How much rate (sm³/day) exceeds this train's capacity?"""
        return self._feasibility_solver.get_excess_rate(
            inlet_stream=inlet_stream, target_pressure=self._target_pressure
        )


def with_asv(units: Sequence[ProcessUnit]) -> tuple[ConfigurationHandler, list[ProcessUnit]]:
    mixer = DirectMixer()
    splitter = DirectSplitter()
    recirculation_loop = RecirculationLoop(
        mixer=mixer,
        splitter=splitter,
    )
    process_pipeline = [
        mixer,
        *units,
        splitter,
    ]
    return recirculation_loop, process_pipeline


def choke_factory(fluid_service: FluidService) -> tuple[Choke, ChokeConfigurationHandler]:
    choke = Choke(fluid_service=fluid_service)

    return choke, ChokeConfigurationHandler(
        choke=choke,
    )


class ProcessSimulationMapper:
    def __init__(
        self,
        expression_evaluator: ExpressionEvaluator,
        fluid_service: FluidService,
        reference_service: ReferenceService,
        process_simulation_period: Period,
        resources: Resources,
    ):
        self._expression_evaluator = expression_evaluator.get_subset_for_period(process_simulation_period)
        self._fluid_service = fluid_service
        self._reference_service = reference_service
        self._resources = resources

    def _resolve_train_reference(self, ref: str | YamlSerialProcessSystem) -> YamlSerialProcessSystem:
        if isinstance(ref, str):
            return self._reference_service.get_process_system(reference=ref)
        else:
            return ref

    def _resolve_compressor_stage_reference(
        self, ref: str | YamlCompressorStageProcessSystem
    ) -> YamlCompressorStageProcessSystem:
        if isinstance(ref, str):
            return self._reference_service.get_compressor_stage(reference=ref)
        else:
            return ref

    def _resolve_compressor_reference(self, ref: str | YamlCompressor) -> YamlCompressor:
        if isinstance(ref, str):
            return self._reference_service.get_compressor(reference=ref)
        else:
            return ref

    def _get_compressor_chart(self, yaml_compressor_model_chart: YamlCompressorModelChart) -> ChartData:
        yaml_chart = yaml_compressor_model_chart.chart
        yaml_curves = yaml_chart.curves
        control_margin = yaml_compressor_model_chart.control_margin
        control_margin_unit = (
            Unit.FRACTION if control_margin.unit == YamlControlMarginUnits.FRACTION else Unit.PERCENTAGE
        )
        control_margin_fraction = control_margin_unit.to(Unit.FRACTION)(control_margin.value)

        if isinstance(yaml_curves, YamlFile):
            resource_name = yaml_curves.file
            resource = self._resources.get(resource_name)
            if resource is None:
                raise DomainValidationException(f"Resource '{resource_name}' not found for variable speed chart.")
            try:
                return UserDefinedChartData.from_resource(
                    resource, units=yaml_chart.units, is_single_speed=False, control_margin=control_margin_fraction
                )
            except InvalidResourceException as e:
                raise InvalidChartResourceException(
                    message=str(e), file_mark=e.file_mark, resource_name=resource_name
                ) from e
        else:
            return UserDefinedChartData.from_yaml_curves(
                yaml_curves, units=yaml_chart.units, control_margin=control_margin_fraction
            )

    def _get_compressor(self, yaml_compressor_stage: YamlCompressorStageProcessSystem) -> Compressor:
        yaml_compressor = self._resolve_compressor_reference(yaml_compressor_stage.compressor)

        chart: ChartData = self._get_compressor_chart(yaml_compressor_model_chart=yaml_compressor.compressor_model)

        return Compressor(
            compressor_chart=chart,
            fluid_service=self._fluid_service,
        )

    def _resolve_stream_reference(self, ref: str | YamlInletStream) -> YamlInletStream:
        if isinstance(ref, str):
            return self._reference_service.get_stream(reference=ref)
        else:
            return ref

    def _resolve_fluid_model_reference(self, ref: str | YamlFluidModel) -> YamlFluidModel:
        if isinstance(ref, str):
            return self._reference_service.get_fluid(reference=ref)
        else:
            return ref

    def _map_conditions(self, condition: YamlExpressionType | None, conditions: list[YamlExpressionType] | None):
        if condition:
            assert isinstance(condition, ExpressionType)
            return condition
        else:
            assert isinstance(conditions, list)
            return handle_condition_list(conditions)

    def _get_regularity(self) -> Regularity:
        return Regularity(
            expression_evaluator=self._expression_evaluator,
            target_period=self._expression_evaluator.get_period(),
        )

    def _map_rate(
        self, yaml_rate: YamlInletStreamRate
    ) -> ExpressionTimeSeriesFlowRate:  # TODO: Ok? treat everything as expression when reading from yaml?
        return ExpressionTimeSeriesFlowRate(
            time_series_expression=TimeSeriesExpression(
                expression_evaluator=self._expression_evaluator,
                expression=yaml_rate.value,
                condition=self._map_conditions(yaml_rate.condition, yaml_rate.conditions),
            ),
            consumption_rate_type=yaml_rate.type,
            regularity=self._get_regularity(),
        )

    def _map_pressure(self, pressure: ExpressionType) -> TimeSeriesExpression:
        return TimeSeriesExpression(
            expression_evaluator=self._expression_evaluator,
            expression=pressure,
        )

    def _map_temperature(self, temperature: ExpressionType) -> TimeSeriesExpression:
        return TimeSeriesExpression(
            expression_evaluator=self._expression_evaluator,
            expression=temperature,
        )

    def _map_fluid_model(self, yaml_fluid_model: YamlFluidModel) -> FluidModel:
        match yaml_fluid_model:
            case YamlPredefinedFluidModel():
                return predefined_fluid_model_mapper(yaml_fluid_model)
            case YamlCompositionFluidModel():
                return composition_fluid_model_mapper(yaml_fluid_model)
            case _:
                assert_never(yaml_fluid_model)

    def map_anti_surge_strategy(
        self,
        simulator: ProcessRunner,
        recirculation_loop_ids: Sequence[ConfigurationHandlerId],
        compressors: Sequence[Compressor],
        recirculation_type: Literal["INDIVIDUAL_ASV", "COMMON_ASV"],
    ) -> AntiSurgeStrategy:
        match recirculation_type:
            case "COMMON_ASV":
                return CommonASVAntiSurgeStrategy(
                    simulator=simulator,
                    root_finding_strategy=ScipyRootFindingStrategy(),
                    first_compressor=compressors[0],
                    recirculation_loop_id=recirculation_loop_ids[0],
                )
            case "INDIVIDUAL_ASV":
                return IndividualASVAntiSurgeStrategy(
                    simulator=simulator,
                    recirculation_loop_ids=recirculation_loop_ids,
                    compressors=compressors,
                )
            case _:
                assert_never(recirculation_type)

    def map_process_simulation(
        self, yaml_process_simulation: YamlProcessSimulation
    ) -> tuple[list[ProcessPipeline], ProcessSimulation]:
        process_pipelines: list[ProcessPipeline] = []
        constraints: dict[ProcessPipelineId, Constraint] = {}
        pressure_control_configs: dict[ProcessPipelineId, PressureControlConfig] = {}
        anti_surge_configs: dict[ProcessPipelineId, AntiSurgeConfig] = {}

        process_pipeline_reference_to_id_map: dict[str, ProcessPipelineId] = {}
        for yaml_compressor_train_item in yaml_process_simulation.targets:
            shaft = VariableSpeedShaft()
            item = self._resolve_train_reference(yaml_compressor_train_item.target)
            process_unit_map: dict[ProcessUnitId, ProcessUnit] = {}
            compressor_stages: list[list[ProcessUnitId]] = []
            compressor_ids: list[ProcessUnitId] = []
            for yaml_serial_item in item.items:
                yaml_compressor_stage = self._resolve_compressor_stage_reference(yaml_serial_item.target)
                compressor = self._get_compressor(yaml_compressor_stage=yaml_compressor_stage)
                compressor_ids.append(compressor.get_id())
                temperature_setter = TemperatureSetter(
                    required_temperature_kelvin=0,
                    fluid_service=self._fluid_service,
                )
                choke = Choke(fluid_service=self._fluid_service, pressure_change=0)
                liquid_remover = LiquidRemover(fluid_service=self._fluid_service)
                process_unit_map[temperature_setter.get_id()] = temperature_setter
                process_unit_map[choke.get_id()] = choke
                process_unit_map[liquid_remover.get_id()] = liquid_remover
                process_unit_map[compressor.get_id()] = compressor

                compressor_stages.append(
                    [temperature_setter.get_id(), choke.get_id(), liquid_remover.get_id(), compressor.get_id()]
                )

            for compressor_id in compressor_ids:
                compressor = process_unit_map[compressor_id]
                assert isinstance(compressor, Compressor)
                shaft.connect(compressor)

            try:
                pressure_control = yaml_process_simulation.pressure_control[item.name]
            except KeyError as e:
                raise DomainValidationException(f"Missing pressure control for process system '{item.name}'") from e

            configuration_handlers = []

            if pressure_control == "COMMON_ASV":
                recirculation_loop, process_units = with_asv(units=list(process_unit_map.values()))
                configuration_handlers.append(recirculation_loop)
            else:
                process_units = []
                configuration_handlers = []
                for compressor_stage_ids in compressor_stages:
                    stage_units = [process_unit_map[stage_unit_id] for stage_unit_id in compressor_stage_ids]
                    recirculation_loop, stage_process_units = with_asv(units=stage_units)
                    configuration_handlers.append(recirculation_loop)
                    process_units.extend(stage_process_units)

            if pressure_control == "DOWNSTREAM_CHOKE":
                choke, choke_configuration_handler = choke_factory(fluid_service=self._fluid_service)
                configuration_handlers.append(choke_configuration_handler)
                process_units.append(choke)
            elif pressure_control == "UPSTREAM_CHOKE":
                choke, choke_configuration_handler = choke_factory(fluid_service=self._fluid_service)
                configuration_handlers.append(choke_configuration_handler)
                process_units = [choke, *process_units]
            process_pipeline = ProcessPipeline(
                stream_propagators=process_units,
            )

            pressure_control_configs[process_pipeline.get_id()] = PressureControlConfig(
                type=pressure_control,
            )
            anti_surge_configs[process_pipeline.get_id()] = AntiSurgeConfig(
                type="COMMON_ASV" if pressure_control == "COMMON_ASV" else "INDIVIDUAL_ASV",
            )
            process_pipeline_reference_to_id_map[item.name] = process_pipeline.get_id()
            process_pipelines.append(process_pipeline)

        for process_pipeline_reference, constraint in yaml_process_simulation.constraints.items():
            process_pipeline_id = process_pipeline_reference_to_id_map.get(process_pipeline_reference)
            if process_pipeline_id is None:
                raise DomainValidationException(
                    f"Constraint specified for unknown process system '{process_pipeline_reference}'"
                )
            constraints[process_pipeline_id] = Constraint(
                outlet_pressure=TimeSeriesExpression(
                    expression=constraint.outlet_pressure, expression_evaluator=self._expression_evaluator
                ),
            )

        yaml_stream_distribution = yaml_process_simulation.stream_distribution

        match yaml_stream_distribution.method:
            case "COMMON_STREAM":
                settings = []
                for setting in yaml_stream_distribution.settings:
                    rate_fractions: list[TimeSeriesExpression] = []
                    for rate_fraction in setting.rate_fractions:
                        rate_fractions.append(
                            TimeSeriesExpression(
                                expression=rate_fraction,
                                expression_evaluator=self._expression_evaluator,
                                condition=None,
                            )
                        )

                    overflows = []
                    for overflow in setting.overflow or []:
                        try:
                            to_id = process_pipeline_reference_to_id_map[overflow.to_reference]
                        except KeyError as e:
                            raise DomainValidationException(
                                f"Process system reference '{overflow.to_reference}' defined in overflow does not exist."
                            ) from e

                        try:
                            from_id = process_pipeline_reference_to_id_map[overflow.from_reference]
                        except KeyError as e:
                            raise DomainValidationException(
                                f"Process system reference '{overflow.from_reference}' defined in overflow does not exist."
                            ) from e

                        overflows.append(
                            Overflow(
                                to_id=to_id,
                                from_id=from_id,
                            )
                        )
                    settings.append(
                        CommonStreamSettings(
                            rate_fractions=rate_fractions,
                            overflow=overflows,
                        )
                    )

                yaml_stream = self._resolve_stream_reference(yaml_stream_distribution.inlet_stream)
                yaml_fluid_model = self._resolve_fluid_model_reference(yaml_stream.fluid_model)
                inlet_stream = TimeSeriesStream(
                    pressure_bara=self._map_pressure(yaml_stream.pressure),
                    standard_rate_m3_per_day=self._map_rate(yaml_stream.rate),
                    temperature_kelvin=self._map_temperature(yaml_stream.temperature),
                    fluid_model=self._map_fluid_model(yaml_fluid_model),
                )
                stream_distribution = CommonStreamDistributionConfig(
                    inlet_stream=inlet_stream,
                    settings=settings,
                )
            case "INDIVIDUAL_STREAMS":
                inlet_streams = []
                for inlet_stream in yaml_stream_distribution.inlet_streams:
                    yaml_stream = self._resolve_stream_reference(inlet_stream)
                    yaml_fluid_model = self._resolve_fluid_model_reference(yaml_stream.fluid_model)
                    inlet_streams.append(
                        TimeSeriesStream(
                            pressure_bara=self._map_pressure(yaml_stream.pressure),
                            standard_rate_m3_per_day=self._map_rate(yaml_stream.rate),
                            temperature_kelvin=self._map_temperature(yaml_stream.temperature),
                            fluid_model=self._map_fluid_model(yaml_fluid_model),
                        )
                    )
                stream_distribution = IndividualStreamDistributionConfig(
                    inlet_streams=inlet_streams,
                )
            case _:
                assert_never(yaml_stream_distribution.method)

        process_problems = [
            ProcessProblem(
                process_pipeline_id=process_pipeline.get_id(),
                constraint=constraints[process_pipeline.get_id()],
                anti_surge_strategy=anti_surge_configs[process_pipeline.get_id()],
                pressure_control_strategy=pressure_control_configs[process_pipeline.get_id()],
            )
            for process_pipeline in process_pipelines
        ]

        return (
            process_pipelines,
            ProcessSimulation(
                process_problems=process_problems,
                stream_distribution=stream_distribution,
            ),
        )
