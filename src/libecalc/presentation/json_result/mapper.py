import math
import operator
from collections import defaultdict
from collections.abc import Sequence
from functools import reduce
from typing import assert_never, cast

import numpy as np
from numpy.typing import NDArray

import libecalc
from libecalc.application.graph_result import GraphResult
from libecalc.common.component_info.component_level import ComponentLevel
from libecalc.common.component_info.compressor import CompressorPressureType
from libecalc.common.component_type import ComponentType
from libecalc.common.decorators.feature_flags import Feature
from libecalc.common.errors.exceptions import ProgrammingError
from libecalc.common.serializable_chart import ChartDTO
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period, Periods
from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    RateType,
    TimeSeriesBoolean,
    TimeSeriesFloat,
    TimeSeriesInt,
    TimeSeriesRate,
    TimeSeriesStreamDayRate,
)
from libecalc.core.result.results import CompressorResult, GeneratorSetResult, PumpResult
from libecalc.core.result.results import ConsumerSystemResult as CoreConsumerSystemResult
from libecalc.core.result.results import GenericComponentResult as CoreGenericComponentResult
from libecalc.domain.infrastructure.energy_components.asset.asset import Asset
from libecalc.domain.infrastructure.energy_components.electricity_consumer.electricity_consumer import (
    ElectricityConsumer,
)
from libecalc.domain.infrastructure.energy_components.fuel_consumer.fuel_consumer import FuelConsumerComponent
from libecalc.domain.infrastructure.energy_components.installation.installation import InstallationComponent
from libecalc.domain.infrastructure.energy_components.legacy_consumer.system import ConsumerSystemConsumerFunction
from libecalc.domain.process.compressor.core.base import CompressorWithTurbineModel
from libecalc.domain.process.compressor.core.sampled import CompressorModelSampled
from libecalc.domain.process.compressor.core.train.base import CompressorTrainModel
from libecalc.domain.process.core.results import CompressorStreamCondition, CompressorTrainResult
from libecalc.domain.process.core.results import PumpModelResult as CorePumpModelResult
from libecalc.domain.process.core.results.base import Quantity
from libecalc.dto.node_info import NodeInfo
from libecalc.presentation.json_result.aggregators import aggregate_emissions
from libecalc.presentation.json_result.result import ComponentResult as JsonResultComponentResult
from libecalc.presentation.json_result.result.emission import EmissionResult, PartialEmissionResult
from libecalc.presentation.json_result.result.results import (
    AssetResult,
    CompressorModelResult,
    CompressorModelStageResult,
    CompressorStreamConditionResult,
    ConsumerSystemResult,
    GenericConsumerResult,
    GenericModelResult,
    InstallationResult,
    PumpModelResult,
    TurbineModelResult,
)
from libecalc.presentation.yaml.model import YamlModel


