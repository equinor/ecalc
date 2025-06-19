import uuid
from dataclasses import dataclass
from typing import Protocol, TypeVar, assert_never
from uuid import UUID

from libecalc.common.component_type import ComponentType
from libecalc.common.serializable_chart import SingleSpeedChartDTO, VariableSpeedChartDTO
from libecalc.common.units import Unit
from libecalc.domain.energy import EnergyComponent, EnergyModel
from libecalc.domain.energy.energy_network import FuelConsumer, PowerConsumer, PowerProvider, TimeSeries
from libecalc.domain.process.process_change_event import ProcessChangedEvent
from libecalc.domain.process.process_system import CompressorStage, ProcessEntityID, ProcessSystem, ProcessUnit
from libecalc.domain.process.temporal_process_system import TemporalProcessSystem
from libecalc.domain.process.value_objects.model_result import (
    EcalcModelResultLiquidStream,
    EcalcModelResultMultiPhaseStream,
    EcalcModelResultPressure,
    EcalcModelResultRate,
    EcalcProcessUnitStreams,
)
from libecalc.presentation.json_result.result.results import (
    AssetResult,
    ComponentResult,
    CompressorModelResult,
    CompressorModelStageResult,
    CompressorResult,
    CompressorStreamConditionResult,
    ConsumerModelResult,
    ConsumerSystemResult,
    EcalcModelResult,
    GeneratorSetResult,
    GenericConsumerResult,
    InstallationResult,
    PumpModelResult,
    PumpResult,
    TurbineModelResult,
    VentingEmitterResult,
)


class HasParent(Protocol):
    name: str
    parent: str | None


TNode = TypeVar("TNode", bound=HasParent)


def generate_uuid_from_string(value: str) -> UUID:
    """Generate a UUID from a string"""
    return uuid.uuid5(uuid.NAMESPACE_DNS, value)


def find_children(model_results: list[TNode], parent: str, recursive: bool) -> list[TNode]:
    children: list[TNode] = []
    others: list[TNode] = []
    for model_result in model_results:
        if model_result.parent is not None and model_result.parent == parent:
            children.append(model_result)
        else:
            others.append(model_result)

    if not recursive:
        return children

    rec_children: list[TNode] = []
    for child in children:
        rec_children.extend(find_children(others, parent=child.name, recursive=True))

    return [*children, *rec_children]


def generate_id(*args: str) -> UUID:
    return generate_uuid_from_string("-".join(args))


class EcalcModelResultTurbineProcessUnit(ProcessUnit, FuelConsumer, PowerProvider):
    def __init__(self, id: UUID, name: str, model_result: TurbineModelResult):
        self._id: UUID = id
        self._name: str = name
        self._model_result: TurbineModelResult = model_result

    def get_fuel_consumption(self) -> TimeSeries:
        energy_usage = self._model_result.energy_usage
        return TimeSeries(periods=energy_usage.periods.periods, values=energy_usage.values, unit=energy_usage.unit)

    def get_id(self) -> ProcessEntityID:
        return self._id

    def get_name(self) -> str:
        return self._name

    def get_streams(self) -> EcalcProcessUnitStreams:
        return EcalcProcessUnitStreams(inlet_streams=[], outlet_streams=[])

    def get_type(self) -> str:
        return "TURBINE"

    def get_node_id(self):
        raise NotImplementedError

    def get_physical_unit(self):
        raise NotImplementedError

    def get_power_supply(self):
        raise NotImplementedError

    def get_power_output(self) -> TimeSeries:
        power = self._model_result.power
        return TimeSeries(periods=power.periods.periods, values=power.values, unit=power.unit)


