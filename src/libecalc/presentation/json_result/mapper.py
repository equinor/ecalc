import math
import operator
from collections import defaultdict
from functools import reduce
from typing import Any

from pydantic import TypeAdapter

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
from libecalc.common.variables import ExpressionEvaluator
from libecalc.core.result.emission import EmissionResult
from libecalc.domain.emission.emission_intensity import EmissionIntensity
from libecalc.domain.infrastructure.energy_components.asset.asset import Asset
from libecalc.domain.process.dto import CompressorSystemConsumerFunction
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
    CompressorStreamConditionResult,
    PumpModelResult,
    TurbineModelResult,
)


def get_operational_setting_used_id(period: Period, operational_settings_used: TimeSeriesInt) -> int:
    period_index = operational_settings_used.periods.periods.index(period)

    operational_setting_id = operational_settings_used.values[period_index]

    return operational_setting_id - 1


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
                        operational_setting_used_id = get_operational_setting_used_id(
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


def _calculate_emission_intensity(
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


def _to_full_result(
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


def _convert_to_timeseries(
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


def _parse_emissions(
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


def _compute_aggregated_power(
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
        TimeSeriesRate(
            values=[0.0] * graph_result.variables_map.number_of_periods,
            periods=graph_result.variables_map.periods,
            unit=Unit.MEGA_WATT,
            rate_type=RateType.STREAM_DAY,
            regularity=regularity.values,
        ),  # Initial value, handle no power output from components
    )


def _evaluate_installations(
    graph_result: GraphResult, expression_evaluator: ExpressionEvaluator
) -> list[libecalc.presentation.json_result.result.InstallationResult]:
    """
    All subcomponents have already been evaluated, here we basically collect and aggregate the results
    """
    asset_id = graph_result.graph.root
    asset = graph_result.graph.get_node(asset_id)
    installation_results = []
    for installation in asset.installations:
        regularity = TimeSeriesFloat(
            periods=expression_evaluator.get_periods(),
            values=expression_evaluator.evaluate(expression=TemporalModel(installation.regularity)),
            unit=Unit.NONE,
        )
        hydrocarbon_export_rate = expression_evaluator.evaluate(
            expression=TemporalModel(installation.hydrocarbon_export)
        )

        hydrocarbon_export_rate = TimeSeriesRate(
            periods=expression_evaluator.get_periods(),
            values=hydrocarbon_export_rate,
            unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
            rate_type=RateType.CALENDAR_DAY,
            regularity=regularity.values,
        )

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

        power_electrical = _compute_aggregated_power(
            graph_result=graph_result,
            power_components=electrical_components,
            regularity=regularity,
        )

        power_mechanical = _compute_aggregated_power(
            graph_result=graph_result,
            power_components=fuel_components,
            regularity=regularity,
        )

        power = power_electrical + power_mechanical

        energy_usage = (
            reduce(
                operator.add,
                [
                    TimeSeriesRate.from_timeseries_stream_day_rate(component.energy_usage, regularity=regularity)
                    for component in sub_components
                    if component.energy_usage.unit == Unit.STANDARD_CUBIC_METER_PER_DAY
                ],
            )
            if sub_components
            else 0
        )

        emission_dto_results = _convert_to_timeseries(
            graph_result,
            graph_result.emission_results,
            regularity,
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
                is_valid=TimeSeriesBoolean(
                    periods=expression_evaluator.get_periods(),
                    values=aggregate_is_valid(sub_components),
                    unit=Unit.NONE,
                ),
                power=power,
                power_cumulative=power.to_volumes().to_unit(Unit.GIGA_WATT_HOURS).cumulative(),
                power_electrical=power_electrical,
                power_electrical_cumulative=power_electrical.to_volumes().to_unit(Unit.GIGA_WATT_HOURS).cumulative(),
                power_mechanical=power_mechanical,
                power_mechanical_cumulative=power_mechanical.to_volumes().to_unit(Unit.GIGA_WATT_HOURS).cumulative(),
                energy_usage=energy_usage.to_calendar_day()
                if energy_usage.unit == Unit.STANDARD_CUBIC_METER_PER_DAY
                else energy_usage.to_stream_day(),
                energy_usage_cumulative=energy_usage.to_volumes().cumulative(),
                hydrocarbon_export_rate=hydrocarbon_export_rate,
                emissions=_to_full_result(aggregated_emissions),
                regularity=TimeSeriesFloat(
                    periods=expression_evaluator.get_periods(),
                    values=regularity.values,
                    unit=Unit.NONE,
                ),
            )
        ) if sub_components else None
    return installation_results


def get_asset_result(graph_result: GraphResult) -> libecalc.presentation.json_result.result.results.EcalcModelResult:
    asset_id = graph_result.graph.root
    asset = graph_result.graph.get_node(asset_id)

    if not isinstance(asset, Asset):
        raise ProgrammingError("Need an asset graph to get asset result")

    installation_results = _evaluate_installations(
        graph_result=graph_result,
        expression_evaluator=graph_result.variables_map,
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

        if consumer_node_info.component_type in [ComponentType.COMPRESSOR, ComponentType.COMPRESSOR_SYSTEM]:
            component = graph_result.graph.get_node(consumer_id)

            for model in consumer_result.models:
                period = model.periods.period

                inlet_pressure_eval = get_requested_compressor_pressures(
                    energy_usage_model=component.energy_usage_model,
                    pressure_type=CompressorPressureType.INLET_PRESSURE,
                    name=model.name,
                    operational_settings_used=consumer_result.component_result.operational_settings_used
                    if consumer_node_info.component_type == ComponentType.COMPRESSOR_SYSTEM
                    else None,
                    model_periods=model.periods,
                )
                outlet_pressure_eval = get_requested_compressor_pressures(
                    energy_usage_model=component.energy_usage_model,
                    pressure_type=CompressorPressureType.OUTLET_PRESSURE,
                    name=model.name,
                    operational_settings_used=consumer_result.component_result.operational_settings_used
                    if consumer_node_info.component_type == ComponentType.COMPRESSOR_SYSTEM
                    else None,
                    model_periods=model.periods,
                )

                requested_inlet_pressure = TimeSeriesFloat(
                    periods=graph_result.variables_map.get_periods(),
                    values=graph_result.variables_map.evaluate(inlet_pressure_eval).tolist(),
                    unit=Unit.BARA,
                ).for_period(period=period)

                requested_outlet_pressure = TimeSeriesFloat(
                    periods=graph_result.variables_map.get_periods(),
                    values=graph_result.variables_map.evaluate(outlet_pressure_eval).tolist(),
                    unit=Unit.BARA,
                ).for_period(period=period)

                model_stage_results = []
                # Convert rates in stage results from lists to time series:
                for i, stage_result in enumerate(model.stage_results):
                    model_stage_result = CompressorModelStageResult(
                        chart=stage_result.chart,
                        chart_area_flags=stage_result.chart_area_flags,
                        energy_usage_unit=stage_result.energy_usage_unit,
                        power_unit=stage_result.power_unit,
                        fluid_composition=stage_result.fluid_composition,
                        asv_recirculation_loss_mw=TimeSeriesRate(
                            periods=model.periods,
                            rate_type=RateType.STREAM_DAY,
                            regularity=regularity.for_periods(model.periods).values,
                            values=stage_result.asv_recirculation_loss_mw
                            if stage_result.asv_recirculation_loss_mw is not None
                            else [math.nan] * len(model.periods),
                            unit=Unit.MEGA_WATT,
                        ),
                        head_exceeds_maximum=TimeSeriesBoolean(
                            periods=model.periods,
                            values=stage_result.head_exceeds_maximum
                            if stage_result.asv_recirculation_loss_mw is not None
                            else [math.nan] * len(model.periods),
                            unit=Unit.NONE,
                        ),
                        is_valid=TimeSeriesBoolean(
                            periods=model.periods,
                            values=stage_result.is_valid,
                            unit=Unit.NONE,
                        ),
                        polytropic_efficiency=TimeSeriesFloat(
                            periods=model.periods,
                            values=stage_result.polytropic_efficiency
                            if stage_result.polytropic_efficiency is not None
                            else [math.nan] * len(model.periods),
                            unit=Unit.FRACTION,
                        ),
                        polytropic_enthalpy_change_before_choke_kJ_per_kg=TimeSeriesFloat(
                            periods=model.periods,
                            values=stage_result.polytropic_enthalpy_change_before_choke_kJ_per_kg
                            if stage_result.polytropic_enthalpy_change_before_choke_kJ_per_kg is not None
                            else [math.nan] * len(model.periods),
                            unit=Unit.POLYTROPIC_HEAD_KILO_JOULE_PER_KG,
                        ),
                        polytropic_enthalpy_change_kJ_per_kg=TimeSeriesFloat(
                            periods=model.periods,
                            values=stage_result.polytropic_enthalpy_change_kJ_per_kg
                            if stage_result.polytropic_enthalpy_change_kJ_per_kg is not None
                            else [math.nan] * len(model.periods),
                            unit=Unit.POLYTROPIC_HEAD_KILO_JOULE_PER_KG,
                        ),
                        polytropic_head_kJ_per_kg=TimeSeriesFloat(
                            periods=model.periods,
                            values=stage_result.polytropic_head_kJ_per_kg
                            if stage_result.polytropic_head_kJ_per_kg is not None
                            else [math.nan] * len(model.periods),
                            unit=Unit.POLYTROPIC_HEAD_KILO_JOULE_PER_KG,
                        ),
                        energy_usage=TimeSeriesRate(
                            periods=model.periods,
                            values=stage_result.energy_usage
                            if stage_result.energy_usage is not None
                            else [math.nan] * len(model.periods),
                            unit=stage_result.energy_usage_unit,
                            rate_type=RateType.STREAM_DAY,
                            regularity=regularity.for_periods(model.periods).values,
                        ),
                        mass_rate_kg_per_hr=TimeSeriesFloat(
                            periods=model.periods,
                            values=stage_result.mass_rate_kg_per_hr
                            if stage_result.mass_rate_kg_per_hr is not None
                            else [math.nan] * len(model.periods),
                            unit=Unit.KILO_PER_HOUR,
                        ),
                        mass_rate_before_asv_kg_per_hr=TimeSeriesFloat(
                            periods=model.periods,
                            values=stage_result.mass_rate_before_asv_kg_per_hr
                            if stage_result.mass_rate_before_asv_kg_per_hr is not None
                            else [math.nan] * len(model.periods),
                            unit=Unit.KILO_PER_HOUR,
                        ),
                        power=TimeSeriesRate(
                            periods=model.periods,
                            values=stage_result.power
                            if stage_result.power is not None
                            else [math.nan] * len(model.periods),
                            unit=stage_result.power_unit,
                            rate_type=RateType.STREAM_DAY,
                            regularity=regularity.for_periods(model.periods).values,
                        ),
                        pressure_is_choked=TimeSeriesBoolean(
                            periods=model.periods,
                            values=stage_result.pressure_is_choked
                            if stage_result.pressure_is_choked is not None
                            else [math.nan] * len(model.periods),
                            unit=Unit.NONE,
                        ),
                        rate_exceeds_maximum=TimeSeriesBoolean(
                            periods=model.periods,
                            values=stage_result.rate_exceeds_maximum
                            if stage_result.rate_exceeds_maximum is not None
                            else [math.nan] * len(model.periods),
                            unit=Unit.NONE,
                        ),
                        rate_has_recirculation=TimeSeriesBoolean(
                            periods=model.periods,
                            values=stage_result.rate_has_recirculation
                            if stage_result.rate_has_recirculation is not None
                            else [math.nan] * len(model.periods),
                            unit=Unit.NONE,
                        ),
                        speed=TimeSeriesFloat(
                            periods=model.periods,
                            values=stage_result.speed
                            if stage_result.speed is not None
                            else [math.nan] * len(model.periods),
                            unit=Unit.SPEED_RPM,
                        ),
                        inlet_stream_condition=CompressorStreamConditionResult(
                            actual_rate_m3_per_hr=TimeSeriesFloat(
                                periods=model.periods,
                                values=stage_result.inlet_stream_condition.actual_rate_m3_per_hr
                                if stage_result.inlet_stream_condition.actual_rate_m3_per_hr is not None
                                else [math.nan] * len(model.periods),
                                unit=Unit.ACTUAL_VOLUMETRIC_M3_PER_HOUR,
                            ),
                            actual_rate_before_asv_m3_per_hr=TimeSeriesFloat(
                                periods=model.periods,
                                values=stage_result.inlet_stream_condition.actual_rate_before_asv_m3_per_hr
                                if stage_result.inlet_stream_condition.actual_rate_before_asv_m3_per_hr is not None
                                else [math.nan] * len(model.periods),
                                unit=Unit.ACTUAL_VOLUMETRIC_M3_PER_HOUR,
                            ),
                            standard_rate_sm3_per_day=TimeSeriesRate(
                                periods=model.periods,
                                values=stage_result.inlet_stream_condition.standard_rate_sm3_per_day
                                if stage_result.inlet_stream_condition.standard_rate_sm3_per_day is not None
                                else [math.nan] * len(model.periods),
                                unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                                rate_type=RateType.STREAM_DAY,
                                regularity=regularity.for_periods(model.periods).values,
                            ),
                            standard_rate_before_asv_sm3_per_day=TimeSeriesRate(
                                periods=model.periods,
                                values=stage_result.inlet_stream_condition.standard_rate_before_asv_sm3_per_day
                                if stage_result.inlet_stream_condition.standard_rate_before_asv_sm3_per_day is not None
                                else [math.nan] * len(model.periods),
                                unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                                rate_type=RateType.STREAM_DAY,
                                regularity=regularity.for_periods(model.periods).values,
                            ),
                            kappa=TimeSeriesFloat(
                                periods=model.periods,
                                values=stage_result.inlet_stream_condition.kappa
                                if stage_result.inlet_stream_condition.kappa is not None
                                else [math.nan] * len(model.periods),
                                unit=Unit.NONE,
                            ),
                            density_kg_per_m3=TimeSeriesFloat(
                                periods=model.periods,
                                values=stage_result.inlet_stream_condition.density_kg_per_m3
                                if stage_result.inlet_stream_condition.density_kg_per_m3 is not None
                                else [math.nan] * len(model.periods),
                                unit=Unit.KG_M3,
                            ),
                            pressure=TimeSeriesFloat(
                                periods=model.periods,
                                values=stage_result.inlet_stream_condition.pressure
                                if stage_result.inlet_stream_condition.pressure is not None
                                else [math.nan] * len(model.periods),
                                unit=Unit.BARA,
                            ),
                            temperature_kelvin=TimeSeriesFloat(
                                periods=model.periods,
                                values=stage_result.inlet_stream_condition.temperature_kelvin
                                if stage_result.inlet_stream_condition.temperature_kelvin is not None
                                else [math.nan] * len(model.periods),
                                unit=Unit.KELVIN,
                            ),
                            z=TimeSeriesFloat(
                                periods=model.periods,
                                values=stage_result.inlet_stream_condition.z
                                if stage_result.inlet_stream_condition.z is not None
                                else [math.nan] * len(model.periods),
                                unit=Unit.NONE,
                            ),
                            periods=model.periods,
                            name="Inlet stream condition",
                        ),
                        outlet_stream_condition=CompressorStreamConditionResult(
                            actual_rate_m3_per_hr=TimeSeriesFloat(
                                periods=model.periods,
                                values=stage_result.outlet_stream_condition.actual_rate_m3_per_hr
                                if stage_result.outlet_stream_condition.actual_rate_m3_per_hr is not None
                                else [math.nan] * len(model.periods),
                                unit=Unit.ACTUAL_VOLUMETRIC_M3_PER_HOUR,
                            ),
                            actual_rate_before_asv_m3_per_hr=TimeSeriesFloat(
                                periods=model.periods,
                                values=stage_result.outlet_stream_condition.actual_rate_before_asv_m3_per_hr
                                if stage_result.outlet_stream_condition.actual_rate_before_asv_m3_per_hr is not None
                                else [math.nan] * len(model.periods),
                                unit=Unit.ACTUAL_VOLUMETRIC_M3_PER_HOUR,
                            ),
                            standard_rate_sm3_per_day=TimeSeriesRate(
                                periods=model.periods,
                                values=stage_result.outlet_stream_condition.standard_rate_sm3_per_day
                                if stage_result.outlet_stream_condition.standard_rate_sm3_per_day is not None
                                else [math.nan] * len(model.periods),
                                unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                                rate_type=RateType.STREAM_DAY,
                                regularity=regularity.for_periods(model.periods).values,
                            ),
                            standard_rate_before_asv_sm3_per_day=TimeSeriesRate(
                                periods=model.periods,
                                values=stage_result.outlet_stream_condition.standard_rate_before_asv_sm3_per_day
                                if stage_result.outlet_stream_condition.standard_rate_before_asv_sm3_per_day is not None
                                else [math.nan] * len(model.periods),
                                unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                                rate_type=RateType.STREAM_DAY,
                                regularity=regularity.for_periods(model.periods).values,
                            ),
                            kappa=TimeSeriesFloat(
                                periods=model.periods,
                                values=stage_result.outlet_stream_condition.kappa
                                if stage_result.outlet_stream_condition.kappa is not None
                                else [math.nan] * len(model.periods),
                                unit=Unit.NONE,
                            ),
                            density_kg_per_m3=TimeSeriesFloat(
                                periods=model.periods,
                                values=stage_result.outlet_stream_condition.density_kg_per_m3
                                if stage_result.outlet_stream_condition.density_kg_per_m3 is not None
                                else [math.nan] * len(model.periods),
                                unit=Unit.KG_M3,
                            ),
                            pressure=TimeSeriesFloat(
                                periods=model.periods,
                                values=stage_result.outlet_stream_condition.pressure
                                if stage_result.outlet_stream_condition.pressure is not None
                                else [math.nan] * len(model.periods),
                                unit=Unit.BARA,
                            ),
                            temperature_kelvin=TimeSeriesFloat(
                                periods=model.periods,
                                values=stage_result.outlet_stream_condition.temperature_kelvin
                                if stage_result.outlet_stream_condition.temperature_kelvin is not None
                                else [math.nan] * len(model.periods),
                                unit=Unit.KELVIN,
                            ),
                            z=TimeSeriesFloat(
                                periods=model.periods,
                                values=stage_result.outlet_stream_condition.z
                                if stage_result.outlet_stream_condition.z is not None
                                else [math.nan] * len(model.periods),
                                unit=Unit.NONE,
                            ),
                            periods=model.periods,
                            name="Outlet stream condition",
                        ),
                        name=f"Stage {i + 1}",
                        periods=model.periods,
                    )

                    model_stage_results.append(model_stage_result)

                turbine_result = (
                    TurbineModelResult(
                        energy_usage_unit=model.turbine_result.energy_usage_unit,
                        power_unit=model.turbine_result.power_unit,
                        efficiency=TimeSeriesFloat(
                            periods=model.periods,
                            values=model.turbine_result.efficiency
                            if model.turbine_result.efficiency is not None
                            else [math.nan] * len(model.periods),
                            unit=Unit.FRACTION,
                        ),
                        energy_usage=TimeSeriesRate(
                            periods=model.periods,
                            values=model.turbine_result.energy_usage
                            if model.turbine_result.energy_usage is not None
                            else [math.nan] * len(model.periods),
                            unit=model.turbine_result.energy_usage_unit,
                            rate_type=RateType.STREAM_DAY,
                            regularity=regularity.for_periods(model.periods).values,
                        ),
                        exceeds_maximum_load=TimeSeriesBoolean(
                            periods=model.periods,
                            values=model.turbine_result.exceeds_maximum_load
                            if model.turbine_result.exceeds_maximum_load is not None
                            else [math.nan] * len(model.periods),
                            unit=Unit.NONE,
                        ),
                        fuel_rate=TimeSeriesRate(
                            periods=model.periods,
                            values=model.turbine_result.fuel_rate
                            if model.turbine_result.fuel_rate is not None
                            else [math.nan] * len(model.periods),
                            unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                            rate_type=RateType.STREAM_DAY,
                            regularity=regularity.for_periods(model.periods).values,
                        ),
                        is_valid=TimeSeriesBoolean(
                            periods=model.periods,
                            values=model.turbine_result.is_valid,
                            unit=Unit.NONE,
                        ),
                        load=TimeSeriesRate(
                            periods=model.periods,
                            values=model.turbine_result.load
                            if model.turbine_result.load is not None
                            else [math.nan] * len(model.periods),
                            unit=model.turbine_result.energy_usage_unit,
                            rate_type=RateType.STREAM_DAY,
                            regularity=regularity.for_periods(model.periods).values,
                        ),
                        power=TimeSeriesRate(
                            periods=model.periods,
                            values=model.turbine_result.power
                            if model.turbine_result.power is not None
                            else [math.nan] * len(model.periods),
                            unit=model.turbine_result.power_unit,
                            rate_type=RateType.STREAM_DAY,
                            regularity=regularity.for_periods(model.periods).values,
                        ),
                        periods=model.periods,
                        name=model.name,
                    )
                    if model.turbine_result is not None
                    else None
                )

                inlet_stream_condition = CompressorStreamConditionResult(
                    actual_rate_m3_per_hr=TimeSeriesFloat(
                        periods=model.periods,
                        values=model.inlet_stream_condition.actual_rate_m3_per_hr
                        if model.inlet_stream_condition.actual_rate_m3_per_hr is not None
                        else [math.nan] * len(model.periods),
                        unit=Unit.ACTUAL_VOLUMETRIC_M3_PER_HOUR,
                    ),
                    actual_rate_before_asv_m3_per_hr=TimeSeriesFloat(
                        periods=model.periods,
                        values=[math.nan] * len(model.periods),
                        unit=Unit.ACTUAL_VOLUMETRIC_M3_PER_HOUR,
                    ),  # not relevant for compressor train, only for stage
                    standard_rate_sm3_per_day=TimeSeriesRate(
                        periods=model.periods,
                        values=model.inlet_stream_condition.standard_rate_sm3_per_day
                        if model.inlet_stream_condition.standard_rate_sm3_per_day is not None
                        else [math.nan] * len(model.periods),
                        unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                        rate_type=RateType.STREAM_DAY,
                        regularity=regularity.for_periods(model.periods).values,
                    ),
                    standard_rate_before_asv_sm3_per_day=TimeSeriesRate(
                        periods=model.periods,
                        values=[math.nan] * len(model.periods),
                        unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                        rate_type=RateType.STREAM_DAY,
                        regularity=regularity.for_periods(model.periods).values,
                    ),  # not relevant for compressor train, only for stage
                    kappa=TimeSeriesFloat(
                        periods=model.periods,
                        values=model.inlet_stream_condition.kappa
                        if model.inlet_stream_condition.kappa is not None
                        else [math.nan] * len(model.periods),
                        unit=Unit.NONE,
                    ),
                    density_kg_per_m3=TimeSeriesFloat(
                        periods=model.periods,
                        values=model.inlet_stream_condition.density_kg_per_m3
                        if model.inlet_stream_condition.density_kg_per_m3 is not None
                        else [math.nan] * len(model.periods),
                        unit=Unit.KG_M3,
                    ),
                    pressure=TimeSeriesFloat(
                        periods=model.periods,
                        values=model.inlet_stream_condition.pressure
                        if model.inlet_stream_condition.pressure is not None
                        else [math.nan] * len(model.periods),
                        unit=Unit.BARA,
                    ),
                    temperature_kelvin=TimeSeriesFloat(
                        periods=model.periods,
                        values=model.inlet_stream_condition.temperature_kelvin
                        if model.inlet_stream_condition.temperature_kelvin is not None
                        else [math.nan] * len(model.periods),
                        unit=Unit.KELVIN,
                    ),
                    z=TimeSeriesFloat(
                        periods=model.periods,
                        values=model.inlet_stream_condition.z
                        if model.inlet_stream_condition.z is not None
                        else [math.nan] * len(model.periods),
                        unit=Unit.NONE,
                    ),
                    periods=model.periods,
                    name="Inlet stream condition",
                )

                outlet_stream_condition = CompressorStreamConditionResult(
                    actual_rate_m3_per_hr=TimeSeriesFloat(
                        periods=model.periods,
                        values=model.outlet_stream_condition.actual_rate_m3_per_hr
                        if model.outlet_stream_condition.actual_rate_m3_per_hr is not None
                        else [math.nan] * len(model.periods),
                        unit=Unit.ACTUAL_VOLUMETRIC_M3_PER_HOUR,
                    ),
                    actual_rate_before_asv_m3_per_hr=TimeSeriesFloat(
                        periods=model.periods,
                        values=[math.nan] * len(model.periods),
                        unit=Unit.ACTUAL_VOLUMETRIC_M3_PER_HOUR,
                    ),  # not relevant for compressor train, only for stage
                    standard_rate_sm3_per_day=TimeSeriesRate(
                        periods=model.periods,
                        values=model.outlet_stream_condition.standard_rate_sm3_per_day
                        if model.outlet_stream_condition.standard_rate_sm3_per_day is not None
                        else [math.nan] * len(model.periods),
                        unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                        rate_type=RateType.STREAM_DAY,
                        regularity=regularity.for_periods(model.periods).values,
                    ),
                    standard_rate_before_asv_sm3_per_day=TimeSeriesRate(
                        periods=model.periods,
                        values=[math.nan] * len(model.periods),
                        unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                        rate_type=RateType.STREAM_DAY,
                        regularity=regularity.for_periods(model.periods).values,
                    ),  # not relevant for compressor train, only for stage
                    kappa=TimeSeriesFloat(
                        periods=model.periods,
                        values=model.outlet_stream_condition.kappa
                        if model.outlet_stream_condition.kappa is not None
                        else [math.nan] * len(model.periods),
                        unit=Unit.NONE,
                    ),
                    density_kg_per_m3=TimeSeriesFloat(
                        periods=model.periods,
                        values=model.outlet_stream_condition.density_kg_per_m3
                        if model.outlet_stream_condition.density_kg_per_m3 is not None
                        else [math.nan] * len(model.periods),
                        unit=Unit.KG_M3,
                    ),
                    pressure=TimeSeriesFloat(
                        periods=model.periods,
                        values=model.outlet_stream_condition.pressure
                        if model.outlet_stream_condition.pressure is not None
                        else [math.nan] * len(model.periods),
                        unit=Unit.BARA,
                    ),
                    temperature_kelvin=TimeSeriesFloat(
                        periods=model.periods,
                        values=model.outlet_stream_condition.temperature_kelvin
                        if model.outlet_stream_condition.temperature_kelvin is not None
                        else [math.nan] * len(model.periods),
                        unit=Unit.KELVIN,
                    ),
                    z=TimeSeriesFloat(
                        periods=model.periods,
                        values=model.outlet_stream_condition.z
                        if model.outlet_stream_condition.z is not None
                        else [math.nan] * len(model.periods),
                        unit=Unit.NONE,
                    ),
                    periods=model.periods,
                    name="Outlet stream condition",
                )

                if len(model.rate_sm3_day) > 0 and isinstance(model.rate_sm3_day[0], list):
                    # Handle multi stream
                    # Select the first rate from multi stream, only a workaround until we have more info by using
                    # streams
                    rate = TimeSeriesRate(
                        periods=model.periods,
                        values=model.rate_sm3_day[0],
                        unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                        rate_type=RateType.STREAM_DAY,
                        regularity=regularity.for_periods(model.periods).values,
                    )
                    maximum_rate = TimeSeriesRate(
                        periods=model.periods,
                        values=model.max_standard_rate[0]  # WORKAROUND: We only pick max rate for first stream for now
                        if model.max_standard_rate is not None
                        else [math.nan] * len(model.periods),
                        unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                        rate_type=RateType.STREAM_DAY,
                        regularity=regularity.for_periods(model.periods).values,
                    )
                else:
                    rate = TimeSeriesRate(
                        periods=model.periods,
                        values=model.rate_sm3_day,
                        unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                        rate_type=RateType.STREAM_DAY,
                        regularity=regularity.for_periods(model.periods).values,
                    )
                    maximum_rate = TimeSeriesRate(
                        periods=model.periods,
                        values=model.max_standard_rate
                        if model.max_standard_rate is not None
                        else [math.nan] * len(model.periods),
                        unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                        rate_type=RateType.STREAM_DAY,
                        regularity=regularity.for_periods(model.periods).values,
                    )

                models.extend(
                    [
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
                            turbine_result=turbine_result,
                            inlet_stream_condition=inlet_stream_condition,
                            outlet_stream_condition=outlet_stream_condition,
                        )
                    ]
                )
        elif consumer_node_info.component_type in [ComponentType.PUMP, ComponentType.PUMP_SYSTEM]:
            for model in consumer_result.models:
                models.extend(
                    [
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
                            inlet_liquid_rate_m3_per_day=TimeSeriesRate(
                                periods=model.periods,
                                values=model.inlet_liquid_rate_m3_per_day
                                if model.inlet_liquid_rate_m3_per_day is not None
                                else [math.nan] * len(model.periods),
                                unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                                rate_type=RateType.STREAM_DAY,
                                regularity=regularity.for_periods(model.periods).values,
                            ),
                            inlet_pressure_bar=TimeSeriesFloat(
                                periods=model.periods,
                                values=model.inlet_pressure_bar
                                if model.inlet_pressure_bar is not None
                                else [math.nan] * len(model.periods),
                                unit=Unit.BARA,
                            ),
                            outlet_pressure_bar=TimeSeriesFloat(
                                periods=model.periods,
                                values=model.outlet_pressure_bar
                                if model.outlet_pressure_bar is not None
                                else [math.nan] * len(model.periods),
                                unit=Unit.BARA,
                            ),
                            operational_head=TimeSeriesFloat(
                                periods=model.periods,
                                values=model.operational_head
                                if model.operational_head is not None
                                else [math.nan] * len(model.periods),
                                unit=Unit.POLYTROPIC_HEAD_JOULE_PER_KG,
                            ),
                        )
                    ]
                )

        else:
            models.extend(
                [
                    TypeAdapter(libecalc.presentation.json_result.result.ConsumerModelResult).validate_python(
                        {
                            **model.model_dump(),
                            "parent": consumer_id,
                            "componentType": model.component_type.value,
                            "component_level": ComponentLevel.MODEL,
                            "energy_usage_cumulative": TimeSeriesRate.from_timeseries_stream_day_rate(
                                model.energy_usage, regularity=regularity
                            )
                            .to_volumes()
                            .cumulative()
                            .model_dump(),
                            "power_cumulative": (
                                TimeSeriesRate.from_timeseries_stream_day_rate(model.power, regularity=regularity)
                                .to_volumes()
                                .to_unit(Unit.GIGA_WATT_HOURS)
                                .cumulative()
                                .model_dump()
                                if model.power is not None
                                else None
                            ),
                            "power": TimeSeriesRate.from_timeseries_stream_day_rate(model.power, regularity=regularity),
                            "energy_usage": TimeSeriesRate.from_timeseries_stream_day_rate(
                                model.energy_usage, regularity=regularity
                            ),
                        }
                    )
                    for model in consumer_result.models
                ]
            )

        obj: libecalc.presentation.json_result.result.ComponentResult
        if consumer_node_info.component_type == ComponentType.GENERATOR_SET:
            obj = libecalc.presentation.json_result.result.results.GeneratorSetResult(
                name=consumer_node_info.name,
                parent=graph_result.graph.get_predecessor(consumer_id),
                component_level=consumer_node_info.component_level,
                componentType=consumer_node_info.component_type.value,
                emissions=_parse_emissions(graph_result.emission_results[consumer_id], regularity)
                if consumer_id in graph_result.emission_results
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
        elif consumer_node_info.component_type == ComponentType.PUMP:
            obj = libecalc.presentation.json_result.result.results.PumpResult(
                name=consumer_node_info.name,
                parent=graph_result.graph.get_predecessor(consumer_id),
                component_level=consumer_node_info.component_level,
                componentType=consumer_node_info.component_type.value,
                emissions=_parse_emissions(graph_result.emission_results[consumer_id], regularity)
                if consumer_id in graph_result.emission_results
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
        elif consumer_node_info.component_type == ComponentType.COMPRESSOR:
            obj = libecalc.presentation.json_result.result.results.CompressorResult(
                name=consumer_node_info.name,
                parent=graph_result.graph.get_predecessor(consumer_id),
                component_level=consumer_node_info.component_level,
                componentType=consumer_node_info.component_type.value,
                emissions=_parse_emissions(graph_result.emission_results[consumer_id], regularity)
                if consumer_id in graph_result.emission_results
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
        else:  # COMPRESSOR_SYSTEM, PUMP_SYSTEM, GENERIC, TURBINE, VENTING_EMITTER
            emissions = (
                _parse_emissions(graph_result.emission_results[consumer_id], regularity)
                if consumer_id in graph_result.emission_results
                else {}
            )
            obj = TypeAdapter(libecalc.presentation.json_result.result.ComponentResult).validate_python(
                {
                    **consumer_result.component_result.model_dump(exclude={"typ"}),
                    "name": consumer_node_info.name,
                    "parent": graph_result.graph.get_predecessor(consumer_id),
                    "component_level": consumer_node_info.component_level,
                    "componentType": consumer_node_info.component_type.value,
                    "emissions": emissions,
                    "energy_usage_cumulative": TimeSeriesRate.from_timeseries_stream_day_rate(
                        consumer_result.component_result.energy_usage, regularity=regularity
                    )
                    .to_volumes()
                    .cumulative()
                    .model_dump(),
                    "power_cumulative": TimeSeriesRate.from_timeseries_stream_day_rate(
                        consumer_result.component_result.power, regularity=regularity
                    )
                    .to_volumes()
                    .to_unit(Unit.GIGA_WATT_HOURS)
                    .cumulative()
                    .model_dump()
                    if consumer_result.component_result.power is not None
                    else None,
                    "power": TimeSeriesRate.from_timeseries_stream_day_rate(
                        consumer_result.component_result.power, regularity=regularity
                    ),
                    "energy_usage": TimeSeriesRate.from_timeseries_stream_day_rate(
                        consumer_result.component_result.energy_usage, regularity=regularity
                    ).to_calendar_day()
                    if consumer_result.component_result.energy_usage.unit == Unit.STANDARD_CUBIC_METER_PER_DAY
                    else TimeSeriesRate.from_timeseries_stream_day_rate(
                        consumer_result.component_result.energy_usage, regularity=regularity
                    ).to_stream_day(),
                },
            )

        sub_components.append(obj)

    # When only venting emitters are specified, without a generator set: the installation result
    # is empty for this installation. Ensure that the installation regularity is found, even if only
    # venting emitters are defined for one installation:
    if len(installation_results) < len(asset.installations):
        regularities = {
            installation.id: TimeSeriesFloat(
                values=graph_result.variables_map.evaluate(expression=TemporalModel(installation.regularity)).tolist(),
                unit=Unit.NONE,
                periods=graph_result.variables_map.get_periods(),
            )
            for installation in asset.installations
        }

    time_series_zero = TimeSeriesRate(
        values=[0] * graph_result.variables_map.number_of_periods,
        periods=graph_result.variables_map.get_periods(),
        unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
        rate_type=RateType.CALENDAR_DAY,
        regularity=[1] * graph_result.variables_map.number_of_periods,
    )

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
                    emissions=_parse_emissions(
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

    # dto timeseries
    asset_hydrocarbon_export_rate_core = (
        reduce(
            operator.add,
            [installation.hydrocarbon_export_rate for installation in installation_results],
        )
        if installation_results
        else time_series_zero
    )

    emission_dto_results = _convert_to_timeseries(
        graph_result,
        graph_result.emission_results,
        regularities,
    )
    asset_aggregated_emissions = aggregate_emissions(list(emission_dto_results.values()))

    asset_power_core = (
        reduce(
            operator.add,
            [installation.power for installation in installation_results if installation.power is not None],
        )
        if installation_results
        else None
    )

    asset_power_electrical_core = (
        reduce(
            operator.add,
            [
                installation.power_electrical
                for installation in installation_results
                if installation.power_electrical is not None
            ],
        )
        if installation_results
        else None
    )

    asset_power_mechanical_core = (
        reduce(
            operator.add,
            [
                installation.power_mechanical
                for installation in installation_results
                if installation.power_mechanical is not None
            ],
        )
        if installation_results
        else None
    )

    asset_power_cumulative = (
        asset_power_core.to_volumes().to_unit(Unit.GIGA_WATT_HOURS).cumulative() if installation_results else None
    )

    asset_power_electrical_cumulative = (
        asset_power_electrical_core.to_volumes().to_unit(Unit.GIGA_WATT_HOURS).cumulative()
        if asset_power_electrical_core
        else None
    )

    asset_power_mechanical_cumulative = (
        asset_power_mechanical_core.to_volumes().to_unit(Unit.GIGA_WATT_HOURS).cumulative()
        if asset_power_mechanical_core
        else None
    )

    asset_energy_usage_core = (
        reduce(
            operator.add,
            [installation.energy_usage for installation in installation_results],
        )
        if installation_results
        else time_series_zero
    )

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
        emissions=_to_full_result(asset_aggregated_emissions),
    )

    return Numbers.format_results_to_precision(
        libecalc.presentation.json_result.result.results.EcalcModelResult(
            component_result=asset_result_dto,
            sub_components=sub_components,
            models=models,
        ),
        precision=6,
    )