class ModelResultHelper:
    """
    A helper class for mapping model results from core to structured results that can be used
    for e.g. reporting or further analysis.

    This class provides static methods to process compressor, pump, generic, and turbine models
    """

    @staticmethod
    def map_rate(
        rate_sm3_day: Sequence[float] | list[list[float]],
        max_standard_rate: Sequence[float] | None,
        periods: Periods,
        regularity: TimeSeriesFloat,
    ) -> tuple[TimeSeriesRate, TimeSeriesRate]:
        # Handle multi stream
        # Select the first rate from multi stream, only a workaround until we have more info by using
        # streams
        if len(rate_sm3_day) > 0 and isinstance(rate_sm3_day[0], list):
            rate = TimeSeriesHelper.initialize_timeseries(
                periods=periods,
                values=rate_sm3_day[0],
                unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                rate_type=RateType.STREAM_DAY,
                regularity=regularity.for_periods(periods).values,
            )
            maximum_rate = TimeSeriesHelper.initialize_timeseries(
                periods=periods,
                values=max_standard_rate  # WORKAROUND: We now only return a single max rate - for one stream only
                if max_standard_rate is not None
                else [math.nan] * len(periods),
                unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                rate_type=RateType.STREAM_DAY,
                regularity=regularity.for_periods(periods).values,
            )
            return rate, maximum_rate
        else:
            rate_sm3_day = cast(Sequence[float], rate_sm3_day)
            rate = TimeSeriesHelper.initialize_timeseries(
                periods=periods,
                values=rate_sm3_day,
                unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                rate_type=RateType.STREAM_DAY,
                regularity=regularity.for_periods(periods).values,
            )
            maximum_rate = TimeSeriesHelper.initialize_timeseries(
                periods=periods,
                values=max_standard_rate if max_standard_rate is not None else [math.nan] * len(periods),
                unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                rate_type=RateType.STREAM_DAY,
                regularity=regularity.for_periods(periods).values,
            )
            return rate, maximum_rate

    @staticmethod
    def process_single_compressor_model(
        consumer: FuelConsumerComponent | ElectricityConsumer,
        consumer_result: CompressorResult,
        consumer_node_info: NodeInfo,
        regularity: TimeSeriesFloat,
    ) -> list[CompressorModelResult]:
        models: list[CompressorModelResult] = []
        for temporal_result in consumer_result.temporal_results:
            period = temporal_result.periods.period
            periods = temporal_result.periods
            temporal_result = temporal_result.energy_function_result
            assert isinstance(temporal_result, CompressorTrainResult)

            def pressure_or_nan(pressure: NDArray[np.float64] | None):
                if pressure is None:
                    return TimeSeriesFloat(
                        periods=periods,
                        values=[math.nan] * len(periods),
                        unit=Unit.BARA,
                    )

                return TimeSeriesFloat(
                    periods=periods,
                    values=pressure,
                    unit=Unit.BARA,
                )

            model_for_period = consumer.energy_usage_model.get_model(period)
            requested_inlet_pressure = pressure_or_nan(model_for_period.get_requested_inlet_pressure())
            requested_outlet_pressure = pressure_or_nan(model_for_period.get_requested_outlet_pressure())

            model_stage_results = CompressorHelper.process_stage_results(temporal_result, regularity, periods=periods)
            turbine_result = ModelResultHelper.process_turbine_result(
                model=temporal_result, regularity=regularity, periods=periods, name=consumer.name
            )

            inlet_stream_condition = CompressorHelper.process_inlet_stream_condition(
                periods,
                temporal_result.inlet_stream_condition,
                regularity,
            )

            outlet_stream_condition = CompressorHelper.process_outlet_stream_condition(
                periods,
                temporal_result.outlet_stream_condition,
                regularity,
            )

            rate, maximum_rate = ModelResultHelper.map_rate(
                temporal_result.rate_sm3_day, temporal_result.max_standard_rate, periods, regularity
            )

            energy_result = temporal_result.get_energy_result()

            energy_usage = TimeSeriesHelper.initialize_timeseries_rate_from_quantity(
                periods=periods,
                quantity=energy_result.energy_usage,
                rate_type=RateType.STREAM_DAY,
                regularity=regularity.for_periods(periods).values,
            )
            power = (
                TimeSeriesHelper.initialize_timeseries_rate_from_quantity(
                    periods=periods,
                    quantity=energy_result.power,
                    rate_type=RateType.STREAM_DAY,
                    regularity=regularity.for_periods(periods).values,
                )
                if energy_result.power is not None
                else None
            )

            models.append(
                CompressorModelResult(
                    parent=consumer_node_info.id,
                    name=consumer_node_info.name,
                    componentType=consumer_node_info.component_type,
                    component_level=ComponentLevel.MODEL,
                    energy_usage=energy_usage,
                    requested_inlet_pressure=requested_inlet_pressure,
                    requested_outlet_pressure=requested_outlet_pressure,
                    rate=rate,
                    maximum_rate=maximum_rate,
                    stage_results=model_stage_results,
                    failure_status=list(temporal_result.failure_status)
                    if temporal_result.failure_status is not None
                    else None,
                    periods=periods,
                    is_valid=TimeSeriesHelper.initialize_timeseries_bool(
                        periods=periods,
                        values=energy_result.is_valid,
                    ),
                    energy_usage_cumulative=energy_usage.to_volumes().cumulative(),
                    power_cumulative=power.to_volumes().to_unit(Unit.GIGA_WATT_HOURS).cumulative()
                    if power is not None
                    else None,
                    power=power,
                    turbine_result=turbine_result,
                    inlet_stream_condition=inlet_stream_condition,
                    outlet_stream_condition=outlet_stream_condition,
                )
            )
        return models

    @staticmethod
    def process_compressor_models(
        graph_result: GraphResult,
        consumer_result: CompressorResult | CoreConsumerSystemResult,
        consumer_id: str,
        consumer_node_info: NodeInfo,
        regularity: TimeSeriesFloat,
    ) -> list[CompressorModelResult]:
        models = []
        component = graph_result.graph.get_node(consumer_id)
        assert isinstance(component, FuelConsumerComponent | ElectricityConsumer)

        energy_usage_model = component.energy_usage_model

        is_compressor_system = all(
            isinstance(model, ConsumerSystemConsumerFunction) for model in energy_usage_model.get_models()
        )
        is_compressor = all(
            isinstance(model, CompressorTrainModel | CompressorWithTurbineModel | CompressorModelSampled)
            for model in energy_usage_model.get_models()
        )
        assert is_compressor_system or is_compressor

        if is_compressor:
            assert isinstance(consumer_result, CompressorResult)
            return ModelResultHelper.process_single_compressor_model(
                consumer=component,
                consumer_result=consumer_result,
                consumer_node_info=consumer_node_info,
                regularity=regularity,
            )

        assert isinstance(consumer_result, CoreConsumerSystemResult)
        assert is_compressor_system
        for temporal_result in consumer_result.temporal_results:
            period = temporal_result.periods.period
            periods = temporal_result.periods
            for system_consumer_result in temporal_result.consumer_results:
                energy_usage_model = cast(TemporalModel[ConsumerSystemConsumerFunction], component.energy_usage_model)
                requested_inlet_pressure = CompressorHelper.get_requested_compressor_pressures(
                    energy_usage_model=energy_usage_model,
                    pressure_type=CompressorPressureType.INLET_PRESSURE,
                    name=system_consumer_result.name,
                    operational_settings_used=consumer_result.operational_settings_used
                    if consumer_node_info.component_type == ComponentType.COMPRESSOR_SYSTEM
                    else None,
                    model_periods=periods,
                ).for_period(period)
                requested_outlet_pressure = CompressorHelper.get_requested_compressor_pressures(
                    energy_usage_model=energy_usage_model,
                    pressure_type=CompressorPressureType.OUTLET_PRESSURE,
                    name=system_consumer_result.name,
                    operational_settings_used=consumer_result.operational_settings_used
                    if consumer_node_info.component_type == ComponentType.COMPRESSOR_SYSTEM
                    else None,
                    model_periods=periods,
                ).for_period(period)

                compressor_train_result = system_consumer_result.result
                assert isinstance(compressor_train_result, CompressorTrainResult)

                model_stage_results = CompressorHelper.process_stage_results(
                    model=compressor_train_result, regularity=regularity, periods=periods
                )
                turbine_result = ModelResultHelper.process_turbine_result(
                    model=compressor_train_result,
                    regularity=regularity,
                    periods=periods,
                    name=system_consumer_result.name,
                )

                inlet_stream_condition = CompressorHelper.process_inlet_stream_condition(
                    periods,
                    compressor_train_result.inlet_stream_condition,
                    regularity,
                )

                outlet_stream_condition = CompressorHelper.process_outlet_stream_condition(
                    periods,
                    compressor_train_result.outlet_stream_condition,
                    regularity,
                )

                rate, maximum_rate = ModelResultHelper.map_rate(
                    rate_sm3_day=compressor_train_result.rate_sm3_day,
                    max_standard_rate=compressor_train_result.max_standard_rate,
                    periods=periods,
                    regularity=regularity,
                )

                energy_result = compressor_train_result.get_energy_result()

                energy_usage = TimeSeriesHelper.initialize_timeseries_rate_from_quantity(
                    periods=periods,
                    quantity=energy_result.energy_usage,
                    rate_type=RateType.STREAM_DAY,
                    regularity=regularity.for_periods(periods).values,
                )
                power = (
                    TimeSeriesHelper.initialize_timeseries_rate_from_quantity(
                        periods=periods,
                        quantity=energy_result.power,
                        rate_type=RateType.STREAM_DAY,
                        regularity=regularity.for_periods(periods).values,
                    )
                    if energy_result.power is not None
                    else None
                )

                models.append(
                    CompressorModelResult(
                        parent=consumer_id,
                        name=system_consumer_result.name,
                        componentType=ComponentType.COMPRESSOR,
                        component_level=ComponentLevel.MODEL,
                        energy_usage=energy_usage,
                        requested_inlet_pressure=requested_inlet_pressure,
                        requested_outlet_pressure=requested_outlet_pressure,
                        rate=rate,
                        maximum_rate=maximum_rate,
                        stage_results=model_stage_results,
                        failure_status=list(compressor_train_result.failure_status)
                        if compressor_train_result.failure_status is not None
                        else None,
                        periods=periods,
                        is_valid=TimeSeriesHelper.initialize_timeseries_bool(
                            periods=periods,
                            values=energy_result.is_valid,
                        ),
                        energy_usage_cumulative=energy_usage.to_volumes().cumulative(),
                        power=power if power is not None else None,
                        power_cumulative=power.to_volumes().to_unit(Unit.GIGA_WATT_HOURS).cumulative()
                        if power is not None
                        else None,
                        turbine_result=turbine_result,
                        inlet_stream_condition=inlet_stream_condition,
                        outlet_stream_condition=outlet_stream_condition,
                    )
                )
        return models

    @staticmethod
    def process_pump_models(
        consumer_result: PumpResult | CoreConsumerSystemResult,
        node_info: NodeInfo,
        regularity: TimeSeriesFloat,
    ) -> list[PumpModelResult]:
        if isinstance(consumer_result, PumpResult):
            models: list[PumpModelResult] = []
            for model in consumer_result.temporal_results:
                periods = model.periods
                model = model.energy_function_result
                energy_result = model.get_energy_result()
                assert isinstance(model, CorePumpModelResult)
                energy_usage = TimeSeriesHelper.initialize_timeseries_rate_from_quantity(
                    periods=periods,
                    quantity=energy_result.energy_usage,
                    rate_type=RateType.STREAM_DAY,
                    regularity=regularity.for_periods(periods).values,
                )
                power = (
                    TimeSeriesHelper.initialize_timeseries_rate_from_quantity(
                        periods=periods,
                        quantity=energy_result.power,
                        rate_type=RateType.STREAM_DAY,
                        regularity=regularity.for_periods(periods).values,
                    )
                    if energy_result.power is not None
                    else None
                )
                models.append(
                    PumpModelResult(
                        parent=node_info.id,
                        name=node_info.name,
                        componentType=node_info.component_type,
                        component_level=ComponentLevel.MODEL,
                        energy_usage=energy_usage,
                        energy_usage_cumulative=energy_usage.to_volumes().cumulative(),
                        is_valid=TimeSeriesHelper.initialize_timeseries_bool(
                            periods=periods,
                            values=energy_result.is_valid,
                        ),
                        periods=periods,
                        power=power if power is not None else None,
                        power_cumulative=(
                            power.to_volumes().to_unit(Unit.GIGA_WATT_HOURS).cumulative() if power is not None else None
                        ),
                        inlet_liquid_rate_m3_per_day=TimeSeriesHelper.initialize_timeseries(
                            periods=periods,
                            values=model.rate,
                            unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                            rate_type=RateType.STREAM_DAY,
                            regularity=regularity,
                        ),
                        inlet_pressure_bar=TimeSeriesHelper.initialize_timeseries(
                            periods=periods,
                            values=model.suction_pressure,
                            unit=Unit.BARA,
                        ),
                        outlet_pressure_bar=TimeSeriesHelper.initialize_timeseries(
                            periods=periods,
                            values=model.discharge_pressure,
                            unit=Unit.BARA,
                        ),
                        operational_head=TimeSeriesHelper.initialize_timeseries(
                            periods=periods,
                            values=model.operational_head,
                            unit=Unit.POLYTROPIC_HEAD_JOULE_PER_KG,
                        ),
                    )
                )
            return models
        elif isinstance(consumer_result, CoreConsumerSystemResult):
            models = []
            for temporal_result in consumer_result.temporal_results:
                periods = temporal_result.periods
                for system_consumer_result in temporal_result.consumer_results:
                    pump_model_result = system_consumer_result.result
                    energy_result = pump_model_result.get_energy_result()
                    assert isinstance(pump_model_result, CorePumpModelResult)
                    energy_usage = TimeSeriesHelper.initialize_timeseries_rate_from_quantity(
                        periods=periods,
                        quantity=energy_result.energy_usage,
                        rate_type=RateType.STREAM_DAY,
                        regularity=regularity.for_periods(periods).values,
                    )
                    power = (
                        TimeSeriesHelper.initialize_timeseries_rate_from_quantity(
                            periods=periods,
                            quantity=energy_result.power,
                            rate_type=RateType.STREAM_DAY,
                            regularity=regularity.for_periods(periods).values,
                        )
                        if energy_result.power is not None
                        else None
                    )
                    models.append(
                        PumpModelResult(
                            parent=node_info.id,
                            name=system_consumer_result.name,
                            componentType=ComponentType.PUMP,
                            component_level=ComponentLevel.MODEL,
                            energy_usage=energy_usage,
                            energy_usage_cumulative=energy_usage.to_volumes().cumulative(),
                            is_valid=TimeSeriesHelper.initialize_timeseries_bool(
                                periods=periods,
                                values=energy_result.is_valid,
                            ),
                            periods=periods,
                            power=power if power is not None else None,
                            power_cumulative=(
                                power.to_volumes().to_unit(Unit.GIGA_WATT_HOURS).cumulative()
                                if power is not None
                                else None
                            ),
                            inlet_liquid_rate_m3_per_day=TimeSeriesHelper.initialize_timeseries(
                                periods=periods,
                                values=pump_model_result.rate,
                                unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                                rate_type=RateType.STREAM_DAY,
                                regularity=regularity,
                            ),
                            inlet_pressure_bar=TimeSeriesHelper.initialize_timeseries(
                                periods=periods,
                                values=pump_model_result.suction_pressure,
                                unit=Unit.BARA,
                            ),
                            outlet_pressure_bar=TimeSeriesHelper.initialize_timeseries(
                                periods=periods,
                                values=pump_model_result.discharge_pressure,
                                unit=Unit.BARA,
                            ),
                            operational_head=TimeSeriesHelper.initialize_timeseries(
                                periods=periods,
                                values=pump_model_result.operational_head,
                                unit=Unit.POLYTROPIC_HEAD_JOULE_PER_KG,
                            ),
                        )
                    )
            return models
        else:
            assert_never(consumer_result)

    @staticmethod
    def process_generic_models(
        consumer_result: CoreGenericComponentResult, node_info: NodeInfo, regularity: TimeSeriesFloat
    ) -> list[GenericModelResult]:
        models = []
        for temporal_result in consumer_result.temporal_results:
            periods = temporal_result.periods
            model = temporal_result.energy_function_result
            energy_result = model.get_energy_result()
            energy_usage = TimeSeriesHelper.initialize_timeseries_rate_from_quantity(
                periods=periods,
                quantity=energy_result.energy_usage,
                rate_type=RateType.STREAM_DAY,
                regularity=regularity.for_periods(periods).values,
            )
            power = (
                TimeSeriesHelper.initialize_timeseries_rate_from_quantity(
                    periods=periods,
                    quantity=energy_result.power,
                    rate_type=RateType.STREAM_DAY,
                    regularity=regularity.for_periods(periods).values,
                )
                if energy_result.power is not None
                else None
            )
            models.append(
                GenericModelResult(
                    parent=node_info.id,
                    name=node_info.name,
                    componentType=node_info.component_type,
                    component_level=ComponentLevel.MODEL,
                    periods=periods,
                    is_valid=TimeSeriesHelper.initialize_timeseries_bool(
                        periods=periods,
                        values=energy_result.is_valid,
                    ),
                    energy_usage=energy_usage,
                    energy_usage_cumulative=energy_usage.to_volumes().cumulative(),
                    power=power,
                    power_cumulative=(
                        power.to_volumes().to_unit(Unit.GIGA_WATT_HOURS).cumulative() if power is not None else None
                    ),
                )
            )
        return models

    @staticmethod
    def process_turbine_result(
        model: CompressorTrainResult, regularity: TimeSeriesFloat, periods: Periods, name: str
    ) -> TurbineModelResult | None:
        if model.turbine_result is None:
            return None

        turbine_energy_result = model.turbine_result.get_energy_result()
        assert turbine_energy_result.power is not None

        energy_usage = TimeSeriesHelper.initialize_timeseries_rate_from_quantity(
            periods=periods,
            quantity=turbine_energy_result.energy_usage,
            rate_type=RateType.STREAM_DAY,
            regularity=regularity.for_periods(periods).values,
        )
        power = TimeSeriesHelper.initialize_timeseries_rate_from_quantity(
            periods=periods,
            quantity=turbine_energy_result.power,
            rate_type=RateType.STREAM_DAY,
            regularity=regularity.for_periods(periods).values,
        )
        return TurbineModelResult(
            efficiency=TimeSeriesHelper.initialize_timeseries(
                periods=periods, values=model.turbine_result.efficiency, unit=Unit.FRACTION
            ),
            energy_usage=energy_usage,
            energy_usage_unit=turbine_energy_result.energy_usage.unit,
            exceeds_maximum_load=TimeSeriesHelper.initialize_timeseries_bool(
                periods=periods,
                values=model.turbine_result.exceeds_maximum_load,
            ),
            fuel_rate=energy_usage,
            is_valid=TimeSeriesHelper.initialize_timeseries_bool(
                periods=periods,
                values=turbine_energy_result.is_valid,
            ),
            load=power,
            power=power,
            power_unit=turbine_energy_result.power.unit,
            periods=periods,
            name=name,
        )


