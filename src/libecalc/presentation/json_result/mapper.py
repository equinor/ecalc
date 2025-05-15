import math
import operator
from collections import defaultdict
from functools import reduce
from typing import Any

import numpy as np

import libecalc
from libecalc.application.graph_result import GraphResult
from libecalc.common.component_info.component_level import ComponentLevel
from libecalc.common.component_info.compressor import CompressorPressureType
from libecalc.common.component_type import ComponentType
from libecalc.common.decorators.feature_flags import Feature
from libecalc.common.errors.exceptions import ProgrammingError
from libecalc.common.math.numbers import Numbers
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period, Periods
from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    RateType,
    TimeSeriesBoolean,
    TimeSeriesFloat,
    TimeSeriesInt,
    TimeSeriesRate,
)
from libecalc.core.result.emission import EmissionResult
from libecalc.core.result.results import EcalcModelResult
from libecalc.domain.emission.emission_intensity import EmissionIntensity
from libecalc.domain.infrastructure.energy_components.asset.asset import Asset
from libecalc.domain.process.dto.consumer_system import CompressorSystemConsumerFunction
from libecalc.dto import node_info
from libecalc.expression import Expression
from libecalc.presentation.json_result.aggregators import (
    aggregate_emissions,
    aggregate_is_valid,
)
from libecalc.presentation.json_result.result.emission import (
    EmissionIntensityResult,
    PartialEmissionResult,
)
from libecalc.presentation.json_result.result.results import (
    AssetResult,
    CompressorModelResult,
    CompressorModelStageResult,
    CompressorOperationalSettingResult,
    CompressorStreamConditionResult,
    GenericModelResult,
    InstallationResult,
    OperationalSettingResult,
    PumpModelResult,
    PumpOperationalSettingResult,
    TurbineModelResult,
)


