from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, assert_never

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.common.errors.exceptions import HeaderNotFoundException, InvalidResourceException
from libecalc.common.utils.rates import RateType
from libecalc.common.variables import ExpressionEvaluator
from libecalc.domain.regularity import Regularity
from libecalc.domain.resource import Resource, Resources
from libecalc.ecalc_model.equipment.equipment_id import EquipmentId
from libecalc.ecalc_model.process.process_units import (
    TimeSeriesChokeProcessUnit,
    TimeSeriesDirectMixerProcessUnit,
    TimeSeriesDirectSplitterProcessUnit,
    TimeSeriesInletProcessUnit,
    TimeSeriesOutletProcessUnit,
    TimeSeriesPressureDropperProcessUnit,
    TimeSeriesProcessUnit,
    TimeSeriesPumpProcessUnit,
)
from libecalc.ecalc_model.process.pump.liquid_recirculation_loop import LiquidRecirculationLoop
from libecalc.ecalc_model.process.pump.pump_pipeline import PumpPipeline
from libecalc.ecalc_model.process.pump.pump_problems import validate_pump_problems
from libecalc.ecalc_model.process.pump.pump_simulation import (
    PumpCommonStreamDistributionConfig,
    PumpCommonStreamSettings,
    PumpConstraint,
    PumpIndividualStreamDistributionConfig,
    PumpProblem,
    PumpSimulation,
    PumpStreamDistributionConfig,
)
from libecalc.ecalc_model.process.pump.time_series_liquid_stream import TimeSeriesLiquidStream
from libecalc.ecalc_model.time_series_configuration import TimeSeriesPressureDropperConfiguration
from libecalc.expression.expression import ExpressionType
from libecalc.presentation.yaml.domain.expression_time_series_flow_rate import ExpressionTimeSeriesFlowRate
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression
from libecalc.presentation.yaml.mappers.charts.user_defined_chart_mapper import (
    user_defined_chart_from_resource,
    user_defined_chart_from_yaml_curves,
)
from libecalc.presentation.yaml.mappers.model import InvalidChartResourceException
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords
from libecalc.presentation.yaml.yaml_types.process.yaml_process_references import InstanceReference
from libecalc.presentation.yaml.yaml_types.process.yaml_process_units import YamlPressureDropperDefinition
from libecalc.presentation.yaml.yaml_types.pump.yaml_liquid_stream import YamlLiquidInletStream
from libecalc.presentation.yaml.yaml_types.pump.yaml_pump_model import YamlPumpChart, YamlPumpModel
from libecalc.presentation.yaml.yaml_types.pump.yaml_pump_pipeline import YamlPumpPipeline, YamlPumpProcessUnit
from libecalc.presentation.yaml.yaml_types.pump.yaml_pump_simulation import (
    YamlPumpCommonStreamDistribution,
    YamlPumpConstraint,
    YamlPumpIndividualStreamDistribution,
    YamlPumpPressureControl,
    YamlPumpSimulation,
)
from libecalc.presentation.yaml.yaml_types.yaml_data_or_file import YamlFile
from libecalc.presentation.yaml.yaml_types.yaml_pump import PumpReference
from libecalc.process.chart.chart import ChartData
from libecalc.process.process_pipeline.process_pipeline import ProcessPipelineId
from libecalc.process.process_pipeline.process_unit import ProcessUnitId

type PumpProcessConfigurations = dict[ProcessUnitId, TimeSeriesPressureDropperConfiguration]


@dataclass(frozen=True)
class _PumpControl:
    yaml_constraint: YamlPumpConstraint
    target_process_unit: TimeSeriesProcessUnit
    choke: TimeSeriesChokeProcessUnit | None


