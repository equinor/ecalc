from collections.abc import Iterable
from datetime import datetime
from typing import TypeVar, assert_never

from libecalc.common.errors.exceptions import ProgrammingError
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Frequency, Period, Periods
from libecalc.common.units import Unit
from libecalc.common.utils.rates import TimeSeries
from libecalc.domain.fuel import Fuel
from libecalc.domain.infrastructure.energy_components.installation.installation import InstallationComponent
from libecalc.domain.installation import FuelConsumer, Installation
from libecalc.presentation.exporter.domain.exportable import (
    Attribute,
    AttributeMeta,
    AttributeSet,
    Exportable,
    ExportableSet,
    ExportableType,
)
from libecalc.presentation.yaml.domain.category_service import CategoryService
from libecalc.presentation.yaml.model import YamlModel


class TimeSeriesAttribute(Attribute):
    def __init__(self, time_series: TimeSeries[float], attribute_meta: AttributeMeta):
        self._attribute_meta = attribute_meta
        self._time_series = time_series

    def datapoints(self) -> Iterable[tuple[Period, float]]:
        return self._time_series.datapoints()

    def get_meta(self) -> AttributeMeta:
        return self._attribute_meta


TCategory = TypeVar("TCategory")


class InstallationExportable(Exportable):
    def __init__(self, installation: Installation, category_service: CategoryService):
        self._installation = installation
        self._category_service = category_service
        self._frequency: Frequency | None = None

    def get_electricity_production(self, unit: Unit) -> AttributeSet:
        attributes = []
        for electricity_producer in self._installation.get_electricity_producers():
            consumer_category = self._category_service.get_category(electricity_producer.get_id())
            for period, category in consumer_category.items():
                power_production_rate = electricity_producer.get_power_production()

                electricity_production_volumes = power_production_rate.for_period(period).to_volumes().to_unit(unit)

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
        for electricity_producer in self._installation.get_electricity_producers():
            max_electricity_production = electricity_producer.get_maximum_power_production()
            if max_electricity_production is None:
                continue

            consumer_category = self._category_service.get_category(electricity_producer.get_id())
            for period, category in consumer_category.items():
                max_usage_from_shore_rate = max_electricity_production.for_period(period).to_unit(unit)

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
        for storage_container in self._installation.get_storage_containers():
            storage_rates = storage_container.get_storage_rates()
            storage_volumes = storage_rates.to_volumes().to_unit(unit)

            consumer_category = self._category_service.get_category(storage_container.get_id())

            for period, category in consumer_category.items():
                attributes.append(
                    TimeSeriesAttribute(
                        time_series=storage_volumes.for_period(period),
                        attribute_meta=AttributeMeta(
                            fuel_category=None,
                            consumer_category=category,
                        ),
                    )
                )

        return AttributeSet(attributes)

    def get_category(self) -> str | None:
        installation_category = self._category_service.get_category(self._installation.get_id())
        if installation_category is None:
            return None
        categories = list(installation_category.get_models())
        assert len(categories) == 1
        return categories[0]

    def get_periods(self) -> Periods:
        # TODO: Not this
        assert isinstance(self._installation, InstallationComponent)
        return self._installation.expression_evaluator.get_periods()

    @staticmethod
    def _combine_categories(
        fuel_category: TemporalModel[str | None] = None,
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

        def _get_category(
            temporal_category: TemporalModel[TCategory] | None, period: Period | datetime
        ) -> TCategory | None:
            """
            Get category for a timestep, returning None if temporal category is None or not defined for timestep
            Args:
                temporal_category: temporal category
                period: the period to get category for

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
                        fuel_category=_get_category(fuel_category, period),
                        consumer_category=_get_category(consumer_category, period),
                        producer_category=_get_category(producer_category, period),
                    ),
                )
            )
        return combined

    def _get_temporal_fuel_category(self, temporal_fuel: TemporalModel[Fuel]) -> TemporalModel[str | None]:
        """
        Combine the temporal model for fuel and the temporal category, intersection of the two periods gives the actual
        period where the category applies.
        """
        temporal_fuel_category_dict: dict[Period, str | None] = {}
        for fuel_period, fuel in temporal_fuel.items():
            fuel_category = self._category_service.get_category(fuel.get_id())
            if fuel_category is None:
                temporal_fuel_category_dict[fuel_period] = None
            else:
                for fuel_category_period, category in fuel_category.items():
                    intersected_period = Period.intersection(fuel_period, fuel_category_period)
                    assert intersected_period is not None, "Period for fuel and fuel category should intersect"
                    temporal_fuel_category_dict[intersected_period] = category

        return TemporalModel(temporal_fuel_category_dict)

    def get_fuel_consumption(self) -> AttributeSet:
        attributes = []
        for fuel_consumer in self._installation.get_fuel_consumers():
            fuel_rate = fuel_consumer.get_fuel_consumption()
            consumer_category = self._category_service.get_category(fuel_consumer.get_id())

            fuel_category = self._get_temporal_fuel_category(fuel_rate.fuel)

            for period, attribute_meta in self._combine_categories(fuel_category, consumer_category):  # type: ignore[arg-type]
                attributes.append(
                    TimeSeriesAttribute(
                        time_series=fuel_rate.rate.for_period(period).to_volumes(),
                        attribute_meta=attribute_meta,
                    )
                )

        return AttributeSet(attributes)

    def get_power_consumption(self, unit: Unit) -> AttributeSet:
        attributes = []

        for power_consumer in self._installation.get_power_consumers():
            consumer_category = self._category_service.get_category(power_consumer.get_id())
            assert consumer_category is not None
            producer_id = power_consumer.get_producer_id()
            if producer_id is not None:
                producer_category = self._category_service.get_category(producer_id)
                assert producer_category is not None
                iterator = self._combine_categories(
                    consumer_category=consumer_category, producer_category=producer_category
                )
            else:
                iterator = [
                    (period, AttributeMeta(fuel_category=None, consumer_category=category))
                    for period, category in consumer_category.items()
                ]

            for period, attribute_meta in iterator:
                electricity_consumption_volumes = (
                    power_consumer.get_power_consumption().for_period(period).to_volumes().to_unit(unit)
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

        return AttributeSet(attributes)

    def get_emissions(self, unit: Unit) -> AttributeSet:
        attributes = []

        for emitter in self._installation.get_emitters():
            emissions = emitter.get_emissions()
            consumer_category = self._category_service.get_category(emitter.get_id())
            assert consumer_category is not None

            if isinstance(emitter, FuelConsumer):
                fuel = emitter.get_fuel()
                fuel_category = self._get_temporal_fuel_category(fuel)
                iterator = self._combine_categories(fuel_category, consumer_category)
            else:
                iterator = [
                    (period, AttributeMeta(fuel_category=None, consumer_category=category))
                    for period, category in consumer_category.items()
                ]
            for period, attribute_meta in iterator:
                for emission_name, emission in emissions.items():
                    emission_volumes = emission.for_period(period).to_volumes().to_unit(unit)
                    emission_attribute_meta = AttributeMeta(
                        fuel_category=attribute_meta.fuel_category,
                        consumer_category=attribute_meta.consumer_category,
                        emission_type=emission_name,
                    )
                    attributes.append(
                        TimeSeriesAttribute(
                            time_series=emission_volumes,
                            attribute_meta=emission_attribute_meta,
                        )
                    )

        return AttributeSet(attributes)

    def get_name(self) -> str:
        return self._installation.get_name()


class ExportableYamlModel(ExportableSet):
    def __init__(self, yaml_model: YamlModel):
        self._yaml_model = yaml_model

    def get_from_type(self, exportable_type: ExportableType) -> list[Exportable]:
        if exportable_type == ExportableType.INSTALLATION:
            return [
                InstallationExportable(installation, category_service=self._yaml_model.get_category_service())
                for installation in self._yaml_model.get_installations()
            ]
        else:
            assert_never(exportable_type)
