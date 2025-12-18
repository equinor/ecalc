import math
import operator
from collections.abc import Sequence
from functools import reduce
from typing import assert_never, cast

import numpy as np
from numpy.typing import NDArray

import libecalc
from libecalc.common.component_info.component_level import ComponentLevel
from libecalc.common.component_info.compressor import CompressorPressureType
from libecalc.common.component_type import ComponentType
from libecalc.common.decorators.feature_flags import Feature
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
)
from libecalc.core.result.results import CompressorResult, PumpResult
from libecalc.core.result.results import ConsumerSystemResult as CoreConsumerSystemResult
from libecalc.core.result.results import GenericComponentResult as CoreGenericComponentResult
from libecalc.domain.energy import Emitter, EnergyModel
from libecalc.domain.energy.energy_component import EnergyContainerID
from libecalc.domain.infrastructure.energy_components.electricity_consumer.electricity_consumer import (
    ElectricityConsumer,
)
from libecalc.domain.infrastructure.energy_components.fuel_consumer.fuel_consumer import FuelConsumerComponent
from libecalc.domain.infrastructure.energy_components.installation.installation import InstallationComponent
from libecalc.domain.infrastructure.energy_components.legacy_consumer.system import ConsumerSystemConsumerFunction
from libecalc.domain.installation import FuelConsumer, PowerConsumer
from libecalc.domain.process.compressor.core.base import CompressorWithTurbineModel
from libecalc.domain.process.compressor.core.sampled import CompressorModelSampled
from libecalc.domain.process.compressor.core.train.base import CompressorTrainModel
from libecalc.domain.process.core.results import CompressorStreamCondition, CompressorTrainResult
from libecalc.domain.process.core.results import PumpModelResult as CorePumpModelResult
from libecalc.domain.process.core.results.base import Quantity
from libecalc.dto.node_info import NodeInfo
from libecalc.presentation.json_result.result import ComponentResult as JsonResultComponentResult
from libecalc.presentation.json_result.result import EcalcModelResult
from libecalc.presentation.json_result.result.emission import EmissionResult
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
    VentingEmitterResult,
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
        container_info: NodeInfo,
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
                    parent=container_info.name,
                    name=container_info.name,
                    componentType=container_info.component_type,
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
        energy_model: EnergyModel,
        consumer_result: CompressorResult | CoreConsumerSystemResult,
        container_info: NodeInfo,
        regularity: TimeSeriesFloat,
    ) -> list[CompressorModelResult]:
        models = []
        component = energy_model.get_energy_container(container_info.id)
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
                container_info=container_info,
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
                    if container_info.component_type == ComponentType.COMPRESSOR_SYSTEM
                    else None,
                    model_periods=periods,
                ).for_period(period)
                requested_outlet_pressure = CompressorHelper.get_requested_compressor_pressures(
                    energy_usage_model=energy_usage_model,
                    pressure_type=CompressorPressureType.OUTLET_PRESSURE,
                    name=system_consumer_result.name,
                    operational_settings_used=consumer_result.operational_settings_used
                    if container_info.component_type == ComponentType.COMPRESSOR_SYSTEM
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
                        parent=container_info.name,
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
        container_info: NodeInfo,
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
                        parent=container_info.name,
                        name=container_info.name,
                        componentType=container_info.component_type,
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
                            parent=container_info.name,
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
        consumer_result: CoreGenericComponentResult, container_info: NodeInfo, regularity: TimeSeriesFloat
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
                    parent=container_info.name,
                    name=container_info.name,
                    componentType=container_info.component_type,
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
        emissions: dict[str, TimeSeriesRate],
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
                rate=emissions[key],
                cumulative=emissions[key].to_volumes().cumulative(),
            )
            for key in emissions
        }


class TimeSeriesHelper:
    """
    A helper class for initializing and converting time series data.

    This class provides static methods to:
    - Convert emission results to time series format.
    - Initialize time series with given periods, values, and units.
    - Convert time series to cumulative values.
    """

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