class ComponentResultHelper:
    """
    A helper class for mapping component results from core to structured results that can be used
    for e.g. reporting or further analysis.

    This class provides static methods to process various component types, i.e. generator sets,
    pumps, compressors, generic components, and consumer systems.

    Component results are top level results for each component. Individual models for a given component
    are processed separately in the ModelResultHelper class
    """

    @staticmethod
    def process_generator_set_result(
        model: YamlModel,
        consumer_result: GeneratorSetResult,
        consumer_node_info: NodeInfo,
        regularity: TimeSeriesFloat,
    ) -> libecalc.presentation.json_result.result.results.GeneratorSetResult:
        graph_result = model.get_graph_result()
        return libecalc.presentation.json_result.result.results.GeneratorSetResult(
            name=consumer_node_info.name,
            parent=graph_result.graph.get_predecessor(consumer_result.id),
            component_level=consumer_node_info.component_level,
            componentType=consumer_node_info.component_type,
            emissions=EmissionHelper.parse_emissions(graph_result.emission_results[consumer_result.id], regularity)
            if consumer_result.id in graph_result.emission_results
            else {},
            energy_usage_cumulative=TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.energy_usage, regularity=regularity
            )
            .to_volumes()
            .cumulative(),
            power_cumulative=TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.power, regularity=regularity
            )
            .to_volumes()
            .to_unit(Unit.GIGA_WATT_HOURS)
            .cumulative()
            if consumer_result.power is not None
            else None,
            power=TimeSeriesRate.from_timeseries_stream_day_rate(consumer_result.power, regularity=regularity)
            if consumer_result.power is not None
            else None,
            energy_usage=TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.energy_usage, regularity=regularity
            ).to_calendar_day()
            if consumer_result.energy_usage.unit == Unit.STANDARD_CUBIC_METER_PER_DAY
            else TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.energy_usage, regularity=regularity
            ).to_stream_day(),
            power_capacity_margin=TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.power_capacity_margin, regularity=regularity
            ),
            periods=consumer_result.periods,
            id=consumer_result.id,
            is_valid=model.get_validity(consumer_node_info.id),
        )

    @staticmethod
    def process_pump_component_result(
        model: YamlModel,
        consumer_result: PumpResult,
        consumer_node_info: NodeInfo,
        regularity: TimeSeriesFloat,
    ) -> libecalc.presentation.json_result.result.results.PumpResult:
        graph_result = model.get_graph_result()
        return libecalc.presentation.json_result.result.results.PumpResult(
            name=consumer_node_info.name,
            parent=graph_result.graph.get_predecessor(consumer_result.id),
            component_level=consumer_node_info.component_level,
            componentType=consumer_node_info.component_type,
            emissions=EmissionHelper.parse_emissions(graph_result.emission_results[consumer_result.id], regularity)
            if consumer_result.id in graph_result.emission_results
            else {},
            energy_usage_cumulative=TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.energy_usage, regularity=regularity
            )
            .to_volumes()
            .cumulative(),
            power_cumulative=TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.power, regularity=regularity
            )
            .to_volumes()
            .to_unit(Unit.GIGA_WATT_HOURS)
            .cumulative()
            if consumer_result.power is not None
            else None,
            power=TimeSeriesRate.from_timeseries_stream_day_rate(consumer_result.power, regularity=regularity),
            energy_usage=TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.energy_usage, regularity=regularity
            ).to_calendar_day()
            if consumer_result.energy_usage.unit == Unit.STANDARD_CUBIC_METER_PER_DAY
            else TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.energy_usage, regularity=regularity
            ).to_stream_day(),
            inlet_liquid_rate_m3_per_day=TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.inlet_liquid_rate_m3_per_day, regularity=regularity
            ),
            inlet_pressure_bar=consumer_result.inlet_pressure_bar,
            outlet_pressure_bar=consumer_result.outlet_pressure_bar,
            operational_head=consumer_result.operational_head,
            periods=consumer_result.periods,
            id=consumer_result.id,
            is_valid=model.get_validity(consumer_node_info.id),
        )

    @staticmethod
    def process_compressor_component_result(
        model: YamlModel,
        consumer_result: CompressorResult,
        consumer_node_info: NodeInfo,
        regularity: TimeSeriesFloat,
    ) -> libecalc.presentation.json_result.result.results.CompressorResult:
        graph_result = model.get_graph_result()
        return libecalc.presentation.json_result.result.results.CompressorResult(
            name=consumer_node_info.name,
            parent=graph_result.graph.get_predecessor(consumer_result.id),
            component_level=consumer_node_info.component_level,
            componentType=consumer_node_info.component_type,
            emissions=EmissionHelper.parse_emissions(graph_result.emission_results[consumer_result.id], regularity)
            if consumer_result.id in graph_result.emission_results
            else {},
            energy_usage_cumulative=TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.energy_usage, regularity=regularity
            )
            .to_volumes()
            .cumulative(),
            power_cumulative=TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.power, regularity=regularity
            )
            .to_volumes()
            .to_unit(Unit.GIGA_WATT_HOURS)
            .cumulative()
            if consumer_result.power is not None
            else None,
            power=TimeSeriesRate.from_timeseries_stream_day_rate(consumer_result.power, regularity=regularity),
            energy_usage=TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.energy_usage, regularity=regularity
            ).to_calendar_day()
            if consumer_result.energy_usage.unit == Unit.STANDARD_CUBIC_METER_PER_DAY
            else TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.energy_usage, regularity=regularity
            ).to_stream_day(),
            recirculation_loss=TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.recirculation_loss, regularity=regularity
            ),
            rate_exceeds_maximum=consumer_result.rate_exceeds_maximum,
            periods=consumer_result.periods,
            id=consumer_result.id,
            is_valid=model.get_validity(consumer_node_info.id),
        )

    @staticmethod
    def process_generic_component_result(
        model: YamlModel,
        consumer_result: CoreGenericComponentResult,
        consumer_node_info: NodeInfo,
        regularity: TimeSeriesFloat,
    ) -> GenericConsumerResult:
        graph_result = model.get_graph_result()
        consumer_id = consumer_result.id
        emissions = (
            EmissionHelper.parse_emissions(graph_result.emission_results[consumer_id], regularity)
            if consumer_id in graph_result.emission_results
            else {}
        )
        return libecalc.presentation.json_result.result.GenericConsumerResult(
            name=consumer_node_info.name,
            parent=graph_result.graph.get_predecessor(consumer_result.id),
            component_level=consumer_node_info.component_level,
            componentType=consumer_node_info.component_type,
            emissions=emissions,
            energy_usage_cumulative=TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.energy_usage, regularity=regularity
            )
            .to_volumes()
            .cumulative(),
            power_cumulative=TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.power, regularity=regularity
            )
            .to_volumes()
            .to_unit(Unit.GIGA_WATT_HOURS)
            .cumulative()
            if consumer_result.power is not None
            else None,
            power=TimeSeriesRate.from_timeseries_stream_day_rate(consumer_result.power, regularity=regularity),
            energy_usage=TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.energy_usage, regularity=regularity
            ).to_calendar_day()
            if consumer_result.energy_usage.unit == Unit.STANDARD_CUBIC_METER_PER_DAY
            else TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.energy_usage, regularity=regularity
            ).to_stream_day(),
            periods=consumer_result.periods,
            id=consumer_result.id,
            is_valid=model.get_validity(consumer_node_info.id),
        )

    @staticmethod
    def process_consumer_system_component_result(
        model: YamlModel,
        consumer_result: CoreConsumerSystemResult,
        consumer_node_info: NodeInfo,
        regularity: TimeSeriesFloat,
    ) -> ConsumerSystemResult:
        graph_result = model.get_graph_result()
        consumer_id = consumer_result.id
        emissions = (
            EmissionHelper.parse_emissions(graph_result.emission_results[consumer_id], regularity)
            if consumer_id in graph_result.emission_results
            else {}
        )

        return libecalc.presentation.json_result.result.ConsumerSystemResult(
            name=consumer_node_info.name,
            parent=graph_result.graph.get_predecessor(consumer_result.id),
            component_level=consumer_node_info.component_level,
            componentType=consumer_node_info.component_type,
            emissions=emissions,
            energy_usage_cumulative=TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.energy_usage, regularity=regularity
            )
            .to_volumes()
            .cumulative(),
            power_cumulative=TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.power, regularity=regularity
            )
            .to_volumes()
            .to_unit(Unit.GIGA_WATT_HOURS)
            .cumulative()
            if consumer_result.power is not None
            else None,
            power=TimeSeriesRate.from_timeseries_stream_day_rate(consumer_result.power, regularity=regularity),
            energy_usage=TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.energy_usage, regularity=regularity
            ).to_calendar_day()
            if consumer_result.energy_usage.unit == Unit.STANDARD_CUBIC_METER_PER_DAY
            else TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.energy_usage, regularity=regularity
            ).to_stream_day(),
            periods=consumer_result.periods,
            id=consumer_result.id,
            is_valid=model.get_validity(consumer_node_info.id),
            operational_settings_used=consumer_result.operational_settings_used,
            operational_settings_results=None,
        )


