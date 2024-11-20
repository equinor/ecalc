from copy import deepcopy
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Optional, cast, Union

import numpy as np
import pandas as pd
import pytest

from ecalc_cli.infrastructure.file_resource_service import FileResourceService
from libecalc.application.energy_calculator import EnergyCalculator
from libecalc.application.graph_result import GraphResult
from libecalc.common.time_utils import Frequency, calculate_delta_days, Period, Periods
from libecalc.common.units import Unit
from libecalc.common.utils.rates import RateType
from libecalc.common.variables import VariablesMap
from libecalc.dto.types import ConsumerUserDefinedCategoryType, InstallationUserDefinedCategoryType
from libecalc.presentation.exporter.configs.configs import LTPConfig
from libecalc.presentation.exporter.dto.dtos import FilteredResult, QueryResult
from libecalc.presentation.exporter.infrastructure import ExportableGraphResult
from libecalc.presentation.json_result.mapper import get_asset_result
from libecalc.presentation.json_result.result import EcalcModelResult
from libecalc.presentation.yaml.configuration_service import ConfigurationService
from libecalc.presentation.yaml.model import YamlModel
from libecalc.presentation.yaml.resource_service import ResourceService
from libecalc.presentation.yaml.yaml_entities import MemoryResource, ResourceStream
from libecalc.presentation.yaml.yaml_models.pyyaml_yaml_model import PyYamlYamlModel
from libecalc.presentation.yaml.yaml_models.yaml_model import YamlValidator, YamlConfiguration, ReaderType
from libecalc.presentation.yaml.yaml_types.components.legacy.yaml_electricity_consumer import YamlElectricityConsumer
from libecalc.presentation.yaml.yaml_types.components.yaml_asset import YamlAsset
from libecalc.presentation.yaml.yaml_types.components.yaml_installation import YamlInstallation
from libecalc.presentation.yaml.yaml_types.facility_model.yaml_facility_model import YamlFacilityModel
from libecalc.presentation.yaml.yaml_types.fuel_type.yaml_fuel_type import YamlFuelType
from libecalc.presentation.yaml.yaml_types.time_series.yaml_time_series import YamlTimeSeriesCollection
from libecalc.presentation.yaml.yaml_types.yaml_stream_conditions import YamlEmissionRateUnits
from libecalc.testing.yaml_builder import (
    YamlAssetBuilder,
    YamlVentingEmitterDirectTypeBuilder,
    YamlInstallationBuilder,
    YamlElectricity2fuelBuilder,
    YamlTimeSeriesBuilder,
    YamlGeneratorSetBuilder,
    YamlEnergyUsageModelCompressorBuilder,
    YamlCompressorTabularBuilder,
    YamlFuelConsumerBuilder,
    YamlEnergyUsageModelDirectBuilder,
    YamlElectricityConsumerBuilder,
)

from tests.libecalc.presentation.exporter.memory_resources import (
    generator_electricity2fuel_17MW_resource,
    onshore_power_electricity2fuel_resource,
    cable_loss_time_series_resource,
    compressor_sampled_fuel_driven_resource,
    generator_fuel_power_to_fuel_resource,
    generator_diesel_power_to_fuel_resource,
    max_usage_from_shore_time_series_resource,
)
from libecalc.presentation.yaml.yaml_types.components.legacy.energy_usage_model.yaml_energy_usage_model_direct import (
    ConsumptionRateType,
)

date1 = datetime(2027, 1, 1)
date2 = datetime(2027, 4, 10)
date3 = datetime(2028, 1, 1)
date4 = datetime(2028, 4, 10)
date5 = datetime(2029, 1, 1)

period1 = Period(date1, date2)
period2 = Period(date2, date3)
period3 = Period(date3, date4)
period4 = Period(date4, date5)
period5 = Period(date5)

period_from_date1 = Period(date1)
period_from_date3 = Period(date3)
full_period = Period(datetime(1900, 1, 1))

days_year1_first_half = period1.duration.days
days_year2_first_half = period3.duration.days

days_year1_second_half = period2.duration.days
days_year2_second_half = period4.duration.days


class OverridableStreamConfigurationService(ConfigurationService):
    def __init__(self, stream: ResourceStream, overrides: Optional[dict] = None):
        self._overrides = overrides
        self._stream = stream

    def get_configuration(self) -> YamlValidator:
        main_yaml_model = YamlConfiguration.Builder.get_yaml_reader(ReaderType.PYYAML).read(
            main_yaml=self._stream,
            enable_include=True,
        )

        if self._overrides is not None:
            main_yaml_model._internal_datamodel.update(self._overrides)
        return cast(YamlValidator, main_yaml_model)


# LTP specific methods:
def get_consumption(
    model: Union[YamlInstallation, YamlAsset, YamlModel],
    variables: VariablesMap,
    frequency: Frequency,
    periods: Periods,
) -> FilteredResult:
    energy_calculator = EnergyCalculator(graph=model.get_graph())
    precision = 6

    consumer_results = energy_calculator.evaluate_energy_usage(variables)
    emission_results = energy_calculator.evaluate_emissions(
        variables_map=variables,
        consumer_results=consumer_results,
    )

    graph_result = GraphResult(
        graph=model.get_graph(),
        variables_map=variables,
        consumer_results=consumer_results,
        emission_results=emission_results,
    )

    ltp_filter = LTPConfig.filter(frequency=frequency)
    ltp_result = ltp_filter.filter(ExportableGraphResult(graph_result), periods)

    return ltp_result


def get_sum_ltp_column(ltp_result: FilteredResult, installation_nr, ltp_column: str) -> float:
    installation_query_results = ltp_result.query_results[installation_nr].query_results
    column = [column for column in installation_query_results if column.id == ltp_column][0]

    ltp_sum = sum(float(v) for (k, v) in column.values.items())
    return ltp_sum


def get_ltp_column(ltp_result: FilteredResult, installation_nr, ltp_column: str) -> QueryResult:
    installation_query_results = ltp_result.query_results[installation_nr].query_results
    column = [column for column in installation_query_results if column.id == ltp_column][0]

    return column


def get_ltp_result(model, variables, frequency=Frequency.YEAR):
    return get_consumption(model=model, variables=variables, periods=variables.get_periods(), frequency=frequency)


def create_variables_map(time_vector, rate_values=None):
    variables = {"RATE": rate_values} if rate_values else {}
    return VariablesMap(time_vector=time_vector, variables=variables)


def calculate_asset_result(
    model: YamlModel,
    variables: VariablesMap,
):
    model = model
    graph = model.get_graph()
    energy_calculator = EnergyCalculator(graph=graph)

    consumer_results = energy_calculator.evaluate_energy_usage(variables)
    emission_results = energy_calculator.evaluate_emissions(variables, consumer_results)

    results_core = GraphResult(
        graph=graph,
        variables_map=variables,
        consumer_results=consumer_results,
        emission_results=emission_results,
    )

    results_dto = get_asset_result(results_core)

    return results_dto


def get_yaml_model(yaml_string: str, frequency: Frequency, resource_service: Optional[dict[str:MemoryResource]] = None):
    configuration_service = OverridableStreamConfigurationService(
        stream=ResourceStream(name="", stream=StringIO(yaml_string)),
    )
    if resource_service is not None:
        resource_service = resource_service
    else:
        resource_service = FileResourceService(working_directory=Path(""))

    return YamlModel(
        configuration_service=configuration_service,
        resource_service=resource_service,
        output_frequency=frequency,
    ).validate_for_run()


