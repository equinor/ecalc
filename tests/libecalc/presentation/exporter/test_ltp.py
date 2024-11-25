from copy import deepcopy
from datetime import datetime
from typing import Union

import numpy as np
import pandas as pd
import pytest

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
from libecalc.presentation.yaml.model import YamlModel
from libecalc.presentation.yaml.yaml_types.components.legacy.yaml_electricity_consumer import YamlElectricityConsumer
from libecalc.presentation.yaml.yaml_types.components.yaml_asset import YamlAsset
from libecalc.presentation.yaml.yaml_types.components.yaml_installation import YamlInstallation
from libecalc.presentation.yaml.yaml_types.fuel_type.yaml_fuel_type import YamlFuelType
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


from libecalc.presentation.yaml.yaml_types.components.legacy.energy_usage_model.yaml_energy_usage_model_direct import (
    ConsumptionRateType,
)


# LTP specific methods:


class LtpTestHelper:
    def __init__(self):
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

    def get_consumption(
        self,
        model: Union[YamlInstallation, YamlAsset, YamlModel],
        variables: VariablesMap,
        frequency: Frequency,
        periods: Periods,
    ) -> FilteredResult:
        energy_calculator = EnergyCalculator(energy_model=model, expression_evaluator=variables)
        precision = 6

        consumer_results = energy_calculator.evaluate_energy_usage()
        emission_results = energy_calculator.evaluate_emissions()

        graph_result = GraphResult(
            graph=model.get_graph(),
            variables_map=variables,
            consumer_results=consumer_results,
            emission_results=emission_results,
        )

        ltp_filter = LTPConfig.filter(frequency=frequency)
        ltp_result = ltp_filter.filter(ExportableGraphResult(graph_result), periods)

        return ltp_result

    def get_sum_ltp_column(self, ltp_result: FilteredResult, installation_nr, ltp_column: str) -> float:
        installation_query_results = ltp_result.query_results[installation_nr].query_results
        column = [column for column in installation_query_results if column.id == ltp_column][0]

        ltp_sum = sum(float(v) for (k, v) in column.values.items())
        return ltp_sum

    def get_ltp_column(self, ltp_result: FilteredResult, installation_nr, ltp_column: str) -> QueryResult:
        installation_query_results = ltp_result.query_results[installation_nr].query_results
        column = [column for column in installation_query_results if column.id == ltp_column][0]

        return column

    def get_ltp_result(self, model, variables, frequency=Frequency.YEAR):
        return self.get_consumption(
            model=model, variables=variables, periods=variables.get_periods(), frequency=frequency
        )

    def create_variables_map(self, time_vector, rate_values=None):
        variables = {"RATE": rate_values} if rate_values else {}
        return VariablesMap(time_vector=time_vector, variables=variables)

    def calculate_asset_result(self, model: YamlModel, variables: VariablesMap):
        model = model
        graph = model.get_graph()
        energy_calculator = EnergyCalculator(energy_model=model, expression_evaluator=variables)

        consumer_results = energy_calculator.evaluate_energy_usage()
        emission_results = energy_calculator.evaluate_emissions()

        results_core = GraphResult(
            graph=graph,
            variables_map=variables,
            consumer_results=consumer_results,
            emission_results=emission_results,
        )

        results_dto = get_asset_result(results_core)

        return results_dto

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
        el2fuel: Union[str, dict[datetime, str]] = None,
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


@pytest.fixture(scope="module")
def ltp():
    return LtpTestHelper()