class CompressorHelper:
    """
    A helper class for processing compressor-related data and results.

    This class provides static methods to:
    - Retrieve requested compressor pressures.
    - Process stage results for compressors.
    - Process inlet and outlet stream conditions for compressors.
    """

    @staticmethod  # type: ignore[misc]
    @Feature.experimental(feature_description="Reporting requested pressures is an experimental feature.")
    def get_requested_compressor_pressures(
        energy_usage_model: TemporalModel[ConsumerSystemConsumerFunction],
        pressure_type: CompressorPressureType,
        name: str,
        model_periods: Periods,
        operational_settings_used: TimeSeriesInt | None = None,
    ) -> TimeSeriesFloat:
        """Get temporal model for compressor inlet- and outlet pressures.

        The pressures are the actual pressures defined by user in input.

        Args:
            energy_usage_model (Dict[Period, Any]): Temporal energy model.
            pressure_type (CompressorPressureType): Compressor pressure type, inlet- or outlet.
            name (str): Name of compressor.
            model_periods (Periods): Actual periods in the model.
            operational_settings_used (Optional[TimeSeriesInt]): Time series indicating which priority is active.

        Returns:
            TemporalModel[Expression]: Temporal model with pressures as expressions.
        """
        periods = []
        values = []
        for period, model in energy_usage_model.items():
            # Loop periods in temporal model, to find correct operational settings used:
            periods_in_period = period.get_periods(model_periods)
            for _period in periods_in_period:
                for compressor in model.consumers:
                    if compressor.name == name:
                        operational_setting_used_id = OperationalSettingHelper.get_operational_setting_used_id(
                            period=_period,
                            operational_settings_used=operational_settings_used,  # type: ignore[arg-type]
                        )
                        operational_setting = model.operational_settings[operational_setting_used_id]

                        # Find correct compressor in case of different pressures for different components in system:
                        compressor_nr = int(
                            [i for i, compressor in enumerate(model.consumers) if compressor.name == name][0]
                        )

                        if pressure_type.value == CompressorPressureType.INLET_PRESSURE:
                            pressures = operational_setting.suction_pressures[compressor_nr]
                        else:
                            pressures = operational_setting.discharge_pressures[compressor_nr]
                        if pressures is not None:
                            try:
                                idx = pressures.get_periods().periods.index(_period)
                                value = float(pressures.get_values()[idx])
                            except ValueError:
                                value = math.nan
                        else:
                            value = math.nan
                        periods.append(_period)
                        values.append(value)
        return TimeSeriesFloat(
            periods=Periods(periods),
            values=values,
            unit=Unit.BARA,
        )

    @staticmethod
    def process_stage_results(
        model: CompressorTrainResult,
        regularity: TimeSeriesFloat,
        periods: Periods,
    ) -> list[CompressorModelStageResult]:
        model_stage_results = []
        # Convert rates in stage results from lists to time series:
        for i, stage_result in enumerate(model.stage_results):
            model_stage_result = CompressorModelStageResult(
                chart=ChartDTO.from_domain(stage_result.chart) if stage_result.chart is not None else None,
                chart_area_flags=list(stage_result.chart_area_flags),
                energy_usage_unit=stage_result.energy_usage_unit,
                power_unit=stage_result.power_unit,
                fluid_composition=stage_result.fluid_composition,
                asv_recirculation_loss_mw=TimeSeriesHelper.initialize_timeseries(
                    periods=periods,
                    values=stage_result.asv_recirculation_loss_mw,
                    unit=Unit.MEGA_WATT,
                    rate_type=RateType.STREAM_DAY,
                    regularity=regularity,
                ),
                head_exceeds_maximum=TimeSeriesHelper.initialize_timeseries_bool(
                    periods=periods,
                    values=stage_result.head_exceeds_maximum,
                ),
                is_valid=TimeSeriesHelper.initialize_timeseries_bool(
                    periods=periods,
                    values=stage_result.is_valid,
                ),
                polytropic_efficiency=TimeSeriesHelper.initialize_timeseries(
                    periods=periods, values=stage_result.polytropic_efficiency, unit=Unit.FRACTION
                ),
                polytropic_enthalpy_change_before_choke_kJ_per_kg=TimeSeriesHelper.initialize_timeseries(
                    periods=periods,
                    values=stage_result.polytropic_enthalpy_change_before_choke_kJ_per_kg,
                    unit=Unit.POLYTROPIC_HEAD_KILO_JOULE_PER_KG,
                ),
                polytropic_enthalpy_change_kJ_per_kg=TimeSeriesHelper.initialize_timeseries(
                    periods=periods,
                    values=stage_result.polytropic_enthalpy_change_kJ_per_kg,
                    unit=Unit.POLYTROPIC_HEAD_KILO_JOULE_PER_KG,
                ),
                polytropic_head_kJ_per_kg=TimeSeriesHelper.initialize_timeseries(
                    periods=periods,
                    values=stage_result.polytropic_head_kJ_per_kg,
                    unit=Unit.POLYTROPIC_HEAD_KILO_JOULE_PER_KG,
                ),
                energy_usage=TimeSeriesHelper.initialize_timeseries(
                    periods=periods,
                    values=stage_result.energy_usage,
                    unit=stage_result.energy_usage_unit,
                    rate_type=RateType.STREAM_DAY,
                    regularity=regularity,
                ),
                mass_rate_kg_per_hr=TimeSeriesHelper.initialize_timeseries(
                    periods=periods,
                    values=stage_result.mass_rate_kg_per_hr,
                    unit=Unit.KILO_PER_HOUR,
                ),
                mass_rate_before_asv_kg_per_hr=TimeSeriesHelper.initialize_timeseries(
                    periods=periods, values=stage_result.mass_rate_before_asv_kg_per_hr, unit=Unit.KILO_PER_HOUR
                ),
                power=TimeSeriesHelper.initialize_timeseries(
                    periods=periods,
                    values=stage_result.power,
                    unit=stage_result.power_unit,
                    rate_type=RateType.STREAM_DAY,
                    regularity=regularity,
                ),
                pressure_is_choked=TimeSeriesHelper.initialize_timeseries_bool(
                    periods=periods,
                    values=stage_result.pressure_is_choked,
                ),
                rate_exceeds_maximum=TimeSeriesHelper.initialize_timeseries_bool(
                    periods=periods,
                    values=stage_result.rate_exceeds_maximum,
                ),
                rate_has_recirculation=TimeSeriesHelper.initialize_timeseries_bool(
                    periods=periods,
                    values=stage_result.rate_has_recirculation,
                ),
                speed=TimeSeriesHelper.initialize_timeseries(
                    periods=periods, values=stage_result.speed, unit=Unit.SPEED_RPM
                ),
                inlet_stream_condition=CompressorHelper.process_inlet_stream_condition(
                    periods, stage_result.inlet_stream_condition, regularity
                ),
                outlet_stream_condition=CompressorHelper.process_outlet_stream_condition(
                    periods, stage_result.outlet_stream_condition, regularity
                ),
                name=f"Stage {i + 1}",
                periods=periods,
            )
            model_stage_results.append(model_stage_result)
        return model_stage_results

    @staticmethod
    def process_inlet_stream_condition(
        periods: Periods, inlet_stream_condition: CompressorStreamCondition, regularity: TimeSeriesFloat
    ) -> CompressorStreamConditionResult:
        return CompressorStreamConditionResult(
            actual_rate_m3_per_hr=TimeSeriesHelper.initialize_timeseries(
                periods=periods,
                values=inlet_stream_condition.actual_rate_m3_per_hr,
                unit=Unit.ACTUAL_VOLUMETRIC_M3_PER_HOUR,
            ),
            actual_rate_before_asv_m3_per_hr=TimeSeriesHelper.initialize_timeseries(
                periods=periods,
                values=inlet_stream_condition.actual_rate_before_asv_m3_per_hr,
                unit=Unit.ACTUAL_VOLUMETRIC_M3_PER_HOUR,
            ),  # not relevant for compressor train, only for stage
            standard_rate_sm3_per_day=TimeSeriesHelper.initialize_timeseries(
                periods=periods,
                values=inlet_stream_condition.standard_rate_sm3_per_day,
                unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                rate_type=RateType.STREAM_DAY,
                regularity=regularity,
            ),
            standard_rate_before_asv_sm3_per_day=TimeSeriesHelper.initialize_timeseries(
                periods=periods,
                values=inlet_stream_condition.standard_rate_before_asv_sm3_per_day,
                unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                rate_type=RateType.STREAM_DAY,
                regularity=regularity,
            ),  # not relevant for compressor train, only for stage
            kappa=TimeSeriesHelper.initialize_timeseries(
                periods=periods, values=inlet_stream_condition.kappa, unit=Unit.NONE
            ),
            density_kg_per_m3=TimeSeriesHelper.initialize_timeseries(
                periods=periods, values=inlet_stream_condition.density_kg_per_m3, unit=Unit.KG_M3
            ),
            pressure=TimeSeriesHelper.initialize_timeseries(
                periods=periods, values=inlet_stream_condition.pressure, unit=Unit.BARA
            ),
            temperature_kelvin=TimeSeriesHelper.initialize_timeseries(
                periods=periods, values=inlet_stream_condition.temperature_kelvin, unit=Unit.KELVIN
            ),
            z=TimeSeriesHelper.initialize_timeseries(periods=periods, values=inlet_stream_condition.z, unit=Unit.NONE),
            periods=periods,
            name="Inlet stream condition",
        )

    @staticmethod
    def process_outlet_stream_condition(
        periods: Periods, outlet_stream_condition: CompressorStreamCondition, regularity: TimeSeriesFloat
    ) -> CompressorStreamConditionResult:
        return CompressorStreamConditionResult(
            actual_rate_m3_per_hr=TimeSeriesHelper.initialize_timeseries(
                periods=periods,
                values=outlet_stream_condition.actual_rate_m3_per_hr,
                unit=Unit.ACTUAL_VOLUMETRIC_M3_PER_HOUR,
            ),
            actual_rate_before_asv_m3_per_hr=TimeSeriesHelper.initialize_timeseries(
                periods=periods,
                values=outlet_stream_condition.actual_rate_before_asv_m3_per_hr,
                unit=Unit.ACTUAL_VOLUMETRIC_M3_PER_HOUR,
            ),  # not relevant for compressor train, only for stage
            standard_rate_sm3_per_day=TimeSeriesHelper.initialize_timeseries(
                periods=periods,
                values=outlet_stream_condition.standard_rate_sm3_per_day,
                unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                rate_type=RateType.STREAM_DAY,
                regularity=regularity,
            ),
            standard_rate_before_asv_sm3_per_day=TimeSeriesHelper.initialize_timeseries(
                periods=periods,
                values=outlet_stream_condition.standard_rate_before_asv_sm3_per_day,
                unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                rate_type=RateType.STREAM_DAY,
                regularity=regularity,
            ),  # not relevant for compressor train, only for stage
            kappa=TimeSeriesHelper.initialize_timeseries(
                periods=periods, values=outlet_stream_condition.kappa, unit=Unit.NONE
            ),
            density_kg_per_m3=TimeSeriesHelper.initialize_timeseries(
                periods=periods, values=outlet_stream_condition.density_kg_per_m3, unit=Unit.KG_M3
            ),
            pressure=TimeSeriesHelper.initialize_timeseries(
                periods=periods, values=outlet_stream_condition.pressure, unit=Unit.BARA
            ),
            temperature_kelvin=TimeSeriesHelper.initialize_timeseries(
                periods=periods, values=outlet_stream_condition.temperature_kelvin, unit=Unit.KELVIN
            ),
            z=TimeSeriesHelper.initialize_timeseries(periods=periods, values=outlet_stream_condition.z, unit=Unit.NONE),
            periods=periods,
            name="Outlet stream condition",
        )


