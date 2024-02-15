import math
import operator
from collections import defaultdict
from datetime import datetime
from functools import reduce
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, TypeAdapter

import libecalc
from libecalc import dto
from libecalc.common.component_info.component_level import ComponentLevel
from libecalc.common.component_info.compressor import CompressorPressureType
from libecalc.common.decorators.feature_flags import Feature
from libecalc.common.errors.exceptions import ProgrammingError
from libecalc.common.temporal_model import TemporalExpression, TemporalModel
from libecalc.common.time_utils import Period
from libecalc.common.units import Unit
from libecalc.common.utils.calculate_emission_intensity import (
    compute_emission_intensity_by_yearly_buckets,
)
from libecalc.common.utils.rates import (
    RateType,
    TimeSeriesBoolean,
    TimeSeriesFloat,
    TimeSeriesInt,
    TimeSeriesRate,
)
from libecalc.core.result import ComponentResult, EcalcModelResult
from libecalc.core.result.emission import EmissionResult
from libecalc.dto.base import ComponentType
from libecalc.dto.component_graph import ComponentGraph
from libecalc.dto.models.consumer_system import CompressorSystemConsumerFunction
from libecalc.dto.result.emission import EmissionIntensityResult, PartialEmissionResult
from libecalc.dto.result.results import (
    CompressorModelResult,
    CompressorModelStageResult,
    CompressorStreamConditionResult,
    PumpModelResult,
    TurbineModelResult,
)
from libecalc.dto.utils.aggregators import aggregate_emissions, aggregate_is_valid
from libecalc.expression import Expression


class EnergyCalculatorResult(BaseModel):
    consumer_results: Dict[str, EcalcModelResult]
    emission_results: Dict[str, Dict[str, EmissionResult]]
    variables_map: dto.VariablesMap


