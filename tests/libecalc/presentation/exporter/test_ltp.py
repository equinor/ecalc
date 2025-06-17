from copy import deepcopy
from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from libecalc.application.graph_result import GraphResult
from libecalc.common.time_utils import Frequency, Period, calculate_delta_days
from libecalc.common.units import Unit
from libecalc.common.utils.rates import RateType
from libecalc.dto.types import ConsumerUserDefinedCategoryType, InstallationUserDefinedCategoryType
from libecalc.presentation.exporter.configs.configs import LTPConfig
from libecalc.presentation.exporter.dto.dtos import FilteredResult, QueryResult
from libecalc.presentation.exporter.infrastructure import ExportableGraphResult
from libecalc.presentation.json_result.mapper import get_asset_result
from libecalc.presentation.json_result.result import EcalcModelResult
from libecalc.presentation.yaml.model import YamlModel
from libecalc.presentation.yaml.yaml_types.components.legacy.energy_usage_model.yaml_energy_usage_model_direct import (
    ConsumptionRateType,
)
from libecalc.presentation.yaml.yaml_types.components.legacy.yaml_electricity_consumer import YamlElectricityConsumer
from libecalc.presentation.yaml.yaml_types.fuel_type.yaml_fuel_type import YamlFuelType
from libecalc.presentation.yaml.yaml_types.yaml_stream_conditions import YamlEmissionRateUnits, YamlOilRateUnits
from libecalc.testing.yaml_builder import (
    YamlAssetBuilder,
    YamlCompressorTabularBuilder,
    YamlElectricity2fuelBuilder,
    YamlElectricityConsumerBuilder,
    YamlEnergyUsageModelCompressorBuilder,
    YamlEnergyUsageModelDirectFuelBuilder,
    YamlFuelConsumerBuilder,
    YamlGeneratorSetBuilder,
    YamlInstallationBuilder,
    YamlTimeSeriesBuilder,
    YamlVentingEmitterDirectTypeBuilder,
    YamlVentingEmitterOilTypeBuilder,
)
from tests.libecalc.presentation.exporter.conftest import memory_resource_factory


class LtpTestHelper:
    def __init__(self, expression_evaluator_factory):
        self._expression_evaluator_factory = expression_evaluator_factory
        # Constants
        self.power_usage_mw = 10
        self.power_offshore_wind_mw = 1
        self.power_compressor_mw = 3
        self.fuel_rate = 67000
        self.diesel_rate = 120000
        self.load_consumer = 10
        self.compressor_rate = 3000000
        self.regularity_installation = 1.0
        self.co2_factor = 1
        self.ch4_factor = 0.1
        self.nox_factor = 0.5
        self.nmvoc_factor = 0

        # Dates
        self.date1 = datetime(2027, 1, 1)
        self.date2 = datetime(2027, 4, 10)
        self.date3 = datetime(2028, 1, 1)
        self.date4 = datetime(2028, 4, 10)
        self.date5 = datetime(2029, 1, 1)
        self.time_vector_installation = [self.date1, self.date2, self.date3, self.date4, self.date5]

        # Periods
        self.period1 = Period(self.date1, self.date2)
        self.period2 = Period(self.date2, self.date3)
        self.period3 = Period(self.date3, self.date4)
        self.period4 = Period(self.date4, self.date5)
        self.period5 = Period(self.date5)
        self.period_from_date1 = Period(self.date1)
        self.period_from_date3 = Period(self.date3)
        self.full_period = Period(datetime(1900, 1, 1))

        # Days
        self.days_year1_first_half = self.period1.duration.days
        self.days_year2_first_half = self.period3.duration.days
        self.days_year1_second_half = self.period2.duration.days
        self.days_year2_second_half = self.period4.duration.days

    def get_graph_result(self, model: YamlModel):
        model.evaluate_energy_usage()
        model.evaluate_emissions()
        return model.get_graph_result()

    def get_ltp_report(self, graph_result: GraphResult, model: YamlModel) -> FilteredResult:
        ltp_filter = LTPConfig.filter(frequency=model.result_options.output_frequency)
        exportable = ExportableGraphResult(graph_result)
        return ltp_filter.filter(exportable, model.variables.get_periods())

    def get_sum_ltp_column(self, ltp_result: FilteredResult, installation_nr, ltp_column: str) -> float:
        installation_query_results = ltp_result.query_results[installation_nr].query_results
        column = [column for column in installation_query_results if column.id == ltp_column][0]

        ltp_sum = sum(float(v) for (k, v) in column.values.items())
        return ltp_sum

    def get_ltp_column(self, ltp_result: FilteredResult, installation_nr, ltp_column: str) -> QueryResult:
        installation_query_results = ltp_result.query_results[installation_nr].query_results
        column = [column for column in installation_query_results if column.id == ltp_column][0]

        return column

    def get_asset_result(self, graph_result: GraphResult):
        return get_asset_result(graph_result)

    def assert_emissions(self, ltp_result, installation_nr, ltp_column, expected_value):
        actual_value = self.get_sum_ltp_column(ltp_result, installation_nr, ltp_column)
        assert actual_value == pytest.approx(expected_value, 0.00001)

    def assert_consumption(self, ltp_result, installation_nr, ltp_column, expected_value):
        actual_value = self.get_sum_ltp_column(ltp_result, installation_nr, ltp_column)
        assert actual_value == pytest.approx(expected_value, 0.00001)

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
            .with_fuel({self.period_from_date1.start: fuel})
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
            self.period1.start: fuel1.name,
            self.period2.start: fuel2.name,
            self.period3.start: fuel1.name,
            self.period4.start: fuel2.name,
            self.period5.start: fuel1.name,
        }

    def offshore_wind_consumer(self, request, power_mw: float = 1):
        energy_usage_model_direct_load = request.getfixturevalue("energy_usage_model_direct_load_factory")
        return (
            YamlElectricityConsumerBuilder()
            .with_name("offshore_wind_consumer")
            .with_category(
                {
                    self.period1.start: ConsumerUserDefinedCategoryType.MISCELLANEOUS,
                    self.period2.start: ConsumerUserDefinedCategoryType.OFFSHORE_WIND,
                    self.period3.start: ConsumerUserDefinedCategoryType.MISCELLANEOUS,
                    self.period4.start: ConsumerUserDefinedCategoryType.OFFSHORE_WIND,
                    self.period5.start: ConsumerUserDefinedCategoryType.MISCELLANEOUS,
                }
            )
            .with_energy_usage_model(
                {
                    self.period1.start: energy_usage_model_direct_load(load=0),
                    self.period2.start: energy_usage_model_direct_load(load=power_mw),
                    self.period3.start: energy_usage_model_direct_load(load=0),
                    self.period4.start: energy_usage_model_direct_load(load=power_mw),
                    self.period5.start: energy_usage_model_direct_load(load=0),
                }
            )
        ).validate()

    def generator_set(
        self,
        request,
        fuel: str = None,
        el_consumer: YamlElectricityConsumer = None,
        el2fuel: str | dict[datetime, str] = None,
        category: dict[datetime, ConsumerUserDefinedCategoryType] = None,
        date: datetime = None,
        name: str = "generator_set",
    ):
        if date is None:
            date = self.period_from_date1.start

        if el_consumer is None:
            direct_load = request.getfixturevalue("el_consumer_direct_base_load_factory")
            el_consumer = direct_load(el_reference_name="base_load", load=self.load_consumer)

        if fuel is None:
            fuel_gas = request.getfixturevalue("fuel_gas_factory")
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
            self.period1.start: reference1,
            self.period2.start: reference2,
            self.period3.start: reference1,
            self.period4.start: reference2,
            self.period5.start: reference1,
        }

    def category_dict(self) -> dict[datetime, ConsumerUserDefinedCategoryType]:
        return {
            self.period1.start: ConsumerUserDefinedCategoryType.TURBINE_GENERATOR,
            self.period2.start: ConsumerUserDefinedCategoryType.POWER_FROM_SHORE,
            self.period3.start: ConsumerUserDefinedCategoryType.TURBINE_GENERATOR,
            self.period4.start: ConsumerUserDefinedCategoryType.POWER_FROM_SHORE,
            self.period5.start: ConsumerUserDefinedCategoryType.TURBINE_GENERATOR,
        }

    def category_dict_coarse(self) -> dict[datetime, ConsumerUserDefinedCategoryType]:
        return {
            self.period1.start: ConsumerUserDefinedCategoryType.TURBINE_GENERATOR,
            self.period2.start: ConsumerUserDefinedCategoryType.POWER_FROM_SHORE,
            self.period_from_date3.start: ConsumerUserDefinedCategoryType.TURBINE_GENERATOR,
        }

    @property
    def dummy_time_series(self):
        return (
            YamlTimeSeriesBuilder().with_name("dummy_time_series").with_type("DEFAULT").with_file("dummy_time_series")
        ).validate()

    def dummy_time_series_resource(self, time_vector, values=None):
        time_vector_str = [str(date) for date in time_vector]
        if not values:
            values = [1] * len(time_vector)
        return memory_resource_factory(
            data=[
                time_vector_str,
                values,
            ],  # float and int with equal value should count as equal.
            headers=[
                "DATE",
                "DUMMY",
            ],
        )

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
        return LtpTestHelper.consumption_calculate(self, rate=self.fuel_rate, days=[self.days_year2_second_half])

    @property
    def diesel_consumption(self):
        return self.consumption_calculate(
            rate=self.diesel_rate, days=[self.days_year1_first_half, self.days_year2_first_half]
        )

    @property
    def pfs_el_consumption(self):
        return self.el_consumption_calculate(power=self.power_usage_mw, days=[self.days_year1_second_half])

    @property
    def gas_turbine_el_generated(self):
        return self.el_consumption_calculate(
            power=self.power_usage_mw,
            days=[self.days_year1_first_half, self.days_year2_first_half, self.days_year2_second_half],
        )

    @property
    def boiler_fuel_consumption(self):
        return self.consumption_calculate(
            rate=self.fuel_rate,
            days=[self.days_year1_first_half, self.days_year1_second_half, self.days_year2_first_half],
        )

    @property
    def heater_fuel_consumption(self):
        return self.consumption_calculate(rate=self.fuel_rate, days=[self.days_year2_second_half])

    @property
    def co2_from_boiler(self):
        return self.emission_calculate(
            rate=self.fuel_rate,
            factor=self.co2_factor,
            days=[self.days_year1_first_half, self.days_year1_second_half, self.days_year2_first_half],
        )

    @property
    def co2_from_heater(self):
        return self.emission_calculate(rate=self.fuel_rate, factor=self.co2_factor, days=[self.days_year2_second_half])

    @property
    def co2_from_fuel(self):
        return self.emission_calculate(rate=self.fuel_rate, factor=self.co2_factor, days=[self.days_year2_second_half])

    @property
    def co2_from_diesel(self):
        return self.emission_calculate(
            rate=self.diesel_rate,
            factor=self.co2_factor,
            days=[self.days_year1_first_half, self.days_year2_first_half],
        )

    @property
    def ch4_from_diesel(self):
        return self.emission_calculate(
            rate=self.diesel_rate,
            factor=self.ch4_factor,
            days=[self.days_year1_first_half, self.days_year2_first_half],
        )

    @property
    def nox_from_diesel(self):
        return self.emission_calculate(
            rate=self.diesel_rate,
            factor=self.nox_factor,
            days=[self.days_year1_first_half, self.days_year2_first_half],
        )

    @property
    def nmvoc_from_diesel(self):
        return self.emission_calculate(
            rate=self.diesel_rate,
            factor=self.nmvoc_factor,
            days=[self.days_year1_first_half, self.days_year2_first_half],
        )

    @property
    def offshore_wind_el_consumption(self):
        return self.el_consumption_calculate(
            power=self.power_offshore_wind_mw, days=[self.days_year1_second_half, self.days_year2_second_half]
        ) * (-1)

    @property
    def gas_turbine_compressor_el_consumption(self):
        return self.el_consumption_calculate(
            power=self.power_compressor_mw, days=[self.days_year1_second_half, self.days_year2_second_half]
        )