class ModelResultHelper:
    """
    A helper class for mapping model results from core to structured results that can be used
    for e.g. reporting or further analysis.

    This class provides static methods to process compressor, pump, generic, and turbine models
    """

    @staticmethod
    def process_compressor_models(
        graph_result: GraphResult,
        consumer_result: EcalcModelResult,
        consumer_id: str,
        consumer_node_info: node_info.NodeInfo,
        regularity: TimeSeriesFloat,
    ) -> list[CompressorModelResult]:
        models = []
        component = graph_result.graph.get_node(consumer_id)

        for model in consumer_result.models:
            period = model.periods.period

            inlet_pressure_eval = CompressorHelper.get_requested_compressor_pressures(
                energy_usage_model=component.energy_usage_model,
                pressure_type=CompressorPressureType.INLET_PRESSURE,
                name=model.name,
                operational_settings_used=consumer_result.component_result.operational_settings_used
                if consumer_node_info.component_type == ComponentType.COMPRESSOR_SYSTEM
                else None,
                model_periods=model.periods,
            )
            outlet_pressure_eval = CompressorHelper.get_requested_compressor_pressures(
                energy_usage_model=component.energy_usage_model,
                pressure_type=CompressorPressureType.OUTLET_PRESSURE,
                name=model.name,
                operational_settings_used=consumer_result.component_result.operational_settings_used
                if consumer_node_info.component_type == ComponentType.COMPRESSOR_SYSTEM
                else None,
                model_periods=model.periods,
            )

            requested_inlet_pressure = TimeSeriesHelper.initialize_timeseries(
                periods=graph_result.variables_map.get_periods(),
                values=graph_result.variables_map.evaluate(inlet_pressure_eval).tolist(),
                unit=Unit.BARA,
            ).for_period(period=period)

            requested_outlet_pressure = TimeSeriesHelper.initialize_timeseries(
                periods=graph_result.variables_map.get_periods(),
                values=graph_result.variables_map.evaluate(outlet_pressure_eval).tolist(),
                unit=Unit.BARA,
            ).for_period(period=period)

            model_stage_results = CompressorHelper.process_stage_results(model, regularity)
            turbine_result = ModelResultHelper.process_turbine_result(model, regularity)

            inlet_stream_condition = CompressorHelper.process_inlet_stream_condition(
                model.periods, model.inlet_stream_condition, regularity
            )

            outlet_stream_condition = CompressorHelper.process_outlet_stream_condition(
                model.periods, model.outlet_stream_condition, regularity
            )

            # Handle multi stream
            # Select the first rate from multi stream, only a workaround until we have more info by using
            # streams
            if len(model.rate_sm3_day) > 0 and isinstance(model.rate_sm3_day[0], list):
                rate = TimeSeriesHelper.initialize_timeseries(
                    periods=model.periods,
                    values=model.rate_sm3_day[0],
                    unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                    rate_type=RateType.STREAM_DAY,
                    regularity=regularity.for_periods(model.periods).values,
                )
                maximum_rate = TimeSeriesHelper.initialize_timeseries(
                    periods=model.periods,
                    values=model.max_standard_rate  # WORKAROUND: We now only return a single max rate - for one stream only
                    if model.max_standard_rate is not None
                    else [math.nan] * len(model.periods),
                    unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                    rate_type=RateType.STREAM_DAY,
                    regularity=regularity.for_periods(model.periods).values,
                )
            else:
                rate = TimeSeriesHelper.initialize_timeseries(
                    periods=model.periods,
                    values=model.rate_sm3_day,
                    unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                    rate_type=RateType.STREAM_DAY,
                    regularity=regularity.for_periods(model.periods).values,
                )
                maximum_rate = TimeSeriesHelper.initialize_timeseries(
                    periods=model.periods,
                    values=model.max_standard_rate
                    if model.max_standard_rate is not None
                    else [math.nan] * len(model.periods),
                    unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                    rate_type=RateType.STREAM_DAY,
                    regularity=regularity.for_periods(model.periods).values,
                )

            models.append(
                CompressorModelResult(
                    parent=consumer_id,
                    name=model.name,
                    componentType=model.component_type.value,
                    component_level=ComponentLevel.MODEL,
                    energy_usage=TimeSeriesRate.from_timeseries_stream_day_rate(
                        model.energy_usage, regularity=regularity
                    ),
                    requested_inlet_pressure=requested_inlet_pressure,
                    requested_outlet_pressure=requested_outlet_pressure,
                    rate=rate,
                    maximum_rate=maximum_rate,
                    stage_results=model_stage_results,
                    failure_status=model.failure_status,
                    periods=model.periods,
                    is_valid=model.is_valid,
                    energy_usage_cumulative=TimeSeriesRate.from_timeseries_stream_day_rate(
                        model.energy_usage, regularity=regularity
                    )
                    .to_volumes()
                    .cumulative(),
                    power_cumulative=TimeSeriesRate.from_timeseries_stream_day_rate(model.power, regularity=regularity)
                    .to_volumes()
                    .to_unit(Unit.GIGA_WATT_HOURS)
                    .cumulative()
                    if model.power is not None
                    else None,
                    power=TimeSeriesRate.from_timeseries_stream_day_rate(model.power, regularity=regularity)
                    if model.power is not None
                    else None,
                    turbine_result=turbine_result,
                    inlet_stream_condition=inlet_stream_condition,
                    outlet_stream_condition=outlet_stream_condition,
                )
            )
        return models

    @staticmethod
    def process_pump_models(
        consumer_result: EcalcModelResult, consumer_id: str, regularity: TimeSeriesFloat
    ) -> list[PumpModelResult]:
        models = []
        for model in consumer_result.models:
            models.append(
                PumpModelResult(
                    parent=consumer_id,
                    name=model.name,
                    componentType=model.component_type.value,
                    component_level=ComponentLevel.MODEL,
                    energy_usage=TimeSeriesRate.from_timeseries_stream_day_rate(
                        model.energy_usage, regularity=regularity
                    ),
                    is_valid=model.is_valid,
                    energy_usage_cumulative=TimeSeriesRate.from_timeseries_stream_day_rate(
                        model.energy_usage, regularity=regularity
                    )
                    .to_volumes()
                    .cumulative(),
                    periods=model.periods,
                    power_cumulative=(
                        TimeSeriesRate.from_timeseries_stream_day_rate(model.power, regularity=regularity)
                        .to_volumes()
                        .to_unit(Unit.GIGA_WATT_HOURS)
                        .cumulative()
                        if model.power is not None
                        else None
                    ),
                    power=TimeSeriesRate.from_timeseries_stream_day_rate(model.power, regularity=regularity)
                    if model.power is not None
                    else None,
                    inlet_liquid_rate_m3_per_day=TimeSeriesHelper.initialize_timeseries(
                        periods=model.periods,
                        values=model.inlet_liquid_rate_m3_per_day,
                        unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                        rate_type=RateType.STREAM_DAY,
                        regularity=regularity,
                    ),
                    inlet_pressure_bar=TimeSeriesHelper.initialize_timeseries(
                        periods=model.periods, values=model.inlet_pressure_bar, unit=Unit.BARA
                    ),
                    outlet_pressure_bar=TimeSeriesHelper.initialize_timeseries(
                        periods=model.periods, values=model.outlet_pressure_bar, unit=Unit.BARA
                    ),
                    operational_head=TimeSeriesHelper.initialize_timeseries(
                        periods=model.periods, values=model.operational_head, unit=Unit.POLYTROPIC_HEAD_JOULE_PER_KG
                    ),
                )
            )
        return models

    @staticmethod
    def process_generic_models(
        consumer_result: EcalcModelResult, consumer_id: str, regularity: TimeSeriesFloat
    ) -> list[GenericModelResult]:
        models = []
        for model in consumer_result.models:
            models.append(
                GenericModelResult(
                    parent=consumer_id,
                    name=model.name,
                    componentType=model.component_type.value,
                    component_level=ComponentLevel.MODEL,
                    periods=model.periods,
                    is_valid=model.is_valid,
                    energy_usage_cumulative=TimeSeriesRate.from_timeseries_stream_day_rate(
                        model.energy_usage, regularity=regularity
                    )
                    .to_volumes()
                    .cumulative(),
                    power_cumulative=(
                        TimeSeriesRate.from_timeseries_stream_day_rate(model.power, regularity=regularity)
                        .to_volumes()
                        .to_unit(Unit.GIGA_WATT_HOURS)
                        .cumulative()
                        if model.power is not None
                        else None
                    ),
                    power=TimeSeriesRate.from_timeseries_stream_day_rate(model.power, regularity=regularity),
                    energy_usage=TimeSeriesRate.from_timeseries_stream_day_rate(
                        model.energy_usage, regularity=regularity
                    ),
                )
            )
        return models

    @staticmethod
    def process_turbine_result(model, regularity):
        if model.turbine_result is None:
            return None

        return TurbineModelResult(
            energy_usage_unit=model.turbine_result.energy_usage_unit,
            power_unit=model.turbine_result.power_unit,
            efficiency=TimeSeriesHelper.initialize_timeseries(
                periods=model.periods, values=model.turbine_result.efficiency, unit=Unit.FRACTION
            ),
            energy_usage=TimeSeriesHelper.initialize_timeseries(
                periods=model.periods,
                values=model.turbine_result.energy_usage,
                unit=model.turbine_result.energy_usage_unit,
                rate_type=RateType.STREAM_DAY,
                regularity=regularity,
            ),
            exceeds_maximum_load=TimeSeriesHelper.initialize_timeseries(
                periods=model.periods, values=model.turbine_result.exceeds_maximum_load, unit=Unit.NONE
            ),
            fuel_rate=TimeSeriesHelper.initialize_timeseries(
                periods=model.periods,
                values=model.turbine_result.fuel_rate,
                unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                rate_type=RateType.STREAM_DAY,
                regularity=regularity,
            ),
            is_valid=TimeSeriesHelper.initialize_timeseries(
                periods=model.periods, values=model.turbine_result.is_valid, unit=Unit.NONE
            ),
            load=TimeSeriesHelper.initialize_timeseries(
                periods=model.periods,
                values=model.turbine_result.load,
                unit=model.turbine_result.energy_usage_unit,
                rate_type=RateType.STREAM_DAY,
                regularity=regularity,
            ),
            power=TimeSeriesHelper.initialize_timeseries(
                periods=model.periods,
                values=model.turbine_result.power,
                unit=model.turbine_result.power_unit,
                rate_type=RateType.STREAM_DAY,
                regularity=regularity,
            ),
            periods=model.periods,
            name=model.name,
        )