class TestLtp:
    def test_emissions_diesel_fixed_and_mobile(
        self,
        ltp,
        fuel_gas_factory,
        diesel_factory,
        el_consumer_direct_base_load_factory,
        generator_diesel_power_to_fuel_resource,
        generator_fuel_power_to_fuel_resource,
    ):
        fuel = fuel_gas_factory(["co2"], [ltp.co2_factor])
        diesel = diesel_factory(
            ["co2", "ch4", "nox", "nmvoc"], [ltp.co2_factor, ltp.ch4_factor, ltp.nox_factor, ltp.nmvoc_factor]
        )

        generator_fixed = (
            YamlGeneratorSetBuilder()
            .with_name("generator_fixed")
            .with_category(ltp.category_dict())
            .with_consumers(
                [el_consumer_direct_base_load_factory(el_reference_name="base_load", load=ltp.load_consumer)]
            )
            .with_electricity2fuel(
                ltp.temporal_dict(
                    reference1=ltp.generator_diesel_energy_function.name,
                    reference2=ltp.generator_fuel_energy_function.name,
                )
            )
        ).validate()

        generator_mobile = deepcopy(generator_fixed)
        generator_mobile.name = "generator_mobile"

        installation_fixed = (
            YamlInstallationBuilder()
            .with_name("INSTALLATION_FIXED")
            .with_regularity(ltp.regularity_installation)
            .with_fuel(ltp.fuel_multi_temporal(diesel, fuel))
            .with_category(InstallationUserDefinedCategoryType.FIXED)
            .with_generator_sets([generator_fixed])
        ).validate()

        installation_mobile = (
            YamlInstallationBuilder()
            .with_name("INSTALLATION_MOBILE")
            .with_regularity(ltp.regularity_installation)
            .with_fuel(ltp.fuel_multi_temporal(diesel, fuel))
            .with_category(InstallationUserDefinedCategoryType.MOBILE)
            .with_generator_sets([generator_mobile])
        ).validate()

        resources = {
            ltp.generator_diesel_energy_function.name: generator_diesel_power_to_fuel_resource(
                power_usage_mw=ltp.power_usage_mw, diesel_rate=ltp.diesel_rate
            ),
            ltp.generator_fuel_energy_function.name: generator_fuel_power_to_fuel_resource(
                power_usage_mw=ltp.power_usage_mw, fuel_rate=ltp.fuel_rate
            ),
        }

        asset = (
            YamlAssetBuilder()
            .with_start(str(ltp.time_vector_installation[0]))
            .with_end(str(ltp.time_vector_installation[-1]))
            .with_installations([installation_fixed, installation_mobile])
            .with_facility_inputs([ltp.generator_diesel_energy_function, ltp.generator_fuel_energy_function])
            .with_fuel_types([fuel, diesel])
            .get_yaml_model(resources=resources, frequency=Frequency.YEAR)
        )

        variables = ltp.create_variables_map(ltp.time_vector_installation, [1, 1, 1, 1])
        ltp_result = ltp.get_ltp_result(asset, variables)

        ltp.assert_emissions(ltp_result, 0, "engineDieselCo2Mass", ltp.co2_from_diesel)
        ltp.assert_emissions(ltp_result, 1, "engineNoCo2TaxDieselCo2Mass", ltp.co2_from_diesel)
        ltp.assert_emissions(ltp_result, 0, "engineDieselNoxMass", ltp.nox_from_diesel)
        ltp.assert_emissions(ltp_result, 1, "engineNoCo2TaxDieselNoxMass", ltp.nox_from_diesel)
        ltp.assert_emissions(ltp_result, 0, "engineDieselNmvocMass", ltp.nmvoc_from_diesel)
        ltp.assert_emissions(ltp_result, 1, "engineNoCo2TaxDieselNmvocMass", ltp.nmvoc_from_diesel)
        ltp.assert_emissions(ltp_result, 0, "engineDieselCh4Mass", ltp.ch4_from_diesel)
        ltp.assert_emissions(ltp_result, 1, "engineNoCo2TaxDieselCh4Mass", ltp.ch4_from_diesel)

    def test_temporal_models_detailed(
        self,
        ltp,
        diesel_factory,
        fuel_gas_factory,
        generator_diesel_power_to_fuel_resource,
        generator_fuel_power_to_fuel_resource,
        el_consumer_direct_base_load_factory,
    ):
        """Test various queries for LTP reporting. Purpose: ensure that variations in temporal models are captured.

        Detailed temporal models (variations within one year) for:
        - Fuel type
        - Generator set user defined category
        - Generator set model
        """
        variables = ltp.create_variables_map(ltp.time_vector_installation, rate_values=[1, 1, 1, 1])
        fuel = fuel_gas_factory(["co2"], [ltp.co2_factor])
        diesel = diesel_factory(["co2"], [ltp.co2_factor])

        generator_set = (
            YamlGeneratorSetBuilder()
            .with_name("generator_set")
            .with_category(ltp.category_dict_coarse())
            .with_consumers(
                [el_consumer_direct_base_load_factory(el_reference_name="base_load", load=ltp.load_consumer)]
            )
            .with_electricity2fuel(
                ltp.temporal_dict(
                    reference1=ltp.generator_diesel_energy_function.name,
                    reference2=ltp.generator_fuel_energy_function.name,
                )
            )
        ).validate()

        installation = (
            YamlInstallationBuilder()
            .with_name("INSTALLATION A")
            .with_generator_sets([generator_set])
            .with_fuel(ltp.fuel_multi_temporal(fuel1=diesel, fuel2=fuel))
            .with_category(InstallationUserDefinedCategoryType.FIXED)
        ).validate()

        resources = {
            ltp.generator_diesel_energy_function.name: generator_diesel_power_to_fuel_resource(
                power_usage_mw=ltp.power_usage_mw,
                diesel_rate=ltp.diesel_rate,
            ),
            ltp.generator_fuel_energy_function.name: generator_fuel_power_to_fuel_resource(
                power_usage_mw=ltp.power_usage_mw,
                fuel_rate=ltp.fuel_rate,
            ),
        }

        asset = (
            YamlAssetBuilder()
            .with_start(str(ltp.time_vector_installation[0]))
            .with_end(str(ltp.time_vector_installation[-1]))
            .with_installations([installation])
            .with_facility_inputs([ltp.generator_diesel_energy_function, ltp.generator_fuel_energy_function])
            .with_fuel_types([fuel, diesel])
            .get_yaml_model(resources=resources, frequency=Frequency.YEAR)
        )

        ltp_result = ltp.get_ltp_result(asset, variables)

        turbine_fuel_consumption = ltp.get_sum_ltp_column(
            ltp_result, installation_nr=0, ltp_column="turbineFuelGasConsumption"
        )

        # FuelQuery: Check that turbine fuel consumption is included,
        # even if the temporal model starts with diesel every year
        assert turbine_fuel_consumption != 0

        ltp.assert_consumption(ltp_result, 0, "turbineFuelGasConsumption", ltp.fuel_consumption)
        ltp.assert_consumption(ltp_result, 0, "engineDieselConsumption", ltp.diesel_consumption)
        ltp.assert_consumption(ltp_result, 0, "turbineFuelGasCo2Mass", ltp.co2_from_fuel)
        ltp.assert_consumption(ltp_result, 0, "engineDieselCo2Mass", ltp.co2_from_diesel)
        ltp.assert_consumption(ltp_result, 0, "fromShoreConsumption", ltp.pfs_el_consumption)
        ltp.assert_consumption(ltp_result, 0, "gasTurbineGeneratorConsumption", ltp.gas_turbine_el_generated)

    def test_temporal_models_offshore_wind(
        self,
        ltp,
        request,
        fuel_gas_factory,
        generator_fuel_power_to_fuel_resource,
    ):
        """Test ElConsumerPowerConsumptionQuery for calculating offshore wind el-consumption, LTP.

        Detailed temporal models (variations within one year) for:
        - El-consumer user defined category
        - El-consumer energy usage model
        """
        variables = ltp.create_variables_map(ltp.time_vector_installation, rate_values=[1, 1, 1, 1])
        fuel = fuel_gas_factory(["co2"], [ltp.co2_factor])

        generator_set = (
            YamlGeneratorSetBuilder()
            .with_name("generator_set")
            .with_category({ltp.period_from_date1.start: ConsumerUserDefinedCategoryType.TURBINE_GENERATOR})
            .with_consumers([ltp.offshore_wind_consumer(request, ltp.power_offshore_wind_mw)])
            .with_electricity2fuel({ltp.period_from_date1.start: ltp.generator_fuel_energy_function.name})
        ).validate()

        installation = (
            YamlInstallationBuilder()
            .with_name("INSTALLATION A")
            .with_generator_sets([generator_set])
            .with_fuel(fuel.name)
            .with_category(InstallationUserDefinedCategoryType.FIXED)
        ).validate()

        resources = {
            ltp.generator_fuel_energy_function.name: generator_fuel_power_to_fuel_resource(
                power_usage_mw=ltp.power_usage_mw,
                fuel_rate=ltp.fuel_rate,
            ),
        }

        asset = (
            YamlAssetBuilder()
            .with_start(str(ltp.time_vector_installation[0]))
            .with_end(str(ltp.time_vector_installation[-1]))
            .with_installations([installation])
            .with_facility_inputs([ltp.generator_fuel_energy_function])
            .with_fuel_types([fuel])
            .get_yaml_model(resources=resources, frequency=Frequency.YEAR)
        )

        ltp_result = ltp.get_ltp_result(asset, variables)

        offshore_wind_el_consumption = ltp.get_sum_ltp_column(
            ltp_result, installation_nr=0, ltp_column="offshoreWindConsumption"
        )

        # ElConsumerPowerConsumptionQuery: Check that offshore wind el-consumption is correct.
        assert offshore_wind_el_consumption == ltp.offshore_wind_el_consumption

    def test_temporal_models_compressor(
        self,
        ltp,
        generator_fuel_power_to_fuel_resource,
        compressor_sampled_fuel_driven_resource,
        fuel_gas_factory,
    ):
        """Test FuelConsumerPowerConsumptionQuery for calculating gas turbine compressor el-consumption, LTP.

        Detailed temporal models (variations within one year) for:
        - Fuel consumer user defined category
        """
        variables = ltp.create_variables_map(ltp.time_vector_installation, rate_values=[1, 1, 1, 1])
        fuel = fuel_gas_factory(["co2"], [ltp.co2_factor])

        installation = (
            YamlInstallationBuilder()
            .with_name("INSTALLATION A")
            .with_fuel(fuel.name)
            .with_fuel_consumers([ltp.fuel_consumer_compressor(fuel.name)])
            .with_category(InstallationUserDefinedCategoryType.FIXED)
        ).validate()

        resources = {
            ltp.compressor_energy_function.name: compressor_sampled_fuel_driven_resource(
                compressor_rate=ltp.compressor_rate, power_compressor_mw=ltp.power_compressor_mw
            )
        }

        asset = (
            YamlAssetBuilder()
            .with_start(str(ltp.time_vector_installation[0]))
            .with_end(str(ltp.time_vector_installation[-1]))
            .with_installations([installation])
            .with_facility_inputs([ltp.compressor_energy_function])
            .with_fuel_types([fuel])
            .get_yaml_model(resources=resources, frequency=Frequency.YEAR)
        )

        ltp_result = ltp.get_ltp_result(asset, variables)

        gas_turbine_compressor_el_consumption = ltp.get_sum_ltp_column(
            ltp_result, installation_nr=0, ltp_column="gasTurbineCompressorConsumption"
        )

        # FuelConsumerPowerConsumptionQuery. Check gas turbine compressor el consumption.
        assert gas_turbine_compressor_el_consumption == ltp.gas_turbine_compressor_el_consumption

    def test_boiler_heater_categories(self, ltp, fuel_gas_factory):
        variables = ltp.create_variables_map(ltp.time_vector_installation)
        fuel = fuel_gas_factory(["co2"], [ltp.co2_factor])

        energy_usage_model = (
            YamlEnergyUsageModelDirectBuilder()
            .with_fuel_rate(ltp.fuel_rate)
            .with_consumption_rate_type(ConsumptionRateType.STREAM_DAY)
        ).validate()

        fuel_consumer = (
            YamlFuelConsumerBuilder()
            .with_name("boiler_heater")
            .with_fuel(fuel.name)
            .with_energy_usage_model({ltp.full_period.start: energy_usage_model})
            .with_category(
                {
                    Period(ltp.date1, ltp.date4).start: ConsumerUserDefinedCategoryType.BOILER,
                    Period(ltp.date4).start: ConsumerUserDefinedCategoryType.HEATER,
                }
            )
        ).validate()

        installation = (
            YamlInstallationBuilder()
            .with_name("INSTALLATION A")
            .with_category(InstallationUserDefinedCategoryType.FIXED)
            .with_fuel(fuel.name)
            .with_fuel_consumers([fuel_consumer])
            .with_regularity(ltp.regularity_installation)
        ).validate()

        asset = (
            YamlAssetBuilder()
            .with_start(str(ltp.date1))
            .with_end(str(ltp.date5))
            .with_installations([installation])
            .with_fuel_types([fuel])
            .get_yaml_model(frequency=Frequency.YEAR)
        )

        ltp_result = ltp.get_ltp_result(asset, variables)

        ltp.assert_consumption(ltp_result, 0, "boilerFuelGasConsumption", ltp.boiler_fuel_consumption)
        ltp.assert_consumption(ltp_result, 0, "heaterFuelGasConsumption", ltp.heater_fuel_consumption)
        ltp.assert_consumption(ltp_result, 0, "boilerFuelGasCo2Mass", ltp.co2_from_boiler)
        ltp.assert_consumption(ltp_result, 0, "heaterFuelGasCo2Mass", ltp.co2_from_heater)

    def test_total_oil_loaded_old_method(self, ltp, fuel_gas_factory, fuel_consumer_direct_factory):
        """Test total oil loaded/stored for LTP export. Using original method where direct/venting emitters are
        modelled as FUELSCONSUMERS using DIRECT.

        Verify correct volume when model includes emissions related to both storage and loading of oil,
        and when model includes only loading.
        """
        time_vector = [datetime(2027, 1, 1), datetime(2028, 1, 1)]
        variables = ltp.create_variables_map(time_vector)

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
            .with_start(str(ltp.time_vector_installation[0]))
            .with_end(str(ltp.time_vector_installation[-1]))
            .with_installations([installation])
            .with_fuel_types([fuel])
            .get_yaml_model(frequency=Frequency.YEAR)
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
            .with_start(str(ltp.time_vector_installation[0]))
            .with_end(str(ltp.time_vector_installation[-1]))
            .with_installations([installation_loading_only])
            .with_fuel_types([fuel])
            .get_yaml_model(frequency=Frequency.YEAR)
        )

        ltp_result_loading_storage = ltp.get_ltp_result(asset, variables)
        ltp_result_loading_only = ltp.get_ltp_result(asset_loading_only, variables)

        loaded_and_stored_oil_loading_and_storage = ltp.get_sum_ltp_column(
            ltp_result_loading_storage, installation_nr=0, ltp_column="loadedAndStoredOil"
        )
        loaded_and_stored_oil_loading_only = ltp.get_sum_ltp_column(
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
        ltp,
        request,
        fuel_gas_factory,
        generator_fuel_power_to_fuel_resource,
        compressor_sampled_fuel_driven_resource,
    ):
        """Check that new total power includes the sum of electrical- and mechanical power at installation level"""
        variables = ltp.create_variables_map(ltp.time_vector_installation)

        fuel = fuel_gas_factory(["co2"], [ltp.co2_factor])

        generator_set = ltp.generator_set(request)

        installation = (
            YamlInstallationBuilder()
            .with_name("INSTALLATION A")
            .with_generator_sets([generator_set])
            .with_fuel(fuel.name)
            .with_regularity(ltp.regularity_installation)
            .with_fuel_consumers([ltp.fuel_consumer_compressor(fuel.name)])
            .with_category(InstallationUserDefinedCategoryType.FIXED)
        ).validate()

        resources = {
            ltp.generator_fuel_energy_function.name: generator_fuel_power_to_fuel_resource(
                power_usage_mw=ltp.power_usage_mw,
                fuel_rate=ltp.fuel_rate,
            ),
            ltp.compressor_energy_function.name: compressor_sampled_fuel_driven_resource(
                compressor_rate=ltp.compressor_rate, power_compressor_mw=ltp.power_compressor_mw
            ),
        }

        asset = (
            YamlAssetBuilder()
            .with_start(str(ltp.time_vector_installation[0]))
            .with_end(str(ltp.time_vector_installation[-1]))
            .with_installations([installation])
            .with_fuel_types([fuel])
            .with_facility_inputs([ltp.generator_fuel_energy_function, ltp.compressor_energy_function])
            .get_yaml_model(resources=resources, frequency=Frequency.YEAR)
        )

        asset_result = ltp.calculate_asset_result(model=asset, variables=variables)
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
        ltp,
        request,
        fuel_gas_factory,
        el_consumer_direct_base_load_factory,
        generator_fuel_power_to_fuel_resource,
        compressor_sampled_fuel_driven_resource,
    ):
        """Check that new total power includes the sum of electrical- and mechanical power at installation level"""
        variables = ltp.create_variables_map(ltp.time_vector_installation)
        name1 = "INSTALLATION_1"
        name2 = "INSTALLATION_2"

        el_consumer1 = el_consumer_direct_base_load_factory(el_reference_name="base_load1", load=ltp.load_consumer)
        el_consumer2 = el_consumer_direct_base_load_factory(el_reference_name="base_load2", load=ltp.load_consumer)

        fuel = fuel_gas_factory(["co2"], [ltp.co2_factor])

        generator_set1 = ltp.generator_set(request, name="generator_set1", el_consumer=el_consumer1)
        generator_set2 = ltp.generator_set(request, name="generator_set2", el_consumer=el_consumer2)

        installation1 = (
            YamlInstallationBuilder()
            .with_name(name1)
            .with_generator_sets([generator_set1])
            .with_fuel(fuel.name)
            .with_regularity(ltp.regularity_installation)
            .with_fuel_consumers([ltp.fuel_consumer_compressor(fuel.name)])
            .with_category(InstallationUserDefinedCategoryType.FIXED)
        ).validate()

        installation2 = (
            YamlInstallationBuilder()
            .with_name(name2)
            .with_generator_sets([generator_set2])
            .with_fuel(fuel.name)
            .with_regularity(ltp.regularity_installation)
            .with_fuel_consumers([ltp.fuel_consumer_compressor(fuel.name, name="compressor2")])
            .with_category(InstallationUserDefinedCategoryType.FIXED)
        ).validate()

        resources = {
            ltp.generator_fuel_energy_function.name: generator_fuel_power_to_fuel_resource(
                power_usage_mw=ltp.power_usage_mw,
                fuel_rate=ltp.fuel_rate,
            ),
            ltp.compressor_energy_function.name: compressor_sampled_fuel_driven_resource(
                compressor_rate=ltp.compressor_rate, power_compressor_mw=ltp.power_compressor_mw
            ),
        }

        asset = (
            YamlAssetBuilder()
            .with_start(str(ltp.time_vector_installation[0]))
            .with_end(str(ltp.time_vector_installation[-1]))
            .with_installations([installation1, installation2])
            .with_fuel_types([fuel])
            .with_facility_inputs([ltp.generator_fuel_energy_function, ltp.compressor_energy_function])
            .get_yaml_model(resources=resources, frequency=Frequency.YEAR)
        )

        asset.dto.name = "Asset"

        asset_result = ltp.calculate_asset_result(model=asset, variables=variables)

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

    def test_venting_emitters(self, ltp, fuel_consumer_direct_factory, fuel_gas_factory):
        """Test venting emitters for LTP export.

        Verify correct behaviour if input rate is given in different units and rate types (sd and cd).
        """

        time_vector = [datetime(2027, 1, 1), datetime(2028, 1, 1)]
        regularity = 0.2
        emission_rate = 10

        variables = ltp.create_variables_map(time_vector)
        fuel = fuel_gas_factory(["co2"], [ltp.co2_factor])

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
            .with_fuel_consumers([fuel_consumer_direct_factory(fuel.name, ltp.fuel_rate)])
            .with_venting_emitters([venting_emitter_sd_kg_per_day])
            .with_regularity(regularity)
        ).validate()

        installation_sd_tons_per_day = (
            YamlInstallationBuilder()
            .with_name("minimal_installation")
            .with_category(InstallationUserDefinedCategoryType.FIXED)
            .with_fuel_consumers([fuel_consumer_direct_factory(fuel.name, ltp.fuel_rate)])
            .with_venting_emitters([venting_emitter_sd_tons_per_day])
            .with_regularity(regularity)
        ).validate()

        installation_cd_kg_per_day = (
            YamlInstallationBuilder()
            .with_name("minimal_installation")
            .with_category(InstallationUserDefinedCategoryType.FIXED)
            .with_fuel_consumers([fuel_consumer_direct_factory(fuel.name, ltp.fuel_rate)])
            .with_venting_emitters([venting_emitter_cd_kg_per_day])
            .with_regularity(regularity)
        ).validate()

        asset_sd_kg_per_day = (
            YamlAssetBuilder()
            .with_installations([installation_sd_kg_per_day])
            .with_fuel_types([fuel])
            .with_start(str(time_vector[0]))
            .with_end(str(time_vector[-1]))
            .get_yaml_model(frequency=Frequency.YEAR)
        )

        asset_sd_tons_per_day = (
            YamlAssetBuilder()
            .with_installations([installation_sd_tons_per_day])
            .with_fuel_types([fuel])
            .with_start(str(time_vector[0]))
            .with_end(str(time_vector[-1]))
            .get_yaml_model(frequency=Frequency.YEAR)
        )

        asset_cd_kg_per_day = (
            YamlAssetBuilder()
            .with_installations([installation_cd_kg_per_day])
            .with_fuel_types([fuel])
            .with_start(str(time_vector[0]))
            .with_end(str(time_vector[-1]))
            .get_yaml_model(frequency=Frequency.YEAR)
        )

        ltp_result_input_sd_kg_per_day = ltp.get_ltp_result(asset_sd_kg_per_day, variables)
        ltp_result_input_sd_tons_per_day = ltp.get_ltp_result(asset_sd_tons_per_day, variables)
        ltp_result_input_cd_kg_per_day = ltp.get_ltp_result(asset_cd_kg_per_day, variables)

        emission_input_sd_kg_per_day = ltp.get_sum_ltp_column(
            ltp_result_input_sd_kg_per_day, installation_nr=0, ltp_column="storageCh4Mass"
        )
        emission_input_sd_tons_per_day = ltp.get_sum_ltp_column(
            ltp_result_input_sd_tons_per_day, installation_nr=0, ltp_column="storageCh4Mass"
        )
        emission_input_cd_kg_per_day = ltp.get_sum_ltp_column(
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

    def test_only_venting_emitters_no_fuelconsumers(self, ltp, fuel_consumer_direct_factory, fuel_gas_factory):
        """
        Test that it is possible with only venting emitters, without fuelconsumers.
        """
        time_vector = [datetime(2027, 1, 1), datetime(2028, 1, 1)]
        regularity = 0.2
        emission_rate = 10

        variables = ltp.create_variables_map(time_vector)
        fuel = fuel_gas_factory(["co2"], [ltp.co2_factor])

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
            .get_yaml_model(frequency=Frequency.YEAR)
        )

        venting_emitter_only_results = ltp.get_ltp_result(asset, variables)

        # Verify that eCalc is not failing in get_asset_result with only venting emitters -
        # when installation result is empty, i.e. with no genset and fuel consumers:
        assert isinstance(ltp.calculate_asset_result(model=asset, variables=variables), EcalcModelResult)

        # Verify correct emissions:
        emissions_ch4 = ltp.get_sum_ltp_column(
            venting_emitter_only_results, installation_nr=0, ltp_column="storageCh4Mass"
        )
        assert emissions_ch4 == (emission_rate / 1000) * 365 * regularity

        # Installation with only fuel consumers:
        installation_only_fuel_consumers = (
            YamlInstallationBuilder()
            .with_name("Fuel consumer installation")
            .with_category(InstallationUserDefinedCategoryType.FIXED)
            .with_fuel_consumers([fuel_consumer_direct_factory(fuel_reference_name=fuel.name, rate=ltp.fuel_rate)])
            .with_regularity(regularity)
        ).validate()

        asset_multi_installations = (
            YamlAssetBuilder()
            .with_installations([installation_only_emitters, installation_only_fuel_consumers])
            .with_fuel_types([fuel])
            .with_start(str(time_vector[0]))
            .with_end(str(time_vector[-1]))
            .get_yaml_model(frequency=Frequency.YEAR)
        )

        # Verify that eCalc is not failing in get_asset_result, with only venting emitters -
        # when installation result is empty for one installation, i.e. with no genset and fuel consumers.
        # Include asset with two installations, one with only emitters and one with only fuel consumers -
        # ensure that get_asset_result returns a result:
        assert isinstance(
            ltp.calculate_asset_result(model=asset_multi_installations, variables=variables), EcalcModelResult
        )

        asset_ltp_result = ltp.get_ltp_result(asset_multi_installations, variables)

        # Check that the results are the same: For the case with only one installation (only venting emitters),
        # compared to the multi-installation case with two installations. The fuel-consumer installation should
        # give no CH4-contribution (only CO2)
        emissions_ch4_asset = ltp.get_sum_ltp_column(asset_ltp_result, installation_nr=0, ltp_column="storageCh4Mass")
        assert emissions_ch4 == emissions_ch4_asset

    def test_power_from_shore(
        self,
        ltp,
        el_consumer_direct_base_load_factory,
        fuel_gas_factory,
        generator_electricity2fuel_17MW_resource,
        onshore_power_electricity2fuel_resource,
        cable_loss_time_series_resource,
    ):
        """Test power from shore output for LTP export."""

        time_vector_yearly = (
            pd.date_range(datetime(2025, 1, 1), datetime(2031, 1, 1), freq="YS").to_pydatetime().tolist()
        )
        fuel = fuel_gas_factory(
            ["co2", "ch4", "nmvoc", "nox"], [ltp.co2_factor, ltp.ch4_factor, ltp.nmvoc_factor, ltp.nox_factor]
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
                    datetime(2025, 1, 1): ltp.generator_fuel_energy_function.name,
                    datetime(2027, 1, 1): ltp.power_from_shore_energy_function.name,
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
            ltp.generator_fuel_energy_function.name: generator_electricity2fuel_17MW_resource,
            ltp.power_from_shore_energy_function.name: onshore_power_electricity2fuel_resource,
            cable_loss_time_series.name: cable_loss_time_series_resource,
        }

        asset_pfs = (
            YamlAssetBuilder()
            .with_start(time_vector_yearly[0])
            .with_end(time_vector_yearly[-1])
            .with_installations([installation_pfs])
            .with_fuel_types([fuel])
            .with_time_series([cable_loss_time_series])
            .with_facility_inputs([ltp.generator_fuel_energy_function, ltp.power_from_shore_energy_function])
            .get_yaml_model(resources=resources, frequency=Frequency.YEAR)
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
            .with_facility_inputs([ltp.generator_fuel_energy_function, ltp.power_from_shore_energy_function])
            .get_yaml_model(resources=resources, frequency=Frequency.YEAR)
        )

        ltp_result = ltp.get_ltp_result(asset_pfs, asset_pfs.variables)
        ltp_result_csv = ltp.get_ltp_result(asset_pfs_csv, asset_pfs_csv.variables)

        power_from_shore_consumption = ltp.get_sum_ltp_column(
            ltp_result=ltp_result, installation_nr=0, ltp_column="fromShoreConsumption"
        )
        power_supply_onshore = ltp.get_sum_ltp_column(
            ltp_result=ltp_result, installation_nr=0, ltp_column="powerSupplyOnshore"
        )
        max_usage_from_shore = ltp.get_sum_ltp_column(
            ltp_result=ltp_result, installation_nr=0, ltp_column="fromShorePeakMaximum"
        )

        power_supply_onshore_csv = ltp.get_sum_ltp_column(
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
            ltp.get_ltp_column(ltp_result=ltp_result, installation_nr=0, ltp_column="fromShorePeakMaximum").unit
            == Unit.MEGA_WATT
        )

    def test_max_usage_from_shore(
        self,
        ltp,
        el_consumer_direct_base_load_factory,
        generator_electricity2fuel_17MW_resource,
        onshore_power_electricity2fuel_resource,
        max_usage_from_shore_time_series_resource,
        fuel_gas_factory,
    ):
        """Test power from shore output for LTP export."""

        regularity = 0.2
        load = 10
        cable_loss = 0.1

        time_vector_yearly = (
            pd.date_range(datetime(2025, 1, 1), datetime(2031, 1, 1), freq="YS").to_pydatetime().tolist()
        )

        fuel = fuel_gas_factory(
            ["co2", "ch4", "nmvoc", "nox"], [ltp.co2_factor, ltp.ch4_factor, ltp.nmvoc_factor, ltp.nox_factor]
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
                    datetime(2025, 1, 1): ltp.generator_fuel_energy_function.name,
                    datetime(2027, 1, 1): ltp.power_from_shore_energy_function.name,
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
            ltp.generator_fuel_energy_function.name: generator_electricity2fuel_17MW_resource,
            ltp.power_from_shore_energy_function.name: onshore_power_electricity2fuel_resource,
            max_usage_from_shore_time_series.name: max_usage_from_shore_time_series_resource,
        }

        asset_pfs = (
            YamlAssetBuilder()
            .with_start(time_vector_yearly[0])
            .with_end(time_vector_yearly[-1])
            .with_installations([installation_pfs])
            .with_fuel_types([fuel])
            .with_time_series([max_usage_from_shore_time_series])
            .with_facility_inputs([ltp.generator_fuel_energy_function, ltp.power_from_shore_energy_function])
            .get_yaml_model(resources=resources, frequency=Frequency.YEAR)
        )

        ltp_result = ltp.get_ltp_result(asset_pfs, asset_pfs.variables)
        max_usage_from_shore = ltp.get_ltp_column(
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