class EmissionHelper:
    """
    A helper class for processing emission-related data and results.

    This class provides static methods to:
    - Convert partial emission results to full emission results.
    - Parse emissions from core result format to DTO result format.
    - Process venting emitters results.
    """

    @staticmethod
    def to_full_result(
        emissions: dict[str, PartialEmissionResult],
    ) -> dict[str, EmissionResult]:
        """
        From the partial result, generate cumulatives for the full emissions result per installation
        Args:
            emissions:

        Returns:

        """
        return {
            key: EmissionResult(
                name=key,
                periods=emissions[key].periods,
                rate=emissions[key].rate,
                cumulative=emissions[key].rate.to_volumes().cumulative(),
            )
            for key in emissions
        }

    @staticmethod
    def parse_emissions(
        emissions: dict[str, TimeSeriesStreamDayRate], regularity: TimeSeriesFloat
    ) -> dict[str, EmissionResult]:
        """
        Convert emissions from core result format to dto result format.

        Given that core result does NOT have regularity, that needs to be added
        Args:
            emissions:
            regularity:

        Returns:

        """
        return {
            key: EmissionResult(
                name=key,
                periods=emissions[key].periods,
                rate=TimeSeriesRate.from_timeseries_stream_day_rate(
                    emissions[key], regularity=regularity
                ).to_calendar_day(),
                cumulative=TimeSeriesRate.from_timeseries_stream_day_rate(emissions[key], regularity=regularity)
                .to_volumes()
                .cumulative(),
            )
            for key in emissions
        }

    @staticmethod
    def process_venting_emitters_result(
        graph_result: GraphResult,
        asset: Asset,
        regularities: dict[str, TimeSeriesFloat],
        sub_components: list[JsonResultComponentResult],
        time_series_zero: TimeSeriesRate,
    ):
        for installation in asset.installations:
            for venting_emitter in installation.venting_emitters:
                energy_usage = time_series_zero
                sub_components.append(
                    libecalc.presentation.json_result.result.VentingEmitterResult(
                        id=venting_emitter.id,
                        name=venting_emitter.name,
                        componentType=venting_emitter.component_type,
                        component_level=ComponentLevel.CONSUMER,
                        parent=installation.id,
                        emissions=EmissionHelper.parse_emissions(
                            graph_result.emission_results[venting_emitter.id], regularities[installation.id]
                        ),
                        periods=graph_result.variables_map.get_periods(),
                        is_valid=TimeSeriesBoolean(
                            periods=graph_result.variables_map.get_periods(),
                            values=[True] * graph_result.variables_map.number_of_periods,
                            unit=Unit.NONE,
                        ),
                        energy_usage=energy_usage,
                        energy_usage_cumulative=energy_usage.to_volumes().cumulative(),
                    )
                )