class GraphResult:
    def __init__(
        self,
        graph: ComponentGraph,
        consumer_results: Dict[str, EcalcModelResult],
        emission_results: Dict[str, Dict[str, EmissionResult]],
        variables_map: dto.VariablesMap,
    ):
        self.graph = graph
        self.consumer_results = consumer_results
        self.emission_results = emission_results
        self.variables_map = variables_map

    @staticmethod
    def _compute_intensity(
        hydrocarbon_export_rate: TimeSeriesRate,
        emissions: Dict[str, PartialEmissionResult],
    ) -> List[EmissionIntensityResult]:
        hydrocarbon_export_cumulative = hydrocarbon_export_rate.to_volumes().cumulative()
        emission_intensities = []
        for key in emissions:
            cumulative_rate_kg = emissions[key].rate.to_volumes().to_unit(Unit.KILO).cumulative()
            intensity_sm3 = cumulative_rate_kg / hydrocarbon_export_cumulative
            intensity_yearly_sm3 = compute_emission_intensity_by_yearly_buckets(
                emission_cumulative=cumulative_rate_kg,
                hydrocarbon_export_cumulative=hydrocarbon_export_cumulative,
            )
            emission_intensities.append(
                EmissionIntensityResult(
                    name=emissions[key].name,
                    timesteps=emissions[key].timesteps,
                    intensity_sm3=intensity_sm3.model_dump(),  # Converted to TimeSeriesIntensity
                    intensity_boe=intensity_sm3.to_unit(Unit.KG_BOE).model_dump(),
                    intensity_yearly_sm3=intensity_yearly_sm3.model_dump(),
                    intensity_yearly_boe=intensity_yearly_sm3.to_unit(Unit.KG_BOE).model_dump(),
                )
            )
        return emission_intensities

    def _evaluate_installations(self, variables_map: dto.VariablesMap) -> List[libecalc.dto.result.InstallationResult]:
        """
        All subcomponents have already been evaluated, here we basically collect and aggregate the results

        Args:
            variables_map:

        Returns:

        """
        asset_id = self.graph.root
        asset = self.graph.get_node(asset_id)
        installation_results = []
        for installation in asset.installations:
            regularity = TimeSeriesFloat(
                timesteps=variables_map.time_vector,
                values=TemporalExpression.evaluate(
                    temporal_expression=TemporalModel(installation.regularity),
                    variables_map=variables_map,
                ),
                unit=Unit.NONE,
            )
            hydrocarbon_export_rate = TemporalExpression.evaluate(
                temporal_expression=TemporalModel(installation.hydrocarbon_export),
                variables_map=variables_map,
            )
            hydrocarbon_export_rate = TimeSeriesRate(
                timesteps=variables_map.time_vector,
                values=hydrocarbon_export_rate,
                unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                rate_type=RateType.CALENDAR_DAY,
                regularity=regularity.values,
            )

            sub_components = [
                self.consumer_results[component_id].component_result
                for component_id in self.graph.get_successors(installation.id, recursively=True)
                if component_id in self.consumer_results
            ]

            installation_node_info = self.graph.get_node_info(installation.id)
            power = reduce(
                operator.add,
                [
                    TimeSeriesRate.from_timeseries_stream_day_rate(component.power, regularity=regularity)
                    for component in sub_components
                    if self.graph.get_node_info(component.id).component_type == ComponentType.GENERATOR_SET
                ],
                TimeSeriesRate(
                    values=[0.0] * self.variables_map.length,
                    timesteps=self.variables_map.time_vector,
                    unit=Unit.MEGA_WATT,
                    rate_type=RateType.STREAM_DAY,
                    regularity=regularity.values,
                ),  # Initial value, handle no power output from components
            )

            energy_usage = reduce(
                operator.add,
                [
                    TimeSeriesRate.from_timeseries_stream_day_rate(component.energy_usage, regularity=regularity)
                    for component in sub_components
                    if component.energy_usage.unit == Unit.STANDARD_CUBIC_METER_PER_DAY
                ],
            )

            emission_dto_results = self.convert_to_timeseries(self.emission_results, regularity)
            aggregated_emissions = aggregate_emissions(
                [
                    emission_dto_results[fuel_consumer_id]
                    for fuel_consumer_id in self.graph.get_successors(installation.id)
                ]
            )

            installation_results.append(
                libecalc.dto.result.InstallationResult(
                    id=installation.id,
                    name=installation_node_info.name,
                    parent=asset.id,
                    component_level=installation_node_info.component_level,
                    componentType=installation_node_info.component_type,
                    timesteps=variables_map.time_vector,
                    is_valid=TimeSeriesBoolean(
                        timesteps=variables_map.time_vector,
                        values=aggregate_is_valid(sub_components),
                        unit=Unit.NONE,
                    ),
                    power=power,
                    power_cumulative=power.to_volumes().to_unit(Unit.GIGA_WATT_HOURS).cumulative(),
                    energy_usage=energy_usage.to_calendar_day()
                    if energy_usage.unit == Unit.STANDARD_CUBIC_METER_PER_DAY
                    else energy_usage.to_stream_day(),
                    energy_usage_cumulative=energy_usage.to_volumes().cumulative(),
                    hydrocarbon_export_rate=hydrocarbon_export_rate,
                    emissions=self.to_full_result(aggregated_emissions),
                    emission_intensities=self._compute_intensity(
                        hydrocarbon_export_rate=hydrocarbon_export_rate,
                        emissions=aggregated_emissions,
                    ),
                    regularity=TimeSeriesFloat(
                        timesteps=variables_map.time_vector,
                        values=regularity.values,
                        unit=Unit.NONE,
                    ),
                )
            )
        return installation_results

    def get_subgraph(self, node_id: str) -> "GraphResult":
        subgraph = self.graph.get_node(node_id).get_graph()

        return GraphResult(
            graph=subgraph,
            variables_map=self.variables_map,
            consumer_results={
                component_id: consumer_result
                for component_id, consumer_result in self.consumer_results.items()
                if component_id in subgraph
            },
            emission_results={
                component_id: emissions
                for component_id, emissions in self.emission_results.items()
                if component_id in subgraph
            },
        )

    def get_energy_result(self, component_id: str) -> ComponentResult:
        return self.consumer_results[component_id].component_result

    @property
    def timesteps(self):
        return self.variables_map.time_vector

    @staticmethod
    def _parse_emissions(
        emissions: Dict[str, EmissionResult], regularity: TimeSeriesFloat
    ) -> Dict[str, libecalc.dto.result.EmissionResult]:
        """
        Convert emissions from core result format to dto result format.

        Given that core result does NOT have regularity, that needs to be added
        Args:
            emissions:
            regularity:

        Returns:

        """
        return {
            key: libecalc.dto.result.EmissionResult(
                name=key,
                timesteps=emissions[key].timesteps,
                rate=TimeSeriesRate.from_timeseries_stream_day_rate(
                    emissions[key].rate, regularity=regularity
                ).to_calendar_day(),
                cumulative=TimeSeriesRate.from_timeseries_stream_day_rate(emissions[key].rate, regularity=regularity)
                .to_volumes()
                .cumulative(),
            )
            for key in emissions
        }

    def to_full_result(
        self, emissions: Dict[str, PartialEmissionResult]
    ) -> Dict[str, libecalc.dto.result.EmissionResult]:
        """
        From the partial result, generate cumulatives for the full emissions result per installation
        Args:
            emissions:

        Returns:

        """
        return {
            key: libecalc.dto.result.EmissionResult(
                name=key,
                timesteps=emissions[key].timesteps,
                rate=emissions[key].rate,
                cumulative=emissions[key].rate.to_volumes().cumulative(),
            )
            for key in emissions
        }

    @staticmethod
    def operational_setting_used_id(timestep: datetime, operational_settings_used: TimeSeriesInt) -> int:
        timestep_index = operational_settings_used.timesteps.index(timestep)

        operational_setting_id = operational_settings_used.values[timestep_index]

        return operational_setting_id - 1

    @staticmethod
    @Feature.experimental(feature_description="Reporting requested pressures is an experimental feature.")
    def get_requested_compressor_pressures(
        energy_usage_model: Dict[datetime, Any],
        pressure_type: CompressorPressureType,
        name: str,
        model_period: Period,
        model_timesteps: List[datetime],
        operational_settings_used: Optional[TimeSeriesInt] = None,
    ) -> TemporalModel[Expression]:
        """Get temporal model for compressor inlet- and outlet pressures.
        The pressures are the actual pressures defined by user in input.

        :param energy_usage_model: Temporal energy model
        :param pressure_type: Compressor pressure type, inlet- or outlet
        :param name: name of compressor
        :param model_period: start- and stop time for model
        :param model_timesteps: actual timesteps in model
        :param operational_settings_used: time series indicating which priority is active
        :return: Temporal model with pressures as expressions
        """

        evaluated_temporal_energy_usage_models = {}
        default_date = datetime(1900, 1, 1, 0, 0)

        # Extract relevant temporal model:
        if len(energy_usage_model.items()) == 1 and default_date in energy_usage_model:
            model_subset = TemporalModel(energy_usage_model).models[0].model
        else:
            model_subset = TemporalModel({model_period.start: energy_usage_model[model_period.start]}).models[0].model

        if isinstance(model_subset, CompressorSystemConsumerFunction):
            # Loop timesteps in temporal model, to find correct operational settings used:
            for timestep in model_timesteps:
                for compressor in model_subset.compressors:
                    if compressor.name == name:
                        operational_setting_used_id = GraphResult.operational_setting_used_id(
                            timestep=timestep, operational_settings_used=operational_settings_used
                        )

                        operational_setting = model_subset.operational_settings[operational_setting_used_id]

                        # Find correct compressor in case of different pressures for different components in system:
                        compressor_nr = int(
                            [i for i, compressor in enumerate(model_subset.compressors) if compressor.name == name][0]
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
                        evaluated_temporal_energy_usage_models[timestep] = pressures
        else:
            for period, model in TemporalModel(energy_usage_model).items():
                pressures = model.suction_pressure

                if pressure_type.value == CompressorPressureType.OUTLET_PRESSURE:
                    pressures = model.discharge_pressure

                if pressures is None:
                    pressures = math.nan

                if not isinstance(pressures, Expression):
                    pressures = Expression.setup_from_expression(value=pressures)

                evaluated_temporal_energy_usage_models[period.start] = pressures

        return TemporalModel(evaluated_temporal_energy_usage_models)

    def get_asset_result(self) -> libecalc.dto.result.EcalcModelResult:
        asset_id = self.graph.root
        asset = self.graph.get_node(asset_id)

        if not isinstance(asset, dto.Asset):
            raise ProgrammingError("Need an asset graph to get asset result")

        installation_results = self._evaluate_installations(variables_map=self.variables_map)

        regularities: Dict[str, TimeSeriesFloat] = {
            installation.id: installation.regularity for installation in installation_results
        }

        models = []
        sub_components = [*installation_results]
        for consumer_result in self.consumer_results.values():
            consumer_id = consumer_result.component_result.id
            consumer_node_info = self.graph.get_node_info(consumer_id)

            parent_installation_id = self.graph.get_parent_installation_id(consumer_id)
            regularity: TimeSeriesFloat = regularities[parent_installation_id]

            if consumer_node_info.component_type in [ComponentType.COMPRESSOR, ComponentType.COMPRESSOR_SYSTEM]:
                component = self.graph.get_node(consumer_id)

                for model in consumer_result.models:
                    period = Period(model.timesteps[0], model.timesteps[-1])

                    inlet_pressure_eval = GraphResult.get_requested_compressor_pressures(
                        energy_usage_model=component.energy_usage_model,
                        pressure_type=CompressorPressureType.INLET_PRESSURE,
                        name=model.name,
                        operational_settings_used=consumer_result.component_result.operational_settings_used
                        if consumer_node_info.component_type == ComponentType.COMPRESSOR_SYSTEM
                        else None,
                        model_period=period,
                        model_timesteps=model.timesteps,
                    )
                    outlet_pressure_eval = GraphResult.get_requested_compressor_pressures(
                        energy_usage_model=component.energy_usage_model,
                        pressure_type=CompressorPressureType.OUTLET_PRESSURE,
                        name=model.name,
                        operational_settings_used=consumer_result.component_result.operational_settings_used
                        if consumer_node_info.component_type == ComponentType.COMPRESSOR_SYSTEM
                        else None,
                        model_period=period,
                        model_timesteps=model.timesteps,
                    )

                    requested_inlet_pressure = TimeSeriesFloat(
                        timesteps=self.timesteps,
                        values=TemporalExpression.evaluate(inlet_pressure_eval, self.variables_map),
                        unit=Unit.BARA,
                    ).for_period(period=period)

                    requested_outlet_pressure = TimeSeriesFloat(
                        timesteps=self.timesteps,
                        values=TemporalExpression.evaluate(outlet_pressure_eval, self.variables_map),
                        unit=Unit.BARA,
                    ).for_period(period=period)

                    model_stage_results = []
                    # Convert rates in stage results from lists to time series:
                    for stage_result in model.stage_results:
                        model_stage_result = CompressorModelStageResult(
                            chart=stage_result.chart,
                            chart_area_flags=stage_result.chart_area_flags,
                            energy_usage_unit=stage_result.energy_usage_unit,
                            power_unit=stage_result.power_unit,
                            fluid_composition=stage_result.fluid_composition,
                            asv_recirculation_loss_mw=TimeSeriesRate(
                                timesteps=model.timesteps,
                                rate_type=RateType.STREAM_DAY,
                                regularity=regularity.for_timesteps(model.timesteps).values,
                                values=stage_result.asv_recirculation_loss_mw
                                if stage_result.asv_recirculation_loss_mw is not None
                                else [math.nan] * len(model.timesteps),
                                unit=Unit.MEGA_WATT,
                            ),
                            head_exceeds_maximum=TimeSeriesBoolean(
                                timesteps=model.timesteps,
                                values=stage_result.head_exceeds_maximum
                                if stage_result.asv_recirculation_loss_mw is not None
                                else [math.nan] * len(model.timesteps),
                                unit=Unit.NONE,
                            ),
                            is_valid=TimeSeriesBoolean(
                                timesteps=model.timesteps,
                                values=stage_result.is_valid,
                                unit=Unit.NONE,
                            ),
                            polytropic_efficiency=TimeSeriesFloat(
                                timesteps=model.timesteps,
                                values=stage_result.polytropic_efficiency
                                if stage_result.polytropic_efficiency is not None
                                else [math.nan] * len(model.timesteps),
                                unit=Unit.FRACTION,
                            ),
                            polytropic_enthalpy_change_before_choke_kJ_per_kg=TimeSeriesFloat(
                                timesteps=model.timesteps,
                                values=stage_result.polytropic_enthalpy_change_before_choke_kJ_per_kg
                                if stage_result.polytropic_enthalpy_change_before_choke_kJ_per_kg is not None
                                else [math.nan] * len(model.timesteps),
                                unit=Unit.POLYTROPIC_HEAD_KILO_JOULE_PER_KG,
                            ),
                            polytropic_enthalpy_change_kJ_per_kg=TimeSeriesFloat(
                                timesteps=model.timesteps,
                                values=stage_result.polytropic_enthalpy_change_kJ_per_kg
                                if stage_result.polytropic_enthalpy_change_kJ_per_kg is not None
                                else [math.nan] * len(model.timesteps),
                                unit=Unit.POLYTROPIC_HEAD_KILO_JOULE_PER_KG,
                            ),
                            polytropic_head_kJ_per_kg=TimeSeriesFloat(
                                timesteps=model.timesteps,
                                values=stage_result.polytropic_head_kJ_per_kg
                                if stage_result.polytropic_head_kJ_per_kg is not None
                                else [math.nan] * len(model.timesteps),
                                unit=Unit.POLYTROPIC_HEAD_KILO_JOULE_PER_KG,
                            ),
                            energy_usage=TimeSeriesRate(
                                timesteps=model.timesteps,
                                values=stage_result.energy_usage
                                if stage_result.energy_usage is not None
                                else [math.nan] * len(model.timesteps),
                                unit=stage_result.energy_usage_unit,
                                rate_type=RateType.STREAM_DAY,
                                regularity=regularity.for_timesteps(model.timesteps).values,
                            ),
                            mass_rate_kg_per_hr=TimeSeriesRate(
                                timesteps=model.timesteps,
                                values=stage_result.mass_rate_kg_per_hr
                                if stage_result.mass_rate_kg_per_hr is not None
                                else [math.nan] * len(model.timesteps),
                                unit=Unit.KILO_PER_HOUR,
                                rate_type=RateType.STREAM_DAY,
                                regularity=regularity.for_timesteps(model.timesteps).values,
                            ),
                            mass_rate_before_asv_kg_per_hr=TimeSeriesRate(
                                timesteps=model.timesteps,
                                values=stage_result.mass_rate_before_asv_kg_per_hr
                                if stage_result.mass_rate_before_asv_kg_per_hr is not None
                                else [math.nan] * len(model.timesteps),
                                unit=Unit.KILO_PER_HOUR,
                                rate_type=RateType.STREAM_DAY,
                                regularity=regularity.for_timesteps(model.timesteps).values,
                            ),
                            power=TimeSeriesRate(
                                timesteps=model.timesteps,
                                values=stage_result.power
                                if stage_result.power is not None
                                else [math.nan] * len(model.timesteps),
                                unit=stage_result.power_unit,
                                rate_type=RateType.STREAM_DAY,
                                regularity=regularity.for_timesteps(model.timesteps).values,
                            ),
                            pressure_is_choked=TimeSeriesBoolean(
                                timesteps=model.timesteps,
                                values=stage_result.pressure_is_choked
                                if stage_result.pressure_is_choked is not None
                                else [math.nan] * len(model.timesteps),
                                unit=Unit.NONE,
                            ),
                            rate_exceeds_maximum=TimeSeriesBoolean(
                                timesteps=model.timesteps,
                                values=stage_result.rate_exceeds_maximum
                                if stage_result.rate_exceeds_maximum is not None
                                else [math.nan] * len(model.timesteps),
                                unit=Unit.NONE,
                            ),
                            rate_has_recirculation=TimeSeriesBoolean(
                                timesteps=model.timesteps,
                                values=stage_result.rate_has_recirculation
                                if stage_result.rate_has_recirculation is not None
                                else [math.nan] * len(model.timesteps),
                                unit=Unit.NONE,
                            ),
                            speed=TimeSeriesFloat(
                                timesteps=model.timesteps,
                                values=stage_result.speed
                                if stage_result.speed is not None
                                else [math.nan] * len(model.timesteps),
                                unit=Unit.SPEED_RPM,
                            ),
                            inlet_stream_condition=CompressorStreamConditionResult(
                                actual_rate_m3_per_hr=TimeSeriesRate(
                                    timesteps=model.timesteps,
                                    values=stage_result.inlet_stream_condition.actual_rate_m3_per_hr
                                    if stage_result.inlet_stream_condition.actual_rate_m3_per_hr is not None
                                    else [math.nan] * len(model.timesteps),
                                    unit=Unit.ACTUAL_VOLUMETRIC_M3_PER_HOUR,
                                    rate_type=RateType.STREAM_DAY,
                                    regularity=regularity.for_timesteps(model.timesteps).values,
                                ),
                                actual_rate_before_asv_m3_per_hr=TimeSeriesRate(
                                    timesteps=model.timesteps,
                                    values=stage_result.inlet_stream_condition.actual_rate_before_asv_m3_per_hr
                                    if stage_result.inlet_stream_condition.actual_rate_before_asv_m3_per_hr is not None
                                    else [math.nan] * len(model.timesteps),
                                    unit=Unit.ACTUAL_VOLUMETRIC_M3_PER_HOUR,
                                    rate_type=RateType.STREAM_DAY,
                                    regularity=regularity.for_timesteps(model.timesteps).values,
                                ),
                                kappa=TimeSeriesFloat(
                                    timesteps=model.timesteps,
                                    values=stage_result.inlet_stream_condition.kappa
                                    if stage_result.inlet_stream_condition.kappa is not None
                                    else [math.nan] * len(model.timesteps),
                                    unit=Unit.NONE,
                                ),
                                density_kg_per_m3=TimeSeriesRate(
                                    timesteps=model.timesteps,
                                    values=stage_result.inlet_stream_condition.density_kg_per_m3
                                    if stage_result.inlet_stream_condition.density_kg_per_m3 is not None
                                    else [math.nan] * len(model.timesteps),
                                    unit=Unit.KG_M3,
                                    rate_type=RateType.STREAM_DAY,
                                    regularity=regularity.for_timesteps(model.timesteps).values,
                                ),
                                pressure=TimeSeriesFloat(
                                    timesteps=model.timesteps,
                                    values=stage_result.inlet_stream_condition.pressure
                                    if stage_result.inlet_stream_condition.pressure is not None
                                    else [math.nan] * len(model.timesteps),
                                    unit=Unit.BARA,
                                ),
                                pressure_before_choking=TimeSeriesFloat(
                                    timesteps=model.timesteps,
                                    values=stage_result.inlet_stream_condition.pressure_before_choking
                                    if stage_result.inlet_stream_condition.pressure_before_choking is not None
                                    else [math.nan] * len(model.timesteps),
                                    unit=Unit.BARA,
                                ),
                                temperature_kelvin=TimeSeriesFloat(
                                    timesteps=model.timesteps,
                                    values=stage_result.inlet_stream_condition.temperature_kelvin
                                    if stage_result.inlet_stream_condition.temperature_kelvin is not None
                                    else [math.nan] * len(model.timesteps),
                                    unit=Unit.KELVIN,
                                ),
                                z=TimeSeriesFloat(
                                    timesteps=model.timesteps,
                                    values=stage_result.inlet_stream_condition.z
                                    if stage_result.inlet_stream_condition.z is not None
                                    else [math.nan] * len(model.timesteps),
                                    unit=Unit.NONE,
                                ),
                            ),
                            outlet_stream_condition=CompressorStreamConditionResult(
                                actual_rate_m3_per_hr=TimeSeriesRate(
                                    timesteps=model.timesteps,
                                    values=stage_result.outlet_stream_condition.actual_rate_m3_per_hr
                                    if stage_result.outlet_stream_condition.actual_rate_m3_per_hr is not None
                                    else [math.nan] * len(model.timesteps),
                                    unit=Unit.ACTUAL_VOLUMETRIC_M3_PER_HOUR,
                                    rate_type=RateType.STREAM_DAY,
                                    regularity=regularity.for_timesteps(model.timesteps).values,
                                ),
                                actual_rate_before_asv_m3_per_hr=TimeSeriesRate(
                                    timesteps=model.timesteps,
                                    values=stage_result.outlet_stream_condition.actual_rate_before_asv_m3_per_hr
                                    if stage_result.outlet_stream_condition.actual_rate_before_asv_m3_per_hr is not None
                                    else [math.nan] * len(model.timesteps),
                                    unit=Unit.ACTUAL_VOLUMETRIC_M3_PER_HOUR,
                                    rate_type=RateType.STREAM_DAY,
                                    regularity=regularity.for_timesteps(model.timesteps).values,
                                ),
                                kappa=TimeSeriesFloat(
                                    timesteps=model.timesteps,
                                    values=stage_result.outlet_stream_condition.kappa
                                    if stage_result.outlet_stream_condition.kappa is not None
                                    else [math.nan] * len(model.timesteps),
                                    unit=Unit.NONE,
                                ),
                                density_kg_per_m3=TimeSeriesRate(
                                    timesteps=model.timesteps,
                                    values=stage_result.outlet_stream_condition.density_kg_per_m3
                                    if stage_result.outlet_stream_condition.density_kg_per_m3 is not None
                                    else [math.nan] * len(model.timesteps),
                                    unit=Unit.KG_M3,
                                    rate_type=RateType.STREAM_DAY,
                                    regularity=regularity.for_timesteps(model.timesteps).values,
                                ),
                                pressure=TimeSeriesFloat(
                                    timesteps=model.timesteps,
                                    values=stage_result.outlet_stream_condition.pressure
                                    if stage_result.outlet_stream_condition.pressure is not None
                                    else [math.nan] * len(model.timesteps),
                                    unit=Unit.BARA,
                                ),
                                pressure_before_choking=TimeSeriesFloat(
                                    timesteps=model.timesteps,
                                    values=stage_result.outlet_stream_condition.pressure_before_choking
                                    if stage_result.outlet_stream_condition.pressure_before_choking is not None
                                    else [math.nan] * len(model.timesteps),
                                    unit=Unit.BARA,
                                ),
                                temperature_kelvin=TimeSeriesFloat(
                                    timesteps=model.timesteps,
                                    values=stage_result.outlet_stream_condition.temperature_kelvin
                                    if stage_result.outlet_stream_condition.temperature_kelvin is not None
                                    else [math.nan] * len(model.timesteps),
                                    unit=Unit.KELVIN,
                                ),
                                z=TimeSeriesFloat(
                                    timesteps=model.timesteps,
                                    values=stage_result.outlet_stream_condition.z
                                    if stage_result.outlet_stream_condition.z is not None
                                    else [math.nan] * len(model.timesteps),
                                    unit=Unit.NONE,
                                ),
                            ),
                        )

                        model_stage_results.append(model_stage_result)

                    turbine_result = (
                        TurbineModelResult(
                            energy_usage_unit=model.turbine_result.energy_usage_unit,
                            power_unit=model.turbine_result.power_unit,
                            efficiency=TimeSeriesFloat(
                                timesteps=model.timesteps,
                                values=model.turbine_result.efficiency
                                if model.turbine_result.efficiency is not None
                                else [math.nan] * len(model.timesteps),
                                unit=Unit.FRACTION,
                            ),
                            energy_usage=TimeSeriesRate(
                                timesteps=model.timesteps,
                                values=model.turbine_result.energy_usage
                                if model.turbine_result.energy_usage is not None
                                else [math.nan] * len(model.timesteps),
                                unit=model.turbine_result.energy_usage_unit,
                                rate_type=RateType.STREAM_DAY,
                                regularity=regularity.for_timesteps(model.timesteps).values,
                            ),
                            exceeds_maximum_load=TimeSeriesBoolean(
                                timesteps=model.timesteps,
                                values=model.turbine_result.exceeds_maximum_load
                                if model.turbine_result.exceeds_maximum_load is not None
                                else [math.nan] * len(model.timesteps),
                                unit=Unit.NONE,
                            ),
                            fuel_rate=TimeSeriesRate(
                                timesteps=model.timesteps,
                                values=model.turbine_result.fuel_rate
                                if model.turbine_result.fuel_rate is not None
                                else [math.nan] * len(model.timesteps),
                                unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                                rate_type=RateType.STREAM_DAY,
                                regularity=regularity.for_timesteps(model.timesteps).values,
                            ),
                            is_valid=TimeSeriesBoolean(
                                timesteps=model.timesteps,
                                values=model.turbine_result.is_valid,
                                unit=Unit.NONE,
                            ),
                            load=TimeSeriesRate(
                                timesteps=model.timesteps,
                                values=model.turbine_result.load
                                if model.turbine_result.load is not None
                                else [math.nan] * len(model.timesteps),
                                unit=model.turbine_result.energy_usage_unit,
                                rate_type=RateType.STREAM_DAY,
                                regularity=regularity.for_timesteps(model.timesteps).values,
                            ),
                            power=TimeSeriesRate(
                                timesteps=model.timesteps,
                                values=model.turbine_result.power
                                if model.turbine_result.power is not None
                                else [math.nan] * len(model.timesteps),
                                unit=model.turbine_result.power_unit,
                                rate_type=RateType.STREAM_DAY,
                                regularity=regularity.for_timesteps(model.timesteps).values,
                            ),
                        )
                        if model.turbine_result is not None
                        else None
                    )

                    if len(model.rate_sm3_day) > 0 and isinstance(model.rate_sm3_day[0], list):
                        # Handle multi stream
                        # Select the first rate from multi stream, only a workaround until we have more info by using
                        # streams
                        rate = TimeSeriesRate(
                            timesteps=model.timesteps,
                            values=model.rate_sm3_day[0],
                            unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                            rate_type=RateType.STREAM_DAY,
                            regularity=regularity.for_timesteps(model.timesteps).values,
                        )
                        maximum_rate = TimeSeriesRate(
                            timesteps=model.timesteps,
                            values=model.max_standard_rate[
                                0
                            ]  # WORKAROUND: We only pick max rate for first stream for now
                            if model.max_standard_rate is not None
                            else [math.nan] * len(model.timesteps),
                            unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                            rate_type=RateType.STREAM_DAY,
                            regularity=regularity.for_timesteps(model.timesteps).values,
                        )
                    else:
                        rate = TimeSeriesRate(
                            timesteps=model.timesteps,
                            values=model.rate_sm3_day,
                            unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                            rate_type=RateType.STREAM_DAY,
                            regularity=regularity.for_timesteps(model.timesteps).values,
                        )
                        maximum_rate = TimeSeriesRate(
                            timesteps=model.timesteps,
                            values=model.max_standard_rate
                            if model.max_standard_rate is not None
                            else [math.nan] * len(model.timesteps),
                            unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                            rate_type=RateType.STREAM_DAY,
                            regularity=regularity.for_timesteps(model.timesteps).values,
                        )

                    models.extend(
                        [
                            CompressorModelResult(
                                parent=consumer_id,
                                name=model.name,
                                componentType=model.component_type,
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
                                timesteps=model.timesteps,
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
                            )
                        ]
                    )
            elif consumer_node_info.component_type in [ComponentType.PUMP, ComponentType.PUMP_SYSTEM]:
                component = self.graph.get_node(consumer_id)
                for model in consumer_result.models:
                    models.extend(
                        [
                            PumpModelResult(
                                parent=consumer_id,
                                name=model.name,
                                componentType=model.component_type,
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
                                timesteps=model.timesteps,
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
                                    timesteps=model.timesteps,
                                    values=model.inlet_liquid_rate_m3_per_day
                                    if model.inlet_liquid_rate_m3_per_day is not None
                                    else [math.nan] * len(model.timesteps),
                                    unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                                    rate_type=RateType.STREAM_DAY,
                                    regularity=regularity.for_timesteps(model.timesteps).values,
                                ),
                                inlet_pressure_bar=TimeSeriesFloat(
                                    timesteps=model.timesteps,
                                    values=model.inlet_pressure_bar
                                    if model.inlet_pressure_bar is not None
                                    else [math.nan] * len(model.timesteps),
                                    unit=Unit.BARA,
                                ),
                                outlet_pressure_bar=TimeSeriesFloat(
                                    timesteps=model.timesteps,
                                    values=model.outlet_pressure_bar
                                    if model.outlet_pressure_bar is not None
                                    else [math.nan] * len(model.timesteps),
                                    unit=Unit.BARA,
                                ),
                                operational_head=TimeSeriesFloat(
                                    timesteps=model.timesteps,
                                    values=model.operational_head
                                    if model.operational_head is not None
                                    else [math.nan] * len(model.timesteps),
                                    unit=Unit.POLYTROPIC_HEAD_JOULE_PER_KG,
                                ),
                            )
                        ]
                    )

            else:
                models.extend(
                    [
                        TypeAdapter(libecalc.dto.result.ConsumerModelResult).validate_python(
                            {
                                **model.model_dump(),
                                "parent": consumer_id,
                                "componentType": model.component_type,
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
                                "power": TimeSeriesRate.from_timeseries_stream_day_rate(
                                    model.power, regularity=regularity
                                ),
                                "energy_usage": TimeSeriesRate.from_timeseries_stream_day_rate(
                                    model.energy_usage, regularity=regularity
                                ),
                            }
                        )
                        for model in consumer_result.models
                    ]
                )

            obj: libecalc.dto.result.ComponentResult
            if consumer_node_info.component_type == ComponentType.GENERATOR_SET:
                obj = dto.result.results.GeneratorSetResult(
                    name=consumer_node_info.name,
                    parent=self.graph.get_predecessor(consumer_id),
                    component_level=consumer_node_info.component_level,
                    componentType=consumer_node_info.component_type,
                    emissions=self._parse_emissions(self.emission_results[consumer_id], regularity)
                    if consumer_id in self.emission_results
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
                    timesteps=consumer_result.component_result.timesteps,
                    id=consumer_result.component_result.id,
                    is_valid=consumer_result.component_result.is_valid,
                )
            elif consumer_node_info.component_type == ComponentType.PUMP:
                obj = dto.result.results.PumpResult(
                    name=consumer_node_info.name,
                    parent=self.graph.get_predecessor(consumer_id),
                    component_level=consumer_node_info.component_level,
                    componentType=consumer_node_info.component_type,
                    emissions=self._parse_emissions(self.emission_results[consumer_id], regularity)
                    if consumer_id in self.emission_results
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
                    timesteps=consumer_result.component_result.timesteps,
                    id=consumer_result.component_result.id,
                    is_valid=consumer_result.component_result.is_valid,
                    streams=consumer_result.component_result.streams,
                )
            elif consumer_node_info.component_type == ComponentType.COMPRESSOR:
                obj = dto.result.results.CompressorResult(
                    name=consumer_node_info.name,
                    parent=self.graph.get_predecessor(consumer_id),
                    component_level=consumer_node_info.component_level,
                    componentType=consumer_node_info.component_type,
                    emissions=self._parse_emissions(self.emission_results[consumer_id], regularity)
                    if consumer_id in self.emission_results
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
                    outlet_pressure_before_choking=consumer_result.component_result.outlet_pressure_before_choking,
                    timesteps=consumer_result.component_result.timesteps,
                    id=consumer_result.component_result.id,
                    is_valid=consumer_result.component_result.is_valid,
                    streams=consumer_result.component_result.streams,
                )
            elif consumer_node_info.component_type == ComponentType.ASSET:
                obj = dto.result.results.AssetResult(
                    name=consumer_node_info.name,
                    parent=self.graph.get_predecessor(consumer_id),
                    component_level=consumer_node_info.component_level,
                    componentType=consumer_node_info.component_type,
                    emissions=self._parse_emissions(self.emission_results[consumer_id], regularity)
                    if consumer_id in self.emission_results
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
                    hydrocarbon_export_rate=TimeSeriesRate.from_timeseries_stream_day_rate(
                        consumer_result.component_result.hydrocarbon_export_rate, regularity=regularity
                    ),
                    emission_intensities=consumer_result.component_result.emission_intensities,
                    timesteps=consumer_result.component_result.timesteps,
                    id=consumer_result.component_result.id,
                    is_valid=consumer_result.component_result.is_valid,
                )
            elif consumer_node_info.component_type == ComponentType.INSTALLATION:
                obj = dto.result.results.InstallationResult(
                    name=consumer_node_info.name,
                    parent=self.graph.get_predecessor(consumer_id),
                    component_level=consumer_node_info.component_level,
                    componentType=consumer_node_info.component_type,
                    emissions=self._parse_emissions(self.emission_results[consumer_id], regularity)
                    if consumer_id in self.emission_results
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
                    regularity=consumer_result.component_result.regularity,
                    timesteps=consumer_result.component_result.timesteps,
                    id=consumer_result.component_result.id,
                    is_valid=consumer_result.component_result.is_valid,
                )
            elif consumer_node_info.component_type == ComponentType.CONSUMER_SYSTEM_V2:
                obj = dto.result.ConsumerSystemResult(
                    id=consumer_result.component_result.id,
                    is_valid=consumer_result.component_result.is_valid,
                    timesteps=consumer_result.component_result.timesteps,
                    name=consumer_node_info.name,
                    parent=self.graph.get_predecessor(consumer_id),
                    component_level=consumer_node_info.component_level,
                    componentType=consumer_node_info.component_type,
                    consumer_type=self.graph.get_node_info(self.graph.get_successors(consumer_id)[0]).component_type,
                    emissions=self._parse_emissions(self.emission_results[consumer_id], regularity)
                    if consumer_id in self.emission_results
                    else {},
                    energy_usage_cumulative=TimeSeriesRate.from_timeseries_stream_day_rate(
                        consumer_result.component_result.energy_usage,
                        regularity=regularity,
                    )
                    .to_volumes()
                    .cumulative(),
                    power_cumulative=TimeSeriesRate.from_timeseries_stream_day_rate(
                        consumer_result.component_result.power,
                        regularity=regularity,
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
                )
            else:  # COMPRESSOR_SYSTEM, PUMP_SYSTEM, GENERIC, TURBINE, VENTING_EMITTER
                emissions = (
                    self._parse_emissions(self.emission_results[consumer_id], regularity)
                    if consumer_id in self.emission_results
                    else {}
                )
                obj = TypeAdapter(libecalc.dto.result.ComponentResult).validate_python(
                    {
                        **consumer_result.component_result.model_dump(exclude={"typ"}),
                        "name": consumer_node_info.name,
                        "parent": self.graph.get_predecessor(consumer_id),
                        "component_level": consumer_node_info.component_level,
                        "componentType": consumer_node_info.component_type,
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

        for installation in asset.installations:
            regularity = regularities[installation.id]  # Already evaluated regularities
            for venting_emitter in installation.venting_emitters:
                energy_usage = TimeSeriesRate(
                    timesteps=self.variables_map.time_vector,
                    values=[0.0] * self.variables_map.length,
                    regularity=[1] * self.variables_map.length,  # Dummy. Has no effect since value is 0
                    unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                    rate_type=RateType.CALENDAR_DAY,
                )
                sub_components.append(
                    libecalc.dto.result.VentingEmitterResult(
                        id=venting_emitter.id,
                        name=venting_emitter.name,
                        componentType=venting_emitter.component_type,
                        component_level=ComponentLevel.CONSUMER,
                        parent=installation.id,
                        emissions=self._parse_emissions(self.emission_results[venting_emitter.id], regularity),
                        timesteps=self.variables_map.time_vector,
                        is_valid=TimeSeriesBoolean(
                            timesteps=self.variables_map.time_vector,
                            values=[True] * self.variables_map.length,
                            unit=Unit.NONE,
                        ),
                        energy_usage=energy_usage,
                        energy_usage_cumulative=energy_usage.to_volumes().cumulative(),
                    )
                )

        # dto timeseries
        asset_hydrocarbon_export_rate_core = reduce(
            operator.add,
            [installation.hydrocarbon_export_rate for installation in installation_results],
        )

        emission_dto_results = self.convert_to_timeseries(
            self.emission_results,
            regularities,
        )
        asset_aggregated_emissions = aggregate_emissions(list(emission_dto_results.values()))

        asset_power_core = reduce(
            operator.add,
            [installation.power for installation in installation_results if installation.power is not None],
        )

        asset_power_cumulative = asset_power_core.to_volumes().to_unit(Unit.GIGA_WATT_HOURS).cumulative()

        asset_energy_usage_core = reduce(
            operator.add,
            [installation.energy_usage for installation in installation_results],
        )

        asset_energy_usage_cumulative = asset_energy_usage_core.to_volumes().cumulative()

        asset_node_info = self.graph.get_node_info(asset_id)
        asset_result_dto = libecalc.dto.result.AssetResult(
            id=asset.id,
            name=asset_node_info.name,
            component_level=asset_node_info.component_level,
            componentType=asset_node_info.component_type,
            timesteps=self.variables_map.time_vector,
            is_valid=TimeSeriesBoolean(
                timesteps=self.variables_map.time_vector,
                values=aggregate_is_valid(installation_results),
                unit=Unit.NONE,
            ),
            power=asset_power_core,
            power_cumulative=asset_power_cumulative,
            energy_usage=asset_energy_usage_core,
            energy_usage_cumulative=asset_energy_usage_cumulative,
            hydrocarbon_export_rate=asset_hydrocarbon_export_rate_core,
            emissions=self.to_full_result(asset_aggregated_emissions),
            emission_intensities=self._compute_intensity(
                hydrocarbon_export_rate=asset_hydrocarbon_export_rate_core,
                emissions=asset_aggregated_emissions,
            ),
        )

        return libecalc.dto.result.EcalcModelResult(
            component_result=asset_result_dto,
            sub_components=sub_components,
            models=models,
        )

    def get_emissions(self, component_id: str) -> Dict[str, EmissionResult]:
        return self.emission_results[component_id]

    def get_results(self) -> EnergyCalculatorResult:
        return EnergyCalculatorResult(
            consumer_results=self.consumer_results,
            emission_results=self.emission_results,
            variables_map=self.variables_map,
        )

    def convert_to_timeseries(
        self,
        emission_core_results: Dict[str, Dict[str, EmissionResult]],
        regularities: Union[TimeSeriesFloat, Dict[str, TimeSeriesFloat]],
    ) -> Dict[str, Dict[str, PartialEmissionResult]]:
        """
        Emissions by consumer id and emission name
        Args:
            emission_core_results:
            regularities:

        Returns:

        """
        dto_result: Dict[str, Dict[str, PartialEmissionResult]] = {}

        for consumer_id, emissions in emission_core_results.items():
            installation_id = self.graph.get_parent_installation_id(consumer_id)
            dto_result[consumer_id] = defaultdict()

            if isinstance(regularities, Dict):
                regularity = regularities[installation_id]
            else:
                regularity = regularities

            for emission_name, emission_result in emissions.items():
                dto_result[consumer_id][emission_name] = PartialEmissionResult.from_emission_core_result(
                    emission_result, regularity=regularity
                )

        return dto_result