class InstallationMapper:
    """
    A helper class for evaluating and aggregating installation results.

    This class provides static methods to:
    - Evaluate installations and collect results.
    - Sum attribute values from a list of InstallationResult objects.
    - Compute aggregated power for installations.
    """

    def __init__(self, model: YamlModel):
        self._model = model

    def get_parent(self, container_id: EnergyContainerID) -> str:
        energy_model = self._model.get_energy_model()
        parent_id = energy_model.get_parent(container_id=container_id)
        parent_container_info = self._model.get_container_info(parent_id)
        return parent_container_info.name

    def get_emissions(self, container_id: EnergyContainerID) -> dict[str, TimeSeriesRate] | None:
        emitter = self._model.get_emitter(container_id)
        if emitter is None:
            return None
        return {
            emission_name: emission_rate.to_calendar_day()
            for emission_name, emission_rate in emitter.get_emissions().items()
        }

    def get_fuel_consumption_rate(self, container_id: EnergyContainerID) -> TimeSeriesRate | None:
        fuel_consumer = self._model.get_fuel_consumer(container_id=container_id)
        if fuel_consumer is None:
            return None
        return fuel_consumer.get_fuel_consumption().rate.to_calendar_day()

    def get_power_consumption_rate(self, container_id: EnergyContainerID) -> TimeSeriesRate | None:
        power_consumer = self._model.get_power_consumer(container_id=container_id)
        if power_consumer is None:
            return None
        return power_consumer.get_power_consumption().to_stream_day()

    def get_periods(self) -> Periods:
        return self._model.variables.get_periods()

    def get_zero_fuel_consumption_rate(self) -> TimeSeriesRate:
        periods = self.get_periods()
        number_of_periods = len(periods)
        return TimeSeriesRate(
            values=[0] * number_of_periods,
            periods=periods,
            unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
            rate_type=RateType.CALENDAR_DAY,
            regularity=[1] * number_of_periods,
        )

    def map_venting_emitter(self, container_id: EnergyContainerID) -> VentingEmitterResult:
        container_info = self._model.get_container_info(container_id)
        emissions = self.get_emissions(container_id)

        fuel_rate = self.get_zero_fuel_consumption_rate()
        power_rate = None
        fuel_volume_cumulative = fuel_rate.to_volumes().cumulative()
        power_cumulative = None

        energy_usage = fuel_rate or power_rate
        energy_usage_cumulative = fuel_volume_cumulative or power_cumulative
        return VentingEmitterResult(
            id=container_info.name,
            name=container_info.name,
            parent=self.get_parent(container_id),
            component_level=container_info.component_level,
            componentType=container_info.component_type,
            is_valid=self._model.get_validity(container_info.id),
            periods=energy_usage.periods,
            emissions=EmissionHelper.to_full_result(emissions=emissions) if emissions is not None else {},
            energy_usage_cumulative=energy_usage_cumulative,
            power_cumulative=power_cumulative,
            power=power_rate,
            energy_usage=energy_usage,
        )

    def map_pump(
        self,
        container_id: EnergyContainerID,
        inlet_liquid_rate_m3_per_day: TimeSeriesRate,
        inlet_pressure_bar: TimeSeriesFloat,
        outlet_pressure_bar: TimeSeriesFloat,
        operational_head: TimeSeriesFloat,
    ):
        container_info = self._model.get_container_info(container_id)

        emissions = self.get_emissions(container_id)

        fuel_rate = self.get_fuel_consumption_rate(container_id=container_id)
        power_rate = self.get_power_consumption_rate(container_id=container_id)
        fuel_volume_cumulative = fuel_rate.to_volumes().cumulative() if fuel_rate else None
        power_cumulative = power_rate.to_volumes().to_unit(Unit.GIGA_WATT_HOURS).cumulative() if power_rate else None

        energy_usage = fuel_rate or power_rate
        energy_usage_cumulative = fuel_volume_cumulative or power_cumulative
        return libecalc.presentation.json_result.result.results.PumpResult(
            id=container_info.name,
            name=container_info.name,
            parent=self.get_parent(container_id),
            component_level=container_info.component_level,
            componentType=container_info.component_type,
            is_valid=self._model.get_validity(container_info.id),
            periods=energy_usage.periods,
            emissions=EmissionHelper.to_full_result(emissions=emissions) if emissions is not None else {},
            energy_usage_cumulative=energy_usage_cumulative,
            power_cumulative=power_cumulative,
            power=power_rate,
            energy_usage=energy_usage,
            inlet_liquid_rate_m3_per_day=inlet_liquid_rate_m3_per_day,
            inlet_pressure_bar=inlet_pressure_bar,
            outlet_pressure_bar=outlet_pressure_bar,
            operational_head=operational_head,
        )

    def map_consumer_system(self, container_id: EnergyContainerID) -> ConsumerSystemResult:
        container_info = self._model.get_container_info(container_id)

        emissions = self.get_emissions(container_id)

        fuel_rate = self.get_fuel_consumption_rate(container_id=container_id)
        power_rate = self.get_power_consumption_rate(container_id=container_id)
        fuel_volume_cumulative = fuel_rate.to_volumes().cumulative() if fuel_rate else None
        power_cumulative = power_rate.to_volumes().to_unit(Unit.GIGA_WATT_HOURS).cumulative() if power_rate else None

        energy_usage = fuel_rate or power_rate
        energy_usage_cumulative = fuel_volume_cumulative or power_cumulative
        return ConsumerSystemResult(
            id=container_info.name,
            name=container_info.name,
            parent=self.get_parent(container_id),
            component_level=container_info.component_level,
            componentType=container_info.component_type,
            is_valid=self._model.get_validity(container_info.id),
            periods=energy_usage.periods,
            emissions=EmissionHelper.to_full_result(emissions=emissions) if emissions is not None else {},
            energy_usage_cumulative=energy_usage_cumulative,
            power_cumulative=power_cumulative,
            power=power_rate,
            energy_usage=energy_usage,
            operational_settings_used=self._model.get_operational_settings_used(container_id),
            operational_settings_results=None,
        )

    def map_generator_set(
        self,
        container_id: EnergyContainerID,
    ) -> libecalc.presentation.json_result.result.results.GeneratorSetResult:
        container_info = self._model.get_container_info(container_id)

        emissions = self.get_emissions(container_id)

        fuel_rate = self.get_fuel_consumption_rate(container_id=container_id)
        assert fuel_rate is not None, "Generator set should have fuel consumption"
        electricity_producer = self._model.get_electricity_producer(container_id)
        power_requirement_rate = electricity_producer.get_power_requirement()
        assert power_requirement_rate is not None, "Generator set should have a power requirement"
        fuel_volume_cumulative = fuel_rate.to_volumes().cumulative()
        power_cumulative = power_requirement_rate.to_volumes().to_unit(Unit.GIGA_WATT_HOURS).cumulative()

        power_capacity_margin = electricity_producer.get_power_capacity_margin()

        energy_usage = fuel_rate
        energy_usage_cumulative = fuel_volume_cumulative
        return libecalc.presentation.json_result.result.results.GeneratorSetResult(
            id=container_info.name,
            name=container_info.name,
            parent=self.get_parent(container_id),
            component_level=container_info.component_level,
            componentType=container_info.component_type,
            is_valid=self._model.get_validity(container_info.id),
            periods=energy_usage.periods,
            emissions=EmissionHelper.to_full_result(emissions=emissions) if emissions is not None else {},
            energy_usage_cumulative=energy_usage_cumulative,
            power_cumulative=power_cumulative,
            power=power_requirement_rate,
            energy_usage=energy_usage,
            power_capacity_margin=power_capacity_margin,
        )

    def map_generic_component(self, container_id: EnergyContainerID) -> GenericConsumerResult:
        container_info = self._model.get_container_info(container_id)

        emissions = self.get_emissions(container_id)

        fuel_rate = self.get_fuel_consumption_rate(container_id=container_id)
        power_rate = self.get_power_consumption_rate(container_id=container_id)
        fuel_volume_cumulative = fuel_rate.to_volumes().cumulative() if fuel_rate else None
        power_cumulative = power_rate.to_volumes().to_unit(Unit.GIGA_WATT_HOURS).cumulative() if power_rate else None

        energy_usage = fuel_rate or power_rate
        energy_usage_cumulative = fuel_volume_cumulative or power_cumulative
        return GenericConsumerResult(
            id=container_info.name,
            name=container_info.name,
            parent=self.get_parent(container_id),
            component_level=container_info.component_level,
            componentType=container_info.component_type,
            is_valid=self._model.get_validity(container_info.id),
            periods=energy_usage.periods,
            emissions=EmissionHelper.to_full_result(emissions=emissions) if emissions is not None else {},
            energy_usage_cumulative=energy_usage_cumulative,
            power_cumulative=power_cumulative,
            power=power_rate,
            energy_usage=energy_usage,
        )

    def map_compressor(
        self,
        container_id: EnergyContainerID,
        recirculation_loss: TimeSeriesRate,
        rate_exceeds_maximum: TimeSeriesBoolean,
    ) -> libecalc.presentation.json_result.result.results.CompressorResult:
        container_info = self._model.get_container_info(container_id)

        emissions = self.get_emissions(container_id)

        fuel_rate = self.get_fuel_consumption_rate(container_id=container_id)
        power_rate = self.get_power_consumption_rate(container_id=container_id)
        fuel_volume_cumulative = fuel_rate.to_volumes().cumulative() if fuel_rate else None
        power_cumulative = power_rate.to_volumes().to_unit(Unit.GIGA_WATT_HOURS).cumulative() if power_rate else None

        energy_usage = fuel_rate or power_rate
        energy_usage_cumulative = fuel_volume_cumulative or power_cumulative

        return libecalc.presentation.json_result.result.results.CompressorResult(
            id=container_info.name,
            name=container_info.name,
            parent=self.get_parent(container_id),
            component_level=container_info.component_level,
            componentType=container_info.component_type,
            is_valid=self._model.get_validity(container_info.id),
            periods=energy_usage.periods,
            emissions=EmissionHelper.to_full_result(emissions=emissions) if emissions is not None else {},
            energy_usage_cumulative=energy_usage_cumulative,
            power_cumulative=power_cumulative,
            power=power_rate,
            energy_usage=energy_usage,
            recirculation_loss=recirculation_loss,
            rate_exceeds_maximum=rate_exceeds_maximum,
        )

    def map_installation(self, installation: InstallationComponent, parent_name: str) -> InstallationResult | None:
        expression_evaluator = installation.expression_evaluator
        regularity = installation.regularity
        hydrocarbon_export_rate = installation.hydrocarbon_export.time_series

        installation_node_info = self._model.get_container_info(installation.get_id())

        power_electrical = self.aggregate_power_consumption(installation.get_electrical_power_consumers())

        power_mechanical = self.aggregate_power_consumption(installation.get_mechanical_power_consumers())

        power = (
            power_electrical + power_mechanical
            if power_electrical and power_mechanical
            else (power_mechanical or power_electrical)
        )

        fuel_consumption = self.aggregate_fuel_consumption(installation.get_fuel_consumers())

        return libecalc.presentation.json_result.result.InstallationResult(
            id=installation_node_info.name,
            name=installation_node_info.name,
            parent=parent_name,
            component_level=installation_node_info.component_level,
            componentType=installation_node_info.component_type,
            periods=expression_evaluator.get_periods(),
            is_valid=self._model.get_validity(installation.get_id()),
            power=power,
            power_cumulative=power.to_volumes().to_unit(Unit.GIGA_WATT_HOURS).cumulative() if power else None,
            power_electrical=power_electrical,
            power_electrical_cumulative=power_electrical.to_volumes().to_unit(Unit.GIGA_WATT_HOURS).cumulative()
            if power_electrical
            else None,
            power_mechanical=power_mechanical,
            power_mechanical_cumulative=power_mechanical.to_volumes().to_unit(Unit.GIGA_WATT_HOURS).cumulative()
            if power_mechanical
            else None,
            energy_usage=fuel_consumption,
            energy_usage_cumulative=fuel_consumption.to_volumes().cumulative(),
            hydrocarbon_export_rate=hydrocarbon_export_rate,
            emissions=EmissionHelper.to_full_result(self.aggregate_emissions(installation.get_emitters())),
            regularity=regularity.time_series,
        )

    def map_container(self, container_id: EnergyContainerID) -> EcalcModelResult:
        model = self._model
        energy_model = model.get_energy_model()
        energy_container = energy_model.get_energy_container(container_id)
        container_info = model.get_container_info(container_id)
        process_type = energy_container.get_component_process_type()

        assert process_type != ComponentType.ASSET and process_type != ComponentType.INSTALLATION
        regularity = model.get_regularity(container_id).time_series

        if process_type == ComponentType.COMPRESSOR:
            result = model.get_container_result(container_id)
            compressor_models = ModelResultHelper.process_compressor_models(
                energy_model=energy_model,
                consumer_result=result,
                container_info=container_info,
                regularity=regularity,
            )
            # TODO: Don't use result to get recirculation loss and rate_exceeds_maximum, aggregate from compressor models instead. We don't want to aggregate results in core, only keep track of what to aggregate.
            sub_component = self.map_compressor(
                container_id=container_id,
                recirculation_loss=TimeSeriesRate.from_timeseries_stream_day_rate(
                    result.recirculation_loss,
                    regularity=regularity,
                ),
                rate_exceeds_maximum=result.rate_exceeds_maximum,
            )
            return EcalcModelResult(
                component_result=sub_component,
                models=compressor_models,
                sub_components=[],
            )
        elif process_type == ComponentType.PUMP:
            result = model.get_container_result(container_id)
            pump_models = ModelResultHelper.process_pump_models(
                consumer_result=result,
                container_info=container_info,
                regularity=model.get_regularity(container_id).time_series,
            )
            # TODO: Don't use result to get liquid rate, pressures and head, aggregate from pump models instead. We don't want to aggregate results in core, only keep track of what to aggregate.
            sub_component = self.map_pump(
                container_id=container_id,
                inlet_liquid_rate_m3_per_day=TimeSeriesRate.from_timeseries_stream_day_rate(
                    result.inlet_liquid_rate_m3_per_day,
                    regularity=regularity,
                ),
                inlet_pressure_bar=result.inlet_pressure_bar,
                outlet_pressure_bar=result.outlet_pressure_bar,
                operational_head=result.operational_head,
            )
            return EcalcModelResult(
                component_result=sub_component,
                models=pump_models,
                sub_components=[],
            )
        elif process_type == ComponentType.COMPRESSOR_SYSTEM or process_type == ComponentType.PUMP_SYSTEM:
            sub_component = self.map_consumer_system(container_id)
            result = model.get_container_result(container_id)
            models: list[CompressorModelResult | PumpModelResult | GenericModelResult] = []
            if process_type == ComponentType.COMPRESSOR_SYSTEM:
                models.extend(
                    ModelResultHelper.process_compressor_models(
                        energy_model=energy_model,
                        consumer_result=result,
                        container_info=container_info,
                        regularity=regularity,
                    )
                )
            else:
                assert process_type == ComponentType.PUMP_SYSTEM
                models.extend(
                    ModelResultHelper.process_pump_models(
                        consumer_result=result, container_info=container_info, regularity=regularity
                    )
                )
            return EcalcModelResult(
                component_result=sub_component,
                models=models,
                sub_components=[],
            )
        elif process_type == ComponentType.GENERIC:
            sub_component = self.map_generic_component(container_id)
            result = model.get_container_result(container_id)
            generic_models = ModelResultHelper.process_generic_models(
                consumer_result=result, container_info=container_info, regularity=regularity
            )
            return EcalcModelResult(component_result=sub_component, models=generic_models, sub_components=[])
        elif process_type == ComponentType.GENERATOR_SET:
            sub_component = self.map_generator_set(
                container_id,
            )
            ecalc_model_result = EcalcModelResult(component_result=sub_component, models=[], sub_components=[])
            for sub_container_id in energy_model.get_consumers(container_id):
                sub_container_result = self.map_container(sub_container_id)
                ecalc_model_result.sub_components.append(sub_container_result.component_result)
                ecalc_model_result.sub_components.extend(sub_container_result.sub_components)
                ecalc_model_result.models.extend(sub_container_result.models)

            return ecalc_model_result

        elif process_type == ComponentType.VENTING_EMITTER:
            sub_component = self.map_venting_emitter(container_id)
            return EcalcModelResult(
                component_result=sub_component,
                sub_components=[],
                models=[],
            )
        else:
            assert_never(process_type)

    @staticmethod
    def aggregate_emissions(emitters: list[Emitter]) -> dict[str, TimeSeriesRate]:
        emission_rates: dict[str, TimeSeriesRate] = {}
        for emitter in emitters:
            emissions = emitter.get_emissions()
            for emission_name, emission_rate in emissions.items():
                if emission_name not in emission_rates:
                    emission_rates[emission_name] = emission_rate.to_calendar_day()
                else:
                    emission_rates[emission_name] += emission_rate.to_calendar_day()
        return emission_rates

    @staticmethod
    def aggregate_power_consumption(
        power_consumers: list[PowerConsumer],
    ) -> TimeSeriesRate | None:
        if len(power_consumers) == 0:
            return None

        return reduce(
            operator.add,
            [consumer.get_power_consumption().to_unit(Unit.MEGA_WATT) for consumer in power_consumers],
        )

    def aggregate_fuel_consumption(
        self,
        fuel_consumers: list[FuelConsumer],
    ) -> TimeSeriesRate | None:
        if len(fuel_consumers) == 0:
            return self.get_zero_fuel_consumption_rate()

        return reduce(
            operator.add,
            [
                consumer.get_fuel_consumption().rate.to_unit(Unit.STANDARD_CUBIC_METER_PER_DAY).to_calendar_day()
                for consumer in fuel_consumers
            ],
        )