class TimeSeriesHelper:
    """
    A helper class for initializing and converting time series data.

    This class provides static methods to:
    - Convert emission results to time series format.
    - Initialize time series with given periods, values, and units.
    - Convert time series to cumulative values.
    """

    @staticmethod
    def convert_to_timeseries(
        graph_result: GraphResult,
        emission_core_results: dict[str, dict[str, TimeSeriesStreamDayRate]],
        regularities: TimeSeriesFloat | dict[str, TimeSeriesFloat],
    ) -> dict[str, dict[str, PartialEmissionResult]]:
        """
        Emissions by consumer id and emission name
        Args:
            graph_result:
            emission_core_results:
            regularities:

        Returns:

        """
        dto_result: dict[str, dict[str, PartialEmissionResult]] = {}

        for consumer_id, emissions in emission_core_results.items():
            installation_id = graph_result.graph.get_parent_installation_id(consumer_id)
            dto_result[consumer_id] = defaultdict()

            if isinstance(regularities, dict):
                regularity = regularities[installation_id]
            else:
                regularity = regularities

            for emission_name, emission_rate in emissions.items():
                dto_result[consumer_id][emission_name] = PartialEmissionResult.from_emission_core_result(
                    emission_rate, emission_name=emission_name, regularity=regularity
                )

        return dto_result

    @staticmethod
    def initialize_timeseries_bool(
        values: Sequence[bool],
        periods: Periods,
    ) -> TimeSeriesBoolean:
        if not isinstance(values, list):
            if isinstance(values, np.ndarray):
                values = values.tolist()
            else:
                values = list(values)

        return TimeSeriesBoolean(
            periods=periods,
            values=values,
            unit=Unit.NONE,
        )

    @staticmethod
    def initialize_timeseries_rate_from_quantity(
        quantity: Quantity, periods: Periods, rate_type: RateType, regularity: list[float]
    ) -> TimeSeriesRate:
        return TimeSeriesRate(
            periods=periods,
            values=quantity.values,
            unit=quantity.unit,
            rate_type=rate_type,
            regularity=regularity,
        )

    @staticmethod
    def initialize_timeseries_float_from_quantity(quantity: Quantity, periods: Periods) -> TimeSeriesFloat:
        return TimeSeriesFloat(
            periods=periods,
            values=quantity.values,
            unit=quantity.unit,
        )

    @staticmethod
    def initialize_timeseries(
        periods: Periods,
        values: Sequence[float] | list[float] | np.ndarray | TimeSeriesFloat | TimeSeriesRate | None,
        unit: Unit,
        rate_type: RateType = None,
        regularity: TimeSeriesFloat | list[float] = None,
    ) -> TimeSeriesFloat | TimeSeriesRate:
        if values is None:
            values = [np.nan] * len(periods)
        elif isinstance(values, np.ndarray):
            values = values.tolist()
        elif (
            isinstance(values, TimeSeriesFloat)
            or isinstance(values, TimeSeriesRate)
            or isinstance(values, TimeSeriesBoolean)
        ):
            return values
        else:
            if not isinstance(values, list):
                values = list(values)

        values = cast(list[float], values)

        if rate_type:
            if isinstance(regularity, list):
                regularity_values = regularity
            elif regularity and hasattr(regularity, "for_periods"):
                regularity_values = regularity.for_periods(periods).values
            else:
                regularity_values = None

            return TimeSeriesRate(
                periods=periods,
                values=values,
                unit=unit,
                rate_type=rate_type,
                regularity=regularity_values,
            )
        else:
            return TimeSeriesFloat(
                periods=periods,
                values=values,
                unit=unit,
            )

    @staticmethod
    def convert_to_cumulative(
        unit: Unit,
        timeseries: TimeSeriesRate | None = None,
    ) -> TimeSeriesRate | None:
        return timeseries.to_volumes().to_unit(unit).cumulative() if timeseries else None