class EcalcModelResultCompressorProcessUnit(CompressorStage, ProcessUnit, PowerConsumer):
    def __init__(self, id: UUID, model_result: CompressorModelStageResult):
        self._id: UUID = id
        self._model_result: CompressorModelStageResult = model_result

    def get_id(self) -> UUID:
        return self._id

    def get_type(self) -> str:
        return "COMPRESSOR_STAGE"

    def get_name(self) -> str:
        return self._model_result.name

    def get_compressor_chart(self) -> VariableSpeedChartDTO | SingleSpeedChartDTO | None:
        return self._model_result.chart

    def get_streams(self) -> EcalcProcessUnitStreams:
        return EcalcProcessUnitStreams(
            inlet_streams=[
                _map_compressor_stream_conditions_to_multi_phase_stream(
                    self._model_result.inlet_stream_condition, from_=None, to=self.get_id()
                ),
            ],
            outlet_streams=[
                _map_compressor_stream_conditions_to_multi_phase_stream(
                    self._model_result.outlet_stream_condition, from_=self.get_id(), to=None
                ),
            ],
        )

    def get_node_id(self):
        raise NotImplementedError

    def get_physical_unit(self):
        raise NotImplementedError

    def get_power_demand(self) -> TimeSeries:
        power = self._model_result.power
        return TimeSeries(
            periods=power.periods.periods,
            values=power.values,
            unit=power.unit,
        )


@dataclass(frozen=True)
class EcalcChokeProcessUnit(ProcessUnit):
    id_: UUID
    name: str
    in_stream: CompressorStreamConditionResult
    out_stream: CompressorStreamConditionResult

    def get_id(self) -> ProcessEntityID:
        return self.id_

    def get_type(self) -> str:
        return self.name.upper()

    def get_name(self) -> str:
        return self.name

    def get_streams(self) -> EcalcProcessUnitStreams:
        return EcalcProcessUnitStreams(
            inlet_streams=[
                EcalcModelResultMultiPhaseStream(
                    from_process_unit_id=None,
                    to_process_unit_id=self.id_,
                    rate=EcalcModelResultRate.from_time_series(self.in_stream.actual_rate_m3_per_hr),
                    pressure=EcalcModelResultPressure.from_time_series(self.in_stream.pressure),
                )
            ],
            outlet_streams=[
                EcalcModelResultMultiPhaseStream(
                    from_process_unit_id=self.id_,
                    to_process_unit_id=None,
                    rate=EcalcModelResultRate.from_time_series(self.out_stream.actual_rate_m3_per_hr),
                    pressure=EcalcModelResultPressure.from_time_series(self.out_stream.pressure),
                )
            ],
        )


class EcalcModelResultCompressorTrainProcessSystem(ProcessSystem):
    def __init__(self, id: UUID, model_result: CompressorModelResult):
        self._id: UUID = id
        self._model_result: CompressorModelResult = model_result

    def get_id(self) -> UUID:
        return self._id

    def get_type(self) -> str:
        return "COMPRESSOR_TRAIN"

    def get_name(self) -> str:
        return self._model_result.name

    def _is_choked(self, first: CompressorStreamConditionResult, second: CompressorStreamConditionResult) -> bool:
        return first.actual_rate_m3_per_hr != second.actual_rate_m3_per_hr or first.pressure != second.pressure

    def get_process_units(self) -> list[ProcessUnit | ProcessSystem]:
        process_units: list[ProcessUnit | ProcessSystem] = []

        first_stage = self._model_result.stage_results[0]

        if self._is_choked(first_stage.inlet_stream_condition, self._model_result.inlet_stream_condition):
            inlet_choke: ProcessUnit = EcalcChokeProcessUnit(
                id_=generate_id(str(self.get_id()), "upstream_choke"),
                name="upstream_choke",
                in_stream=self._model_result.inlet_stream_condition,
                out_stream=first_stage.inlet_stream_condition,
            )
            process_units.append(inlet_choke)

        process_units.extend(
            [
                EcalcModelResultCompressorProcessUnit(
                    id=generate_id(str(self.get_id()), stage.name), model_result=stage
                )
                for stage in self._model_result.stage_results
            ]
        )

        if self._model_result.turbine_result is not None:
            turbine_process_unit = EcalcModelResultTurbineProcessUnit(
                id=generate_id(str(self.get_id()), "turbine"),
                name="turbine",
                model_result=self._model_result.turbine_result,
            )
            process_units.append(turbine_process_unit)

        last_stage = self._model_result.stage_results[-1]
        if self._is_choked(last_stage.outlet_stream_condition, self._model_result.outlet_stream_condition):
            outlet_choke: ProcessUnit = EcalcChokeProcessUnit(
                id_=generate_id(str(self.get_id()), "downstream_choke"),
                name="downstream_choke",
                in_stream=last_stage.outlet_stream_condition,
                out_stream=self._model_result.outlet_stream_condition,
            )
            process_units.append(outlet_choke)

        return process_units