def get_asset_yaml_model(
    installations: [YamlInstallation],
    time_vector: list[datetime],
    frequency: Frequency,
    fuel_types: Optional[list[YamlFuelType]] = None,
    facility_inputs: Optional[list[YamlFacilityModel]] = None,
    resource_service: Optional[ResourceService] = None,
    time_series: Optional[list[YamlTimeSeriesCollection]] = None,
):
    asset = (
        YamlAssetBuilder()
        .with_installations(installations=installations)
        .with_start(time_vector[0])
        .with_end(time_vector[-1])
    )

    if fuel_types is not None:
        asset.fuel_types = fuel_types

    if facility_inputs is not None:
        asset.facility_inputs = facility_inputs

    if time_series is not None:
        asset.time_series = time_series

    asset = asset.validate()

    asset_dict = asset.model_dump(
        serialize_as_any=True,
        mode="json",
        exclude_unset=True,
        by_alias=True,
    )

    asset_yaml_string = PyYamlYamlModel.dump_yaml(yaml_dict=asset_dict)
    asset_yaml_model = get_yaml_model(
        yaml_string=asset_yaml_string, frequency=frequency, resource_service=resource_service
    )

    return asset_yaml_model


class TestLtp:
    @classmethod
    def setup_class(cls):
        cls.power_usage_mw = 10
        cls.power_offshore_wind_mw = 1
        cls.power_compressor_mw = 3

        cls.fuel_rate = 67000
        cls.diesel_rate = 120000

        cls.load_consumer = 10
        cls.compressor_rate = 3000000
        cls.regularity_installation = 1.0

        cls.co2_factor = 1
        cls.ch4_factor = 0.1
        cls.nox_factor = 0.5
        cls.nmvoc_factor = 0

        cls.time_vector_installation = [date1, date2, date3, date4, date5]

    def emission_calculate(self, rate: float, factor: float, days: list[int], regularity: float = None):
        if regularity is None:
            regularity = self.regularity_installation
        emission_kg_per_day = float(rate * factor)
        emission_tons_per_day = Unit.KILO_PER_DAY.to(Unit.TONS_PER_DAY)(emission_kg_per_day)
        n_days = np.sum(days)
        emission_tons = float(emission_tons_per_day * n_days * regularity)
        return emission_tons

    def consumption_calculate(self, rate: float, days: list[int], regularity: float = None):
        if regularity is None:
            regularity = self.regularity_installation
        n_days = np.sum(days)
        return float(rate * n_days * regularity)

    def el_consumption_calculate(self, power: float, days: list[int], regularity: float = None):
        if regularity is None:
            regularity = self.regularity_installation
        n_days = np.sum(days)
        consumption_mw_per_day = power * n_days * regularity
        consumption = float(Unit.MEGA_WATT_DAYS.to(Unit.GIGA_WATT_HOURS)(consumption_mw_per_day))
        return consumption

    def fuel_consumer_compressor(self, fuel: str, name: str = "compressor"):
        return (
            YamlFuelConsumerBuilder()
            .with_name(name)
            .with_fuel({period_from_date1.start: fuel})
            .with_energy_usage_model(self.compressor_energy_usage_model)
            .with_category(
                self.temporal_dict(
                    reference1=ConsumerUserDefinedCategoryType.MISCELLANEOUS,
                    reference2=ConsumerUserDefinedCategoryType.GAS_DRIVEN_COMPRESSOR,
                )
            )
        ).validate()

    def fuel_multi_temporal(self, fuel1: YamlFuelType, fuel2: YamlFuelType):
        return {
            period1.start: fuel1.name,
            period2.start: fuel2.name,
            period3.start: fuel1.name,
            period4.start: fuel2.name,
            period5.start: fuel1.name,
        }

    def offshore_wind_consumer(self, request, power_mw: float = 1):
        energy_usage_model_direct_load = request.getfixturevalue("energy_usage_model_direct_load")
        return (
            YamlElectricityConsumerBuilder()
            .with_name("offshore_wind_consumer")
            .with_category(
                {
                    period1.start: ConsumerUserDefinedCategoryType.MISCELLANEOUS,
                    period2.start: ConsumerUserDefinedCategoryType.OFFSHORE_WIND,
                    period3.start: ConsumerUserDefinedCategoryType.MISCELLANEOUS,
                    period4.start: ConsumerUserDefinedCategoryType.OFFSHORE_WIND,
                    period5.start: ConsumerUserDefinedCategoryType.MISCELLANEOUS,
                }
            )
            .with_energy_usage_model(
                {
                    period1.start: energy_usage_model_direct_load(load=0),
                    period2.start: energy_usage_model_direct_load(load=power_mw),
                    period3.start: energy_usage_model_direct_load(load=0),
                    period4.start: energy_usage_model_direct_load(load=power_mw),
                    period5.start: energy_usage_model_direct_load(load=0),
                }
            )
        ).validate()

    def generator_set(
        self,
        request,
        fuel: str = None,
        el_consumer: YamlElectricityConsumer = None,
        el2fuel: Union[str, dict[datetime, str]] = None,
        category: dict[datetime, ConsumerUserDefinedCategoryType] = None,
        date: datetime = period_from_date1.start,
        name: str = "generator_set",
    ):
        if el_consumer is None:
            direct_load = request.getfixturevalue("el_consumer_direct_base_load")
            el_consumer = direct_load(el_reference_name="base_load", load=self.load_consumer)

        if fuel is None:
            fuel_gas = request.getfixturevalue("fuel_gas")
            fuel = fuel_gas(["co2"], [self.co2_factor]).name

        if el2fuel is None:
            el2fuel = {date: self.generator_fuel_energy_function.name}

        if category is None:
            category = {date: ConsumerUserDefinedCategoryType.TURBINE_GENERATOR}

        return (
            YamlGeneratorSetBuilder()
            .with_name(name)
            .with_fuel(fuel)
            .with_category(category)
            .with_electricity2fuel(el2fuel)
            .with_consumers([el_consumer])
        ).validate()

    def temporal_dict(self, reference1: str, reference2: str):
        return {
            period1.start: reference1,
            period2.start: reference2,
            period3.start: reference1,
            period4.start: reference2,
            period5.start: reference1,
        }

    def category_dict(self) -> dict[datetime, ConsumerUserDefinedCategoryType]:
        return {
            period1.start: ConsumerUserDefinedCategoryType.TURBINE_GENERATOR,
            period2.start: ConsumerUserDefinedCategoryType.POWER_FROM_SHORE,
            period3.start: ConsumerUserDefinedCategoryType.TURBINE_GENERATOR,
            period4.start: ConsumerUserDefinedCategoryType.POWER_FROM_SHORE,
            period5.start: ConsumerUserDefinedCategoryType.TURBINE_GENERATOR,
        }

    def category_dict_coarse(self) -> dict[datetime, ConsumerUserDefinedCategoryType]:
        return {
            period1.start: ConsumerUserDefinedCategoryType.TURBINE_GENERATOR,
            period2.start: ConsumerUserDefinedCategoryType.POWER_FROM_SHORE,
            period_from_date3.start: ConsumerUserDefinedCategoryType.TURBINE_GENERATOR,
        }

    @property
    def generator_fuel_energy_function(self):
        return (
            YamlElectricity2fuelBuilder()
            .with_name("generator_fuel_energy_function")
            .with_file("generator_fuel_energy_function")
        ).validate()

    @property
    def generator_diesel_energy_function(self):
        return (
            YamlElectricity2fuelBuilder()
            .with_name("generator_diesel_energy_function")
            .with_file("generator_diesel_energy_function")
        ).validate()

    @property
    def compressor_energy_function(self):
        return (
            YamlCompressorTabularBuilder()
            .with_name("compressor_energy_function")
            .with_file("compressor_energy_function")
        ).validate()

    @property
    def power_from_shore_energy_function(self):
        return (
            YamlElectricity2fuelBuilder().with_name("pfs_energy_function").with_file("pfs_energy_function")
        ).validate()

    @property
    def compressor_energy_usage_model(self):
        return (
            YamlEnergyUsageModelCompressorBuilder()
            .with_rate(self.compressor_rate)
            .with_suction_pressure(200)
            .with_discharge_pressure(400)
            .with_energy_function(self.compressor_energy_function.name)
        ).validate()

    @property
    def fuel_consumption(self):
        return TestLtp.consumption_calculate(self, rate=self.fuel_rate, days=[days_year2_second_half])

    @property
    def diesel_consumption(self):
        return TestLtp.consumption_calculate(
            self, rate=self.diesel_rate, days=[days_year1_first_half, days_year2_first_half]
        )

    @property
    def pfs_el_consumption(self):
        return TestLtp.el_consumption_calculate(self, power=self.power_usage_mw, days=[days_year1_second_half])

    @property
    def gas_turbine_el_generated(self):
        return TestLtp.el_consumption_calculate(
            self, power=self.power_usage_mw, days=[days_year1_first_half, days_year2_first_half, days_year2_second_half]
        )

    @property
    def boiler_fuel_consumption(self):
        return TestLtp.consumption_calculate(
            self, rate=self.fuel_rate, days=[days_year1_first_half, days_year1_second_half, days_year2_first_half]
        )

    @property
    def heater_fuel_consumption(self):
        return TestLtp.consumption_calculate(self, rate=self.fuel_rate, days=[days_year2_second_half])

    @property
    def co2_from_boiler(self):
        return TestLtp.emission_calculate(
            self,
            rate=self.fuel_rate,
            factor=self.co2_factor,
            days=[days_year1_first_half, days_year1_second_half, days_year2_first_half],
        )

    @property
    def co2_from_heater(self):
        return TestLtp.emission_calculate(
            self, rate=self.fuel_rate, factor=self.co2_factor, days=[days_year2_second_half]
        )

    @property
    def co2_from_fuel(self):
        return TestLtp.emission_calculate(
            self, rate=self.fuel_rate, factor=self.co2_factor, days=[days_year2_second_half]
        )

    @property
    def co2_from_diesel(self):
        return TestLtp.emission_calculate(
            self, rate=self.diesel_rate, factor=self.co2_factor, days=[days_year1_first_half, days_year2_first_half]
        )

    @property
    def ch4_from_diesel(self):
        return TestLtp.emission_calculate(
            self, rate=self.diesel_rate, factor=self.ch4_factor, days=[days_year1_first_half, days_year2_first_half]
        )

    @property
    def nox_from_diesel(self):
        return TestLtp.emission_calculate(
            self, rate=self.diesel_rate, factor=self.nox_factor, days=[days_year1_first_half, days_year2_first_half]
        )

    @property
    def nmvoc_from_diesel(self):
        return TestLtp.emission_calculate(
            self, rate=self.diesel_rate, factor=self.nmvoc_factor, days=[days_year1_first_half, days_year2_first_half]
        )

    @property
    def offshore_wind_el_consumption(self):
        return TestLtp.el_consumption_calculate(
            self, power=self.power_offshore_wind_mw, days=[days_year1_second_half, days_year2_second_half]
        ) * (-1)

    @property
    def gas_turbine_compressor_el_consumption(self):
        return TestLtp.el_consumption_calculate(
            self, power=self.power_compressor_mw, days=[days_year1_second_half, days_year2_second_half]
        )

    def test_emissions_diesel_fixed_and_mobile(
        self,
        fuel_gas,
        diesel,
        resource_service_factory,
        el_consumer_direct_base_load,
        generator_diesel_power_to_fuel_resource,
        generator_fuel_power_to_fuel_resource,
    ):
        fuel = fuel_gas(["co2"], [self.co2_factor])
        fuel_diesel = diesel(
            ["co2", "ch4", "nox", "nmvoc"], [self.co2_factor, self.ch4_factor, self.nox_factor, self.nmvoc_factor]
        )

        generator_fixed = (
            YamlGeneratorSetBuilder()
            .with_name("generator_fixed")
            .with_category(self.category_dict())
            .with_consumers([el_consumer_direct_base_load(el_reference_name="base_load", load=self.load_consumer)])
            .with_electricity2fuel(
                self.temporal_dict(
                    reference1=self.generator_diesel_energy_function.name,
                    reference2=self.generator_fuel_energy_function.name,
                )
            )
        ).validate()

        generator_mobile = deepcopy(generator_fixed)
        generator_mobile.name = "generator_mobile"

        installation_fixed = (
            YamlInstallationBuilder()
            .with_name("INSTALLATION_FIXED")
            .with_regularity(self.regularity_installation)
            .with_fuel(self.fuel_multi_temporal(fuel_diesel, fuel))
            .with_category(InstallationUserDefinedCategoryType.FIXED)
            .with_generator_sets([generator_fixed])
        ).validate()

        installation_mobile = (
            YamlInstallationBuilder()
            .with_name("INSTALLATION_MOBILE")
            .with_regularity(self.regularity_installation)
            .with_fuel(self.fuel_multi_temporal(fuel_diesel, fuel))
            .with_category(InstallationUserDefinedCategoryType.MOBILE)
            .with_generator_sets([generator_mobile])
        ).validate()

        resources = {
            self.generator_diesel_energy_function.name: generator_diesel_power_to_fuel_resource(
                power_usage_mw=self.power_usage_mw, diesel_rate=self.diesel_rate
            ),
            self.generator_fuel_energy_function.name: generator_fuel_power_to_fuel_resource(
                power_usage_mw=self.power_usage_mw, fuel_rate=self.fuel_rate
            ),
        }
        resource_service = resource_service_factory(resources=resources)

        asset = get_asset_yaml_model(
            installations=[installation_fixed, installation_mobile],
            fuel_types=[fuel, fuel_diesel],
            time_vector=self.time_vector_installation,
            facility_inputs=[self.generator_diesel_energy_function, self.generator_fuel_energy_function],
            frequency=Frequency.YEAR,
            resource_service=resource_service,
        )

        variables = create_variables_map(self.time_vector_installation, [1, 1, 1, 1])
        ltp_result = get_ltp_result(asset, variables)

        co2_from_diesel_fixed = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column="engineDieselCo2Mass")
        co2_from_diesel_mobile = get_sum_ltp_column(
            ltp_result, installation_nr=1, ltp_column="engineNoCo2TaxDieselCo2Mass"
        )

        nox_from_diesel_fixed = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column="engineDieselNoxMass")
        nox_from_diesel_mobile = get_sum_ltp_column(
            ltp_result, installation_nr=1, ltp_column="engineNoCo2TaxDieselNoxMass"
        )

        nmvoc_from_diesel_fixed = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column="engineDieselNmvocMass")
        nmvoc_from_diesel_mobile = get_sum_ltp_column(
            ltp_result, installation_nr=1, ltp_column="engineNoCo2TaxDieselNmvocMass"
        )

        ch4_from_diesel_fixed = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column="engineDieselCh4Mass")
        ch4_from_diesel_mobile = get_sum_ltp_column(
            ltp_result, installation_nr=1, ltp_column="engineNoCo2TaxDieselCh4Mass"
        )

        assert co2_from_diesel_fixed == self.co2_from_diesel
        assert co2_from_diesel_mobile == self.co2_from_diesel
        assert nox_from_diesel_fixed == self.nox_from_diesel
        assert nox_from_diesel_mobile == self.nox_from_diesel
        assert nmvoc_from_diesel_fixed == self.nmvoc_from_diesel
        assert nmvoc_from_diesel_mobile == self.nmvoc_from_diesel
        assert ch4_from_diesel_fixed == self.ch4_from_diesel
        assert ch4_from_diesel_mobile == self.ch4_from_diesel

    def test_temporal_models_detailed(
        self,
        diesel,
        fuel_gas,
        generator_diesel_power_to_fuel_resource,
        generator_fuel_power_to_fuel_resource,
        resource_service_factory,
        el_consumer_direct_base_load,
    ):
        """Test various queries for LTP reporting. Purpose: ensure that variations in temporal models are captured.

        Detailed temporal models (variations within one year) for:
        - Fuel type
        - Generator set user defined category
        - Generator set model
        """
        variables = create_variables_map(self.time_vector_installation, rate_values=[1, 1, 1, 1])
        fuel = fuel_gas(["co2"], [self.co2_factor])
        diesel = diesel(["co2"], [self.co2_factor])

        generator_set = (
            YamlGeneratorSetBuilder()
            .with_name("generator_set")
            .with_category(self.category_dict_coarse())
            .with_consumers([el_consumer_direct_base_load(el_reference_name="base_load", load=self.load_consumer)])
            .with_electricity2fuel(
                self.temporal_dict(
                    reference1=self.generator_diesel_energy_function.name,
                    reference2=self.generator_fuel_energy_function.name,
                )
            )
        ).validate()

        installation = (
            YamlInstallationBuilder()
            .with_name("INSTALLATION A")
            .with_generator_sets([generator_set])
            .with_fuel(self.fuel_multi_temporal(fuel1=diesel, fuel2=fuel))
            .with_category(InstallationUserDefinedCategoryType.FIXED)
        ).validate()

        resources = {
            self.generator_diesel_energy_function.name: generator_diesel_power_to_fuel_resource(
                power_usage_mw=self.power_usage_mw,
                diesel_rate=self.diesel_rate,
            ),
            self.generator_fuel_energy_function.name: generator_fuel_power_to_fuel_resource(
                power_usage_mw=self.power_usage_mw,
                fuel_rate=self.fuel_rate,
            ),
        }
        resource_service = resource_service_factory(resources=resources)

        asset = get_asset_yaml_model(
            installations=[installation],
            fuel_types=[fuel, diesel],
            time_vector=self.time_vector_installation,
            facility_inputs=[self.generator_diesel_energy_function, self.generator_fuel_energy_function],
            frequency=Frequency.YEAR,
            resource_service=resource_service,
        )

        ltp_result = get_ltp_result(asset, variables)

        turbine_fuel_consumption = get_sum_ltp_column(
            ltp_result, installation_nr=0, ltp_column="turbineFuelGasConsumption"
        )
        engine_diesel_consumption = get_sum_ltp_column(
            ltp_result, installation_nr=0, ltp_column="engineDieselConsumption"
        )

        gas_turbine_el_generated = get_sum_ltp_column(
            ltp_result, installation_nr=0, ltp_column="gasTurbineGeneratorConsumption"
        )
        pfs_el_consumption = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column="fromShoreConsumption")

        co2_from_fuel = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column="turbineFuelGasCo2Mass")
        co2_from_diesel = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column="engineDieselCo2Mass")

        # FuelQuery: Check that turbine fuel consumption is included,
        # even if the temporal model starts with diesel every year
        assert turbine_fuel_consumption != 0

        # FuelQuery: Check that turbine fuel consumption is correct
        # fuel_consumption = expected_fuel_consumption(fuel_rate, regularity_installation)
        # diesel_consumption = expected_diesel_consumption(diesel_rate, regularity_installation)

        assert turbine_fuel_consumption == self.fuel_consumption

        # FuelQuery: Check that turbine fuel gas is not categorized as diesel,
        # even if the temporal model starts with diesel every year
        assert engine_diesel_consumption != self.diesel_consumption + self.fuel_consumption

        # FuelQuery: Check that diesel consumption is correct
        assert engine_diesel_consumption == pytest.approx(self.diesel_consumption, 0.00001)

        # ElectricityGeneratedQuery: Check that turbine power generation is correct.
        assert gas_turbine_el_generated == pytest.approx(self.gas_turbine_el_generated, 0.00001)

        # ElectricityGeneratedQuery: Check that power from shore el consumption is correct.
        assert pfs_el_consumption == pytest.approx(self.pfs_el_consumption, 0.00001)

        # EmissionQuery. Check that co2 from fuel is correct.
        assert co2_from_fuel == self.co2_from_fuel

        # EmissionQuery: Emissions. Check that co2 from diesel is correct.
        assert co2_from_diesel == self.co2_from_diesel

    def test_temporal_models_offshore_wind(
        self,
        request,
        el_consumer_direct_base_load,
        fuel_gas,
        generator_fuel_power_to_fuel_resource,
        resource_service_factory,
    ):
        """Test ElConsumerPowerConsumptionQuery for calculating offshore wind el-consumption, LTP.

        Detailed temporal models (variations within one year) for:
        - El-consumer user defined category
        - El-consumer energy usage model
        """
        variables = create_variables_map(self.time_vector_installation, rate_values=[1, 1, 1, 1])
        fuel = fuel_gas(["co2"], [self.co2_factor])

        generator_set = (
            YamlGeneratorSetBuilder()
            .with_name("generator_set")
            .with_category({period_from_date1.start: ConsumerUserDefinedCategoryType.TURBINE_GENERATOR})
            .with_consumers([self.offshore_wind_consumer(request, self.power_offshore_wind_mw)])
            .with_electricity2fuel({period_from_date1.start: self.generator_fuel_energy_function.name})
        ).validate()

        installation = (
            YamlInstallationBuilder()
            .with_name("INSTALLATION A")
            .with_generator_sets([generator_set])
            .with_fuel(fuel.name)
            .with_category(InstallationUserDefinedCategoryType.FIXED)
        ).validate()

        resources = {
            self.generator_fuel_energy_function.name: generator_fuel_power_to_fuel_resource(
                power_usage_mw=self.power_usage_mw,
                fuel_rate=self.fuel_rate,
            ),
        }

        resource_service = resource_service_factory(resources=resources)

        asset = get_asset_yaml_model(
            installations=[installation],
            fuel_types=[fuel],
            time_vector=self.time_vector_installation,
            facility_inputs=[self.generator_fuel_energy_function],
            frequency=Frequency.YEAR,
            resource_service=resource_service,
        )

        ltp_result = get_ltp_result(asset, variables)

        offshore_wind_el_consumption = get_sum_ltp_column(
            ltp_result, installation_nr=0, ltp_column="offshoreWindConsumption"
        )

        # ElConsumerPowerConsumptionQuery: Check that offshore wind el-consumption is correct.
        assert offshore_wind_el_consumption == self.offshore_wind_el_consumption

    def test_temporal_models_compressor(
        self,
        generator_fuel_power_to_fuel_resource,
        compressor_sampled_fuel_driven_resource,
        resource_service_factory,
        fuel_gas,
    ):
        """Test FuelConsumerPowerConsumptionQuery for calculating gas turbine compressor el-consumption, LTP.

        Detailed temporal models (variations within one year) for:
        - Fuel consumer user defined category
        """
        variables = create_variables_map(self.time_vector_installation, rate_values=[1, 1, 1, 1])
        fuel = fuel_gas(["co2"], [self.co2_factor])

        generator_set = (
            YamlGeneratorSetBuilder()
            .with_name("generator_set")
            .with_category({period_from_date1.start: ConsumerUserDefinedCategoryType.TURBINE_GENERATOR})
            .with_electricity2fuel({period_from_date1.start: self.generator_fuel_energy_function.name})
        ).validate()

        installation = (
            YamlInstallationBuilder()
            .with_name("INSTALLATION A")
            .with_generator_sets([generator_set])
            .with_fuel(fuel.name)
            .with_fuel_consumers([self.fuel_consumer_compressor(fuel.name)])
            .with_category(InstallationUserDefinedCategoryType.FIXED)
        ).validate()

        resources = {
            self.generator_fuel_energy_function.name: generator_fuel_power_to_fuel_resource(
                power_usage_mw=self.power_usage_mw,
                fuel_rate=self.fuel_rate,
            ),
            self.compressor_energy_function.name: compressor_sampled_fuel_driven_resource(
                compressor_rate=self.compressor_rate, power_compressor_mw=self.power_compressor_mw
            ),
        }

        resource_service = resource_service_factory(resources=resources)

        asset = get_asset_yaml_model(
            installations=[installation],
            fuel_types=[fuel],
            time_vector=self.time_vector_installation,
            facility_inputs=[self.generator_fuel_energy_function, self.compressor_energy_function],
            frequency=Frequency.YEAR,
            resource_service=resource_service,
        )

        ltp_result = get_ltp_result(asset, variables)

        gas_turbine_compressor_el_consumption = get_sum_ltp_column(
            ltp_result, installation_nr=0, ltp_column="gasTurbineCompressorConsumption"
        )

        # FuelConsumerPowerConsumptionQuery. Check gas turbine compressor el consumption.
        assert gas_turbine_compressor_el_consumption == self.gas_turbine_compressor_el_consumption

    def test_boiler_heater_categories(self, fuel_gas):
        variables = create_variables_map(self.time_vector_installation)
        fuel = fuel_gas(["co2"], [self.co2_factor])

        energy_usage_model = (
            YamlEnergyUsageModelDirectBuilder()
            .with_fuel_rate(self.fuel_rate)
            .with_consumption_rate_type(ConsumptionRateType.STREAM_DAY)
        ).validate()

        fuel_consumer = (
            YamlFuelConsumerBuilder()
            .with_name("boiler_heater")
            .with_fuel(fuel.name)
            .with_energy_usage_model({full_period.start: energy_usage_model})
            .with_category(
                {
                    Period(date1, date4).start: ConsumerUserDefinedCategoryType.BOILER,
                    Period(date4).start: ConsumerUserDefinedCategoryType.HEATER,
                }
            )
        ).validate()

        installation = (
            YamlInstallationBuilder()
            .with_name("INSTALLATION A")
            .with_category(InstallationUserDefinedCategoryType.FIXED)
            .with_fuel(fuel.name)
            .with_fuel_consumers([fuel_consumer])
            .with_regularity(self.regularity_installation)
        ).validate()

        asset = get_asset_yaml_model(
            installations=[installation],
            fuel_types=[fuel],
            time_vector=[date1, date5],
            frequency=Frequency.YEAR,
        )

        ltp_result = get_ltp_result(asset, variables)

        boiler_fuel_consumption = get_sum_ltp_column(
            ltp_result, installation_nr=0, ltp_column="boilerFuelGasConsumption"
        )
        heater_fuel_consumption = get_sum_ltp_column(
            ltp_result, installation_nr=0, ltp_column="heaterFuelGasConsumption"
        )
        co2_from_boiler = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column="boilerFuelGasCo2Mass")
        co2_from_heater = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column="heaterFuelGasCo2Mass")

        assert boiler_fuel_consumption == self.boiler_fuel_consumption
        assert heater_fuel_consumption == self.heater_fuel_consumption
        assert co2_from_boiler == self.co2_from_boiler
        assert co2_from_heater == self.co2_from_heater

    def test_total_oil_loaded_old_method(self, fuel_gas, fuel_consumer_direct):
        """Test total oil loaded/stored for LTP export. Using original method where direct/venting emitters are
        modelled as FUELSCONSUMERS using DIRECT.

        Verify correct volume when model includes emissions related to both storage and loading of oil,
        and when model includes only loading.
        """
        time_vector = [datetime(2027, 1, 1), datetime(2028, 1, 1)]
        variables = create_variables_map(time_vector)

        regularity = 0.6
        emission_factor = 2
        rate = 100

        fuel = fuel_gas(["ch4"], [emission_factor])
        loading = fuel_consumer_direct(
            fuel_reference_name=fuel.name, rate=rate, name="loading", category=ConsumerUserDefinedCategoryType.LOADING
        )

        storage = fuel_consumer_direct(
            fuel_reference_name=fuel.name, rate=rate, name="storage", category=ConsumerUserDefinedCategoryType.STORAGE
        )

        installation = (
            YamlInstallationBuilder()
            .with_name("minimal_installation")
            .with_fuel(fuel.name)
            .with_fuel_consumers([loading, storage])
            .with_regularity(regularity)
            .with_category(InstallationUserDefinedCategoryType.FIXED)
        ).validate()

        asset = get_asset_yaml_model(
            installations=[installation],
            fuel_types=[fuel],
            time_vector=self.time_vector_installation,
            frequency=Frequency.YEAR,
        )

        installation_loading_only = (
            YamlInstallationBuilder()
            .with_name("minimal_installation")
            .with_fuel(fuel.name)
            .with_fuel_consumers([loading])
            .with_regularity(regularity)
            .with_category(InstallationUserDefinedCategoryType.FIXED)
        ).validate()

        asset_loading_only = get_asset_yaml_model(
            installations=[installation_loading_only],
            fuel_types=[fuel],
            time_vector=self.time_vector_installation,
            frequency=Frequency.YEAR,
        )

        ltp_result_loading_storage = get_ltp_result(asset, variables)
        ltp_result_loading_only = get_ltp_result(asset_loading_only, variables)

        loaded_and_stored_oil_loading_and_storage = get_sum_ltp_column(
            ltp_result_loading_storage, installation_nr=0, ltp_column="loadedAndStoredOil"
        )
        loaded_and_stored_oil_loading_only = get_sum_ltp_column(
            ltp_result_loading_only, installation_nr=0, ltp_column="loadedAndStoredOil"
        )

        # Verify output for total oil loaded/stored, if only loading is specified.
        assert loaded_and_stored_oil_loading_only is not None

        # Verify correct volume for oil loaded/stored
        assert loaded_and_stored_oil_loading_and_storage == rate * 365 * regularity

        # Verify that total oil loaded/stored is the same if only loading is specified,
        # compared to a model with both loading and storage.
        assert loaded_and_stored_oil_loading_and_storage == loaded_and_stored_oil_loading_only

    def test_electrical_and_mechanical_power_installation(
        self,
        request,
        fuel_gas,
        resource_service_factory,
        generator_fuel_power_to_fuel_resource,
        compressor_sampled_fuel_driven_resource,
    ):
        """Check that new total power includes the sum of electrical- and mechanical power at installation level"""
        variables = create_variables_map(self.time_vector_installation)

        fuel = fuel_gas(["co2"], [self.co2_factor])

        generator_set = self.generator_set(request)

        installation = (
            YamlInstallationBuilder()
            .with_name("INSTALLATION A")
            .with_generator_sets([generator_set])
            .with_fuel(fuel.name)
            .with_regularity(self.regularity_installation)
            .with_fuel_consumers([self.fuel_consumer_compressor(fuel.name)])
            .with_category(InstallationUserDefinedCategoryType.FIXED)
        ).validate()

        resources = {
            self.generator_fuel_energy_function.name: generator_fuel_power_to_fuel_resource(
                power_usage_mw=self.power_usage_mw,
                fuel_rate=self.fuel_rate,
            ),
            self.compressor_energy_function.name: compressor_sampled_fuel_driven_resource(
                compressor_rate=self.compressor_rate, power_compressor_mw=self.power_compressor_mw
            ),
        }

        resource_service = resource_service_factory(resources=resources)

        asset = get_asset_yaml_model(
            installations=[installation],
            fuel_types=[fuel],
            time_vector=self.time_vector_installation,
            facility_inputs=[self.generator_fuel_energy_function, self.compressor_energy_function],
            frequency=Frequency.YEAR,
            resource_service=resource_service,
        )

        asset_result = calculate_asset_result(model=asset, variables=variables)
        power_fuel_driven_compressor = asset_result.get_component_by_name("compressor").power_cumulative.values[-1]
        power_generator_set = asset_result.get_component_by_name("generator_set").power_cumulative.values[-1]

        # Extract cumulative electrical-, mechanical- and total power.
        power_electrical_installation = asset_result.get_component_by_name(
            "INSTALLATION A"
        ).power_electrical_cumulative.values[-1]

        power_mechanical_installation = asset_result.get_component_by_name(
            "INSTALLATION A"
        ).power_mechanical_cumulative.values[-1]

        power_total_installation = asset_result.get_component_by_name("INSTALLATION A").power_cumulative.values[-1]

        # Verify that total power is correct
        assert power_total_installation == power_electrical_installation + power_mechanical_installation

        # Verify that electrical power equals genset power, and mechanical power equals power from gas driven compressor:
        assert power_generator_set == power_electrical_installation
        assert power_fuel_driven_compressor == power_mechanical_installation

    def test_electrical_and_mechanical_power_asset(
        self,
        request,
        fuel_gas,
        el_consumer_direct_base_load,
        generator_fuel_power_to_fuel_resource,
        compressor_sampled_fuel_driven_resource,
        resource_service_factory,
    ):
        """Check that new total power includes the sum of electrical- and mechanical power at installation level"""
        variables = create_variables_map(self.time_vector_installation)
        name1 = "INSTALLATION_1"
        name2 = "INSTALLATION_2"

        el_consumer1 = el_consumer_direct_base_load(el_reference_name="base_load1", load=self.load_consumer)
        el_consumer2 = el_consumer_direct_base_load(el_reference_name="base_load2", load=self.load_consumer)

        fuel = fuel_gas(["co2"], [self.co2_factor])

        generator_set1 = self.generator_set(request, name="generator_set1", el_consumer=el_consumer1)
        generator_set2 = self.generator_set(request, name="generator_set2", el_consumer=el_consumer2)

        installation1 = (
            YamlInstallationBuilder()
            .with_name(name1)
            .with_generator_sets([generator_set1])
            .with_fuel(fuel.name)
            .with_regularity(self.regularity_installation)
            .with_fuel_consumers([self.fuel_consumer_compressor(fuel.name)])
            .with_category(InstallationUserDefinedCategoryType.FIXED)
        ).validate()

        installation2 = (
            YamlInstallationBuilder()
            .with_name(name2)
            .with_generator_sets([generator_set2])
            .with_fuel(fuel.name)
            .with_regularity(self.regularity_installation)
            .with_fuel_consumers([self.fuel_consumer_compressor(fuel.name, name="compressor2")])
            .with_category(InstallationUserDefinedCategoryType.FIXED)
        ).validate()

        resources = {
            self.generator_fuel_energy_function.name: generator_fuel_power_to_fuel_resource(
                power_usage_mw=self.power_usage_mw,
                fuel_rate=self.fuel_rate,
            ),
            self.compressor_energy_function.name: compressor_sampled_fuel_driven_resource(
                compressor_rate=self.compressor_rate, power_compressor_mw=self.power_compressor_mw
            ),
        }

        resource_service = resource_service_factory(resources=resources)

        asset = get_asset_yaml_model(
            installations=[installation1, installation2],
            fuel_types=[fuel],
            time_vector=self.time_vector_installation,
            facility_inputs=[self.generator_fuel_energy_function, self.compressor_energy_function],
            frequency=Frequency.YEAR,
            resource_service=resource_service,
        )
        asset.dto.name = "Asset"

        asset_result = calculate_asset_result(model=asset, variables=variables)

        power_el_1 = asset_result.get_component_by_name(name1).power_electrical_cumulative.values[-1]
        power_mech_1 = asset_result.get_component_by_name(name1).power_mechanical_cumulative.values[-1]

        power_el_2 = asset_result.get_component_by_name(name2).power_electrical_cumulative.values[-1]
        power_mech_2 = asset_result.get_component_by_name(name2).power_mechanical_cumulative.values[-1]

        asset_power_el = asset_result.get_component_by_name("Asset").power_electrical_cumulative.values[-1]

        asset_power_mech = asset_result.get_component_by_name("Asset").power_mechanical_cumulative.values[-1]

        # Verify that electrical power is correct at asset level
        assert asset_power_el == power_el_1 + power_el_2

        # Verify that mechanical power is correct at asset level:
        assert asset_power_mech == power_mech_1 + power_mech_2

    def test_venting_emitters(self, fuel_consumer_direct, fuel_gas):
        """Test venting emitters for LTP export.

        Verify correct behaviour if input rate is given in different units and rate types (sd and cd).
        """

        time_vector = [datetime(2027, 1, 1), datetime(2028, 1, 1)]
        regularity = 0.2
        emission_rate = 10

        variables = create_variables_map(time_vector)
        fuel = fuel_gas(["co2"], [self.co2_factor])

        venting_emitter_sd_kg_per_day = (
            YamlVentingEmitterDirectTypeBuilder()
            .with_name("Venting emitter 1")
            .with_category(ConsumerUserDefinedCategoryType.STORAGE)
            .with_emission_names_rates_units_and_types(
                names=["ch4"],
                rates=[emission_rate],
                units=[YamlEmissionRateUnits.KILO_PER_DAY],
                rate_types=[RateType.STREAM_DAY],
            )
        ).validate()

        venting_emitter_sd_tons_per_day = (
            YamlVentingEmitterDirectTypeBuilder()
            .with_name("Venting emitter 1")
            .with_category(ConsumerUserDefinedCategoryType.STORAGE)
            .with_emission_names_rates_units_and_types(
                names=["ch4"],
                rates=[emission_rate],
                units=[YamlEmissionRateUnits.TONS_PER_DAY],
                rate_types=[RateType.STREAM_DAY],
            )
        ).validate()

        venting_emitter_cd_kg_per_day = (
            YamlVentingEmitterDirectTypeBuilder()
            .with_name("Venting emitter 1")
            .with_category(ConsumerUserDefinedCategoryType.STORAGE)
            .with_emission_names_rates_units_and_types(
                names=["ch4"],
                rates=[emission_rate],
                units=[YamlEmissionRateUnits.KILO_PER_DAY],
                rate_types=[RateType.CALENDAR_DAY],
            )
        ).validate()

        installation_sd_kg_per_day = (
            YamlInstallationBuilder()
            .with_name("minimal_installation")
            .with_category(InstallationUserDefinedCategoryType.FIXED)
            .with_fuel_consumers([fuel_consumer_direct(fuel.name, self.fuel_rate)])
            .with_venting_emitters([venting_emitter_sd_kg_per_day])
            .with_regularity(regularity)
        ).validate()

        installation_sd_tons_per_day = (
            YamlInstallationBuilder()
            .with_name("minimal_installation")
            .with_category(InstallationUserDefinedCategoryType.FIXED)
            .with_fuel_consumers([fuel_consumer_direct(fuel.name, self.fuel_rate)])
            .with_venting_emitters([venting_emitter_sd_tons_per_day])
            .with_regularity(regularity)
        ).validate()

        installation_cd_kg_per_day = (
            YamlInstallationBuilder()
            .with_name("minimal_installation")
            .with_category(InstallationUserDefinedCategoryType.FIXED)
            .with_fuel_consumers([fuel_consumer_direct(fuel.name, self.fuel_rate)])
            .with_venting_emitters([venting_emitter_cd_kg_per_day])
            .with_regularity(regularity)
        ).validate()

        asset_sd_kg_per_day = get_asset_yaml_model(
            installations=[installation_sd_kg_per_day],
            fuel_types=[fuel],
            time_vector=time_vector,
            frequency=Frequency.YEAR,
        )

        asset_sd_tons_per_day = get_asset_yaml_model(
            installations=[installation_sd_tons_per_day],
            fuel_types=[fuel],
            time_vector=time_vector,
            frequency=Frequency.YEAR,
        )

        asset_cd_kg_per_day = get_asset_yaml_model(
            installations=[installation_cd_kg_per_day],
            fuel_types=[fuel],
            time_vector=time_vector,
            frequency=Frequency.YEAR,
        )

        ltp_result_input_sd_kg_per_day = get_ltp_result(asset_sd_kg_per_day, variables)
        ltp_result_input_sd_tons_per_day = get_ltp_result(asset_sd_tons_per_day, variables)
        ltp_result_input_cd_kg_per_day = get_ltp_result(asset_cd_kg_per_day, variables)

        emission_input_sd_kg_per_day = get_sum_ltp_column(
            ltp_result_input_sd_kg_per_day, installation_nr=0, ltp_column="storageCh4Mass"
        )
        emission_input_sd_tons_per_day = get_sum_ltp_column(
            ltp_result_input_sd_tons_per_day, installation_nr=0, ltp_column="storageCh4Mass"
        )
        emission_input_cd_kg_per_day = get_sum_ltp_column(
            ltp_result_input_cd_kg_per_day, installation_nr=0, ltp_column="storageCh4Mass"
        )

        # Verify correct emissions when input is kg per day. Output should be in tons per day - hence dividing by 1000
        assert emission_input_sd_kg_per_day == (emission_rate / 1000) * 365 * regularity

        # Verify correct emissions when input is tons per day.
        assert emission_input_sd_tons_per_day == emission_rate * 365 * regularity

        # Verify that input calendar day vs input stream day is linked correctly through regularity
        assert emission_input_cd_kg_per_day == emission_input_sd_kg_per_day / regularity

        # Verify that results is independent of regularity, when input rate is in calendar days
        assert emission_input_cd_kg_per_day == (emission_rate / 1000) * 365

    def test_only_venting_emitters_no_fuelconsumers(self, fuel_consumer_direct, fuel_gas):
        """
        Test that it is possible with only venting emitters, without fuelconsumers.
        """
        time_vector = [datetime(2027, 1, 1), datetime(2028, 1, 1)]
        regularity = 0.2
        emission_rate = 10

        variables = create_variables_map(time_vector)
        fuel = fuel_gas(["co2"], [self.co2_factor])

        # Installation with only venting emitters:
        venting_emitter = (
            YamlVentingEmitterDirectTypeBuilder()
            .with_name("Venting emitter 1")
            .with_category(ConsumerUserDefinedCategoryType.STORAGE)
            .with_emission_names_rates_units_and_types(
                names=["ch4"],
                rates=[emission_rate],
                units=[YamlEmissionRateUnits.KILO_PER_DAY],
                rate_types=[RateType.STREAM_DAY],
            )
        ).validate()

        installation_only_emitters = (
            YamlInstallationBuilder()
            .with_name("Venting emitter installation")
            .with_category(InstallationUserDefinedCategoryType.FIXED)
            .with_venting_emitters([venting_emitter])
            .with_regularity(regularity)
        ).validate()

        asset = get_asset_yaml_model(
            installations=[installation_only_emitters], time_vector=time_vector, frequency=Frequency.YEAR
        )

        venting_emitter_only_results = get_ltp_result(asset, variables)

        # Verify that eCalc is not failing in get_asset_result with only venting emitters -
        # when installation result is empty, i.e. with no genset and fuel consumers:
        assert isinstance(calculate_asset_result(model=asset, variables=variables), EcalcModelResult)

        # Verify correct emissions:
        emissions_ch4 = get_sum_ltp_column(venting_emitter_only_results, installation_nr=0, ltp_column="storageCh4Mass")
        assert emissions_ch4 == (emission_rate / 1000) * 365 * regularity

        # Installation with only fuel consumers:
        installation_only_fuel_consumers = (
            YamlInstallationBuilder()
            .with_name("Fuel consumer installation")
            .with_category(InstallationUserDefinedCategoryType.FIXED)
            .with_fuel_consumers([fuel_consumer_direct(fuel_reference_name=fuel.name, rate=self.fuel_rate)])
            .with_regularity(regularity)
        ).validate()

        asset_multi_installations = get_asset_yaml_model(
            installations=[installation_only_emitters, installation_only_fuel_consumers],
            fuel_types=[fuel],
            time_vector=time_vector,
            frequency=Frequency.YEAR,
        )

        # Verify that eCalc is not failing in get_asset_result, with only venting emitters -
        # when installation result is empty for one installation, i.e. with no genset and fuel consumers.
        # Include asset with two installations, one with only emitters and one with only fuel consumers -
        # ensure that get_asset_result returns a result:
        assert isinstance(
            calculate_asset_result(model=asset_multi_installations, variables=variables), EcalcModelResult
        )

        asset_ltp_result = get_ltp_result(asset_multi_installations, variables)

        # Check that the results are the same: For the case with only one installation (only venting emitters),
        # compared to the multi-installation case with two installations. The fuel-consumer installation should
        # give no CH4-contribution (only CO2)
        emissions_ch4_asset = get_sum_ltp_column(asset_ltp_result, installation_nr=0, ltp_column="storageCh4Mass")
        assert emissions_ch4 == emissions_ch4_asset

    def test_power_from_shore(
        self,
        request,
        el_consumer_direct_base_load,
        fuel_gas,
        resource_service_factory,
        generator_electricity2fuel_17MW_resource,
        onshore_power_electricity2fuel_resource,
        cable_loss_time_series_resource,
    ):
        """Test power from shore output for LTP export."""

        time_vector_yearly = (
            pd.date_range(datetime(2025, 1, 1), datetime(2031, 1, 1), freq="YS").to_pydatetime().tolist()
        )
        fuel = fuel_gas(
            ["co2", "ch4", "nmvoc", "nox"], [self.co2_factor, self.ch4_factor, self.nmvoc_factor, self.nox_factor]
        )

        regularity = 0.2
        load = 10
        cable_loss = 0.1
        max_from_shore = 12

        cable_loss_time_series = (
            YamlTimeSeriesBuilder().with_name("CABLE_LOSS").with_type("DEFAULT").with_file("CABLE_LOSS")
        ).validate()

        generator_set = (
            YamlGeneratorSetBuilder()
            .with_name("generator1")
            .with_category(
                {
                    datetime(2025, 1, 1): ConsumerUserDefinedCategoryType.TURBINE_GENERATOR,
                    datetime(2027, 1, 1): ConsumerUserDefinedCategoryType.POWER_FROM_SHORE,
                }
            )
            .with_electricity2fuel(
                {
                    datetime(2025, 1, 1): self.generator_fuel_energy_function.name,
                    datetime(2027, 1, 1): self.power_from_shore_energy_function.name,
                }
            )
            .with_consumers([el_consumer_direct_base_load(el_reference_name="base_load", load=load)])
            .with_cable_loss(cable_loss)
            .with_max_usage_from_shore(max_from_shore)
        ).validate()

        installation_pfs = (
            YamlInstallationBuilder()
            .with_name("minimal_installation")
            .with_category(InstallationUserDefinedCategoryType.FIXED)
            .with_fuel(fuel.name)
            .with_generator_sets([generator_set])
            .with_regularity(regularity)
        ).validate()

        resources = {
            self.generator_fuel_energy_function.name: generator_electricity2fuel_17MW_resource,
            self.power_from_shore_energy_function.name: onshore_power_electricity2fuel_resource,
            cable_loss_time_series.name: cable_loss_time_series_resource,
        }
        resource_service = resource_service_factory(resources=resources)

        asset_pfs = get_asset_yaml_model(
            installations=[installation_pfs],
            fuel_types=[fuel],
            time_vector=time_vector_yearly,
            time_series=[cable_loss_time_series],
            facility_inputs=[self.generator_fuel_energy_function, self.power_from_shore_energy_function],
            frequency=Frequency.YEAR,
            resource_service=resource_service,
        )

        generator_set_csv = deepcopy(generator_set)
        generator_set_csv.cable_loss = "CABLE_LOSS;CABLE_LOSS_FACTOR"

        installation_pfs_csv = (
            YamlInstallationBuilder()
            .with_name("minimal_installation_csv")
            .with_category(InstallationUserDefinedCategoryType.FIXED)
            .with_fuel(fuel.name)
            .with_generator_sets([generator_set_csv])
            .with_regularity(regularity)
        ).validate()

        asset_pfs_csv = get_asset_yaml_model(
            installations=[installation_pfs_csv],
            fuel_types=[fuel],
            time_vector=time_vector_yearly,
            time_series=[cable_loss_time_series],
            facility_inputs=[self.generator_fuel_energy_function, self.power_from_shore_energy_function],
            frequency=Frequency.YEAR,
            resource_service=resource_service,
        )

        ltp_result = get_ltp_result(asset_pfs, asset_pfs.variables)
        ltp_result_csv = get_ltp_result(asset_pfs_csv, asset_pfs_csv.variables)

        power_from_shore_consumption = get_sum_ltp_column(
            ltp_result=ltp_result, installation_nr=0, ltp_column="fromShoreConsumption"
        )
        power_supply_onshore = get_sum_ltp_column(
            ltp_result=ltp_result, installation_nr=0, ltp_column="powerSupplyOnshore"
        )
        max_usage_from_shore = get_sum_ltp_column(
            ltp_result=ltp_result, installation_nr=0, ltp_column="fromShorePeakMaximum"
        )

        power_supply_onshore_csv = get_sum_ltp_column(
            ltp_result=ltp_result_csv, installation_nr=0, ltp_column="powerSupplyOnshore"
        )

        # In the temporal model, the category is POWER_FROM_SHORE the last three years, within the period 2025 - 2030:
        delta_days = calculate_delta_days(time_vector_yearly)[2:6]

        # Check that power from shore consumption is correct
        assert power_from_shore_consumption == sum([load * days * regularity * 24 / 1000 for days in delta_days])

        # Check that power supply onshore is power from shore consumption * (1 + cable loss)
        assert power_supply_onshore == pytest.approx(
            sum([load * (1 + cable_loss) * days * regularity * 24 / 1000 for days in delta_days])
        )

        # Check that max usage from shore is just a report of the input
        # Max usage from shore is 0 until 2027.6.1 and the 12 until 2031.1.1, so
        # 2027, 2028, 2029 and 2030 (4 years) should all have 12 as max usage from shore.
        assert max_usage_from_shore == max_from_shore * 4

        # Check that reading cable loss from csv-file gives same result as using constant
        assert power_supply_onshore == power_supply_onshore_csv

        # Verify correct unit for max usage from shore
        assert (
            get_ltp_column(ltp_result=ltp_result, installation_nr=0, ltp_column="fromShorePeakMaximum").unit
            == Unit.MEGA_WATT
        )

    def test_max_usage_from_shore(
        self,
        el_consumer_direct_base_load,
        generator_electricity2fuel_17MW_resource,
        onshore_power_electricity2fuel_resource,
        max_usage_from_shore_time_series_resource,
        resource_service_factory,
        fuel_gas,
    ):
        """Test power from shore output for LTP export."""

        regularity = 0.2
        load = 10
        cable_loss = 0.1

        time_vector_yearly = (
            pd.date_range(datetime(2025, 1, 1), datetime(2031, 1, 1), freq="YS").to_pydatetime().tolist()
        )

        fuel = fuel_gas(
            ["co2", "ch4", "nmvoc", "nox"], [self.co2_factor, self.ch4_factor, self.nmvoc_factor, self.nox_factor]
        )

        max_usage_from_shore_time_series = (
            YamlTimeSeriesBuilder()
            .with_name("MAX_USAGE_FROM_SHORE")
            .with_type("DEFAULT")
            .with_file("MAX_USAGE_FROM_SHORE")
        ).validate()

        generator_set = (
            YamlGeneratorSetBuilder()
            .with_name("generator1")
            .with_category(
                {
                    datetime(2025, 1, 1): ConsumerUserDefinedCategoryType.TURBINE_GENERATOR,
                    datetime(2027, 1, 1): ConsumerUserDefinedCategoryType.POWER_FROM_SHORE,
                }
            )
            .with_electricity2fuel(
                {
                    datetime(2025, 1, 1): self.generator_fuel_energy_function.name,
                    datetime(2027, 1, 1): self.power_from_shore_energy_function.name,
                }
            )
            .with_consumers([el_consumer_direct_base_load(el_reference_name="base_load", load=load)])
            .with_cable_loss(cable_loss)
            .with_max_usage_from_shore("MAX_USAGE_FROM_SHORE;MAX_USAGE_FROM_SHORE")
        ).validate()

        installation_pfs = (
            YamlInstallationBuilder()
            .with_name("minimal_installation")
            .with_category(InstallationUserDefinedCategoryType.FIXED)
            .with_fuel(fuel.name)
            .with_generator_sets([generator_set])
            .with_regularity(regularity)
        ).validate()

        resources = {
            self.generator_fuel_energy_function.name: generator_electricity2fuel_17MW_resource,
            self.power_from_shore_energy_function.name: onshore_power_electricity2fuel_resource,
            max_usage_from_shore_time_series.name: max_usage_from_shore_time_series_resource,
        }
        resource_service = resource_service_factory(resources=resources)

        asset_pfs = get_asset_yaml_model(
            installations=[installation_pfs],
            fuel_types=[fuel],
            time_vector=time_vector_yearly,
            time_series=[max_usage_from_shore_time_series],
            facility_inputs=[self.generator_fuel_energy_function, self.power_from_shore_energy_function],
            frequency=Frequency.YEAR,
            resource_service=resource_service,
        )

        ltp_result = get_ltp_result(asset_pfs, asset_pfs.variables)
        max_usage_from_shore = get_ltp_column(
            ltp_result=ltp_result, installation_nr=0, ltp_column="fromShorePeakMaximum"
        )
        max_usage_from_shore_2027 = float(
            max_usage_from_shore.values[Period(datetime(2027, 1, 1), datetime(2028, 1, 1))]
        )
        # In the input memory resource max usage from shore is 250 (1.12.2026), 290 (1.6.2027), 283 (1.1.2028)
        # and 283 (1.1.2029). Ensure that the correct value is set for 2027 (290 from 1.6):
        assert max_usage_from_shore_2027 == 290.0

        # Ensure that values in 2027, 2028 and 2029 are correct, based on input file:
        assert [float(max_pfs) for max_pfs in max_usage_from_shore.values.values()][2:5] == [
            290,
            283,
            283,
        ]