class InstallationHelper:
    """
    A helper class for evaluating and aggregating installation results.

    This class provides static methods to:
    - Evaluate installations and collect results.
    - Sum attribute values from a list of InstallationResult objects.
    - Compute aggregated power for installations.
    """

    @staticmethod
    def evaluate_installations(
        model: YamlModel,
        parent_id: str,
    ) -> list[InstallationResult]:
        """
        All subcomponents have already been evaluated, here we basically collect and aggregate the results
        """
        graph_result = model.get_graph_result()
        installation_results = []
        for installation in model.get_installations():
            assert isinstance(installation, InstallationComponent)
            expression_evaluator = installation.expression_evaluator
            regularity = installation.regularity
            hydrocarbon_export_rate = installation.evaluated_hydrocarbon_export_rate

            sub_components = [
                graph_result.get_energy_result(component_id)
                for component_id in graph_result.graph.get_successors(installation.id, recursively=True)
                if component_id in graph_result.consumer_results
            ]

            power_components = [
                graph_result.get_energy_result(component_id)
                for component_id in graph_result.graph.get_successors(installation.id, recursively=False)
                if component_id in graph_result.consumer_results
            ]

            electrical_components = []
            fuel_components = []

            for component in power_components:
                if graph_result.graph.get_node_info(component.id).component_type == ComponentType.GENERATOR_SET:
                    electrical_components.append(component)
                else:
                    fuel_components.append(component)

            installation_node_info = graph_result.graph.get_node_info(installation.id)

            power_electrical = InstallationHelper.compute_aggregated_power(
                graph_result=graph_result,
                power_components=electrical_components,
                regularity=regularity.time_series,
            )

            power_mechanical = InstallationHelper.compute_aggregated_power(
                graph_result=graph_result,
                power_components=fuel_components,
                regularity=regularity.time_series,
            )

            power = power_electrical + power_mechanical

            energy_usage = (
                reduce(
                    operator.add,
                    [
                        TimeSeriesRate.from_timeseries_stream_day_rate(
                            component.energy_usage, regularity=regularity.time_series
                        )
                        for component in sub_components
                        if component.energy_usage.unit == Unit.STANDARD_CUBIC_METER_PER_DAY
                    ],
                )
                if sub_components
                else 0
            )

            emission_dto_results = TimeSeriesHelper.convert_to_timeseries(
                graph_result,
                graph_result.emission_results,
                regularity.time_series,
            )
            aggregated_emissions = aggregate_emissions(
                [
                    emission_dto_results[fuel_consumer_id]
                    for fuel_consumer_id in graph_result.graph.get_successors(installation.id)
                ]
            )

            installation_results.append(
                libecalc.presentation.json_result.result.InstallationResult(
                    id=installation.id,
                    name=installation_node_info.name,
                    parent=parent_id,
                    component_level=installation_node_info.component_level,
                    componentType=installation_node_info.component_type,
                    periods=expression_evaluator.get_periods(),
                    is_valid=model.get_validity(installation.id),
                    power=power,
                    power_cumulative=power.to_volumes().to_unit(Unit.GIGA_WATT_HOURS).cumulative(),
                    power_electrical=power_electrical,
                    power_electrical_cumulative=power_electrical.to_volumes()
                    .to_unit(Unit.GIGA_WATT_HOURS)
                    .cumulative(),
                    power_mechanical=power_mechanical,
                    power_mechanical_cumulative=power_mechanical.to_volumes()
                    .to_unit(Unit.GIGA_WATT_HOURS)
                    .cumulative(),
                    energy_usage=energy_usage.to_calendar_day()
                    if energy_usage.unit == Unit.STANDARD_CUBIC_METER_PER_DAY
                    else energy_usage.to_stream_day(),
                    energy_usage_cumulative=energy_usage.to_volumes().cumulative(),
                    hydrocarbon_export_rate=hydrocarbon_export_rate,
                    emissions=EmissionHelper.to_full_result(aggregated_emissions),
                    regularity=regularity.time_series,
                )
            ) if sub_components else None
        return installation_results

    @staticmethod
    def sum_installation_attribute_values(
        installation_results: list[InstallationResult], attribute: str, default_value: TimeSeriesRate | None = None
    ) -> TimeSeriesRate | None:
        """
        Combines the specified attribute values from a list of InstallationResult objects using addition.
        If the list is empty, returns the default value.
        """

        return (
            reduce(
                operator.add,
                [
                    getattr(installation, attribute)
                    for installation in installation_results
                    if getattr(installation, attribute) is not None
                ],
            )
            if installation_results
            else default_value
        )

    @staticmethod
    def compute_aggregated_power(
        graph_result: GraphResult,
        regularity: TimeSeriesFloat,
        power_components: list,
    ):
        return reduce(
            operator.add,
            [
                TimeSeriesRate.from_timeseries_stream_day_rate(component.power, regularity=regularity)
                for component in power_components
                if component.power is not None
            ],
            TimeSeriesHelper.initialize_timeseries(
                values=[0.0] * graph_result.variables_map.number_of_periods,
                periods=graph_result.variables_map.periods,
                unit=Unit.MEGA_WATT,
                rate_type=RateType.STREAM_DAY,
                regularity=regularity.values,
            ),  # Initial value, handle no power output from components
        )


