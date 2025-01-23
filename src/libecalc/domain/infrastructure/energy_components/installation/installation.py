import operator
from collections import defaultdict
from functools import reduce
from typing import Optional, Union

import libecalc
from libecalc.application.energy.emitter import Emitter
from libecalc.application.energy.energy_component import EnergyComponent
from libecalc.common.component_info.component_level import ComponentLevel
from libecalc.common.component_type import ComponentType
from libecalc.common.string.string_utils import generate_id
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period
from libecalc.common.units import Unit
from libecalc.common.utils.emission_intensity import EmissionIntensity
from libecalc.common.utils.rates import RateType, TimeSeriesBoolean, TimeSeriesFloat, TimeSeriesRate
from libecalc.common.variables import ExpressionEvaluator
from libecalc.core.result.emission import EmissionResult
from libecalc.domain.infrastructure.energy_components.consumer_system.consumer_system_dto import ConsumerSystem
from libecalc.domain.infrastructure.energy_components.fuel_consumer.fuel_consumer import FuelConsumer
from libecalc.domain.infrastructure.energy_components.generator_set.generator_set_dto import GeneratorSet
from libecalc.domain.infrastructure.energy_components.legacy_consumer.component import ConsumerResult
from libecalc.dto.component_graph import ComponentGraph
from libecalc.dto.types import InstallationUserDefinedCategoryType
from libecalc.dto.utils.validators import (
    convert_expression,
    validate_temporal_model,
)
from libecalc.expression import Expression
from libecalc.presentation.json_result.aggregators import (
    aggregate_emissions,
    aggregate_is_valid,
)
from libecalc.presentation.json_result.result.emission import EmissionIntensityResult, PartialEmissionResult
from libecalc.presentation.yaml.yaml_types.emitters.yaml_venting_emitter import (
    YamlVentingEmitter,
)