class EcalcModelResultPumpProcessUnit(ProcessUnit, PowerConsumer):
    def __init__(self, id: UUID, model_result: PumpModelResult):
        self._id: UUID = id
        self._model_result: PumpModelResult = model_result

    def get_id(self) -> UUID:
        return self._id

    def get_type(self) -> str:
        return self._model_result.componentType

    def get_name(self) -> str:
        return self._model_result.name

    def get_streams(self) -> EcalcProcessUnitStreams:
        rate_inlet = self._model_result.inlet_liquid_rate_m3_per_day
        pressure_inlet = self._model_result.inlet_pressure_bar
        pressure_outlet = self._model_result.outlet_pressure_bar

        return EcalcProcessUnitStreams(
            inlet_streams=[
                EcalcModelResultLiquidStream(
                    from_process_unit_id=None,
                    to_process_unit_id=self.get_id(),
                    rate=EcalcModelResultRate.from_time_series(rate_inlet) if rate_inlet is not None else None,
                    pressure=EcalcModelResultPressure.from_time_series(pressure_inlet)
                    if pressure_inlet is not None
                    else None,
                ),
            ],
            outlet_streams=[
                EcalcModelResultLiquidStream(
                    from_process_unit_id=self.get_id(),
                    to_process_unit_id=None,
                    rate=EcalcModelResultRate.from_time_series(rate_inlet)
                    if rate_inlet is not None
                    else None,  # TODO - we don't have outlet rate, ok to use inlet here?
                    pressure=EcalcModelResultPressure.from_time_series(pressure_outlet)
                    if pressure_outlet is not None
                    else None,
                ),
            ],
        )

    def get_node_id(self):
        raise NotImplementedError

    def get_physical_unit(self):
        raise NotImplementedError

    def get_power_demand(self) -> TimeSeries:
        power = self._model_result.power
        assert power is not None, "Pump should have power since it's a power consumer"
        return TimeSeries(
            periods=power.periods.periods,
            values=power.values,
            unit=power.unit,
        )


class EcalcModelResultConsumerSystemProcessSystem(ProcessSystem):
    def __init__(self, id: UUID):
        self._id: UUID = id

    def get_id(self) -> ProcessEntityID:
        return self._id

    def get_type(self) -> str:
        return "CONSUMER_SYSTEM"

    def get_name(self) -> str:
        return "some name"

    def get_process_units(self) -> list[ProcessSystem | ProcessUnit]:
        return []