class OperationalSettingHelper:
    @staticmethod
    def get_operational_setting_used_id(period: Period, operational_settings_used: TimeSeriesInt) -> int:
        period_index = operational_settings_used.periods.periods.index(period)

        operational_setting_id = operational_settings_used.values[period_index]

        return operational_setting_id - 1


def get_asset_result(model: YamlModel) -> libecalc.presentation.json_result.result.results.EcalcModelResult:
    graph_result = model.get_graph_result()
    asset_id = graph_result.graph.root
    asset = graph_result.graph.get_node(asset_id)

    if not isinstance(asset, Asset):
        raise ProgrammingError("Need an asset graph to get asset result")

    # Start processing installation results
    installation_results = InstallationHelper.evaluate_installations(
        model=model,
        parent_id=asset_id,
    )

    regularities: dict[str, TimeSeriesFloat] = {
        installation.id: installation.regularity for installation in installation_results
    }

    models: list[CompressorModelResult | PumpModelResult | GenericModelResult] = []
    sub_components: list[JsonResultComponentResult] = [*installation_results]
    for consumer_result in graph_result.consumer_results.values():
        consumer_id = consumer_result.id
        consumer_node_info = graph_result.graph.get_node_info(consumer_id)

        parent_installation_id = graph_result.graph.get_parent_installation_id(consumer_id)
        regularity: TimeSeriesFloat = regularities[parent_installation_id]

        sub_component: JsonResultComponentResult
        if isinstance(consumer_result, CompressorResult):
            sub_component = ComponentResultHelper.process_compressor_component_result(
                model, consumer_result, consumer_node_info, regularity
            )
            models.extend(
                ModelResultHelper.process_compressor_models(
                    graph_result, consumer_result, consumer_id, consumer_node_info, regularity
                )
            )
        elif isinstance(consumer_result, PumpResult):
            sub_component = ComponentResultHelper.process_pump_component_result(
                model, consumer_result, consumer_node_info, regularity
            )
            models.extend(
                ModelResultHelper.process_pump_models(
                    consumer_result=consumer_result, node_info=consumer_node_info, regularity=regularity
                )
            )
        elif isinstance(consumer_result, CoreConsumerSystemResult):
            sub_component = ComponentResultHelper.process_consumer_system_component_result(
                model, consumer_result, consumer_node_info, regularity
            )
            if consumer_node_info.component_type == ComponentType.COMPRESSOR_SYSTEM:
                models.extend(
                    ModelResultHelper.process_compressor_models(
                        graph_result, consumer_result, consumer_id, consumer_node_info, regularity
                    )
                )
            else:
                assert consumer_node_info.component_type == ComponentType.PUMP_SYSTEM
                models.extend(
                    ModelResultHelper.process_pump_models(
                        consumer_result=consumer_result, node_info=consumer_node_info, regularity=regularity
                    )
                )
        elif isinstance(
            consumer_result,
            CoreGenericComponentResult,
        ):
            sub_component = ComponentResultHelper.process_generic_component_result(
                model, consumer_result, consumer_node_info, regularity
            )
            models.extend(
                ModelResultHelper.process_generic_models(
                    consumer_result=consumer_result, node_info=consumer_node_info, regularity=regularity
                )
            )

        elif isinstance(consumer_result, GeneratorSetResult):
            sub_component = ComponentResultHelper.process_generator_set_result(
                model, consumer_result, consumer_node_info, regularity
            )
        else:
            assert_never(consumer_result)

        sub_components.append(sub_component)

    # When only venting emitters are specified, without a generator set: the installation result
    # is empty for this installation. Ensure that the installation regularity is found, even if only
    # venting emitters are defined for one installation:
    if len(installation_results) < len(asset.installations):
        regularities = {installation.id: installation.regularity.time_series for installation in asset.installations}

    time_series_zero = TimeSeriesHelper.initialize_timeseries(
        values=[0] * graph_result.variables_map.number_of_periods,
        periods=graph_result.variables_map.get_periods(),
        unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
        rate_type=RateType.CALENDAR_DAY,
        regularity=[1] * graph_result.variables_map.number_of_periods,
    )

    # Add venting emitters to sub_components:
    EmissionHelper.process_venting_emitters_result(graph_result, asset, regularities, sub_components, time_series_zero)  # type: ignore[arg-type]

    # Summing hydrocarbon export rates from all installations
    asset_hydrocarbon_export_rate_core = InstallationHelper.sum_installation_attribute_values(
        installation_results,
        "hydrocarbon_export_rate",
        time_series_zero,  # type: ignore[arg-type]
    )

    # Converting emission results to time series format
    emission_dto_results = TimeSeriesHelper.convert_to_timeseries(
        graph_result,
        graph_result.emission_results,
        regularities,
    )

    # Aggregating emissions from all installations
    asset_aggregated_emissions = aggregate_emissions(list(emission_dto_results.values()))

    # Summing power values from all installations
    asset_power_core = InstallationHelper.sum_installation_attribute_values(installation_results, "power")
    asset_power_electrical_core = InstallationHelper.sum_installation_attribute_values(
        installation_results, "power_electrical"
    )
    asset_power_mechanical_core = InstallationHelper.sum_installation_attribute_values(
        installation_results, "power_mechanical"
    )

    # Converting total power to cumulative values in Giga Watt Hours
    asset_power_cumulative = TimeSeriesHelper.convert_to_cumulative(Unit.GIGA_WATT_HOURS, asset_power_core)
    asset_power_electrical_cumulative = TimeSeriesHelper.convert_to_cumulative(
        Unit.GIGA_WATT_HOURS, asset_power_electrical_core
    )
    asset_power_mechanical_cumulative = TimeSeriesHelper.convert_to_cumulative(
        Unit.GIGA_WATT_HOURS, asset_power_mechanical_core
    )

    # Summing energy usage from all installations
    asset_energy_usage_core = InstallationHelper.sum_installation_attribute_values(
        installation_results,
        "energy_usage",
        time_series_zero,  # type: ignore[arg-type]
    )

    # Converting total energy usage to cumulative values
    asset_energy_usage_cumulative = asset_energy_usage_core.to_volumes().cumulative()

    asset_node_info = graph_result.graph.get_node_info(asset_id)
    asset_result_dto = AssetResult(
        id=asset.id,
        name=asset_node_info.name,
        component_level=asset_node_info.component_level,
        componentType=asset_node_info.component_type,
        periods=graph_result.variables_map.get_periods(),
        is_valid=model.get_validity(asset.id),
        power=asset_power_core,
        power_cumulative=asset_power_cumulative,
        power_electrical=asset_power_electrical_core,
        power_electrical_cumulative=asset_power_electrical_cumulative,
        power_mechanical=asset_power_mechanical_core,
        power_mechanical_cumulative=asset_power_mechanical_cumulative,
        energy_usage=asset_energy_usage_core,
        energy_usage_cumulative=asset_energy_usage_cumulative,
        hydrocarbon_export_rate=asset_hydrocarbon_export_rate_core,
        emissions=EmissionHelper.to_full_result(asset_aggregated_emissions),
    )

    return libecalc.presentation.json_result.result.results.EcalcModelResult(
        component_result=asset_result_dto,
        sub_components=sub_components,
        models=models,
    )