@pytest.fixture(scope="function")
def ltp_test_helper(expression_evaluator_factory):
    return LtpTestHelper(expression_evaluator_factory=expression_evaluator_factory)


class TestLtp:
    def test_emissions_diesel_fixed_and_mobile(
        self,
        ltp_test_helper,
        fuel_gas_factory,
        diesel_factory,
        el_consumer_direct_base_load_factory,
        generator_diesel_power_to_fuel_resource,
        generator_fuel_power_to_fuel_resource,
        yaml_asset_configuration_service_factory,
        yaml_model_factory,
    ):
        dummy_time_series_resource = ltp_test_helper.dummy_time_series_resource(
            ltp_test_helper.time_vector_installation
        )
        fuel = fuel_gas_factory(["co2"], [ltp_test_helper.co2_factor])
        diesel = diesel_factory(
            ["co2", "ch4", "nox", "nmvoc"],
            [
                ltp_test_helper.co2_factor,
                ltp_test_helper.ch4_factor,
                ltp_test_helper.nox_factor,
                ltp_test_helper.nmvoc_factor,
            ],
        )

        generator_builder = (
            YamlGeneratorSetBuilder()
            .with_name("generator_fixed")
            .with_category(ltp_test_helper.category_dict())
            .with_electricity2fuel(
                ltp_test_helper.temporal_dict(
                    reference1=ltp_test_helper.generator_diesel_energy_function.name,
                    reference2=ltp_test_helper.generator_fuel_energy_function.name,
                )
            )
        )

        generator_mobile = (
            generator_builder.with_consumers(
                [
                    el_consumer_direct_base_load_factory(
                        el_reference_name="base_load_mobile", load=ltp_test_helper.load_consumer
                    )
                ]
            )
            .with_name("generator_mobile")
            .validate()
        )

        generator_fixed = (
            generator_builder.with_consumers(
                [
                    el_consumer_direct_base_load_factory(
                        el_reference_name="base_load_fixed", load=ltp_test_helper.load_consumer
                    )
                ]
            )
            .with_name("generator_fixed")
            .validate()
        )

        installation_fixed = (
            YamlInstallationBuilder()
            .with_name("INSTALLATION_FIXED")
            .with_regularity(ltp_test_helper.regularity_installation)
            .with_fuel(ltp_test_helper.fuel_multi_temporal(diesel, fuel))
            .with_category(InstallationUserDefinedCategoryType.FIXED)
            .with_generator_sets([generator_fixed])
        ).validate()

        installation_mobile = (
            YamlInstallationBuilder()
            .with_name("INSTALLATION_MOBILE")
            .with_regularity(ltp_test_helper.regularity_installation)
            .with_fuel(ltp_test_helper.fuel_multi_temporal(diesel, fuel))
            .with_category(InstallationUserDefinedCategoryType.MOBILE)
            .with_generator_sets([generator_mobile])
        ).validate()

        resources = {
            ltp_test_helper.generator_diesel_energy_function.name: generator_diesel_power_to_fuel_resource(
                power_usage_mw=ltp_test_helper.power_usage_mw, diesel_rate=ltp_test_helper.diesel_rate
            ),
            ltp_test_helper.generator_fuel_energy_function.name: generator_fuel_power_to_fuel_resource(
                power_usage_mw=ltp_test_helper.power_usage_mw, fuel_rate=ltp_test_helper.fuel_rate
            ),
            ltp_test_helper.dummy_time_series.name: dummy_time_series_resource,
        }

        asset = (
            YamlAssetBuilder()
            .with_start(str(ltp_test_helper.time_vector_installation[0]))
            .with_end(str(ltp_test_helper.time_vector_installation[-1]))
            .with_installations([installation_fixed, installation_mobile])
            .with_facility_inputs(
                [ltp_test_helper.generator_diesel_energy_function, ltp_test_helper.generator_fuel_energy_function]
            )
            .with_time_series([ltp_test_helper.dummy_time_series])
            .with_fuel_types([fuel, diesel])
        ).validate()

        configuration_service = yaml_asset_configuration_service_factory(model=asset, name="test_asset")
        asset = yaml_model_factory(
            configuration=configuration_service.get_configuration(),
            resources=resources,
            frequency=Frequency.YEAR,
        )

        graph_result = ltp_test_helper.get_graph_result(asset)
        ltp_result = ltp_test_helper.get_ltp_report(graph_result=graph_result, model=asset)

        ltp_test_helper.assert_emissions(ltp_result, 0, "engineDieselCo2Mass", ltp_test_helper.co2_from_diesel)
        ltp_test_helper.assert_emissions(ltp_result, 1, "engineNoCo2TaxDieselCo2Mass", ltp_test_helper.co2_from_diesel)
        ltp_test_helper.assert_emissions(ltp_result, 0, "engineDieselNoxMass", ltp_test_helper.nox_from_diesel)
        ltp_test_helper.assert_emissions(ltp_result, 1, "engineNoCo2TaxDieselNoxMass", ltp_test_helper.nox_from_diesel)
        ltp_test_helper.assert_emissions(ltp_result, 0, "engineDieselNmvocMass", ltp_test_helper.nmvoc_from_diesel)
        ltp_test_helper.assert_emissions(
            ltp_result, 1, "engineNoCo2TaxDieselNmvocMass", ltp_test_helper.nmvoc_from_diesel
        )
        ltp_test_helper.assert_emissions(ltp_result, 0, "engineDieselCh4Mass", ltp_test_helper.ch4_from_diesel)
        ltp_test_helper.assert_emissions(ltp_result, 1, "engineNoCo2TaxDieselCh4Mass", ltp_test_helper.ch4_from_diesel)

    def test_temporal_models_detailed(
        self,
        ltp_test_helper,
        diesel_factory,
        fuel_gas_factory,
        generator_diesel_power_to_fuel_resource,
        generator_fuel_power_to_fuel_resource,
        el_consumer_direct_base_load_factory,
        yaml_model_factory,
        yaml_asset_configuration_service_factory,
    ):
        """Test various queries for LTP reporting. Purpose: ensure that variations in temporal models are captured.

        Detailed temporal models (variations within one year) for:
        - Fuel type
        - Generator set user defined category
        - Generator set model
        """
        dummy_time_series_resource = ltp_test_helper.dummy_time_series_resource(
            ltp_test_helper.time_vector_installation
        )
        fuel = fuel_gas_factory(["co2"], [ltp_test_helper.co2_factor])
        diesel = diesel_factory(["co2"], [ltp_test_helper.co2_factor])

        generator_set = (
            YamlGeneratorSetBuilder()
            .with_name("generator_set")
            .with_category(ltp_test_helper.category_dict_coarse())
            .with_consumers(
                [
                    el_consumer_direct_base_load_factory(
                        el_reference_name="base_load", load=ltp_test_helper.load_consumer
                    )
                ]
            )
            .with_electricity2fuel(
                ltp_test_helper.temporal_dict(
                    reference1=ltp_test_helper.generator_diesel_energy_function.name,
                    reference2=ltp_test_helper.generator_fuel_energy_function.name,
                )
            )
        ).validate()

        installation = (
            YamlInstallationBuilder()
            .with_name("INSTALLATION A")
            .with_generator_sets([generator_set])
            .with_fuel(ltp_test_helper.fuel_multi_temporal(fuel1=diesel, fuel2=fuel))
            .with_category(InstallationUserDefinedCategoryType.FIXED)
        ).validate()

        resources = {
            ltp_test_helper.generator_diesel_energy_function.name: generator_diesel_power_to_fuel_resource(
                power_usage_mw=ltp_test_helper.power_usage_mw,
                diesel_rate=ltp_test_helper.diesel_rate,
            ),
            ltp_test_helper.generator_fuel_energy_function.name: generator_fuel_power_to_fuel_resource(
                power_usage_mw=ltp_test_helper.power_usage_mw,
                fuel_rate=ltp_test_helper.fuel_rate,
            ),
            ltp_test_helper.dummy_time_series.name: dummy_time_series_resource,
        }

        asset = (
            YamlAssetBuilder()
            .with_start(str(ltp_test_helper.time_vector_installation[0]))
            .with_end(str(ltp_test_helper.time_vector_installation[-1]))
            .with_installations([installation])
            .with_time_series([ltp_test_helper.dummy_time_series])
            .with_facility_inputs(
                [ltp_test_helper.generator_diesel_energy_function, ltp_test_helper.generator_fuel_energy_function]
            )
            .with_fuel_types([fuel, diesel])
        ).validate()

        configuration_service = yaml_asset_configuration_service_factory(model=asset, name="test_asset")
        asset = yaml_model_factory(
            configuration=configuration_service.get_configuration(),
            resources=resources,
            frequency=Frequency.YEAR,
        )

        graph_result = ltp_test_helper.get_graph_result(asset)
        ltp_result = ltp_test_helper.get_ltp_report(graph_result=graph_result, model=asset)

        turbine_fuel_consumption = ltp_test_helper.get_sum_ltp_column(
            ltp_result, installation_nr=0, ltp_column="turbineFuelGasConsumption"
        )

        # FuelQuery: Check that turbine fuel consumption is included,
        # even if the temporal model starts with diesel every year
        assert turbine_fuel_consumption != 0

        ltp_test_helper.assert_consumption(ltp_result, 0, "turbineFuelGasConsumption", ltp_test_helper.fuel_consumption)
        ltp_test_helper.assert_consumption(ltp_result, 0, "engineDieselConsumption", ltp_test_helper.diesel_consumption)
        ltp_test_helper.assert_consumption(ltp_result, 0, "turbineFuelGasCo2Mass", ltp_test_helper.co2_from_fuel)
        ltp_test_helper.assert_consumption(ltp_result, 0, "engineDieselCo2Mass", ltp_test_helper.co2_from_diesel)
        ltp_test_helper.assert_consumption(ltp_result, 0, "fromShoreConsumption", ltp_test_helper.pfs_el_consumption)
        ltp_test_helper.assert_consumption(
            ltp_result, 0, "gasTurbineGeneratorConsumption", ltp_test_helper.gas_turbine_el_generated
        )

    def test_temporal_models_offshore_wind(
        self,
        request,
        ltp_test_helper,
        fuel_gas_factory,
        generator_fuel_power_to_fuel_resource,
        yaml_asset_configuration_service_factory,
        yaml_model_factory,
    ):
        """Test ElConsumerPowerConsumptionQuery for calculating offshore wind el-consumption, LTP.

        Detailed temporal models (variations within one year) for:
        - El-consumer user defined category
        - El-consumer energy usage model
        """
        dummy_time_series_resource = ltp_test_helper.dummy_time_series_resource(
            ltp_test_helper.time_vector_installation
        )
        fuel = fuel_gas_factory(["co2"], [ltp_test_helper.co2_factor])

        generator_set = (
            YamlGeneratorSetBuilder()
            .with_name("generator_set")
            .with_category({ltp_test_helper.period_from_date1.start: ConsumerUserDefinedCategoryType.TURBINE_GENERATOR})
            .with_consumers([ltp_test_helper.offshore_wind_consumer(request, ltp_test_helper.power_offshore_wind_mw)])
            .with_electricity2fuel(
                {ltp_test_helper.period_from_date1.start: ltp_test_helper.generator_fuel_energy_function.name}
            )
        ).validate()

        installation = (
            YamlInstallationBuilder()
            .with_name("INSTALLATION A")
            .with_generator_sets([generator_set])
            .with_fuel(fuel.name)
            .with_category(InstallationUserDefinedCategoryType.FIXED)
        ).validate()

        resources = {
            ltp_test_helper.generator_fuel_energy_function.name: generator_fuel_power_to_fuel_resource(
                power_usage_mw=ltp_test_helper.power_usage_mw,
                fuel_rate=ltp_test_helper.fuel_rate,
            ),
            ltp_test_helper.dummy_time_series.name: dummy_time_series_resource,
        }

        asset = (
            YamlAssetBuilder()
            .with_start(str(ltp_test_helper.time_vector_installation[0]))
            .with_end(str(ltp_test_helper.time_vector_installation[-1]))
            .with_installations([installation])
            .with_time_series([ltp_test_helper.dummy_time_series])
            .with_facility_inputs([ltp_test_helper.generator_fuel_energy_function])
            .with_fuel_types([fuel])
        ).validate()

        configuration_service = yaml_asset_configuration_service_factory(model=asset, name="test_asset")
        asset = yaml_model_factory(
            configuration=configuration_service.get_configuration(),
            resources=resources,
            frequency=Frequency.YEAR,
        )

        graph_result = ltp_test_helper.get_graph_result(asset)
        ltp_result = ltp_test_helper.get_ltp_report(graph_result=graph_result, model=asset)

        offshore_wind_el_consumption = ltp_test_helper.get_sum_ltp_column(
            ltp_result, installation_nr=0, ltp_column="offshoreWindConsumption"
        )

        # ElConsumerPowerConsumptionQuery: Check that offshore wind el-consumption is correct.
        assert offshore_wind_el_consumption == ltp_test_helper.offshore_wind_el_consumption

    def test_temporal_models_compressor(
        self,
        ltp_test_helper,
        generator_fuel_power_to_fuel_resource,
        compressor_sampled_fuel_driven_resource,
        fuel_gas_factory,
        yaml_model_factory,
        yaml_asset_configuration_service_factory,
    ):
        """Test FuelConsumerPowerConsumptionQuery for calculating gas turbine compressor el-consumption, LTP.

        Detailed temporal models (variations within one year) for:
        - Fuel consumer user defined category
        """
        dummy_time_series_resource = ltp_test_helper.dummy_time_series_resource(
            ltp_test_helper.time_vector_installation
        )
        fuel = fuel_gas_factory(["co2"], [ltp_test_helper.co2_factor])

        installation = (
            YamlInstallationBuilder()
            .with_name("INSTALLATION A")
            .with_fuel(fuel.name)
            .with_fuel_consumers([ltp_test_helper.fuel_consumer_compressor(fuel.name)])
            .with_category(InstallationUserDefinedCategoryType.FIXED)
        ).validate()

        resources = {
            ltp_test_helper.compressor_energy_function.name: compressor_sampled_fuel_driven_resource(
                compressor_rate=ltp_test_helper.compressor_rate, power_compressor_mw=ltp_test_helper.power_compressor_mw
            ),
            ltp_test_helper.dummy_time_series.name: dummy_time_series_resource,
        }

        asset = (
            YamlAssetBuilder()
            .with_start(str(ltp_test_helper.time_vector_installation[0]))
            .with_end(str(ltp_test_helper.time_vector_installation[-1]))
            .with_installations([installation])
            .with_time_series([ltp_test_helper.dummy_time_series])
            .with_facility_inputs([ltp_test_helper.compressor_energy_function])
            .with_fuel_types([fuel])
        ).validate()

        configuration_service = yaml_asset_configuration_service_factory(model=asset, name="test_asset")
        asset = yaml_model_factory(
            configuration=configuration_service.get_configuration(),
            resources=resources,
            frequency=Frequency.YEAR,
        )

        graph_result = ltp_test_helper.get_graph_result(asset)
        ltp_result = ltp_test_helper.get_ltp_report(graph_result=graph_result, model=asset)

        gas_turbine_compressor_el_consumption = ltp_test_helper.get_sum_ltp_column(
            ltp_result, installation_nr=0, ltp_column="gasTurbineCompressorConsumption"
        )

        # FuelConsumerPowerConsumptionQuery. Check gas turbine compressor el consumption.
        assert gas_turbine_compressor_el_consumption == ltp_test_helper.gas_turbine_compressor_el_consumption

    def test_boiler_heater_categories(
        self, ltp_test_helper, fuel_gas_factory, yaml_model_factory, yaml_asset_configuration_service_factory
    ):
        dummy_time_series_resource = ltp_test_helper.dummy_time_series_resource(
            ltp_test_helper.time_vector_installation
        )
        fuel = fuel_gas_factory(["co2"], [ltp_test_helper.co2_factor])

        energy_usage_model = (
            YamlEnergyUsageModelDirectFuelBuilder()
            .with_fuel_rate(ltp_test_helper.fuel_rate)
            .with_consumption_rate_type(ConsumptionRateType.STREAM_DAY)
        ).validate()

        fuel_consumer = (
            YamlFuelConsumerBuilder()
            .with_name("boiler_heater")
            .with_fuel(fuel.name)
            .with_energy_usage_model({ltp_test_helper.full_period.start: energy_usage_model})
            .with_category(
                {
                    Period(ltp_test_helper.date1, ltp_test_helper.date4).start: ConsumerUserDefinedCategoryType.BOILER,
                    Period(ltp_test_helper.date4).start: ConsumerUserDefinedCategoryType.HEATER,
                }
            )
        ).validate()

        installation = (
            YamlInstallationBuilder()
            .with_name("INSTALLATION A")
            .with_category(InstallationUserDefinedCategoryType.FIXED)
            .with_fuel(fuel.name)
            .with_fuel_consumers([fuel_consumer])
            .with_regularity(ltp_test_helper.regularity_installation)
        ).validate()

        resources = {ltp_test_helper.dummy_time_series.name: dummy_time_series_resource}
        asset = (
            YamlAssetBuilder()
            .with_start(str(ltp_test_helper.date1))
            .with_end(str(ltp_test_helper.date5))
            .with_installations([installation])
            .with_time_series([ltp_test_helper.dummy_time_series])
            .with_fuel_types([fuel])
        ).validate()

        configuration_service = yaml_asset_configuration_service_factory(model=asset, name="test_asset")
        asset = yaml_model_factory(
            configuration=configuration_service.get_configuration(),
            resources=resources,
            frequency=Frequency.YEAR,
        )

        graph_result = ltp_test_helper.get_graph_result(asset)
        ltp_result = ltp_test_helper.get_ltp_report(graph_result=graph_result, model=asset)

        ltp_test_helper.assert_consumption(
            ltp_result, 0, "boilerFuelGasConsumption", ltp_test_helper.boiler_fuel_consumption
        )
        ltp_test_helper.assert_consumption(
            ltp_result, 0, "heaterFuelGasConsumption", ltp_test_helper.heater_fuel_consumption
        )
        ltp_test_helper.assert_consumption(ltp_result, 0, "boilerFuelGasCo2Mass", ltp_test_helper.co2_from_boiler)
        ltp_test_helper.assert_consumption(ltp_result, 0, "heaterFuelGasCo2Mass", ltp_test_helper.co2_from_heater)

    def test_total_oil_loaded_old_method(
        self,
        ltp_test_helper,
        fuel_gas_factory,
        fuel_consumer_direct_factory,
        yaml_asset_configuration_service_factory,
        yaml_model_factory,
    ):
        """Test total oil loaded/stored for LTP export. Using original method where direct/venting emitters are
        modelled as FUELSCONSUMERS using DIRECT.

        Verify correct volume when model includes emissions related to both storage and loading of oil,
        and when model includes only loading.
        """
        time_vector = [datetime(2027, 1, 1), datetime(2028, 1, 1)]
        regularity = 0.6
        emission_factor = 2
        rate = 100

        fuel = fuel_gas_factory(["ch4"], [emission_factor])
        loading = fuel_consumer_direct_factory(
            fuel_reference_name=fuel.name, rate=rate, name="loading", category=ConsumerUserDefinedCategoryType.LOADING
        )

        storage = fuel_consumer_direct_factory(
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

        asset = (
            YamlAssetBuilder()
            .with_start(str(time_vector[0]))
            .with_end(str(time_vector[-1]))
            .with_installations([installation])
            .with_fuel_types([fuel])
        ).validate()

        configuration_service = yaml_asset_configuration_service_factory(model=asset, name="test_asset")
        asset = yaml_model_factory(
            configuration=configuration_service.get_configuration(),
            resources={},
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

        asset_loading_only = (
            YamlAssetBuilder()
            .with_start(str(time_vector[0]))
            .with_end(str(time_vector[-1]))
            .with_installations([installation_loading_only])
            .with_fuel_types([fuel])
        ).validate()

        configuration_service = yaml_asset_configuration_service_factory(model=asset_loading_only, name="test_asset")
        asset_loading_only = yaml_model_factory(
            configuration=configuration_service.get_configuration(),
            resources={},
            frequency=Frequency.YEAR,
        )

        graph_result = ltp_test_helper.get_graph_result(asset)
        ltp_result_loading_storage = ltp_test_helper.get_ltp_report(graph_result=graph_result, model=asset)

        graph_result = ltp_test_helper.get_graph_result(asset_loading_only)
        ltp_result_loading_only = ltp_test_helper.get_ltp_report(graph_result=graph_result, model=asset_loading_only)

        loaded_and_stored_oil_loading_and_storage = ltp_test_helper.get_sum_ltp_column(
            ltp_result_loading_storage, installation_nr=0, ltp_column="loadedAndStoredOil"
        )
        loaded_and_stored_oil_loading_only = ltp_test_helper.get_sum_ltp_column(
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
        ltp_test_helper,
        fuel_gas_factory,
        generator_fuel_power_to_fuel_resource,
        compressor_sampled_fuel_driven_resource,
        yaml_asset_configuration_service_factory,
        yaml_model_factory,
    ):
        """Check that new total power includes the sum of electrical- and mechanical power at installation level"""
        time_series_resource = ltp_test_helper.dummy_time_series_resource(
            time_vector=ltp_test_helper.time_vector_installation
        )
        fuel = fuel_gas_factory(["co2"], [ltp_test_helper.co2_factor])

        generator_set = ltp_test_helper.generator_set(request)

        installation = (
            YamlInstallationBuilder()
            .with_name("INSTALLATION A")
            .with_generator_sets([generator_set])
            .with_fuel(fuel.name)
            .with_regularity(ltp_test_helper.regularity_installation)
            .with_fuel_consumers([ltp_test_helper.fuel_consumer_compressor(fuel.name)])
            .with_category(InstallationUserDefinedCategoryType.FIXED)
        ).validate()

        resources = {
            ltp_test_helper.generator_fuel_energy_function.name: generator_fuel_power_to_fuel_resource(
                power_usage_mw=ltp_test_helper.power_usage_mw,
                fuel_rate=ltp_test_helper.fuel_rate,
            ),
            ltp_test_helper.compressor_energy_function.name: compressor_sampled_fuel_driven_resource(
                compressor_rate=ltp_test_helper.compressor_rate, power_compressor_mw=ltp_test_helper.power_compressor_mw
            ),
            ltp_test_helper.dummy_time_series.name: time_series_resource,
        }

        asset = (
            YamlAssetBuilder()
            .with_start(str(ltp_test_helper.time_vector_installation[0]))
            .with_end(str(ltp_test_helper.time_vector_installation[-1]))
            .with_installations([installation])
            .with_fuel_types([fuel])
            .with_time_series([ltp_test_helper.dummy_time_series])
            .with_facility_inputs(
                [ltp_test_helper.generator_fuel_energy_function, ltp_test_helper.compressor_energy_function]
            )
        ).validate()

        configuration_service = yaml_asset_configuration_service_factory(model=asset, name="test_asset")
        asset = yaml_model_factory(
            configuration=configuration_service.get_configuration(),
            resources=resources,
            frequency=Frequency.YEAR,
        )

        graph_result = ltp_test_helper.get_graph_result(asset)
        asset_result = ltp_test_helper.get_asset_result(graph_result)

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
        ltp_test_helper,
        fuel_gas_factory,
        el_consumer_direct_base_load_factory,
        generator_fuel_power_to_fuel_resource,
        compressor_sampled_fuel_driven_resource,
        yaml_model_factory,
        yaml_asset_configuration_service_factory,
    ):
        """Check that new total power includes the sum of electrical- and mechanical power at installation level"""
        time_series_resource = ltp_test_helper.dummy_time_series_resource(ltp_test_helper.time_vector_installation)
        name1 = "INSTALLATION_1"
        name2 = "INSTALLATION_2"

        el_consumer1 = el_consumer_direct_base_load_factory(
            el_reference_name="base_load1", load=ltp_test_helper.load_consumer
        )
        el_consumer2 = el_consumer_direct_base_load_factory(
            el_reference_name="base_load2", load=ltp_test_helper.load_consumer
        )

        fuel = fuel_gas_factory(["co2"], [ltp_test_helper.co2_factor])

        generator_set1 = ltp_test_helper.generator_set(request, name="generator_set1", el_consumer=el_consumer1)
        generator_set2 = ltp_test_helper.generator_set(request, name="generator_set2", el_consumer=el_consumer2)

        installation1 = (
            YamlInstallationBuilder()
            .with_name(name1)
            .with_generator_sets([generator_set1])
            .with_fuel(fuel.name)
            .with_regularity(ltp_test_helper.regularity_installation)
            .with_fuel_consumers([ltp_test_helper.fuel_consumer_compressor(fuel.name)])
            .with_category(InstallationUserDefinedCategoryType.FIXED)
        ).validate()

        installation2 = (
            YamlInstallationBuilder()
            .with_name(name2)
            .with_generator_sets([generator_set2])
            .with_fuel(fuel.name)
            .with_regularity(ltp_test_helper.regularity_installation)
            .with_fuel_consumers([ltp_test_helper.fuel_consumer_compressor(fuel.name, name="compressor2")])
            .with_category(InstallationUserDefinedCategoryType.FIXED)
        ).validate()

        resources = {
            ltp_test_helper.generator_fuel_energy_function.name: generator_fuel_power_to_fuel_resource(
                power_usage_mw=ltp_test_helper.power_usage_mw,
                fuel_rate=ltp_test_helper.fuel_rate,
            ),
            ltp_test_helper.compressor_energy_function.name: compressor_sampled_fuel_driven_resource(
                compressor_rate=ltp_test_helper.compressor_rate, power_compressor_mw=ltp_test_helper.power_compressor_mw
            ),
            ltp_test_helper.dummy_time_series.name: time_series_resource,
        }

        asset = (
            YamlAssetBuilder()
            .with_start(str(ltp_test_helper.time_vector_installation[0]))
            .with_end(str(ltp_test_helper.time_vector_installation[-1]))
            .with_installations([installation1, installation2])
            .with_fuel_types([fuel])
            .with_time_series([ltp_test_helper.dummy_time_series])
            .with_facility_inputs(
                [ltp_test_helper.generator_fuel_energy_function, ltp_test_helper.compressor_energy_function]
            )
        ).validate()

        configuration_service = yaml_asset_configuration_service_factory(model=asset, name="test_asset")
        asset = yaml_model_factory(
            configuration=configuration_service.get_configuration(),
            resources=resources,
            frequency=Frequency.YEAR,
        )

        graph_result = ltp_test_helper.get_graph_result(asset)
        asset_result = ltp_test_helper.get_asset_result(graph_result)

        power_el_1 = asset_result.get_component_by_name(name1).power_electrical_cumulative.values[-1]
        power_mech_1 = asset_result.get_component_by_name(name1).power_mechanical_cumulative.values[-1]

        power_el_2 = asset_result.get_component_by_name(name2).power_electrical_cumulative.values[-1]
        power_mech_2 = asset_result.get_component_by_name(name2).power_mechanical_cumulative.values[-1]

        asset_power_el = asset_result.component_result.power_electrical_cumulative.values[-1]

        asset_power_mech = asset_result.component_result.power_mechanical_cumulative.values[-1]

        # Verify that electrical power is correct at asset level
        assert asset_power_el == power_el_1 + power_el_2

        # Verify that mechanical power is correct at asset level:
        assert asset_power_mech == power_mech_1 + power_mech_2

    def test_venting_emitters(
        self,
        ltp_test_helper,
        fuel_consumer_direct_factory,
        fuel_gas_factory,
        yaml_model_factory,
        yaml_asset_configuration_service_factory,
    ):
        """Test venting emitters for LTP export.

        Verify correct behaviour if input rate is given in different units and rate types (sd and cd).
        """

        time_vector = [datetime(2027, 1, 1), datetime(2028, 1, 1)]
        regularity = 0.2
        emission_rate = 10

        fuel = fuel_gas_factory(["co2"], [ltp_test_helper.co2_factor])

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
            .with_fuel_consumers([fuel_consumer_direct_factory(fuel.name, ltp_test_helper.fuel_rate)])
            .with_venting_emitters([venting_emitter_sd_kg_per_day])
            .with_regularity(regularity)
        ).validate()

        installation_sd_tons_per_day = (
            YamlInstallationBuilder()
            .with_name("minimal_installation")
            .with_category(InstallationUserDefinedCategoryType.FIXED)
            .with_fuel_consumers([fuel_consumer_direct_factory(fuel.name, ltp_test_helper.fuel_rate)])
            .with_venting_emitters([venting_emitter_sd_tons_per_day])
            .with_regularity(regularity)
        ).validate()

        installation_cd_kg_per_day = (
            YamlInstallationBuilder()
            .with_name("minimal_installation")
            .with_category(InstallationUserDefinedCategoryType.FIXED)
            .with_fuel_consumers([fuel_consumer_direct_factory(fuel.name, ltp_test_helper.fuel_rate)])
            .with_venting_emitters([venting_emitter_cd_kg_per_day])
            .with_regularity(regularity)
        ).validate()

        asset_sd_kg_per_day = (
            YamlAssetBuilder()
            .with_installations([installation_sd_kg_per_day])
            .with_fuel_types([fuel])
            .with_start(str(time_vector[0]))
            .with_end(str(time_vector[-1]))
        ).validate()

        asset_sd_tons_per_day = (
            YamlAssetBuilder()
            .with_installations([installation_sd_tons_per_day])
            .with_fuel_types([fuel])
            .with_start(str(time_vector[0]))
            .with_end(str(time_vector[-1]))
        ).validate()

        asset_cd_kg_per_day = (
            YamlAssetBuilder()
            .with_installations([installation_cd_kg_per_day])
            .with_fuel_types([fuel])
            .with_start(str(time_vector[0]))
            .with_end(str(time_vector[-1]))
        ).validate()

        configuration_service = yaml_asset_configuration_service_factory(model=asset_sd_kg_per_day, name="test_asset")
        asset_sd_kg_per_day = yaml_model_factory(
            configuration=configuration_service.get_configuration(),
            resources={},
            frequency=Frequency.YEAR,
        )
        configuration_service = yaml_asset_configuration_service_factory(model=asset_sd_tons_per_day, name="test_asset")
        asset_sd_tons_per_day = yaml_model_factory(
            configuration=configuration_service.get_configuration(),
            resources={},
            frequency=Frequency.YEAR,
        )
        configuration_service = yaml_asset_configuration_service_factory(model=asset_cd_kg_per_day, name="test_asset")
        asset_cd_kg_per_day = yaml_model_factory(
            configuration=configuration_service.get_configuration(),
            resources={},
            frequency=Frequency.YEAR,
        )

        graph_result = ltp_test_helper.get_graph_result(asset_sd_kg_per_day)
        ltp_result_input_sd_kg_per_day = ltp_test_helper.get_ltp_report(
            graph_result=graph_result, model=asset_sd_kg_per_day
        )

        graph_result = ltp_test_helper.get_graph_result(asset_sd_tons_per_day)
        ltp_result_input_sd_tons_per_day = ltp_test_helper.get_ltp_report(
            graph_result=graph_result, model=asset_sd_tons_per_day
        )

        graph_result = ltp_test_helper.get_graph_result(asset_cd_kg_per_day)
        ltp_result_input_cd_kg_per_day = ltp_test_helper.get_ltp_report(
            graph_result=graph_result, model=asset_cd_kg_per_day
        )

        emission_input_sd_kg_per_day = ltp_test_helper.get_sum_ltp_column(
            ltp_result_input_sd_kg_per_day, installation_nr=0, ltp_column="storageCh4Mass"
        )
        emission_input_sd_tons_per_day = ltp_test_helper.get_sum_ltp_column(
            ltp_result_input_sd_tons_per_day, installation_nr=0, ltp_column="storageCh4Mass"
        )
        emission_input_cd_kg_per_day = ltp_test_helper.get_sum_ltp_column(
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

    def test_only_venting_emitters_no_fuelconsumers(
        self,
        ltp_test_helper,
        fuel_consumer_direct_factory,
        fuel_gas_factory,
        yaml_asset_configuration_service_factory,
        yaml_model_factory,
    ):
        """
        Test that it is possible with only venting emitters, without fuelconsumers.
        """
        time_vector = [datetime(2027, 1, 1), datetime(2028, 1, 1)]
        regularity = 0.2
        emission_rate = 10

        fuel = fuel_gas_factory(["co2"], [ltp_test_helper.co2_factor])

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

        asset = (
            YamlAssetBuilder()
            .with_installations([installation_only_emitters])
            .with_start(str(time_vector[0]))
            .with_end(str(time_vector[-1]))
        ).validate()

        configuration_service = yaml_asset_configuration_service_factory(model=asset, name="test_asset")
        asset = yaml_model_factory(
            configuration=configuration_service.get_configuration(),
            resources={},
            frequency=Frequency.YEAR,
        )

        graph_result = ltp_test_helper.get_graph_result(asset)
        venting_emitter_only_results = ltp_test_helper.get_ltp_report(graph_result=graph_result, model=asset)

        # Verify that eCalc is not failing in get_asset_result with only venting emitters -
        # when installation result is empty, i.e. with no genset and fuel consumers:
        assert isinstance(ltp_test_helper.get_asset_result(graph_result), EcalcModelResult)

        # Verify correct emissions:
        emissions_ch4 = ltp_test_helper.get_sum_ltp_column(
            venting_emitter_only_results, installation_nr=0, ltp_column="storageCh4Mass"
        )
        assert emissions_ch4 == (emission_rate / 1000) * 365 * regularity

        # Installation with only fuel consumers:
        installation_only_fuel_consumers = (
            YamlInstallationBuilder()
            .with_name("Fuel consumer installation")
            .with_category(InstallationUserDefinedCategoryType.FIXED)
            .with_fuel_consumers(
                [fuel_consumer_direct_factory(fuel_reference_name=fuel.name, rate=ltp_test_helper.fuel_rate)]
            )
            .with_regularity(regularity)
        ).validate()

        asset_multi_installations = (
            YamlAssetBuilder()
            .with_installations([installation_only_emitters, installation_only_fuel_consumers])
            .with_fuel_types([fuel])
            .with_start(str(time_vector[0]))
            .with_end(str(time_vector[-1]))
        ).validate()

        configuration_service = yaml_asset_configuration_service_factory(
            model=asset_multi_installations, name="test_asset"
        )
        asset_multi_installations = yaml_model_factory(
            configuration=configuration_service.get_configuration(),
            resources={},
            frequency=Frequency.YEAR,
        )
        graph_result = ltp_test_helper.get_graph_result(asset_multi_installations)
        asset_ltp_result = ltp_test_helper.get_ltp_report(graph_result=graph_result, model=asset_multi_installations)

        # Verify that eCalc is not failing in get_asset_result, with only venting emitters -
        # when installation result is empty for one installation, i.e. with no genset and fuel consumers.
        # Include asset with two installations, one with only emitters and one with only fuel consumers -
        # ensure that get_asset_result returns a result:
        assert isinstance(
            ltp_test_helper.get_asset_result(graph_result),
            EcalcModelResult,
        )

        # Check that the results are the same: For the case with only one installation (only venting emitters),
        # compared to the multi-installation case with two installations. The fuel-consumer installation should
        # give no CH4-contribution (only CO2)
        emissions_ch4_asset = ltp_test_helper.get_sum_ltp_column(
            asset_ltp_result, installation_nr=0, ltp_column="storageCh4Mass"
        )
        assert emissions_ch4 == emissions_ch4_asset

    def test_power_from_shore(
        self,
        ltp_test_helper,
        yaml_model_factory,
        el_consumer_direct_base_load_factory,
        fuel_gas_factory,
        generator_electricity2fuel_17MW_resource,
        onshore_power_electricity2fuel_resource,
        cable_loss_time_series_resource,
        yaml_asset_configuration_service_factory,
    ):
        """Test power from shore output for LTP export."""

        time_vector_yearly = (
            pd.date_range(datetime(2025, 1, 1), datetime(2031, 1, 1), freq="YS").to_pydatetime().tolist()
        )
        fuel = fuel_gas_factory(
            ["co2", "ch4", "nmvoc", "nox"],
            [
                ltp_test_helper.co2_factor,
                ltp_test_helper.ch4_factor,
                ltp_test_helper.nmvoc_factor,
                ltp_test_helper.nox_factor,
            ],
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
                    datetime(2025, 1, 1): ltp_test_helper.generator_fuel_energy_function.name,
                    datetime(2027, 1, 1): ltp_test_helper.power_from_shore_energy_function.name,
                }
            )
            .with_consumers([el_consumer_direct_base_load_factory(el_reference_name="base_load", load=load)])
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
            ltp_test_helper.generator_fuel_energy_function.name: generator_electricity2fuel_17MW_resource,
            ltp_test_helper.power_from_shore_energy_function.name: onshore_power_electricity2fuel_resource,
            cable_loss_time_series.name: cable_loss_time_series_resource,
        }

        asset_pfs = (
            YamlAssetBuilder()
            .with_start(time_vector_yearly[0])
            .with_end(time_vector_yearly[-1])
            .with_installations([installation_pfs])
            .with_fuel_types([fuel])
            .with_time_series([cable_loss_time_series])
            .with_facility_inputs(
                [ltp_test_helper.generator_fuel_energy_function, ltp_test_helper.power_from_shore_energy_function]
            )
        ).validate()

        configuration_service = yaml_asset_configuration_service_factory(model=asset_pfs, name="test_asset")
        asset_pfs = yaml_model_factory(
            configuration=configuration_service.get_configuration(),
            resources=resources,
            frequency=Frequency.YEAR,
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

        asset_pfs_csv = (
            YamlAssetBuilder()
            .with_start(time_vector_yearly[0])
            .with_end(time_vector_yearly[-1])
            .with_installations([installation_pfs_csv])
            .with_fuel_types([fuel])
            .with_time_series([cable_loss_time_series])
            .with_facility_inputs(
                [ltp_test_helper.generator_fuel_energy_function, ltp_test_helper.power_from_shore_energy_function]
            )
        ).validate()

        configuration_service = yaml_asset_configuration_service_factory(model=asset_pfs_csv, name="test_asset")
        asset_pfs_csv = yaml_model_factory(
            configuration=configuration_service.get_configuration(),
            resources=resources,
            frequency=Frequency.YEAR,
        )

        graph_result = ltp_test_helper.get_graph_result(asset_pfs)
        ltp_result = ltp_test_helper.get_ltp_report(graph_result=graph_result, model=asset_pfs)

        graph_result = ltp_test_helper.get_graph_result(asset_pfs_csv)
        ltp_result_csv = ltp_test_helper.get_ltp_report(graph_result=graph_result, model=asset_pfs_csv)

        power_from_shore_consumption = ltp_test_helper.get_sum_ltp_column(
            ltp_result=ltp_result, installation_nr=0, ltp_column="fromShoreConsumption"
        )
        power_supply_onshore = ltp_test_helper.get_sum_ltp_column(
            ltp_result=ltp_result, installation_nr=0, ltp_column="powerSupplyOnshore"
        )
        max_usage_from_shore = ltp_test_helper.get_sum_ltp_column(
            ltp_result=ltp_result, installation_nr=0, ltp_column="fromShorePeakMaximum"
        )

        power_supply_onshore_csv = ltp_test_helper.get_sum_ltp_column(
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
            ltp_test_helper.get_ltp_column(
                ltp_result=ltp_result, installation_nr=0, ltp_column="fromShorePeakMaximum"
            ).unit
            == Unit.MEGA_WATT
        )

    def test_max_usage_from_shore(
        self,
        ltp_test_helper,
        el_consumer_direct_base_load_factory,
        generator_electricity2fuel_17MW_resource,
        onshore_power_electricity2fuel_resource,
        max_usage_from_shore_time_series_resource,
        fuel_gas_factory,
        yaml_model_factory,
        yaml_asset_configuration_service_factory,
    ):
        """Test power from shore output for LTP export."""

        regularity = 0.2
        load = 10
        cable_loss = 0.1

        time_vector_yearly = (
            pd.date_range(datetime(2025, 1, 1), datetime(2031, 1, 1), freq="YS").to_pydatetime().tolist()
        )

        fuel = fuel_gas_factory(
            ["co2", "ch4", "nmvoc", "nox"],
            [
                ltp_test_helper.co2_factor,
                ltp_test_helper.ch4_factor,
                ltp_test_helper.nmvoc_factor,
                ltp_test_helper.nox_factor,
            ],
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
                    datetime(2025, 1, 1): ltp_test_helper.generator_fuel_energy_function.name,
                    datetime(2027, 1, 1): ltp_test_helper.power_from_shore_energy_function.name,
                }
            )
            .with_consumers([el_consumer_direct_base_load_factory(el_reference_name="base_load", load=load)])
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
            ltp_test_helper.generator_fuel_energy_function.name: generator_electricity2fuel_17MW_resource,
            ltp_test_helper.power_from_shore_energy_function.name: onshore_power_electricity2fuel_resource,
            max_usage_from_shore_time_series.name: max_usage_from_shore_time_series_resource,
        }

        asset_pfs = (
            YamlAssetBuilder()
            .with_start(time_vector_yearly[0])
            .with_end(time_vector_yearly[-1])
            .with_installations([installation_pfs])
            .with_fuel_types([fuel])
            .with_time_series([max_usage_from_shore_time_series])
            .with_facility_inputs(
                [ltp_test_helper.generator_fuel_energy_function, ltp_test_helper.power_from_shore_energy_function]
            )
        ).validate()

        configuration_service = yaml_asset_configuration_service_factory(model=asset_pfs, name="test_asset")
        asset_pfs = yaml_model_factory(
            configuration=configuration_service.get_configuration(),
            resources=resources,
            frequency=Frequency.YEAR,
        )

        graph_result = ltp_test_helper.get_graph_result(asset_pfs)
        ltp_result = ltp_test_helper.get_ltp_report(graph_result=graph_result, model=asset_pfs)

        max_usage_from_shore = ltp_test_helper.get_ltp_column(
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

    def test_venting_emitters_direct_multiple_emissions_ltp(
        self, ltp_test_helper, yaml_asset_configuration_service_factory, yaml_model_factory
    ):
        """
        Check that multiple emissions are calculated correctly for venting emitter of type DIRECT_EMISSION.
        """
        time_vector = [datetime(2027, 1, 1), datetime(2028, 1, 1), datetime(2029, 1, 1)]
        time_series_resource = ltp_test_helper.dummy_time_series_resource(time_vector)
        regularity = 0.2
        emission_rates = [10, 5]

        venting_emitter = (
            YamlVentingEmitterDirectTypeBuilder()
            .with_name("Venting emitter 1")
            .with_category(ConsumerUserDefinedCategoryType.COLD_VENTING_FUGITIVE)
            .with_emission_names_rates_units_and_types(
                names=["co2", "ch4"],
                rates=emission_rates,
                units=[YamlEmissionRateUnits.KILO_PER_DAY, YamlEmissionRateUnits.KILO_PER_DAY],
                rate_types=[RateType.STREAM_DAY, RateType.STREAM_DAY],
            )
        ).validate()

        installation = (
            YamlInstallationBuilder()
            .with_name("Installation 1")
            .with_category(InstallationUserDefinedCategoryType.FIXED)
            .with_venting_emitters([venting_emitter])
            .with_regularity(regularity)
        ).validate()

        resources = {ltp_test_helper.dummy_time_series.name: time_series_resource}
        asset = (
            YamlAssetBuilder()
            .with_installations([installation])
            .with_time_series([ltp_test_helper.dummy_time_series])
            .with_start(time_vector[0])
            .with_end(time_vector[-1])
        ).validate()

        configuration_service = yaml_asset_configuration_service_factory(model=asset, name="test_asset")
        asset = yaml_model_factory(
            configuration=configuration_service.get_configuration(),
            resources=resources,
            frequency=Frequency.YEAR,
        )

        delta_days = [(time_j - time_i).days for time_i, time_j in zip(time_vector[:-1], time_vector[1:])]

        graph_result = ltp_test_helper.get_graph_result(asset)
        ltp_result = ltp_test_helper.get_ltp_report(graph_result=graph_result, model=asset)

        ch4_emissions = ltp_test_helper.get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column="co2VentingMass")
        co2_emissions = ltp_test_helper.get_sum_ltp_column(
            ltp_result, installation_nr=0, ltp_column="coldVentAndFugitivesCh4Mass"
        )

        assert ch4_emissions == sum(emission_rates[0] * days * regularity / 1000 for days in delta_days)
        assert co2_emissions == sum(emission_rates[1] * days * regularity / 1000 for days in delta_days)

    def test_venting_emitters_volume_multiple_emissions_ltp(
        self, ltp_test_helper, yaml_asset_configuration_service_factory, yaml_model_factory
    ):
        """
        Check that multiple emissions are calculated correctly for venting emitter of type OIL_VOLUME.
        """
        time_vector = [datetime(2027, 1, 1), datetime(2028, 1, 1), datetime(2029, 1, 1)]
        time_series_resource = ltp_test_helper.dummy_time_series_resource(time_vector)

        regularity = 0.2
        emission_factors = [0.1, 0.1]
        oil_rate = 100

        venting_emitter = (
            YamlVentingEmitterOilTypeBuilder()
            .with_name("Venting emitter 1")
            .with_category(ConsumerUserDefinedCategoryType.LOADING)
            .with_rate_and_emission_names_and_factors(
                rate=oil_rate,
                names=["ch4", "nmvoc"],
                factors=emission_factors,
                unit=YamlOilRateUnits.STANDARD_CUBIC_METER_PER_DAY,
                rate_type=RateType.CALENDAR_DAY,
            )
        ).validate()

        installation = (
            YamlInstallationBuilder()
            .with_name("Installation calendar day")
            .with_category(InstallationUserDefinedCategoryType.FIXED)
            .with_venting_emitters([venting_emitter])
            .with_regularity(regularity)
        ).validate()

        resources = {ltp_test_helper.dummy_time_series.name: time_series_resource}
        asset = (
            YamlAssetBuilder()
            .with_installations([installation])
            .with_time_series([ltp_test_helper.dummy_time_series])
            .with_start(time_vector[0])
            .with_end(time_vector[-1])
        ).validate()

        venting_emitter_sd = deepcopy(venting_emitter)
        venting_emitter_sd.volume.rate.type = RateType.STREAM_DAY

        installation_sd = deepcopy(installation)
        installation_sd.venting_emitters = [venting_emitter_sd]

        asset_sd = deepcopy(asset)
        asset_sd.installations = [installation_sd]

        configuration_service = yaml_asset_configuration_service_factory(model=asset, name="test_asset")
        asset = yaml_model_factory(
            configuration=configuration_service.get_configuration(),
            resources=resources,
            frequency=Frequency.YEAR,
        )
        configuration_service = yaml_asset_configuration_service_factory(model=asset_sd, name="test_asset")
        asset_sd = yaml_model_factory(
            configuration=configuration_service.get_configuration(),
            resources=resources,
            frequency=Frequency.YEAR,
        )

        delta_days = [(time_j - time_i).days for time_i, time_j in zip(time_vector[:-1], time_vector[1:])]

        graph_result = ltp_test_helper.get_graph_result(asset)
        ltp_result = ltp_test_helper.get_ltp_report(graph_result=graph_result, model=asset)

        graph_result = ltp_test_helper.get_graph_result(asset_sd)
        ltp_result_stream_day = ltp_test_helper.get_ltp_report(graph_result=graph_result, model=asset_sd)

        ch4_emissions = ltp_test_helper.get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column="loadingNmvocMass")
        nmvoc_emissions = ltp_test_helper.get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column="loadingCh4Mass")
        oil_volume = ltp_test_helper.get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column="loadedAndStoredOil")

        oil_volume_stream_day = ltp_test_helper.get_sum_ltp_column(
            ltp_result_stream_day, installation_nr=0, ltp_column="loadedAndStoredOil"
        )

        assert ch4_emissions == sum(oil_rate * days * emission_factors[0] / 1000 for days in delta_days)
        assert nmvoc_emissions == sum(oil_rate * days * emission_factors[1] / 1000 for days in delta_days)
        assert oil_volume == pytest.approx(sum(oil_rate * days for days in delta_days), abs=1e-5)

        # Check that oil volume is including regularity correctly:
        # Oil volume (input rate in stream day) / oil volume (input rates calendar day) = regularity.
        # Given that the actual rate input values are the same.
        assert oil_volume_stream_day / oil_volume == regularity