class EcalcModelResultEnergyComponent(EnergyComponent, TemporalProcessSystem):
    def __init__(self, component_result: ComponentResult, model_results: list[ConsumerModelResult]):
        self._component_result: ComponentResult = component_result
        self._model_results: list[ConsumerModelResult] = model_results

    @property
    def id(self) -> str:
        return self._component_result.id

    def get_component_process_type(self) -> ComponentType:
        return self._component_result.componentType

    def get_name(self) -> str:
        return self._component_result.name

    def is_provider(self) -> bool:
        return self.get_component_process_type() in [ComponentType.GENERATOR_SET]

    def is_fuel_consumer(self) -> bool:
        if self.get_component_process_type() in [ComponentType.ASSET, ComponentType.INSTALLATION]:
            return True
        else:
            return self._component_result.energy_usage.unit == Unit.STANDARD_CUBIC_METER_PER_DAY

    def is_electricity_consumer(self) -> bool:
        if self.get_component_process_type() in [ComponentType.ASSET, ComponentType.INSTALLATION]:
            return False

        return self._component_result.power is not None

    def get_process_changed_events(self) -> list[ProcessChangedEvent]:
        if isinstance(
            self._component_result,
            AssetResult | InstallationResult | GeneratorSetResult | GenericConsumerResult | VentingEmitterResult,
        ):
            return []
        elif isinstance(self._component_result, ConsumerSystemResult):
            direct_child_models = find_children(self._model_results, parent=self.get_name(), recursive=False)

            unique_start_dates = set()
            for direct_child_model in direct_child_models:
                unique_start_dates.add(direct_child_model.periods.first_date)
            # consumer system is different, need to create unique events
            return [ProcessChangedEvent(start=start, name=str(start)) for start in unique_start_dates]
        elif isinstance(self._component_result, CompressorResult | PumpResult):
            direct_child_models = find_children(self._model_results, parent=self.get_name(), recursive=False)

            process_changed_events = []
            for direct_child_model in direct_child_models:
                start = direct_child_model.periods.first_date
                process_changed_events.append(
                    ProcessChangedEvent(
                        start=start,
                        name=str(start),
                    )
                )

            return process_changed_events
        else:
            assert_never(self._component_result)

    def _get_model_result_for_event(self, event: ProcessChangedEvent) -> ConsumerModelResult:
        model_result_for_event = [
            model_result for model_result in self._model_results if model_result.periods.first_date == event.start
        ]
        assert len(model_result_for_event) == 1, "We should find only one model result that matches event"
        return model_result_for_event[0]

    def get_process_system(self, event: ProcessChangedEvent) -> ProcessSystem | ProcessUnit | None:
        if isinstance(
            self._component_result,
            AssetResult | InstallationResult | GeneratorSetResult | GenericConsumerResult | VentingEmitterResult,
        ):
            return None
        elif isinstance(self._component_result, ConsumerSystemResult):
            return EcalcModelResultConsumerSystemProcessSystem(
                id=generate_id(self.id, event.name, "consumer-system-process-system"),
            )
        elif isinstance(self._component_result, CompressorResult):
            model_result_for_event = self._get_model_result_for_event(event)
            assert isinstance(model_result_for_event, CompressorModelResult)
            return EcalcModelResultCompressorTrainProcessSystem(
                id=generate_id(self.id, event.name, model_result_for_event.name), model_result=model_result_for_event
            )
        elif isinstance(self._component_result, PumpResult):
            model_result_for_event = self._get_model_result_for_event(event)
            assert isinstance(model_result_for_event, PumpModelResult)
            return EcalcModelResultPumpProcessUnit(
                id=generate_id(self.id, event.name, model_result_for_event.name),
                model_result=model_result_for_event,
            )
        else:
            assert_never(self._component_result)


class EcalcModelResultEnergyModel(EnergyModel):
    """
    To be able to map previous runs into process results we need to only rely on EcalcModelResult.

    This wrapper implements the domain interfaces for EnergyModel, EnergyComponent, ProcessSystem and ProcessUnit to
    make it easier to switch from EcalcModelResult to domain objects in the future.
    """

    def __init__(self, ecalc_model_results: EcalcModelResult):
        self._ecalc_model_results: EcalcModelResult = ecalc_model_results

    def _map_energy_component(self, component_result: ComponentResult) -> EnergyComponent:
        return EcalcModelResultEnergyComponent(
            component_result=component_result,
            model_results=find_children(
                model_results=self._ecalc_model_results.models, parent=component_result.name, recursive=True
            ),
        )

    def get_consumers(self, provider_id: str | None = None) -> list[EnergyComponent]:
        if provider_id is None:
            provider_id = self._ecalc_model_results.component_result.name

        return [
            self._map_energy_component(child)
            for child in find_children(self._ecalc_model_results.components, parent=provider_id, recursive=False)
        ]

    def get_energy_components(self) -> list[EnergyComponent]:
        return [
            self._map_energy_component(component_result) for component_result in self._ecalc_model_results.components
        ]

    def get_process_systems(self) -> list[ProcessSystem]:
        return []


def _map_compressor_stream_conditions_to_multi_phase_stream(
    stream_conditions: CompressorStreamConditionResult, from_: ProcessEntityID | None, to: ProcessEntityID | None
) -> EcalcModelResultMultiPhaseStream:
    return EcalcModelResultMultiPhaseStream(
        from_process_unit_id=from_,
        to_process_unit_id=to,
        rate=EcalcModelResultRate.from_time_series(stream_conditions.standard_rate_before_asv_sm3_per_day),
        pressure=EcalcModelResultPressure.from_time_series(stream_conditions.pressure),
    )
