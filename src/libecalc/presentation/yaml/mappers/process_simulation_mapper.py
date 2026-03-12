from abc import ABC
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Literal, assert_never

from libecalc.common.errors.exceptions import InvalidResourceException
from libecalc.common.time_utils import Period
from libecalc.common.units import Unit
from libecalc.common.variables import ExpressionEvaluator
from libecalc.domain.component_validation_error import DomainValidationException
from libecalc.domain.process.entities.process_units.choke import Choke
from libecalc.domain.process.entities.process_units.compressor import Compressor
from libecalc.domain.process.entities.process_units.recirculation_loop import RecirculationLoop
from libecalc.domain.process.entities.shaft import Shaft
from libecalc.domain.process.entities.shaft.shaft import VariableSpeedShaft
from libecalc.domain.process.process_solver.anti_surge.anti_surge_strategy import AntiSurgeStrategy
from libecalc.domain.process.process_solver.anti_surge.common_asv import CommonASVAntiSurgeStrategy
from libecalc.domain.process.process_solver.anti_surge.individual_asv import IndividualASVAntiSurgeStrategy
from libecalc.domain.process.process_solver.pressure_control.common_asv import CommonASVPressureControlStrategy
from libecalc.domain.process.process_solver.pressure_control.downstream_choke import (
    DownstreamChokePressureControlStrategy,
)
from libecalc.domain.process.process_solver.pressure_control.individual_asv import (
    IndividualASVPressureControlStrategy,
    IndividualASVRateControlStrategy,
)
from libecalc.domain.process.process_solver.pressure_control.pressure_control_strategy import PressureControlStrategy
from libecalc.domain.process.process_solver.pressure_control.upstream_choke import UpstreamChokePressureControlStrategy
from libecalc.domain.process.process_solver.process_runner import ProcessRunner
from libecalc.domain.process.process_solver.process_system_runner import ProcessSystemRunner
from libecalc.domain.process.process_solver.search_strategies import ScipyRootFindingStrategy
from libecalc.domain.process.process_system.process_system import (
    ProcessSystem,
    ProcessSystemId,
    create_process_system_id,
)
from libecalc.domain.process.process_system.process_unit import ProcessUnitId, create_process_unit_id
from libecalc.domain.process.process_system.serial_process_system import SerialProcessSystem
from libecalc.domain.process.stream_distribution.common_stream_distribution import (
    CommonStreamDistribution,
    HasCapacity,
    Overflow,
)
from libecalc.domain.process.stream_distribution.individual_stream_distribution import IndividualStreamDistribution
from libecalc.domain.process.stream_distribution.priorities_stream_distribution import (
    HasValidity,
    PrioritiesStreamDistribution,
)
from libecalc.domain.process.stream_distribution.stream_distribution import StreamDistribution
from libecalc.domain.process.value_objects.chart.chart import ChartData
from libecalc.domain.process.value_objects.fluid_stream import FluidModel, FluidService, FluidStream
from libecalc.domain.regularity import Regularity
from libecalc.domain.resource import Resources
from libecalc.domain.time_series_flow_rate import TimeSeriesFlowRate
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
    ProcessSystemReference,
    YamlCommonStreamDistribution,
    YamlCompressor,
    YamlCompressorModelChart,
    YamlCompressorStageProcessSystem,
    YamlIndividualStreamDistribution,
    YamlProcessSimulation,
    YamlSerialProcessSystem,
)
from libecalc.presentation.yaml.yaml_types.models import YamlFluidModel
from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_stages import YamlControlMarginUnits
from libecalc.presentation.yaml.yaml_types.models.yaml_fluid import YamlCompositionFluidModel, YamlPredefinedFluidModel
from libecalc.presentation.yaml.yaml_types.streams.yaml_inlet_stream import YamlInletStream, YamlInletStreamRate
from libecalc.presentation.yaml.yaml_types.yaml_data_or_file import YamlFile


@dataclass
class PressureControlConfig:
    type: Literal["UPSTREAM_CHOKE", "DOWNSTREAM_CHOKE", "COMMON_ASV", "INDIVIDUAL_ASV_RATE", "INDIVIDUAL_ASV_PRESSURE"]
    choke_id: ProcessUnitId | None
    recirculation_loop_ids: Sequence[ProcessSystemId]


class StreamDistributionItem(HasCapacity, HasValidity, ABC): ...