class ComponentResultHelper:
    """
    A helper class for mapping component results from core to structured resultsthat can be used
    for e.g. reporting or further analysis.

    This class provides static methods to process various component types, i.e. generator sets,
    pumps, compressors, generic components, and consumer systems.

    Component results are top level results for each component. Individual models for a given component
    are processed separately in the ModelResultHelper class
    """

    @staticmethod
    def process_generator_set_result(
        graph_result: GraphResult,
        consumer_result: Any,
        consumer_node_info: node_info.NodeInfo,
        regularity: TimeSeriesFloat,
    ) -> libecalc.presentation.json_result.result.results.GeneratorSetResult:
        return libecalc.presentation.json_result.result.results.GeneratorSetResult(
            name=consumer_node_info.name,
            parent=graph_result.graph.get_predecessor(consumer_result.component_result.id),
            component_level=consumer_node_info.component_level,
            componentType=consumer_node_info.component_type.value,
            emissions=EmissionHelper.parse_emissions(
                graph_result.emission_results[consumer_result.component_result.id], regularity
            )
            if consumer_result.component_result.id in graph_result.emission_results
            else {},
            energy_usage_cumulative=TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.component_result.energy_usage, regularity=regularity
            )
            .to_volumes()
            .cumulative(),
            power_cumulative=TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.component_result.power, regularity=regularity
            )
            .to_volumes()
            .to_unit(Unit.GIGA_WATT_HOURS)
            .cumulative()
            if consumer_result.component_result.power is not None
            else None,
            power=TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.component_result.power, regularity=regularity
            ),
            energy_usage=TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.component_result.energy_usage, regularity=regularity
            ).to_calendar_day()
            if consumer_result.component_result.energy_usage.unit == Unit.STANDARD_CUBIC_METER_PER_DAY
            else TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.component_result.energy_usage, regularity=regularity
            ).to_stream_day(),
            power_capacity_margin=TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.component_result.power_capacity_margin, regularity=regularity
            ),
            periods=consumer_result.component_result.periods,
            id=consumer_result.component_result.id,
            is_valid=consumer_result.component_result.is_valid,
        )

    @staticmethod
    def process_pump_component_result(
        graph_result: GraphResult,
        consumer_result: Any,
        consumer_node_info: node_info.NodeInfo,
        regularity: TimeSeriesFloat,
    ) -> libecalc.presentation.json_result.result.results.PumpResult:
        return libecalc.presentation.json_result.result.results.PumpResult(
            name=consumer_node_info.name,
            parent=graph_result.graph.get_predecessor(consumer_result.component_result.id),
            component_level=consumer_node_info.component_level,
            componentType=consumer_node_info.component_type.value,
            emissions=EmissionHelper.parse_emissions(
                graph_result.emission_results[consumer_result.component_result.id], regularity
            )
            if consumer_result.component_result.id in graph_result.emission_results
            else {},
            energy_usage_cumulative=TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.component_result.energy_usage, regularity=regularity
            )
            .to_volumes()
            .cumulative(),
            power_cumulative=TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.component_result.power, regularity=regularity
            )
            .to_volumes()
            .to_unit(Unit.GIGA_WATT_HOURS)
            .cumulative()
            if consumer_result.component_result.power is not None
            else None,
            power=TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.component_result.power, regularity=regularity
            ),
            energy_usage=TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.component_result.energy_usage, regularity=regularity
            ).to_calendar_day()
            if consumer_result.component_result.energy_usage.unit == Unit.STANDARD_CUBIC_METER_PER_DAY
            else TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.component_result.energy_usage, regularity=regularity
            ).to_stream_day(),
            inlet_liquid_rate_m3_per_day=TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.component_result.inlet_liquid_rate_m3_per_day, regularity=regularity
            ),
            inlet_pressure_bar=consumer_result.component_result.inlet_pressure_bar,
            outlet_pressure_bar=consumer_result.component_result.outlet_pressure_bar,
            operational_head=consumer_result.component_result.operational_head,
            periods=consumer_result.component_result.periods,
            id=consumer_result.component_result.id,
            is_valid=consumer_result.component_result.is_valid,
        )

    @staticmethod
    def process_compressor_component_result(
        graph_result: GraphResult,
        consumer_result: Any,
        consumer_node_info: node_info.NodeInfo,
        regularity: TimeSeriesFloat,
    ) -> libecalc.presentation.json_result.result.results.CompressorResult:
        return libecalc.presentation.json_result.result.results.CompressorResult(
            name=consumer_node_info.name,
            parent=graph_result.graph.get_predecessor(consumer_result.component_result.id),
            component_level=consumer_node_info.component_level,
            componentType=consumer_node_info.component_type.value,
            emissions=EmissionHelper.parse_emissions(
                graph_result.emission_results[consumer_result.component_result.id], regularity
            )
            if consumer_result.component_result.id in graph_result.emission_results
            else {},
            energy_usage_cumulative=TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.component_result.energy_usage, regularity=regularity
            )
            .to_volumes()
            .cumulative(),
            power_cumulative=TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.component_result.power, regularity=regularity
            )
            .to_volumes()
            .to_unit(Unit.GIGA_WATT_HOURS)
            .cumulative()
            if consumer_result.component_result.power is not None
            else None,
            power=TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.component_result.power, regularity=regularity
            ),
            energy_usage=TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.component_result.energy_usage, regularity=regularity
            ).to_calendar_day()
            if consumer_result.component_result.energy_usage.unit == Unit.STANDARD_CUBIC_METER_PER_DAY
            else TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.component_result.energy_usage, regularity=regularity
            ).to_stream_day(),
            recirculation_loss=TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.component_result.recirculation_loss, regularity=regularity
            ),
            rate_exceeds_maximum=consumer_result.component_result.rate_exceeds_maximum,
            periods=consumer_result.component_result.periods,
            id=consumer_result.component_result.id,
            is_valid=consumer_result.component_result.is_valid,
        )

    @staticmethod
    def process_generic_component_result(
        graph_result: GraphResult,
        consumer_result: Any,
        consumer_node_info: node_info.NodeInfo,
        regularity: TimeSeriesFloat,
    ) -> libecalc.presentation.json_result.result.GenericConsumerResult:
        consumer_id = consumer_result.component_result.id
        emissions = (
            EmissionHelper.parse_emissions(graph_result.emission_results[consumer_id], regularity)
            if consumer_id in graph_result.emission_results
            else {}
        )
        return libecalc.presentation.json_result.result.GenericConsumerResult(
            name=consumer_node_info.name,
            parent=graph_result.graph.get_predecessor(consumer_result.component_result.id),
            component_level=consumer_node_info.component_level,
            componentType=consumer_node_info.component_type.value,
            emissions=emissions,
            energy_usage_cumulative=TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.component_result.energy_usage, regularity=regularity
            )
            .to_volumes()
            .cumulative(),
            power_cumulative=TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.component_result.power, regularity=regularity
            )
            .to_volumes()
            .to_unit(Unit.GIGA_WATT_HOURS)
            .cumulative()
            if consumer_result.component_result.power is not None
            else None,
            power=TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.component_result.power, regularity=regularity
            ),
            energy_usage=TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.component_result.energy_usage, regularity=regularity
            ).to_calendar_day()
            if consumer_result.component_result.energy_usage.unit == Unit.STANDARD_CUBIC_METER_PER_DAY
            else TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.component_result.energy_usage, regularity=regularity
            ).to_stream_day(),
            periods=consumer_result.component_result.periods,
            id=consumer_result.component_result.id,
            is_valid=consumer_result.component_result.is_valid,
        )

    @staticmethod
    def process_consumer_system_component_result(
        graph_result: GraphResult,
        consumer_result: Any,
        consumer_node_info: node_info.NodeInfo,
        regularity: TimeSeriesFloat,
    ) -> libecalc.presentation.json_result.result.ConsumerSystemResult:
        consumer_id = consumer_result.component_result.id
        emissions = (
            EmissionHelper.parse_emissions(graph_result.emission_results[consumer_id], regularity)
            if consumer_id in graph_result.emission_results
            else {}
        )

        return libecalc.presentation.json_result.result.ConsumerSystemResult(
            name=consumer_node_info.name,
            parent=graph_result.graph.get_predecessor(consumer_result.component_result.id),
            component_level=consumer_node_info.component_level,
            componentType=consumer_node_info.component_type.value,
            emissions=emissions,
            energy_usage_cumulative=TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.component_result.energy_usage, regularity=regularity
            )
            .to_volumes()
            .cumulative(),
            power_cumulative=TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.component_result.power, regularity=regularity
            )
            .to_volumes()
            .to_unit(Unit.GIGA_WATT_HOURS)
            .cumulative()
            if consumer_result.component_result.power is not None
            else None,
            power=TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.component_result.power, regularity=regularity
            ),
            energy_usage=TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.component_result.energy_usage, regularity=regularity
            ).to_calendar_day()
            if consumer_result.component_result.energy_usage.unit == Unit.STANDARD_CUBIC_METER_PER_DAY
            else TimeSeriesRate.from_timeseries_stream_day_rate(
                consumer_result.component_result.energy_usage, regularity=regularity
            ).to_stream_day(),
            periods=consumer_result.component_result.periods,
            id=consumer_result.component_result.id,
            is_valid=consumer_result.component_result.is_valid,
            operational_settings_used=consumer_result.component_result.operational_settings_used,
            operational_settings_results=OperationalSettingHelper.process_operational_settings_results(
                operational_settings_results=consumer_result.component_result.operational_settings_results,
                regularity=regularity,
            ),
        )


