from collections.abc import Iterable
from datetime import datetime
from typing import assert_never

from libecalc.application.graph_result import GraphResult
from libecalc.common.component_type import ComponentType
from libecalc.common.errors.exceptions import ProgrammingError
from libecalc.common.logger import logger
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Frequency, Period, Periods
from libecalc.common.units import Unit
from libecalc.common.utils.rates import TimeSeries, TimeSeriesFloat, TimeSeriesRate, TimeSeriesStreamDayRate
from libecalc.core.result import GeneratorSetResult
from libecalc.domain.infrastructure.emitters.venting_emitter import DirectVentingEmitter, OilVentingEmitter
from libecalc.domain.infrastructure.energy_components.fuel_consumer.fuel_consumer import FuelConsumer
from libecalc.domain.infrastructure.energy_components.generator_set.generator_set_component import (
    GeneratorSetEnergyComponent,
)
from libecalc.dto.utils.validators import convert_expression
from libecalc.presentation.exporter.domain.exportable import (
    Attribute,
    AttributeMeta,
    AttributeSet,
    Exportable,
    ExportableSet,
    ExportableType,
)
from libecalc.presentation.yaml.yaml_types.emitters.yaml_venting_emitter import (
    YamlVentingType,
)


class TimeSeriesAttribute(Attribute):
    def __init__(self, time_series: TimeSeries, attribute_meta: AttributeMeta):
        self._attribute_meta = attribute_meta
        self._time_series = time_series

    def datapoints(self) -> Iterable[tuple[datetime, float]]:
        return self._time_series.datapoints()

    def get_meta(self) -> AttributeMeta:
        return self._attribute_meta