class PumpSimulationMapper:
    def __init__(
        self,
        expression_evaluator: ExpressionEvaluator,
        references: Mapping[InstanceReference, Any],
        resources: Resources,
        pump_equipment_ids: Mapping[PumpReference, EquipmentId],
    ):
        self._expression_evaluator = expression_evaluator
        self._references = references
        self._resources = resources
        self._pump_equipment_ids = pump_equipment_ids

    def map_pump_simulation(
        self, yaml_pump_simulation: YamlPumpSimulation
    ) -> tuple[list[PumpPipeline], PumpSimulation]:
        self._validate_constraint_targets(yaml_pump_simulation)

        pump_pipelines: list[PumpPipeline] = []
        pump_problems: dict[ProcessPipelineId, list[PumpProblem]] = {}
        process_configurations: dict[ProcessPipelineId, PumpProcessConfigurations] = {}
        for target in yaml_pump_simulation.targets:
            yaml_pump_pipeline = self._resolve_pump_pipeline(target)
            constraint_by_pump = self._match_constraints(yaml_pump_simulation, target, yaml_pump_pipeline)
            pump_pipeline, controls, configurations = self._map_pump_pipeline(yaml_pump_pipeline, constraint_by_pump)
            problems = self._map_pump_problems(pump_pipeline, controls)
            validate_pump_problems(pump_pipeline, problems)
            pump_pipelines.append(pump_pipeline)
            pump_problems[pump_pipeline.get_id()] = problems
            if configurations:
                process_configurations[pump_pipeline.get_id()] = configurations

        return pump_pipelines, PumpSimulation(
            name=yaml_pump_simulation.name,
            stream_distribution=self._map_stream_distribution(yaml_pump_simulation),
            pump_problems=pump_problems,
            process_periods=self._expression_evaluator.get_periods().periods,
            process_configurations=process_configurations,
        )

    @staticmethod
    def _validate_constraint_targets(yaml_pump_simulation: YamlPumpSimulation) -> None:
        for constrained in yaml_pump_simulation.constraints:
            if constrained not in yaml_pump_simulation.targets:
                raise EcalcValidationException(
                    f"Pump simulation '{yaml_pump_simulation.name}' has CONSTRAINTS for '{constrained}', which is not "
                    f"one of its TARGETS: {', '.join(yaml_pump_simulation.targets)}."
                )

    def _resolve_pump_pipeline(self, reference: InstanceReference) -> YamlPumpPipeline:
        pump_pipeline = self._references.get(reference)
        if not isinstance(pump_pipeline, YamlPumpPipeline):
            raise EcalcValidationException(f"Pump simulation target '{reference}' is not a pump pipeline.")
        return pump_pipeline

    def _map_pump_pipeline(
        self,
        yaml_pump_pipeline: YamlPumpPipeline,
        constraint_by_pump: Mapping[PumpReference, YamlPumpConstraint],
    ) -> tuple[PumpPipeline, list[_PumpControl], PumpProcessConfigurations]:
        process_units: list[TimeSeriesProcessUnit] = [TimeSeriesInletProcessUnit()]
        recirculation_loops: list[LiquidRecirculationLoop] = []
        controls: list[_PumpControl] = []
        configurations: PumpProcessConfigurations = {}

        for yaml_process_unit in yaml_pump_pipeline.process_units:
            match yaml_process_unit:
                case YamlPumpProcessUnit():
                    yaml_constraint = constraint_by_pump[yaml_process_unit.pump]
                    mixer = TimeSeriesDirectMixerProcessUnit()
                    splitter = TimeSeriesDirectSplitterProcessUnit()
                    process_units.extend([mixer, self._map_pump(yaml_pump_pipeline, yaml_process_unit), splitter])
                    match yaml_constraint.pressure_control:
                        case YamlPumpPressureControl.DOWNSTREAM_CHOKE:
                            choke = TimeSeriesChokeProcessUnit()
                            process_units.append(choke)
                            controls.append(_PumpControl(yaml_constraint, target_process_unit=choke, choke=choke))
                        case YamlPumpPressureControl.NONE:
                            controls.append(_PumpControl(yaml_constraint, target_process_unit=splitter, choke=None))
                        case _:
                            assert_never(yaml_constraint.pressure_control)
                    recirculation_loops.append(
                        LiquidRecirculationLoop(
                            mixer_process_unit_id=mixer.get_id(),
                            splitter_process_unit_id=splitter.get_id(),
                        )
                    )
                case YamlPressureDropperDefinition():
                    pressure_dropper = TimeSeriesPressureDropperProcessUnit()
                    process_units.append(pressure_dropper)
                    configurations[pressure_dropper.get_id()] = TimeSeriesPressureDropperConfiguration(
                        pressure_drop_in_bara=self._map_expression(yaml_process_unit.pressure_drop)
                    )
                case _:
                    assert_never(yaml_process_unit)

        process_units.append(TimeSeriesOutletProcessUnit())
        pump_pipeline = PumpPipeline(
            name=yaml_pump_pipeline.name,
            process_units=process_units,
            process_periods=self._expression_evaluator.get_periods().periods,
            recirculation_loops=recirculation_loops,
        )
        return pump_pipeline, controls, configurations

    def _map_pump(
        self, yaml_pump_pipeline: YamlPumpPipeline, yaml_pump_unit: YamlPumpProcessUnit
    ) -> TimeSeriesPumpProcessUnit:
        pump_equipment_id = self._pump_equipment_ids.get(yaml_pump_unit.pump)
        if pump_equipment_id is None:
            raise EcalcValidationException(
                f"Pump '{yaml_pump_unit.pump}' in pump pipeline '{yaml_pump_pipeline.name}' is not defined in PUMPS."
            )
        if not isinstance(yaml_pump_unit.model, YamlPumpModel):
            raise EcalcValidationException(
                f"MODEL '{yaml_pump_unit.model}' of pump '{yaml_pump_unit.pump}' is not a pump model."
            )
        return TimeSeriesPumpProcessUnit(
            pump_chart=self._map_pump_chart(yaml_pump_unit.model.chart),
            pump_equipment_id=pump_equipment_id,
            minimum_flow_rate_m3_per_hour=yaml_pump_unit.model.minimum_flow_rate,
        )

    def _map_pump_chart(self, yaml_pump_chart: YamlPumpChart) -> ChartData:
        if not isinstance(yaml_pump_chart.curves, YamlFile):
            return user_defined_chart_from_yaml_curves(yaml_pump_chart.curves, units=yaml_pump_chart.units)

        resource_name = yaml_pump_chart.curves.file
        resource = self._resources.get(resource_name)
        if resource is None:
            raise EcalcValidationException(f"Resource '{resource_name}' not found for pump chart.")
        try:
            return user_defined_chart_from_resource(
                resource,
                units=yaml_pump_chart.units,
                is_single_speed=self._is_single_speed(resource),
            )
        except InvalidResourceException as e:
            raise InvalidChartResourceException(
                message=str(e), file_mark=e.file_mark, resource_name=resource_name
            ) from e

    @staticmethod
    def _is_single_speed(resource: Resource) -> bool:
        try:
            speeds = resource.get_float_column(EcalcYamlKeywords.consumer_chart_speed)
        except HeaderNotFoundException:
            return True
        return len(set(speeds)) <= 1

    @staticmethod
    def _match_constraints(
        yaml_pump_simulation: YamlPumpSimulation, target: InstanceReference, yaml_pump_pipeline: YamlPumpPipeline
    ) -> dict[PumpReference, YamlPumpConstraint]:
        subject = f"Pump simulation '{yaml_pump_simulation.name}' target '{target}'"
        pumps = [unit.pump for unit in yaml_pump_pipeline.process_units if isinstance(unit, YamlPumpProcessUnit)]
        constraint_by_pump: dict[PumpReference, YamlPumpConstraint] = {}
        for yaml_constraint in yaml_pump_simulation.constraints.get(target, []):
            if yaml_constraint.process_unit is None and not pumps:
                raise EcalcValidationException(f"{subject} has a constraint, but the pipeline has no pumps.")
            pump = yaml_constraint.process_unit if yaml_constraint.process_unit is not None else pumps[-1]
            if pump not in pumps:
                raise EcalcValidationException(
                    f"{subject} has a constraint for PROCESS_UNIT '{pump}', which is not a pump in the pipeline. "
                    f"Pumps in this pipeline: {', '.join(pumps)}."
                )
            if pump in constraint_by_pump:
                raise EcalcValidationException(
                    f"{subject} has more than one constraint for pump '{pump}'. A constraint without PROCESS_UNIT "
                    "applies to the last pump."
                )
            constraint_by_pump[pump] = yaml_constraint

        missing = [pump for pump in pumps if pump not in constraint_by_pump]
        if missing:
            raise EcalcValidationException(
                f"{subject} must have one constraint per pump. Missing a constraint for: {', '.join(missing)}."
            )
        return constraint_by_pump

    def _map_pump_problems(self, pump_pipeline: PumpPipeline, controls: Sequence[_PumpControl]) -> list[PumpProblem]:
        connection_by_from_unit = {
            connection.get_from_process_unit_id(): connection
            for connection in pump_pipeline.get_process_unit_connections()
        }
        return [
            PumpProblem(
                constraint=PumpConstraint(
                    outlet_pressure=self._map_expression(control.yaml_constraint.outlet_pressure),
                    target_process_unit_id=control.target_process_unit.get_id(),
                    target_process_connection_id=connection_by_from_unit[control.target_process_unit.get_id()].get_id(),
                ),
                pump_pipeline_id=pump_pipeline.get_id(),
                choke_pressure_control_id=control.choke.get_id() if control.choke is not None else None,
            )
            for control in controls
        ]

    def _map_stream_distribution(self, yaml_pump_simulation: YamlPumpSimulation) -> PumpStreamDistributionConfig:
        yaml_stream_distribution = yaml_pump_simulation.stream_distribution
        match yaml_stream_distribution:
            case YamlPumpCommonStreamDistribution():
                return PumpCommonStreamDistributionConfig(
                    inlet_stream=self._map_liquid_stream(yaml_stream_distribution.inlet_stream),
                    settings=[
                        PumpCommonStreamSettings(
                            rate_fractions=[
                                self._map_expression(rate_fraction) for rate_fraction in setting.rate_fractions
                            ],
                            overflow=[],
                        )
                        for setting in yaml_stream_distribution.settings
                    ],
                )
            case YamlPumpIndividualStreamDistribution():
                return PumpIndividualStreamDistributionConfig(
                    inlet_streams=[
                        self._map_liquid_stream(inlet_stream) for inlet_stream in yaml_stream_distribution.inlet_streams
                    ]
                )
            case _:
                assert_never(yaml_stream_distribution)

    def _map_liquid_stream(self, yaml_stream: YamlLiquidInletStream) -> TimeSeriesLiquidStream:
        return TimeSeriesLiquidStream(
            volumetric_rate_m3_per_day=ExpressionTimeSeriesFlowRate(
                time_series_expression=self._map_expression(yaml_stream.rate.value),
                regularity=Regularity(
                    expression_evaluator=self._expression_evaluator,
                    target_period=self._expression_evaluator.get_period(),
                ),
                consumption_rate_type=RateType(yaml_stream.rate.type),
            ),
            pressure_bara=self._map_expression(yaml_stream.pressure),
            density_kg_per_m3=self._map_expression(yaml_stream.density),
        )

    def _map_expression(self, expression: ExpressionType) -> TimeSeriesExpression:
        return TimeSeriesExpression(expression=expression, expression_evaluator=self._expression_evaluator)