class CompressorTrainBuilder:
    def __init__(self, compressors: Sequence[Compressor], fluid_service: FluidService):
        self._fluid_service = fluid_service
        self._process_system = SerialProcessSystem(
            process_system_id=create_process_system_id(), propagators=compressors
        )
        self._compressor_ids = [compressor.get_id() for compressor in compressors]

    def with_individual_asv(self) -> list[ProcessSystemId]:
        recirculation_loop_ids = [create_process_system_id() for _ in range(len(self._compressor_ids))]
        process_units = [
            RecirculationLoop(
                process_system_id=recirculation_loop_id, inner_process=compressor, fluid_service=self._fluid_service
            )
            for recirculation_loop_id, compressor in zip(
                recirculation_loop_ids, self._process_system.get_process_units(), strict=True
            )
        ]
        self._process_system = SerialProcessSystem(
            process_system_id=create_process_system_id(), propagators=process_units
        )
        return recirculation_loop_ids

    def with_common_asv(self) -> ProcessSystemId:
        recirculation_loop_id = create_process_system_id()
        recirculation_loop = RecirculationLoop(
            process_system_id=recirculation_loop_id,
            inner_process=self._process_system,
            fluid_service=self._fluid_service,
        )
        self._process_system = SerialProcessSystem(
            process_system_id=create_process_system_id(), propagators=[recirculation_loop]
        )
        return recirculation_loop_id

    def with_upstream_choke(self) -> ProcessUnitId:
        choke_id = create_process_unit_id()
        self._process_system = SerialProcessSystem(
            process_system_id=create_process_system_id(),
            propagators=[
                Choke(process_unit_id=choke_id, fluid_service=self._fluid_service),
                *self._process_system.get_process_units(),
            ],
        )
        return choke_id

    def with_downstream_choke(self) -> ProcessUnitId:
        choke_id = create_process_unit_id()
        self._process_system = SerialProcessSystem(
            process_system_id=create_process_system_id(),
            propagators=[
                *self._process_system.get_process_units(),
                Choke(process_unit_id=choke_id, fluid_service=self._fluid_service),
            ],
        )
        return choke_id

    def build(self) -> ProcessSystem:
        return self._process_system


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

    def _get_compressor(self, yaml_compressor_stage: YamlCompressorStageProcessSystem, shaft: Shaft) -> Compressor:
        # TODO: deal with stage
        yaml_compressor = self._resolve_compressor_reference(yaml_compressor_stage.compressor)

        chart: ChartData = self._get_compressor_chart(yaml_compressor_model_chart=yaml_compressor.compressor_model)

        return Compressor(
            process_unit_id=create_process_unit_id(),
            compressor_chart=chart,
            fluid_service=self._fluid_service,
            shaft=shaft,
        )

    def _get_compressors(self, target: YamlSerialProcessSystem, shaft: Shaft) -> list[Compressor]:
        return [
            self._get_compressor(
                yaml_compressor_stage=self._resolve_compressor_stage_reference(yaml_compressor.target), shaft=shaft
            )
            for yaml_compressor in target.items
        ]

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

    def _map_rate(self, yaml_rate: YamlInletStreamRate) -> TimeSeriesFlowRate:
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
        if isinstance(yaml_fluid_model, YamlPredefinedFluidModel):
            return predefined_fluid_model_mapper(yaml_fluid_model)
        elif isinstance(yaml_fluid_model, YamlCompositionFluidModel):
            return composition_fluid_model_mapper(yaml_fluid_model)
        else:
            assert_never(yaml_fluid_model)

    def _map_single_stream(
        self, rate: list[float], pressure: list[float], temperature: list[float], fluid_model: FluidModel, index: int
    ):
        return self._fluid_service.create_stream_from_standard_rate(
            fluid_model=fluid_model,
            pressure_bara=pressure[index],
            temperature_kelvin=temperature[index],
            standard_rate_m3_per_day=rate[index],
        )

    def _map_stream(self, yaml_stream: YamlInletStream) -> Iterable[tuple[Period, FluidStream]]:
        rate = self._map_rate(yaml_stream.rate).get_stream_day_values()
        pressure = self._map_pressure(yaml_stream.pressure).get_masked_values()
        temperature = self._map_temperature(yaml_stream.temperature).get_masked_values()
        fluid_model = self._map_fluid_model(
            yaml_fluid_model=self._resolve_fluid_model_reference(yaml_stream.fluid_model)
        )

        for index, period in enumerate(self._expression_evaluator.get_periods().periods):
            yield (
                period,
                self._map_single_stream(
                    rate=rate, pressure=pressure, temperature=temperature, fluid_model=fluid_model, index=index
                ),
            )

    def _map_common_stream_distribution(
        self,
        yaml_stream_distribution: YamlCommonStreamDistribution,
        items: dict[ProcessSystemReference, StreamDistributionItem],
    ) -> Iterable[tuple[Period, StreamDistribution]]:
        inlet_stream = self._resolve_stream_reference(yaml_stream_distribution.inlet_stream)

        for index, (period, inlet_stream) in enumerate(self._map_stream(inlet_stream)):
            settings = []
            for setting in yaml_stream_distribution.settings:
                rate_fractions = [
                    TimeSeriesExpression(
                        expression_evaluator=self._expression_evaluator, expression=rate_fraction
                    ).get_masked_values()[index]
                    for rate_fraction in setting.rate_fractions
                ]
                setting_distribution = CommonStreamDistribution(
                    fluid_service=self._fluid_service,
                    inlet_stream=inlet_stream,
                    overflows=[
                        Overflow(
                            from_id=overflow.from_reference,
                            to_id=overflow.to_reference,
                        )
                        for overflow in setting.overflow
                    ]
                    if setting.overflow is not None
                    else [],
                    rate_fractions=rate_fractions,
                    items=items,
                )
                settings.append(setting_distribution)
            yield (
                period,
                PrioritiesStreamDistribution(
                    stream_distributions=settings,
                    items=list(items.values()),
                ),
            )

    def _map_individual_stream_distribution(
        self, yaml_stream_distribution: YamlIndividualStreamDistribution
    ) -> Iterable[tuple[Period, StreamDistribution]]:
        for period in self._expression_evaluator.get_periods().periods:
            streams: list[FluidStream] = []
            for index, yaml_stream in enumerate(yaml_stream_distribution.inlet_streams):
                yaml_stream = self._resolve_stream_reference(yaml_stream)
                rate = self._map_rate(yaml_stream.rate).get_stream_day_values()
                pressure = self._map_pressure(yaml_stream.pressure).get_masked_values()
                temperature = self._map_temperature(yaml_stream.temperature).get_masked_values()
                fluid_model = self._map_fluid_model(
                    yaml_fluid_model=self._resolve_fluid_model_reference(yaml_stream.fluid_model)
                )
                streams.append(
                    self._map_single_stream(
                        rate=rate,
                        pressure=pressure,
                        temperature=temperature,
                        fluid_model=fluid_model,
                        index=index,
                    )
                )
            yield (
                period,
                IndividualStreamDistribution(
                    streams=streams,
                ),
            )

    def map_process_system(
        self,
        compressors: Sequence[Compressor],
        pressure_control: Literal[
            "COMMON_ASV", "INDIVIDUAL_ASV_RATE", "INDIVIDUAL_ASV_PRESSURE", "DOWNSTREAM_CHOKE", "UPSTREAM_CHOKE"
        ],
    ) -> tuple[ProcessSystem, PressureControlConfig]:
        builder = CompressorTrainBuilder(compressors=compressors, fluid_service=self._fluid_service)

        if pressure_control == "COMMON_ASV":
            recirculation_loop_ids = [builder.with_common_asv()]
        else:
            recirculation_loop_ids = builder.with_individual_asv()

        choke_id = None
        if pressure_control == "DOWNSTREAM_CHOKE":
            choke_id = builder.with_downstream_choke()
        elif pressure_control == "UPSTREAM_CHOKE":
            choke_id = builder.with_upstream_choke()

        return builder.build(), PressureControlConfig(
            type=pressure_control,
            recirculation_loop_ids=recirculation_loop_ids,
            choke_id=choke_id,
        )

    def map_anti_surge_strategy(
        self,
        simulator: ProcessRunner,
        recirculation_loop_ids: Sequence[ProcessSystemId],
        compressors: Sequence[Compressor],
        recirculation_type: Literal["INDIVIDUAL_ASV", "COMMON_ASV"],
    ) -> AntiSurgeStrategy:
        if recirculation_type == "COMMON_ASV":
            return CommonASVAntiSurgeStrategy(
                simulator=simulator,
                root_finding_strategy=ScipyRootFindingStrategy(),
                first_compressor=compressors[0],
                recirculation_loop_id=recirculation_loop_ids[0],
            )
        elif recirculation_type == "INDIVIDUAL_ASV":
            return IndividualASVAntiSurgeStrategy(
                simulator=simulator,
                recirculation_loop_ids=recirculation_loop_ids,
                compressors=compressors,
            )

        assert_never(recirculation_type)

    def map_pressure_control_strategy(
        self,
        simulator: ProcessRunner,
        recirculation_loop_ids: Sequence[ProcessSystemId],
        choke_id: ProcessUnitId | None,
        compressors: Sequence[Compressor],
        pressure_control_type: Literal[
            "COMMON_ASV", "INDIVIDUAL_ASV_RATE", "INDIVIDUAL_ASV_PRESSURE", "DOWNSTREAM_CHOKE", "UPSTREAM_CHOKE"
        ],
    ) -> PressureControlStrategy:
        if pressure_control_type == "COMMON_ASV":
            assert len(recirculation_loop_ids) == 1
            return CommonASVPressureControlStrategy(
                simulator=simulator,
                first_compressor=compressors[0],
                root_finding_strategy=ScipyRootFindingStrategy(),
                recirculation_loop_id=recirculation_loop_ids[0],
            )
        elif pressure_control_type == "INDIVIDUAL_ASV_RATE":
            return IndividualASVRateControlStrategy(
                simulator=simulator,
                recirculation_loop_ids=recirculation_loop_ids,
                compressors=compressors,
            )
        elif pressure_control_type == "INDIVIDUAL_ASV_PRESSURE":
            return IndividualASVPressureControlStrategy(
                simulator=simulator,
                recirculation_loop_ids=recirculation_loop_ids,
                compressors=compressors,
                root_finding_strategy=ScipyRootFindingStrategy(),
            )
        elif pressure_control_type == "DOWNSTREAM_CHOKE":
            assert choke_id is not None
            return DownstreamChokePressureControlStrategy(
                simulator=simulator,
                choke_id=choke_id,
            )
        elif pressure_control_type == "UPSTREAM_CHOKE":
            assert choke_id is not None
            return UpstreamChokePressureControlStrategy(
                simulator=simulator,
                choke_id=choke_id,
                root_finding_strategy=ScipyRootFindingStrategy(),
            )

        assert_never(pressure_control_type)

    def map_process_simulation(self, yaml_process_simulation: YamlProcessSimulation):
        targets = []
        for yaml_compressor_train_item in yaml_process_simulation.targets:
            shaft = VariableSpeedShaft()
            compressors = self._get_compressors(
                self._resolve_train_reference(yaml_compressor_train_item.target), shaft=shaft
            )
            process_system, pressure_control_config = self.map_process_system(
                compressors=compressors,
                pressure_control=yaml_process_simulation.pressure_control,
            )
            targets.append(process_system)
            runner = ProcessSystemRunner(units=process_system.get_process_units(), shaft=shaft)

            anti_surge_strategy = self.map_anti_surge_strategy(
                simulator=runner,
                recirculation_loop_ids=pressure_control_config.recirculation_loop_ids,
                compressors=compressors,
                recirculation_type="COMMON_ASV" if pressure_control_config.type == "COMMON_ASV" else "INDIVIDUAL_ASV",
            )

            pressure_control_strategy = self.map_pressure_control_strategy(
                simulator=runner,
                compressors=compressors,
                recirculation_loop_ids=pressure_control_config.recirculation_loop_ids,
                choke_id=pressure_control_config.choke_id,
                pressure_control_type=pressure_control_config.type,
            )

        yaml_stream_distribution = yaml_process_simulation.stream_distribution
        if yaml_stream_distribution.method == "COMMON_STREAM":
            raise NotImplementedError("Missing HasValid and HasCapacity implementations")
            # stream_distributions = self._map_common_stream_distribution(
            #    yaml_stream_distribution=yaml_stream_distribution, items=[]
            # )
        elif yaml_stream_distribution.method == "INDIVIDUAL_STREAMS":
            stream_distributions = self._map_individual_stream_distribution(
                yaml_stream_distribution=yaml_stream_distribution
            )
        else:
            raise DomainValidationException(
                f"Unsupported stream distribution type. (Got: {yaml_process_simulation.stream_distribution.method}"
            )