class Installation(EnergyComponent):
    def __init__(
        self,
        name: str,
        regularity: dict[Period, Expression],
        hydrocarbon_export: dict[Period, Expression],
        fuel_consumers: list[Union[GeneratorSet, FuelConsumer, ConsumerSystem]],
        expression_evaluator: ExpressionEvaluator,
        venting_emitters: Optional[list[YamlVentingEmitter]] = None,
        user_defined_category: Optional[InstallationUserDefinedCategoryType] = None,
    ):
        self.name = name
        self.hydrocarbon_export = self.convert_expression_installation(hydrocarbon_export)
        self.regularity = self.convert_expression_installation(regularity)
        self.fuel_consumers = fuel_consumers
        self.expression_evaluator = expression_evaluator
        self.user_defined_category = user_defined_category
        self.component_type = ComponentType.INSTALLATION
        self.component_level = ComponentLevel.INSTALLATION
        self.validate_installation_temporal_model()

        if venting_emitters is None:
            venting_emitters = []
        self.venting_emitters = venting_emitters

    def is_fuel_consumer(self) -> bool:
        return True

    def is_electricity_consumer(self) -> bool:
        # Should maybe be True if power from shore?
        return False

    def is_provider(self) -> bool:
        return False

    def is_container(self) -> bool:
        return True

    def get_component_process_type(self) -> ComponentType:
        return self.component_type

    def get_name(self) -> str:
        return self.name

    @property
    def id(self) -> str:
        return generate_id(self.name)

    def validate_installation_temporal_model(self):
        return validate_temporal_model(self.hydrocarbon_export)

    def convert_expression_installation(self, data):
        # Implement the conversion logic here
        return convert_expression(data)

    def get_graph(self) -> ComponentGraph:
        graph = ComponentGraph()
        graph.add_node(self)
        for component in [*self.fuel_consumers, *self.venting_emitters]:
            if hasattr(component, "get_graph"):
                graph.add_subgraph(component.get_graph())
            else:
                graph.add_node(component)

            graph.add_edge(self.id, component.id)

        return graph

    def evaluate_regularity(self) -> TimeSeriesFloat:
        return TimeSeriesFloat(
            periods=self.expression_evaluator.get_periods(),
            values=self.expression_evaluator.evaluate(expression=TemporalModel(self.regularity)).tolist(),
            unit=Unit.NONE,
        )

    def get_installation_result(self, asset_id: str):
        regularity = self.evaluate_regularity()

        hydrocarbon_export_rate = self.get_hydrocarbon_export_rate()

        sub_components = self.get_sub_component_results()

        power_electrical = self.get_aggregated_electrical_power_results()
        power_mechanical = self.get_aggregated_mechanical_power_results()
        power = power_electrical + power_mechanical

        energy_usage = self.get_energy_usage()

        aggregated_emissions = self.get_aggregated_emissions()

        installation_result = (
            libecalc.presentation.json_result.result.InstallationResult(
                id=self.id,
                name=self.name,
                parent=asset_id,
                component_level=self.component_level,
                componentType=self.component_type.value,
                periods=self.expression_evaluator.get_periods(),
                is_valid=self.get_is_valid(),
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
                emissions=aggregated_emissions,
                emission_intensities=_compute_intensity(
                    hydrocarbon_export_rate=hydrocarbon_export_rate,
                    emissions=aggregated_emissions,
                ),
                regularity=TimeSeriesFloat(
                    periods=self.expression_evaluator.get_periods(),
                    values=regularity.values,
                    unit=Unit.NONE,
                ),
            )
            if sub_components
            else None
        )
        return installation_result

    def get_hydrocarbon_export_rate(self) -> TimeSeriesRate:
        hydrocarbon_export_rate = self.expression_evaluator.evaluate(expression=TemporalModel(self.hydrocarbon_export))
        regularity = self.evaluate_regularity()

        hydrocarbon_export_rate = TimeSeriesRate(
            periods=self.expression_evaluator.get_periods(),
            values=hydrocarbon_export_rate.tolist(),
            unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
            rate_type=RateType.CALENDAR_DAY,
            regularity=regularity.values,
        )
        return hydrocarbon_export_rate

    def get_sub_component_results(self) -> list[libecalc.presentation.json_result.result.EcalcModelResult]:
        sub_component_results: list[libecalc.presentation.json_result.result.EcalcModelResult] = []
        for fuel_consumer in self.fuel_consumers:
            sub_component_results.extend(result.component_result for result in self._collect_all_results(fuel_consumer))
        return sub_component_results

    def get_consumer_results(self) -> dict[str, ConsumerResult]:
        consumer_results = {}
        for fuel_consumer in self.fuel_consumers:
            consumer_results.update(
                {result.component_result.id: result for result in self._collect_all_results(fuel_consumer)}
            )
        return consumer_results

    def get_emission_results(self) -> dict[str, dict[str, EmissionResult]]:
        """
        Retrieve the emission results for all components in the installation.

        Returns: a mapping from component_id to emissions
        """
        emission_results: dict[str, dict[str, EmissionResult]] = {}
        for component in self.fuel_consumers:
            if isinstance(component, Emitter):
                emission_result = component.emission_results  # Assuming emission_results is already set
                if emission_result is not None:
                    emission_results[component.id] = emission_result

        return emission_results

    def get_aggregated_emissions(self) -> dict[str, EmissionResult]:
        emission_dto_results = self._get_emission_dto_results()
        successors = [component.id for component in self.fuel_consumers]

        aggregated_emissions = aggregate_emissions(
            [emission_dto_results[fuel_consumer_id] for fuel_consumer_id in successors]
        )

        return {
            key: libecalc.presentation.json_result.result.EmissionResult(
                name=key,
                periods=aggregated_emissions[key].periods,
                rate=aggregated_emissions[key].rate,
                cumulative=aggregated_emissions[key].rate.to_volumes().cumulative(),
            )
            for key in aggregated_emissions
        }

    def get_power_component_results(self) -> list[libecalc.presentation.json_result.result.EcalcModelResult]:
        return [
            self.get_consumer_results()[consumer.id].component_result
            for consumer in self.fuel_consumers
            if consumer.id in self.get_consumer_results()
        ]

    def get_aggregated_electrical_power_results(self) -> TimeSeriesRate:
        return self._compute_aggregated_power(
            power_components=self._get_electrical_component_results(),
            regularity=self.evaluate_regularity(),
        )

    def get_aggregated_mechanical_power_results(self) -> TimeSeriesRate:
        return self._compute_aggregated_power(
            power_components=self._get_fuel_component_results(),
            regularity=self.evaluate_regularity(),
        )

    def get_energy_usage(self) -> TimeSeriesRate:
        regularity = self.evaluate_regularity()
        sub_components = self.get_sub_component_results()
        return (
            reduce(
                operator.add,
                [
                    TimeSeriesRate.from_timeseries_stream_day_rate(component.energy_usage, regularity=regularity)
                    for component in sub_components
                    if component.energy_usage.unit == Unit.STANDARD_CUBIC_METER_PER_DAY
                ],
            )
            if sub_components
            else TimeSeriesRate(
                values=[0.0] * self.expression_evaluator.number_of_periods,
                periods=self.expression_evaluator.get_periods(),
                unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                rate_type=RateType.STREAM_DAY,
                regularity=regularity.values,
            )
        )

    def get_is_valid(self) -> TimeSeriesBoolean:
        sub_components = self.get_sub_component_results()
        return TimeSeriesBoolean(
            periods=self.expression_evaluator.get_periods(),
            values=aggregate_is_valid([component for component in sub_components if hasattr(component, "is_valid")]),
            unit=Unit.NONE,
        )

    def _collect_all_results(self, consumer):
        results = []
        if hasattr(consumer, "consumer_results"):
            results.extend(consumer.consumer_results.values())
        for sub_consumer in getattr(consumer, "consumers", []):
            results.extend(self._collect_all_results(sub_consumer))
        return results

    def _get_electrical_component_results(self) -> list:
        electrical_components = []
        for fuel_consumer in self.fuel_consumers:
            if fuel_consumer.component_type == ComponentType.GENERATOR_SET:
                electrical_components.append(self.get_consumer_results()[fuel_consumer.id].component_result)
        return electrical_components

    def _get_fuel_component_results(self) -> list:
        fuel_components = []
        for fuel_consumer in self.fuel_consumers:
            if fuel_consumer.component_type != ComponentType.GENERATOR_SET:
                fuel_components.append(self.get_consumer_results()[fuel_consumer.id].component_result)
        return fuel_components

    def _compute_aggregated_power(
        self,
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
                values=[0.0] * self.expression_evaluator.number_of_periods,
                periods=self.expression_evaluator.get_periods(),
                unit=Unit.MEGA_WATT,
                rate_type=RateType.STREAM_DAY,
                regularity=regularity.values,
            ),  # Initial value, handle no power output from components
        )

    def _get_emission_dto_results(self) -> dict[str, dict[str, PartialEmissionResult]]:
        emission_core_results = self.get_emission_results()
        return self._convert_to_timeseries(
            emission_core_results=emission_core_results,
            regularities=self.evaluate_regularity(),
        )

    def _convert_to_timeseries(
        self,
        emission_core_results: dict[str, dict[str, EmissionResult]],
        regularities: Union[TimeSeriesFloat, dict[str, TimeSeriesFloat]],
    ) -> dict[str, dict[str, PartialEmissionResult]]:
        dto_result: dict[str, dict[str, PartialEmissionResult]] = {}

        for consumer_id, emissions in emission_core_results.items():
            installation_id = self.id
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


def _compute_intensity(
    hydrocarbon_export_rate: TimeSeriesRate,
    emissions: dict[str, PartialEmissionResult],
) -> list[EmissionIntensityResult]:
    hydrocarbon_export_cumulative = hydrocarbon_export_rate.to_volumes().cumulative()
    emission_intensities = []
    for key in emissions:
        cumulative_rate_kg = emissions[key].rate.to_volumes().to_unit(Unit.KILO).cumulative()
        intensity = EmissionIntensity(
            emission_cumulative=cumulative_rate_kg,
            hydrocarbon_export_cumulative=hydrocarbon_export_cumulative,
        )
        intensity_sm3 = intensity.calculate()
        intensity_yearly_sm3 = intensity.calculate_periods()

        emission_intensities.append(
            EmissionIntensityResult(
                name=emissions[key].name,
                periods=emissions[key].periods,
                intensity_sm3=intensity_sm3,
                intensity_boe=intensity_sm3.to_unit(Unit.KG_BOE),
                intensity_yearly_sm3=intensity_yearly_sm3,
                intensity_yearly_boe=intensity_yearly_sm3.to_unit(Unit.KG_BOE),
            )
        )
    return emission_intensities
