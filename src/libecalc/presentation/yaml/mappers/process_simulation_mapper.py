from collections.abc import Mapping
from typing import Any, assert_never

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.common.errors.exceptions import InvalidResourceException, ProgrammingError
from libecalc.common.units import Unit
from libecalc.common.variables import ExpressionEvaluator
from libecalc.domain.regularity import Regularity
from libecalc.domain.resource import Resources
from libecalc.ecalc_model.equipment.equipment_id import EquipmentId
from libecalc.ecalc_model.equipment.shaft_equipment import ShaftEquipment
from libecalc.ecalc_model.process.configuration_handlers import (
    TimeSeriesConfigurationHandler,
    TimeSeriesShaftConfigurationHandler,
)
from libecalc.ecalc_model.process.process_pipeline import (
    PipelineEvent,
    PipelineEventAction,
    PipelineEventChangeType,
    ProcessPipeline,
    ProcessPipelineSection,
)
from libecalc.ecalc_model.process.process_units import (
    TimeSeriesCompressorProcessUnit,
    TimeSeriesInletProcessUnit,
    TimeSeriesLiquidRemoverProcessUnit,
    TimeSeriesMixerProcessUnit,
    TimeSeriesOutletProcessUnit,
    TimeSeriesPressureDropperProcessUnit,
    TimeSeriesProcessUnit,
    TimeSeriesSplitterProcessUnit,
    TimeSeriesTemperatureSetterProcessUnit,
)
from libecalc.ecalc_model.process_simulation import (
    AntiSurgeConfig,
    CommonStreamDistributionConfig,
    CommonStreamSettings,
    Constraint,
    IndividualStreamDistributionConfig,
    PressureControlConfig,
    ProcessProblem,
    ProcessProblemSection,
    ProcessSimulation,
)
from libecalc.ecalc_model.time_series_configuration import (
    TimeSeriesMixerConfiguration,
    TimeSeriesPressureDropperConfiguration,
    TimeSeriesSplitterConfiguration,
    TimeSeriesTemperatureSetterConfiguration,
)
from libecalc.ecalc_model.time_series_fluid_model import TimeSeriesFluidModel
from libecalc.ecalc_model.time_series_stream import TimeSeriesStream
from libecalc.ecalc_model.timeline_event import TimelineEventService
from libecalc.expression.expression import ExpressionType
from libecalc.presentation.yaml.domain.expression_time_series_flow_rate import ExpressionTimeSeriesFlowRate
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression
from libecalc.presentation.yaml.mappers.charts.user_defined_chart_mapper import (
    user_defined_chart_from_resource,
    user_defined_chart_from_yaml_curves,
)
from libecalc.presentation.yaml.mappers.consumer_function_mapper import handle_condition_list
from libecalc.presentation.yaml.mappers.fluid_mapper import fluid_definition_mapper
from libecalc.presentation.yaml.mappers.model import InvalidChartResourceException
from libecalc.presentation.yaml.mappers.process.build_sections import ProcessSectionBuilder
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import YamlExpressionType
from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_stages import YamlControlMarginUnits
from libecalc.presentation.yaml.yaml_types.process.yaml_fluid_definitions import (
    YamlCompositionFluidDefinition,
    YamlFluidDefinition,
    YamlPredefinedFluidDefinition,
)
from libecalc.presentation.yaml.yaml_types.process.yaml_process_pipeline import (
    YamlCompressorProcessUnitInstance,
    YamlProcessPipeline,
)
from libecalc.presentation.yaml.yaml_types.process.yaml_process_references import (
    InstanceReference,
)
from libecalc.presentation.yaml.yaml_types.process.yaml_process_simulation import (
    YamlProcessSimulation,
)
from libecalc.presentation.yaml.yaml_types.process.yaml_process_units import (
    YamlCompressorModelChart,
    YamlLiquidRemoverDefinition,
    YamlMixerDefinition,
    YamlPressureDropperDefinition,
    YamlSplitterDefinition,
    YamlTemperatureSetterDefinition,
)
from libecalc.presentation.yaml.yaml_types.process.yaml_stream_distribution import (
    YamlCommonStreamDistribution,
    YamlIndividualStreamDistribution,
)
from libecalc.presentation.yaml.yaml_types.streams.yaml_inlet_stream import YamlInletStream, YamlInletStreamRate
from libecalc.presentation.yaml.yaml_types.yaml_compressor import CompressorReference
from libecalc.presentation.yaml.yaml_types.yaml_data_or_file import YamlFile
from libecalc.presentation.yaml.yaml_types.yaml_shaft import ShaftReference
from libecalc.process.chart.chart import ChartData
from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_pipeline.process_pipeline import ProcessPipelineId
from libecalc.process.process_pipeline.process_unit import ProcessUnitId
from libecalc.process.process_solver.feasibility_solver import FeasibilitySolver
from libecalc.process.process_solver.float_constraint import FloatConstraint
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