class InstallationExportable(Exportable):
    def __init__(self, installation_graph: GraphResult):
        self._installation_graph = installation_graph
        self._frequency: Frequency | None = None
        self._installation_dto = installation_graph.graph.get_node(installation_graph.graph.root)

    def get_electricity_production(self, unit: Unit) -> AttributeSet:
        attributes = []
        for fuel_consumer in self._installation_dto.fuel_consumers:
            if not isinstance(fuel_consumer, GeneratorSetEnergyComponent):
                continue

            fuel_consumer_result = self._installation_graph.get_energy_result(fuel_consumer.id)
            assert isinstance(fuel_consumer_result, GeneratorSetResult)
            consumer_category = TemporalModel(fuel_consumer.user_defined_category)
            for period, category in consumer_category.items():
                if fuel_consumer.cable_loss is not None:
                    # TODO: Move this calculation into generator set
                    cable_loss = self._installation_graph.variables_map.evaluate(
                        convert_expression(fuel_consumer.cable_loss)
                    )

                    power_production_values = fuel_consumer_result.power.values * (1 + cable_loss)
                    power_production_rate = TimeSeriesStreamDayRate(
                        periods=fuel_consumer_result.power.periods,
                        values=power_production_values,
                        unit=fuel_consumer_result.power.unit,
                    )
                else:
                    power_production_rate = fuel_consumer_result.power

                electricity_production_volumes = (
                    TimeSeriesRate.from_timeseries_stream_day_rate(
                        power_production_rate,
                        regularity=self._installation_dto.regularity.time_series,
                    )
                    .for_period(period)
                    .to_volumes()
                    .to_unit(unit)
                )

                attributes.append(
                    TimeSeriesAttribute(
                        time_series=electricity_production_volumes,
                        attribute_meta=AttributeMeta(
                            fuel_category=None,
                            consumer_category=None,
                            producer_category=category,
                        ),
                    )
                )
        return AttributeSet(attributes)

    def get_maximum_electricity_production(self, unit: Unit) -> AttributeSet:
        attributes = []
        for fuel_consumer in self._installation_dto.fuel_consumers:
            if not isinstance(fuel_consumer, GeneratorSetEnergyComponent):
                continue

            if fuel_consumer.max_usage_from_shore is None:
                continue

            consumer_category = TemporalModel(fuel_consumer.user_defined_category)
            for period, category in consumer_category.items():
                max_usage_from_shore_values = self._installation_graph.variables_map.evaluate(
                    convert_expression(fuel_consumer.max_usage_from_shore)
                ).tolist()
                max_usage_from_shore_rate = (
                    TimeSeriesRate.from_timeseries_stream_day_rate(
                        TimeSeriesStreamDayRate(
                            periods=self._installation_graph.periods,
                            values=max_usage_from_shore_values,
                            unit=Unit.MEGA_WATT,
                        ),
                        regularity=self._installation_dto.regularity.time_series,
                    )
                    .for_period(period)
                    .to_unit(unit)
                )

                attributes.append(
                    TimeSeriesAttribute(
                        time_series=max_usage_from_shore_rate,
                        attribute_meta=AttributeMeta(
                            fuel_category=None,
                            consumer_category=None,
                            producer_category=category,
                        ),
                    )
                )
        return AttributeSet(attributes)

    def get_storage_volumes(self, unit: Unit) -> AttributeSet:
        attributes = []
        for venting_emitter in self._installation_dto.venting_emitters:
            if venting_emitter.emitter_type != YamlVentingType.OIL_VOLUME:
                continue

            oil_rates = venting_emitter.get_oil_rates(
                regularity=self._installation_dto.regularity.time_series,
            )
            oil_volumes = TimeSeriesRate.from_timeseries_stream_day_rate(
                oil_rates,
                regularity=self._installation_dto.regularity.time_series,
            ).to_volumes()
            oil_volumes = oil_volumes.to_unit(unit)
            attributes.append(
                TimeSeriesAttribute(
                    time_series=oil_volumes,
                    attribute_meta=AttributeMeta(
                        fuel_category=None,
                        consumer_category=venting_emitter.user_defined_category,
                    ),
                )
            )
        return AttributeSet(attributes)

    def get_category(self) -> str:
        return self._installation_dto.user_defined_category

    def get_periods(self) -> Periods:
        return self._installation_graph.periods

    def _get_regularity(self) -> TimeSeriesFloat:
        return TimeSeriesFloat(
            periods=self.get_periods(),
            values=self._installation_graph.variables_map.evaluate(
                expression=TemporalModel(self._installation_dto.regularity)
            ).tolist(),
            unit=Unit.NONE,
        )

    @staticmethod
    def _combine_categories(
        fuel_category: TemporalModel[str] = None,
        consumer_category: TemporalModel[str] = None,
        producer_category: TemporalModel[str] = None,
    ) -> list[tuple[Period, AttributeMeta]]:
        defined_temporal_categories = [
            temporal_category
            for temporal_category in [fuel_category, consumer_category, producer_category]
            if temporal_category is not None
        ]
        if len(defined_temporal_categories) < 2:
            raise ProgrammingError("Should combine at least two temporal categories")

        timesteps = set()
        for temporal_model in defined_temporal_categories:
            for period in temporal_model.get_periods():
                timesteps.add(period.start)
                timesteps.add(period.end)

        periods = Periods.create_periods(sorted(timesteps), include_before=False, include_after=False)

        def _get_category(temporal_category: TemporalModel[str] | None, period: Period) -> str | None:
            """
            Get category for a timestep, returning None if temporal category is None or not defined for timestep
            Args:
                temporal_category: temporal category
                timestep: the timestep to get category for

            Returns: category or None
            """
            if temporal_category is None:
                return None

            try:
                return temporal_category.get_model(period)
            except ValueError:
                # category not defined for timestep
                return None

        combined = []
        for period in periods:
            combined.append(
                (
                    period,
                    AttributeMeta(
                        fuel_category=_get_category(fuel_category, period.start),
                        consumer_category=_get_category(consumer_category, period.start),
                        producer_category=_get_category(producer_category, period.start),
                    ),
                )
            )
        return combined

    def get_fuel_consumption(self) -> AttributeSet:
        attributes = []
        for fuel_consumer in self._installation_dto.fuel_consumers:
            assert isinstance(fuel_consumer, GeneratorSetEnergyComponent | FuelConsumer)

            fuel_consumer_result = self._installation_graph.get_energy_result(fuel_consumer.id)
            consumer_category = TemporalModel(fuel_consumer.user_defined_category)
            fuel_category = TemporalModel(
                {fuel_period: fuel.user_defined_category for fuel_period, fuel in fuel_consumer.fuel.items()}
            )
            for period, attribute_meta in self._combine_categories(fuel_category, consumer_category):
                attributes.append(
                    TimeSeriesAttribute(
                        time_series=TimeSeriesRate.from_timeseries_stream_day_rate(
                            fuel_consumer_result.energy_usage, regularity=self._installation_dto.regularity.time_series
                        )
                        .for_period(period)
                        .to_volumes(),
                        attribute_meta=attribute_meta,
                    )
                )

        return AttributeSet(attributes)

    def get_power_consumption(self, unit: Unit) -> AttributeSet:
        attributes = []

        # Get power consumption from electricity consumers
        for fuel_consumer in self._installation_dto.fuel_consumers:
            if not isinstance(fuel_consumer, GeneratorSetEnergyComponent):
                continue

            for electricity_consumer in fuel_consumer.consumers:
                electricity_consumer_result = self._installation_graph.get_energy_result(electricity_consumer.id)

                if electricity_consumer_result.power is None:
                    continue

                temporal_consumer_category = TemporalModel(electricity_consumer.user_defined_category)
                temporal_producer_category = TemporalModel(fuel_consumer.user_defined_category)
                for period, attribute_meta in self._combine_categories(
                    consumer_category=temporal_consumer_category, producer_category=temporal_producer_category
                ):
                    electricity_consumption_volumes = (
                        TimeSeriesRate.from_timeseries_stream_day_rate(
                            electricity_consumer_result.power,
                            regularity=self._installation_dto.regularity.time_series,
                        )
                        .for_period(period)
                        .to_volumes()
                        .to_unit(unit)
                    )

                    attributes.append(
                        TimeSeriesAttribute(
                            time_series=electricity_consumption_volumes,
                            attribute_meta=AttributeMeta(
                                fuel_category=None,
                                consumer_category=attribute_meta.consumer_category,
                                producer_category=attribute_meta.producer_category,
                            ),
                        )
                    )

        # Get power consumption from fuel consumers
        for fuel_consumer in self._installation_dto.fuel_consumers:
            if not isinstance(fuel_consumer, FuelConsumer):
                continue

            for period, consumer_category in TemporalModel(fuel_consumer.user_defined_category).items():
                fuel_consumer_result = self._installation_graph.get_energy_result(fuel_consumer.id)
                periods = fuel_consumer_result.periods
                shaft_power = fuel_consumer_result.power
                if (
                    shaft_power is not None
                    and 0 < len(shaft_power) == len(periods)
                    and len(fuel_consumer_result.periods) == len(self._installation_graph.periods)
                ):
                    shaft_power_volumes = (
                        TimeSeriesRate.from_timeseries_stream_day_rate(
                            shaft_power, regularity=self._installation_dto.regularity.time_series
                        )
                        .for_period(period)
                        .to_volumes()
                        .to_unit(unit)
                    )

                    attributes.append(
                        TimeSeriesAttribute(
                            time_series=shaft_power_volumes,
                            attribute_meta=AttributeMeta(
                                fuel_category=None,  # Not relevant for power consumer
                                consumer_category=consumer_category,
                            ),
                        )
                    )

                else:
                    # TODO: is this ok?
                    logger.warning(
                        f"A combination of one or more compressors that do not support fuel to power conversion was used."
                        f"We are therefore unable to calculate correct power usage. Please only use compressors which support POWER conversion"
                        f"for fuel consumer '{fuel_consumer.name}'"
                    )

        return AttributeSet(attributes)

    def get_emissions(self, unit: Unit) -> AttributeSet:
        attributes = []

        for fuel_consumer in self._installation_dto.fuel_consumers:
            assert isinstance(fuel_consumer, GeneratorSetEnergyComponent | FuelConsumer)

            emissions = self._installation_graph.get_emissions(fuel_consumer.id)
            consumer_category = TemporalModel(fuel_consumer.user_defined_category)
            fuel_category = TemporalModel(
                {fuel_period: fuel.user_defined_category for fuel_period, fuel in fuel_consumer.fuel.items()}
            )
            for period, attribute_meta in self._combine_categories(fuel_category, consumer_category):
                for emission in emissions.values():
                    emission_volumes = (
                        TimeSeriesRate.from_timeseries_stream_day_rate(
                            emission.rate, regularity=self._installation_dto.regularity.time_series
                        )
                        .for_period(period)
                        .to_volumes()
                        .to_unit(unit)
                    )
                    emission_attribute_meta = AttributeMeta(
                        fuel_category=attribute_meta.fuel_category,
                        consumer_category=attribute_meta.consumer_category,
                        emission_type=emission.name,
                    )
                    attributes.append(
                        TimeSeriesAttribute(
                            time_series=emission_volumes,
                            attribute_meta=emission_attribute_meta,
                        )
                    )

        for venting_emitter in self._installation_dto.venting_emitters:
            assert isinstance(venting_emitter, DirectVentingEmitter | OilVentingEmitter)

            emissions = self._installation_graph.get_emissions(venting_emitter.id)
            for emission in emissions.values():
                attributes.append(
                    TimeSeriesAttribute(
                        time_series=TimeSeriesRate.from_timeseries_stream_day_rate(
                            emission.rate, regularity=self._installation_dto.regularity.time_series
                        )
                        .to_volumes()
                        .to_unit(unit),
                        attribute_meta=AttributeMeta(
                            fuel_category=None,
                            consumer_category=venting_emitter.user_defined_category,
                            emission_type=emission.name,
                        ),
                    )
                )

        return AttributeSet(attributes)

    def get_name(self) -> str:
        return self._installation_graph.graph.get_node_info(self._installation_graph.graph.root).name


class ExportableGraphResult(ExportableSet):
    def __init__(self, graph_result: GraphResult):
        self._graph_result = graph_result

    def get_from_type(self, exportable_type: ExportableType) -> list[Exportable]:
        if exportable_type == ExportableType.INSTALLATION:
            component_type = ComponentType.INSTALLATION
        else:
            assert_never(exportable_type)

        return [
            InstallationExportable(self._graph_result.get_subgraph(installation_id))
            for installation_id in self._graph_result.graph.get_nodes_of_type(component_type)
        ]