class OperationalSettingHelper:
    @staticmethod
    def get_operational_setting_used_id(period: Period, operational_settings_used: TimeSeriesInt) -> int:
        period_index = operational_settings_used.periods.periods.index(period)

        operational_setting_id = operational_settings_used.values[period_index]

        return operational_setting_id - 1


def get_asset_result(model: YamlModel) -> libecalc.presentation.json_result.result.results.EcalcModelResult:
    installation_mapper = InstallationMapper(model)
    energy_model = model.get_energy_model()

    hydrocarbon_export_rates: list[TimeSeriesRate] = []

    fuel_consumers = []
    mechanical_power_consumers = []
    electrical_power_consumers = []
    emitters = []

    sub_components: list[JsonResultComponentResult] = []
    models: list[CompressorModelResult | PumpModelResult | GenericModelResult] = []
    for installation in model.get_installations():
        assert isinstance(installation, InstallationComponent)

        hydrocarbon_export_rates.append(installation.hydrocarbon_export.time_series)

        fuel_consumers.extend(installation.get_fuel_consumers())
        mechanical_power_consumers.extend(installation.get_mechanical_power_consumers())
        electrical_power_consumers.extend(installation.get_electrical_power_consumers())

        emitters.extend(installation.get_emitters())

        mapped_installation = installation_mapper.map_installation(installation, parent_name=model.get_name())
        if mapped_installation is not None:
            sub_components.append(mapped_installation)

        for sub_container_id in energy_model.get_consumers(
            installation.get_id()
        ):  # get_consumers in this case just means successors in graph, i.e. containers in installation container.
            ecalc_model_result = installation_mapper.map_container(sub_container_id)
            sub_components.append(ecalc_model_result.component_result)
            sub_components.extend(ecalc_model_result.sub_components)
            models.extend(ecalc_model_result.models)

    # Summing hydrocarbon export rates from all installations
    asset_hydrocarbon_export_rate_core = reduce(
        operator.add,
        hydrocarbon_export_rates,
    )

    # Summing power values from all installations
    asset_power_electrical_core = installation_mapper.aggregate_power_consumption(electrical_power_consumers)
    asset_power_mechanical_core = installation_mapper.aggregate_power_consumption(mechanical_power_consumers)

    asset_power_core = (
        asset_power_mechanical_core + asset_power_electrical_core
        if asset_power_mechanical_core and asset_power_electrical_core
        else (asset_power_mechanical_core or asset_power_electrical_core)
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
    asset_energy_usage_core = installation_mapper.aggregate_fuel_consumption(fuel_consumers=fuel_consumers)

    # Converting total energy usage to cumulative values
    asset_energy_usage_cumulative = asset_energy_usage_core.to_volumes().cumulative()

    asset_node_info = model.get_container_info(energy_model.get_root())

    model_result = AssetResult(
        id=asset_node_info.name,
        name=asset_node_info.name,
        component_level=asset_node_info.component_level,
        componentType=asset_node_info.component_type,
        periods=model.variables.get_periods(),
        is_valid=model.get_validity(energy_model.get_root()),
        power=asset_power_core,
        power_cumulative=asset_power_cumulative,
        power_electrical=asset_power_electrical_core,
        power_electrical_cumulative=asset_power_electrical_cumulative,
        power_mechanical=asset_power_mechanical_core,
        power_mechanical_cumulative=asset_power_mechanical_cumulative,
        energy_usage=asset_energy_usage_core,
        energy_usage_cumulative=asset_energy_usage_cumulative,
        hydrocarbon_export_rate=asset_hydrocarbon_export_rate_core,
        emissions=EmissionHelper.to_full_result(InstallationMapper.aggregate_emissions(emitters)),
    )

    return libecalc.presentation.json_result.result.results.EcalcModelResult(
        component_result=model_result,
        sub_components=sub_components,
        models=models,
    )