class CompressorHelper:
    """
    A helper class for processing compressor-related data and results.

    This class provides static methods to:
    - Retrieve requested compressor pressures.
    - Process stage results for compressors.
    - Process inlet and outlet stream conditions for compressors.
    """

    @staticmethod
    @Feature.experimental(feature_description="Reporting requested pressures is an experimental feature.")
    def get_requested_compressor_pressures(
        energy_usage_model: dict[Period, Any],
        pressure_type: CompressorPressureType,
        name: str,
        model_periods: Periods,
        operational_settings_used: TimeSeriesInt | None = None,
    ) -> TemporalModel[Expression]:
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

        evaluated_temporal_energy_usage_models = {}

        for period, model in energy_usage_model.items():  # TODO: fix this
            if isinstance(model, CompressorSystemConsumerFunction):
                # Loop periods in temporal model, to find correct operational settings used:
                periods_in_period = period.get_periods(model_periods)
                for _period in periods_in_period:
                    for compressor in model.compressors:
                        if compressor.name == name:
                            operational_setting_used_id = OperationalSettingHelper.get_operational_setting_used_id(
                                period=_period, operational_settings_used=operational_settings_used
                            )

                            operational_setting = model.operational_settings[operational_setting_used_id]

                            # Find correct compressor in case of different pressures for different components in system:
                            compressor_nr = int(
                                [i for i, compressor in enumerate(model.compressors) if compressor.name == name][0]
                            )

                            if pressure_type.value == CompressorPressureType.INLET_PRESSURE:
                                if operational_setting.suction_pressures is not None:
                                    pressures = operational_setting.suction_pressures[compressor_nr]
                                else:
                                    pressures = operational_setting.suction_pressure
                            else:
                                if operational_setting.discharge_pressures is not None:
                                    pressures = operational_setting.discharge_pressures[compressor_nr]
                                else:
                                    pressures = operational_setting.discharge_pressure

                            if pressures is None:
                                pressures = math.nan

                            if not isinstance(pressures, Expression):
                                pressures = Expression.setup_from_expression(value=pressures)
                            evaluated_temporal_energy_usage_models[_period] = pressures
            else:
                pressures = model.suction_pressure

                if pressure_type.value == CompressorPressureType.OUTLET_PRESSURE:
                    pressures = model.discharge_pressure

                if pressures is None:
                    pressures = math.nan

                if not isinstance(pressures, Expression):
                    pressures = Expression.setup_from_expression(value=pressures)

                evaluated_temporal_energy_usage_models[period] = pressures

        return TemporalModel(evaluated_temporal_energy_usage_models)

    @staticmethod
    def process_stage_results(
        model: CompressorModelResult, regularity: TimeSeriesFloat
    ) -> list[CompressorModelStageResult]:
        model_stage_results = []
        # Convert rates in stage results from lists to time series:
        for i, stage_result in enumerate(model.stage_results):
            model_stage_result = CompressorModelStageResult(
                chart=stage_result.chart,
                chart_area_flags=stage_result.chart_area_flags,
                energy_usage_unit=stage_result.energy_usage_unit,
                power_unit=stage_result.power_unit,
                fluid_composition=stage_result.fluid_composition,
                asv_recirculation_loss_mw=TimeSeriesHelper.initialize_timeseries(
                    periods=model.periods,
                    values=stage_result.asv_recirculation_loss_mw,
                    unit=Unit.MEGA_WATT,
                    rate_type=RateType.STREAM_DAY,
                    regularity=regularity,
                ),
                head_exceeds_maximum=TimeSeriesHelper.initialize_timeseries(
                    periods=model.periods, values=stage_result.head_exceeds_maximum, unit=Unit.NONE
                ),
                is_valid=TimeSeriesHelper.initialize_timeseries(
                    periods=model.periods, values=stage_result.is_valid, unit=Unit.NONE
                ),
                polytropic_efficiency=TimeSeriesHelper.initialize_timeseries(
                    periods=model.periods, values=stage_result.polytropic_efficiency, unit=Unit.FRACTION
                ),
                polytropic_enthalpy_change_before_choke_kJ_per_kg=TimeSeriesHelper.initialize_timeseries(
                    periods=model.periods,
                    values=stage_result.polytropic_enthalpy_change_before_choke_kJ_per_kg,
                    unit=Unit.POLYTROPIC_HEAD_KILO_JOULE_PER_KG,
                ),
                polytropic_enthalpy_change_kJ_per_kg=TimeSeriesHelper.initialize_timeseries(
                    periods=model.periods,
                    values=stage_result.polytropic_enthalpy_change_kJ_per_kg,
                    unit=Unit.POLYTROPIC_HEAD_KILO_JOULE_PER_KG,
                ),
                polytropic_head_kJ_per_kg=TimeSeriesHelper.initialize_timeseries(
                    periods=model.periods,
                    values=stage_result.polytropic_head_kJ_per_kg,
                    unit=Unit.POLYTROPIC_HEAD_KILO_JOULE_PER_KG,
                ),
                energy_usage=TimeSeriesHelper.initialize_timeseries(
                    periods=model.periods,
                    values=stage_result.energy_usage,
                    unit=stage_result.energy_usage_unit,
                    rate_type=RateType.STREAM_DAY,
                    regularity=regularity,
                ),
                mass_rate_kg_per_hr=TimeSeriesHelper.initialize_timeseries(
                    periods=model.periods, values=stage_result.mass_rate_kg_per_hr, unit=Unit.KILO_PER_HOUR
                ),
                mass_rate_before_asv_kg_per_hr=TimeSeriesHelper.initialize_timeseries(
                    periods=model.periods, values=stage_result.mass_rate_before_asv_kg_per_hr, unit=Unit.KILO_PER_HOUR
                ),
                power=TimeSeriesHelper.initialize_timeseries(
                    periods=model.periods,
                    values=stage_result.power,
                    unit=stage_result.power_unit,
                    rate_type=RateType.STREAM_DAY,
                    regularity=regularity,
                ),
                pressure_is_choked=TimeSeriesHelper.initialize_timeseries(
                    periods=model.periods, values=stage_result.pressure_is_choked, unit=Unit.NONE
                ),
                rate_exceeds_maximum=TimeSeriesHelper.initialize_timeseries(
                    periods=model.periods, values=stage_result.rate_exceeds_maximum, unit=Unit.NONE
                ),
                rate_has_recirculation=TimeSeriesHelper.initialize_timeseries(
                    periods=model.periods, values=stage_result.rate_has_recirculation, unit=Unit.NONE
                ),
                speed=TimeSeriesHelper.initialize_timeseries(
                    periods=model.periods, values=stage_result.speed, unit=Unit.SPEED_RPM
                ),
                inlet_stream_condition=CompressorHelper.process_inlet_stream_condition(
                    model.periods, stage_result.inlet_stream_condition, regularity
                ),
                outlet_stream_condition=CompressorHelper.process_outlet_stream_condition(
                    model.periods, stage_result.outlet_stream_condition, regularity
                ),
                name=f"Stage {i + 1}",
                periods=model.periods,
            )
            model_stage_results.append(model_stage_result)
        return model_stage_results

    @staticmethod
    def process_inlet_stream_condition(
        periods: Periods, inlet_stream_condition: CompressorStreamConditionResult, regularity: TimeSeriesFloat
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
        periods: Periods, outlet_stream_condition: CompressorStreamConditionResult, regularity: TimeSeriesFloat
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
    - Calculate emission intensity.
    - Convert partial emission results to full emission results.
    - Parse emissions from core result format to DTO result format.
    - Process venting emitters results.
    """

    @staticmethod
    def calculate_emission_intensity(
        hydrocarbon_export_rate: TimeSeriesRate,
        emissions: dict[str, PartialEmissionResult],
    ) -> list[EmissionIntensityResult]:
        hydrocarbon_export_cumulative = hydrocarbon_export_rate.to_volumes().cumulative()
        emission_intensities = []

        co2_emission_result = next((value for key, value in emissions.items() if key.lower() == "co2"), None)
        if co2_emission_result is None:
            return []

        cumulative_rate_kg = co2_emission_result.rate.to_volumes().to_unit(Unit.KILO).cumulative()
        intensity = EmissionIntensity(
            emission_cumulative=cumulative_rate_kg,
            hydrocarbon_export_cumulative=hydrocarbon_export_cumulative,
        )
        intensity_sm3 = intensity.calculate_cumulative()
        intensity_yearly_sm3 = intensity.calculate_for_periods()

        emission_intensities.append(
            EmissionIntensityResult(
                name=co2_emission_result.name,
                periods=co2_emission_result.periods,
                intensity_sm3=intensity_sm3,
                intensity_boe=intensity_sm3.to_unit(Unit.KG_BOE),
                intensity_yearly_sm3=intensity_yearly_sm3,
                intensity_yearly_boe=intensity_yearly_sm3.to_unit(Unit.KG_BOE),
            )
        )
        return emission_intensities

    @staticmethod
    def to_full_result(
        emissions: dict[str, PartialEmissionResult],
    ) -> dict[str, libecalc.presentation.json_result.result.EmissionResult]:
        """
        From the partial result, generate cumulatives for the full emissions result per installation
        Args:
            emissions:

        Returns:

        """
        return {
            key: libecalc.presentation.json_result.result.EmissionResult(
                name=key,
                periods=emissions[key].periods,
                rate=emissions[key].rate,
                cumulative=emissions[key].rate.to_volumes().cumulative(),
            )
            for key in emissions
        }

    @staticmethod
    def parse_emissions(
        emissions: dict[str, EmissionResult], regularity: TimeSeriesFloat
    ) -> dict[str, libecalc.presentation.json_result.result.EmissionResult]:
        """
        Convert emissions from core result format to dto result format.

        Given that core result does NOT have regularity, that needs to be added
        Args:
            emissions:
            regularity:

        Returns:

        """
        return {
            key: libecalc.presentation.json_result.result.EmissionResult(
                name=key,
                periods=emissions[key].periods,
                rate=TimeSeriesRate.from_timeseries_stream_day_rate(
                    emissions[key].rate, regularity=regularity
                ).to_calendar_day(),
                cumulative=TimeSeriesRate.from_timeseries_stream_day_rate(emissions[key].rate, regularity=regularity)
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
        sub_components: list[libecalc.presentation.json_result.result.ComponentResult],
        time_series_zero: TimeSeriesRate,
    ):
        for installation in asset.installations:
            for venting_emitter in installation.venting_emitters:
                energy_usage = time_series_zero
                sub_components.append(
                    libecalc.presentation.json_result.result.VentingEmitterResult(
                        id=venting_emitter.id,
                        name=venting_emitter.name,
                        componentType=venting_emitter.component_type.value,
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
        emission_core_results: dict[str, dict[str, EmissionResult]],
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

            for emission_name, emission_result in emissions.items():
                dto_result[consumer_id][emission_name] = PartialEmissionResult.from_emission_core_result(
                    emission_result, regularity=regularity
                )

        return dto_result

    @staticmethod
    def initialize_timeseries(
        periods: Periods,
        values: list[float] | np.ndarray | TimeSeriesFloat | TimeSeriesRate | TimeSeriesBoolean | None,
        unit: Unit,
        rate_type: RateType = None,
        regularity: TimeSeriesFloat | list[float] = None,
    ) -> TimeSeriesBoolean | TimeSeriesFloat | TimeSeriesRate:
        if values is None:
            values = [np.nan] * len(periods)
        if isinstance(values, np.ndarray):
            values = values.tolist()
        if (
            isinstance(values, TimeSeriesFloat)
            or isinstance(values, TimeSeriesRate)
            or isinstance(values, TimeSeriesBoolean)
        ):
            return values
        if unit == Unit.NONE and isinstance(values, list) and all(isinstance(v, bool) for v in values):
            return TimeSeriesBoolean(
                periods=periods,
                values=values,
                unit=unit,
            )
        elif rate_type:
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
            if not isinstance(values, list):
                values = values.tolist()
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
        graph_result: GraphResult,
    ) -> list[libecalc.presentation.json_result.result.InstallationResult]:
        """
        All subcomponents have already been evaluated, here we basically collect and aggregate the results
        """
        asset_id = graph_result.graph.root
        asset = graph_result.graph.get_node(asset_id)
        installation_results = []
        for installation in asset.installations:
            expression_evaluator = installation.expression_evaluator
            regularity = installation.regularity
            hydrocarbon_export_rate = installation.evaluated_hydrocarbon_export_rate

            sub_components = [
                graph_result.consumer_results[component_id].component_result
                for component_id in graph_result.graph.get_successors(installation.id, recursively=True)
                if component_id in graph_result.consumer_results
            ]

            power_components = [
                graph_result.consumer_results[component_id].component_result
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
                    parent=asset.id,
                    component_level=installation_node_info.component_level,
                    componentType=installation_node_info.component_type.value,
                    periods=expression_evaluator.get_periods(),
                    is_valid=TimeSeriesHelper.initialize_timeseries(
                        periods=expression_evaluator.get_periods(),
                        values=aggregate_is_valid(sub_components),
                        unit=Unit.NONE,
                    ),
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

    @staticmethod
    def process_operational_settings_results(
        operational_settings_results: dict[str, list[Any]], regularity: TimeSeriesFloat
    ) -> dict[str, list[Any]]:
        processed_results = {}
        for key, models in operational_settings_results.items():
            processed_models: list[OperationalSettingResult] = []
            for model in models:
                if model.component_type == ComponentType.PUMP:
                    result = PumpOperationalSettingResult(
                        name=model.name,
                        periods=model.periods,
                        is_valid=model.is_valid,
                        energy_usage=TimeSeriesHelper.initialize_timeseries(
                            model.periods, model.energy_usage.values, model.energy_usage.unit
                        ),
                        power=TimeSeriesHelper.initialize_timeseries(
                            model.periods, model.power.values, model.power.unit
                        ),
                        inlet_liquid_rate_m3_per_day=model.inlet_liquid_rate_m3_per_day,
                        inlet_pressure_bar=model.inlet_pressure_bar,
                        outlet_pressure_bar=model.outlet_pressure_bar,
                        operational_head=model.operational_head,
                    )
                    processed_models.append(result)
                elif model.component_type == ComponentType.COMPRESSOR:
                    model_stage_results = CompressorHelper.process_stage_results(model, regularity)
                    turbine_result = ModelResultHelper.process_turbine_result(model, regularity)

                    inlet_stream_condition = CompressorHelper.process_inlet_stream_condition(
                        model.periods, model.inlet_stream_condition, regularity
                    )

                    outlet_stream_condition = CompressorHelper.process_outlet_stream_condition(
                        model.periods, model.outlet_stream_condition, regularity
                    )
                    result = CompressorOperationalSettingResult(
                        name=model.name,
                        periods=model.periods,
                        is_valid=model.is_valid,
                        energy_usage=TimeSeriesHelper.initialize_timeseries(
                            model.periods, model.energy_usage.values, model.energy_usage.unit
                        ),
                        power=TimeSeriesHelper.initialize_timeseries(
                            model.periods, model.power.values, model.power.unit
                        ),
                        failure_status=model.failure_status,
                        max_standard_rate=model.max_standard_rate,
                        rate_sm3_day=model.rate_sm3_day,
                        inlet_stream_condition=inlet_stream_condition,
                        outlet_stream_condition=outlet_stream_condition,
                        stage_results=model_stage_results,
                        turbine_result=turbine_result if turbine_result else None,
                    )
                    processed_models.append(result)

            processed_results[key] = processed_models
        return processed_results


def get_asset_result(graph_result: GraphResult) -> libecalc.presentation.json_result.result.results.EcalcModelResult:
    asset_id = graph_result.graph.root
    asset = graph_result.graph.get_node(asset_id)

    if not isinstance(asset, Asset):
        raise ProgrammingError("Need an asset graph to get asset result")

    # Start processing installation results
    installation_results = InstallationHelper.evaluate_installations(
        graph_result=graph_result,
    )

    regularities: dict[str, TimeSeriesFloat] = {
        installation.id: installation.regularity for installation in installation_results
    }

    models = []
    sub_components = [*installation_results]
    for consumer_result in graph_result.consumer_results.values():
        consumer_id = consumer_result.component_result.id
        consumer_node_info = graph_result.graph.get_node_info(consumer_id)

        parent_installation_id = graph_result.graph.get_parent_installation_id(consumer_id)
        regularity: TimeSeriesFloat = regularities[parent_installation_id]

        # Start processing model results (for components with models
        if consumer_node_info.component_type in [ComponentType.COMPRESSOR, ComponentType.COMPRESSOR_SYSTEM]:
            models.extend(
                ModelResultHelper.process_compressor_models(
                    graph_result, consumer_result, consumer_id, consumer_node_info, regularity
                )
            )

        elif consumer_node_info.component_type in [ComponentType.PUMP, ComponentType.PUMP_SYSTEM]:
            models.extend(ModelResultHelper.process_pump_models(consumer_result, consumer_id, regularity))

        elif consumer_node_info.component_type == ComponentType.GENERIC:
            models.extend(ModelResultHelper.process_generic_models(consumer_result, consumer_id, regularity))

        else:
            if consumer_result.models:
                raise ProgrammingError(
                    f"Unhandled component type, {consumer_node_info.component_type}, when collecting models"
                )

        # Start processing component (sub_components) results, top level result for each component
        sub_component: libecalc.presentation.json_result.result.ComponentResult

        if consumer_node_info.component_type == ComponentType.GENERATOR_SET:
            sub_component = ComponentResultHelper.process_generator_set_result(
                graph_result, consumer_result, consumer_node_info, regularity
            )

        elif consumer_node_info.component_type == ComponentType.PUMP:
            sub_component = ComponentResultHelper.process_pump_component_result(
                graph_result, consumer_result, consumer_node_info, regularity
            )

        elif consumer_node_info.component_type == ComponentType.COMPRESSOR:
            sub_component = ComponentResultHelper.process_compressor_component_result(
                graph_result, consumer_result, consumer_node_info, regularity
            )

        elif consumer_node_info.component_type == ComponentType.GENERIC:
            sub_component = ComponentResultHelper.process_generic_component_result(
                graph_result, consumer_result, consumer_node_info, regularity
            )

        elif consumer_node_info.component_type in [ComponentType.COMPRESSOR_SYSTEM, ComponentType.PUMP_SYSTEM]:
            sub_component = ComponentResultHelper.process_consumer_system_component_result(
                graph_result, consumer_result, consumer_node_info, regularity
            )
        else:
            raise ProgrammingError(
                f"Unhandled component type, {consumer_node_info.component_type}, when collecting sub_components"
            )

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
    EmissionHelper.process_venting_emitters_result(graph_result, asset, regularities, sub_components, time_series_zero)

    # Summing hydrocarbon export rates from all installations
    asset_hydrocarbon_export_rate_core = InstallationHelper.sum_installation_attribute_values(
        installation_results, "hydrocarbon_export_rate", time_series_zero
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
        installation_results, "energy_usage", time_series_zero
    )

    # Converting total energy usage to cumulative values
    asset_energy_usage_cumulative = asset_energy_usage_core.to_volumes().cumulative()

    asset_node_info = graph_result.graph.get_node_info(asset_id)
    asset_result_dto = AssetResult(
        id=asset.id,
        name=asset_node_info.name,
        component_level=asset_node_info.component_level,
        componentType=asset_node_info.component_type.value,
        periods=graph_result.variables_map.get_periods(),
        is_valid=TimeSeriesBoolean(
            periods=graph_result.variables_map.get_periods(),
            values=aggregate_is_valid(installation_results)
            if installation_results
            else [True] * graph_result.variables_map.number_of_periods,
            unit=Unit.NONE,
        ),
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

    return Numbers.format_results_to_precision(
        libecalc.presentation.json_result.result.results.EcalcModelResult(
            component_result=asset_result_dto,
            sub_components=sub_components,
            models=models,
        ),
        precision=6,
    )