class ProcessSimulationMapper:
    def __init__(
        self,
        expression_evaluator: ExpressionEvaluator,
        references: dict[InstanceReference, Any],
        resources: Resources,
        shafts: Mapping[ShaftReference, ShaftEquipment],
        compressor_equipment_ids: Mapping[CompressorReference, EquipmentId],
        timeline_event_service: TimelineEventService,
    ):
        self._expression_evaluator = expression_evaluator
        self._references = references
        self._resources = resources
        self._timeline_event_service = timeline_event_service
        self._shaft_by_compressor_equipment_id: dict[EquipmentId, ShaftEquipment] = {
            compressor_equipment_id: shaft
            for shaft in shafts.values()
            for compressor_equipment_id in shaft.compressor_equipment_ids
        }
        self._compressor_equipment_ids = compressor_equipment_ids

    def _resolve_pipeline_reference(self, ref: str | YamlProcessPipeline) -> YamlProcessPipeline:
        if isinstance(ref, str):
            o = self._references.get(ref)
            assert isinstance(o, YamlProcessPipeline)
            return o
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
                raise EcalcValidationException(f"Resource '{resource_name}' not found for variable speed chart.")
            if "SPEED" not in resource.get_headers():
                raise EcalcValidationException(
                    f"Chart resource '{resource_name}' is missing required 'SPEED' column. "
                    f"For single-speed charts, use the same speed value for all rows."
                )
            try:
                return user_defined_chart_from_resource(
                    resource,
                    units=yaml_chart.units,
                    is_single_speed=False,
                    control_margin=control_margin_fraction,
                )
            except InvalidResourceException as e:
                raise InvalidChartResourceException(
                    message=str(e), file_mark=e.file_mark, resource_name=resource_name
                ) from e
        else:
            return user_defined_chart_from_yaml_curves(
                yaml_curves, units=yaml_chart.units, control_margin=control_margin_fraction
            )

    def _resolve_stream_reference(self, ref: str | YamlInletStream) -> YamlInletStream:
        if isinstance(ref, str):
            o = self._references.get(ref)
            assert isinstance(o, YamlInletStream)
            return o
        else:
            return ref

    def _map_conditions(
        self, conditions: YamlExpressionType | list[YamlExpressionType] | None
    ) -> YamlExpressionType | None:
        if conditions is None:
            return None
        if isinstance(conditions, list):
            return handle_condition_list(conditions)
        assert isinstance(conditions, int | str | float)
        return conditions

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
                condition=self._map_conditions(
                    yaml_rate.conditions if yaml_rate.conditions is not None else yaml_rate.condition
                ),
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

    def _map_fluid_definition(
        self,
        fluid_definition: YamlFluidDefinition,
    ) -> TimeSeriesFluidModel:
        return fluid_definition_mapper(
            fluid_definition,
            expression_evaluator=self._expression_evaluator,
        )

    def _map_stream(self, yaml_stream: YamlInletStream) -> TimeSeriesStream:
        yaml_fluid_definition = yaml_stream.fluid
        assert isinstance(yaml_fluid_definition, YamlPredefinedFluidDefinition | YamlCompositionFluidDefinition)
        return TimeSeriesStream(
            pressure_bara=self._map_pressure(yaml_stream.pressure),
            standard_rate_m3_per_day=self._map_rate(yaml_stream.rate),
            temperature_kelvin=self._map_temperature(yaml_stream.temperature),
            fluid_model=self._map_fluid_definition(yaml_fluid_definition),
        )

    def _validate_and_map_pipeline_events(
        self,
        yaml_pipeline: YamlProcessPipeline,
        unit_name_to_id: dict[InstanceReference, ProcessUnitId],
        process_unit_map: dict[ProcessUnitId, TimeSeriesProcessUnit],
    ) -> list[PipelineEvent]:
        """Validate pipeline event references and map to domain objects."""
        events: list[PipelineEvent] = []

        for yaml_event in yaml_pipeline.events:
            timeline_event = self._timeline_event_service.get_event_by_reference(yaml_event.ref)
            change_target = unit_name_to_id[yaml_event.change_target]
            change_target_unit = process_unit_map[change_target]
            if not isinstance(change_target_unit, TimeSeriesCompressorProcessUnit):
                raise EcalcValidationException(
                    f"Pipeline event CHANGE_TARGET '{yaml_event.change_target}' is not a compressor."
                )
            match yaml_event.change_to:
                case YamlCompressorModelChart():
                    # Same compressor after the rebundle, so the new model keeps its process unit id and equipment.
                    change_to_unit = TimeSeriesCompressorProcessUnit(
                        compressor_chart=self._get_compressor_chart(yaml_compressor_model_chart=yaml_event.change_to),
                        compressor_equipment_id=change_target_unit.compressor_equipment_id,
                        process_unit_id=change_target,
                    )
                case _:
                    raise EcalcValidationException(
                        f"Pipeline event CHANGE_TO '{yaml_event.change_to}' is not a compressor model."
                    )

            events.append(
                PipelineEvent(
                    action=PipelineEventAction(yaml_event.type.value),
                    change_target=change_target,
                    change_to=change_to_unit,
                    change_type=PipelineEventChangeType(yaml_event.change_type.value),
                    change_time=timeline_event.from_when,
                )
            )

        return events

    def map_process_simulation(
        self, yaml_process_simulation: YamlProcessSimulation
    ) -> tuple[list[ProcessPipeline], ProcessSimulation]:
        process_pipelines: list[ProcessPipeline] = []
        process_problems: list[ProcessProblem] = []

        # Some configurations are not found/set by the solver, but set by user upon process_simulation creation
        predefined_configurations: dict[
            ProcessPipelineId,
            dict[
                ProcessUnitId,
                TimeSeriesTemperatureSetterConfiguration
                | TimeSeriesPressureDropperConfiguration
                | TimeSeriesMixerConfiguration
                | TimeSeriesSplitterConfiguration,
            ],
        ] = {}

        process_pipeline_reference_to_id_map: dict[str, ProcessPipelineId] = {}
        section_builder = ProcessSectionBuilder()
        # Created on each call, not shared: a shaft holds its connected compressors.
        shafts: dict[EquipmentId, TimeSeriesShaftConfigurationHandler] = {}
        for yaml_compressor_train_item in yaml_process_simulation.targets:
            problem_configuration_handlers: list[TimeSeriesConfigurationHandler] = []
            item = self._resolve_pipeline_reference(yaml_compressor_train_item)
            process_unit_map: dict[ProcessUnitId, TimeSeriesProcessUnit] = {}
            unit_name_to_id: dict[InstanceReference, ProcessUnitId] = {}
            problem_time_series_configurations: dict[
                ProcessUnitId,
                TimeSeriesTemperatureSetterConfiguration
                | TimeSeriesPressureDropperConfiguration
                | TimeSeriesMixerConfiguration
                | TimeSeriesSplitterConfiguration,
            ] = {}

            for yaml_process_unit in item.process_units:
                match yaml_process_unit:
                    case YamlCompressorProcessUnitInstance():
                        if not isinstance(yaml_process_unit.model, YamlCompressorModelChart):
                            raise EcalcValidationException(
                                f"MODEL '{yaml_process_unit.model}' of compressor '{yaml_process_unit.compressor}' is "
                                "not a compressor model."
                            )
                        compressor_equipment_id = self._compressor_equipment_ids[yaml_process_unit.compressor]
                        unit = TimeSeriesCompressorProcessUnit(
                            compressor_chart=self._get_compressor_chart(
                                yaml_compressor_model_chart=yaml_process_unit.model
                            ),
                            compressor_equipment_id=compressor_equipment_id,
                        )
                        unit_name_to_id[yaml_process_unit.get_instance_reference()] = unit.get_id()
                        shaft_equipment_id = self._shaft_by_compressor_equipment_id[compressor_equipment_id].get_id()
                        if shaft_equipment_id not in shafts:
                            shafts[shaft_equipment_id] = TimeSeriesShaftConfigurationHandler(
                                shaft_equipment_id=shaft_equipment_id
                            )
                        shaft = shafts[shaft_equipment_id]
                        shaft.connect(unit.get_id())

                        if shaft not in problem_configuration_handlers:
                            problem_configuration_handlers.append(shaft)

                    case YamlPressureDropperDefinition():
                        unit = TimeSeriesPressureDropperProcessUnit()
                        problem_time_series_configurations[unit.get_id()] = TimeSeriesPressureDropperConfiguration(
                            pressure_drop_in_bara=self._map_pressure(yaml_process_unit.pressure_drop)
                        )

                    case YamlTemperatureSetterDefinition():
                        unit = TimeSeriesTemperatureSetterProcessUnit()
                        problem_time_series_configurations[unit.get_id()] = TimeSeriesTemperatureSetterConfiguration(
                            temperature_in_celsius=self._map_temperature(yaml_process_unit.temperature)
                        )

                    case YamlLiquidRemoverDefinition():
                        unit = TimeSeriesLiquidRemoverProcessUnit()

                    case YamlMixerDefinition():
                        yaml_stream = self._resolve_stream_reference(yaml_process_unit.sidestream)
                        unit = TimeSeriesMixerProcessUnit()
                        problem_time_series_configurations[unit.get_id()] = TimeSeriesMixerConfiguration(
                            sidestream=self._map_stream(yaml_stream)
                        )

                    case YamlSplitterDefinition():
                        unit = TimeSeriesSplitterProcessUnit()
                        problem_time_series_configurations[unit.get_id()] = TimeSeriesSplitterConfiguration(
                            offtake_rate=self._map_rate(yaml_process_unit.offtake_rate),
                        )

                    case _:
                        assert_never(yaml_process_unit)

                process_unit_map[unit.get_id()] = unit

            # Since we, in addition to intra-section connection, have inter-section connections, we keep them separate
            # from section, and keep track of them at pipeline level
            process_pipeline_sections: list[ProcessPipelineSection] = []
            process_problem_sections: list[ProcessProblemSection] = []
            pipeline_constraints = yaml_process_simulation.constraints.get(item.name)

            if not pipeline_constraints:
                raise EcalcValidationException(f"Missing constraint for process system '{item.name}'")

            mapped_sections = section_builder.partition_and_validate(
                process_unit_map=process_unit_map,
                unit_name_to_id=unit_name_to_id,
                pipeline_constraints=pipeline_constraints,
            )
            assembled_sections = section_builder.assemble_sections(mapped_sections=mapped_sections)

            # Set up pipeline and pipeline sections
            for nr, assembled_section in enumerate(assembled_sections):
                process_section_process_units = list(assembled_section.process_units)
                if nr == 0:  # first section
                    process_section_process_units.insert(0, TimeSeriesInletProcessUnit())
                if nr == len(mapped_sections) - 1:  # last section
                    process_section_process_units.append(TimeSeriesOutletProcessUnit())

                process_pipeline_sections.append(ProcessPipelineSection(process_units=process_section_process_units))

            # TODO: Simply events for now ...
            pipeline_events = self._validate_and_map_pipeline_events(
                yaml_pipeline=item,
                unit_name_to_id=unit_name_to_id,
                process_unit_map=process_unit_map,
            )
            # TODO: We should move this class to this module/layer
            # in particular because it creates necessary connections, which means that they will get new IDs
            process_pipeline = ProcessPipeline(
                name=item.name,
                process_pipeline_sections=process_pipeline_sections,
                events=pipeline_events,
                process_periods=self._expression_evaluator.get_periods().periods,
            )

            # Set up problem and problem sections
            for nr, (pipeline_section, mapped_section, assembled_section) in enumerate(
                zip(process_pipeline_sections, mapped_sections, assembled_sections, strict=True)
            ):
                # For the first n-1 sections, we put it at the last unit, for the nth section we put it before the outlet unit
                constraint_position = -2
                if nr == len(process_pipeline_sections):
                    constraint_position = -1
                target_process_unit_id = pipeline_section.get_process_units()[
                    constraint_position
                ].get_id()  # The last unit is the outlet, so we take the one before that
                # TODO: The mapped_section.target_process_unit_id is incorrect, as that is before we apply ASV and Pressure Control ...
                try:
                    constraint = Constraint(
                        outlet_pressure=TimeSeriesExpression(
                            expression=mapped_section.constraint.outlet_pressure,
                            expression_evaluator=self._expression_evaluator,
                        ),
                        target_process_unit_id=target_process_unit_id,
                        target_process_connection_id=next(
                            process_unit_connection.get_id()
                            for process_unit_connection in process_pipeline.get_process_unit_connections()
                            if process_unit_connection.get_from_process_unit_id() == target_process_unit_id
                        ),
                    )
                except StopIteration:
                    raise ProgrammingError(
                        f"Not able to set constraint on OUTLET of process unit '{mapped_section.target_process_unit_id}' because the Connection ID was not found."
                    ) from None

                process_problem_sections.append(
                    ProcessProblemSection(
                        process_pipeline_section_id=pipeline_section.get_id(),
                        # configuration_handlers=assembled_section.configuration_handlers,  # TODO: We currently store config handlers at problem level. They may be inter or intra section ...
                        constraint=constraint,
                        pressure_control=PressureControlConfig(type=mapped_section.constraint.pressure_control),
                        anti_surge=AntiSurgeConfig(mapped_section.constraint.anti_surge),
                    )
                )
                # Choke and recirculation configuration handlers are currently intra-section config handlers
                problem_configuration_handlers.extend(assembled_section.configuration_handlers)

            predefined_configurations[process_pipeline.get_id()] = problem_time_series_configurations

            process_pipeline_reference_to_id_map[item.name] = process_pipeline.get_id()
            process_pipelines.append(process_pipeline)
            process_problems.append(
                ProcessProblem(
                    process_problem_sections=process_problem_sections,
                    configuration_handlers=problem_configuration_handlers,
                    process_pipeline_id=process_pipeline.get_id(),
                )
            )

        for process_pipeline_reference in yaml_process_simulation.constraints:
            process_pipeline_id = process_pipeline_reference_to_id_map.get(process_pipeline_reference)
            if process_pipeline_id is None:
                raise EcalcValidationException(
                    f"Constraint specified for unknown process system '{process_pipeline_reference}'"
                )

        yaml_stream_distribution = yaml_process_simulation.stream_distribution

        match yaml_stream_distribution:
            case YamlCommonStreamDistribution():
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
                            raise EcalcValidationException(
                                f"Process system reference '{overflow.to_reference}' defined in overflow does not exist."
                            ) from e

                        try:
                            from_id = process_pipeline_reference_to_id_map[overflow.from_reference]
                        except KeyError as e:
                            raise EcalcValidationException(
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
                inlet_stream = self._map_stream(yaml_stream)
                stream_distribution = CommonStreamDistributionConfig(
                    inlet_stream=inlet_stream,
                    settings=settings,
                )
            case YamlIndividualStreamDistribution():
                inlet_streams = []
                for inlet_stream in yaml_stream_distribution.inlet_streams:
                    yaml_stream = self._resolve_stream_reference(inlet_stream)

                    inlet_streams.append(self._map_stream(yaml_stream))
                stream_distribution = IndividualStreamDistributionConfig(
                    inlet_streams=inlet_streams,
                )
            case _:
                assert_never(yaml_stream_distribution)

        return (
            process_pipelines,
            ProcessSimulation(
                name=yaml_process_simulation.name,
                process_problems=process_problems,
                stream_distribution=stream_distribution,
                process_periods=self._expression_evaluator.get_periods().periods,
                process_configurations=predefined_configurations,
            ),
        )
