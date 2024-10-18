import abc

from libecalc.common.time_utils import Frequency
from libecalc.common.units import Unit
from libecalc.presentation.exporter.aggregators import (
    Aggregator,
    InstallationAggregator,
)
from libecalc.presentation.exporter.appliers import (
    Applier,
    FormatValuesToPrecisionModifier,
    InvertValuesModifier,
)
from libecalc.presentation.exporter.filters import Filter
from libecalc.presentation.exporter.queries import (
    ElectricityGeneratedQuery,
    EmissionQuery,
    FuelQuery,
    MaxUsageFromShoreQuery,
    PowerConsumptionQuery,
    StorageVolumeQuery,
)

"""
Currently we set precision of results to be formatted with 6 decimals
"""
LTP_PRECISION = 6


class ResultConfig(abc.ABC):
    @staticmethod
    @abc.abstractmethod
    def aggregator(frequency: Frequency) -> Aggregator:
        pass

    @staticmethod
    @abc.abstractmethod
    def filter(frequency: Frequency) -> Filter:
        pass


class LTPConfig(ResultConfig):
    """Default configuration for Long Term Prognosis (LTP) TSV Export
    Defines columns and queries to run against the eCalc result data structure, to
    get a cleaner to-the-point dataset customized for LTP.
    """

    @staticmethod
    def filter(frequency: Frequency) -> Filter:
        return Filter(
            aggregator=LTPConfig.aggregator(frequency=frequency),
        )

    @staticmethod
    def aggregator(frequency: Frequency) -> Aggregator:
        return InstallationAggregator(
            frequency=frequency,
            appliers=[
                Applier(
                    name="turbineFuelGasConsumption",
                    title="Fuel Consumption",
                    unit=Unit.STANDARD_CUBIC_METER,
                    query=FuelQuery(
                        installation_category="FIXED",
                        fuel_type_category="FUEL-GAS",
                        consumer_categories=["TURBINE-GENERATOR", "GAS-DRIVEN-COMPRESSOR"],
                    ),
                ),
                Applier(
                    name="flareGasConsumption",
                    title="Flare Gas",
                    unit=Unit.STANDARD_CUBIC_METER,
                    query=FuelQuery(
                        installation_category="FIXED",
                        consumer_categories=["FLARE"],
                    ),
                ),
                Applier(
                    name="engineDieselConsumption",
                    title="Diesel Consumption",
                    unit=Unit.LITRES,
                    query=FuelQuery(
                        installation_category="FIXED",
                        fuel_type_category="DIESEL",
                    ),
                ),
                Applier(
                    name="engineNoCo2TaxDieselConsumption",
                    title="No CO2 Tax Diesel Consumption",
                    unit=Unit.LITRES,
                    query=FuelQuery(
                        installation_category="MOBILE",
                        fuel_type_category="DIESEL",
                    ),
                ),
                Applier(
                    name="boilerFuelGasConsumption",
                    title="Boiler Fuel Consumption",
                    unit=Unit.STANDARD_CUBIC_METER,
                    query=FuelQuery(
                        installation_category="FIXED",
                        consumer_categories=["BOILER"],
                        fuel_type_category="FUEL-GAS",
                    ),
                ),
                Applier(
                    name="boilerDieselConsumption",
                    title="Boiler Diesel Consumption",
                    unit=Unit.LITRES,
                    query=FuelQuery(
                        installation_category="FIXED",
                        consumer_categories=["BOILER"],
                        fuel_type_category="DIESEL",
                    ),
                ),
                Applier(
                    name="heaterFuelGasConsumption",
                    title="Heater Fuel Consumption",
                    unit=Unit.STANDARD_CUBIC_METER,
                    query=FuelQuery(
                        installation_category="FIXED",
                        consumer_categories=["HEATER"],
                        fuel_type_category="FUEL-GAS",
                    ),
                ),
                Applier(
                    name="heaterDieselConsumption",
                    title="Heater Diesel Consumption",
                    unit=Unit.LITRES,
                    query=FuelQuery(
                        installation_category="FIXED",
                        consumer_categories=["HEATER"],
                        fuel_type_category="DIESEL",
                    ),
                ),
                Applier(
                    name="turbineFuelGasCo2Mass",
                    title="CO2 From Fuel Gas",
                    unit=Unit.TONS,
                    query=EmissionQuery(
                        installation_category="FIXED",
                        fuel_type_category="FUEL-GAS",
                        consumer_categories=["TURBINE-GENERATOR", "GAS-DRIVEN-COMPRESSOR"],
                        emission_type="co2",
                    ),
                ),
                Applier(
                    name="flareGasCo2Mass",
                    title="CO2 From Flare",
                    unit=Unit.TONS,
                    query=EmissionQuery(
                        installation_category="FIXED",
                        consumer_categories=["FLARE"],
                        emission_type="co2",
                    ),
                ),
                Applier(
                    name="engineDieselCo2Mass",
                    title="CO2 From Diesel",
                    unit=Unit.TONS,
                    query=EmissionQuery(
                        installation_category="FIXED",
                        fuel_type_category="DIESEL",
                        emission_type="co2",
                    ),
                ),
                Applier(
                    name="engineNoCo2TaxDieselCo2Mass",
                    title="CO2 From Diesel No CO2 Tax",
                    unit=Unit.TONS,
                    query=EmissionQuery(
                        installation_category="MOBILE",
                        fuel_type_category="DIESEL",
                        emission_type="co2",
                    ),
                ),
                Applier(
                    name="boilerFuelGasCo2Mass",
                    title="CO2 From Boiler Fuel Gas",
                    unit=Unit.TONS,
                    query=EmissionQuery(
                        installation_category="FIXED",
                        fuel_type_category="FUEL-GAS",
                        consumer_categories=["BOILER"],
                        emission_type="co2",
                    ),
                ),
                Applier(
                    name="boilerDieselCo2Mass",
                    title="CO2 From Boiler Diesel",
                    unit=Unit.TONS,
                    query=EmissionQuery(
                        installation_category="FIXED",
                        fuel_type_category="DIESEL",
                        consumer_categories=["BOILER"],
                        emission_type="co2",
                    ),
                ),
                Applier(
                    name="heaterFuelGasCo2Mass",
                    title="CO2 From Heater Fuel Gas",
                    unit=Unit.TONS,
                    query=EmissionQuery(
                        installation_category="FIXED",
                        fuel_type_category="FUEL-GAS",
                        consumer_categories=["HEATER"],
                        emission_type="co2",
                    ),
                ),
                Applier(
                    name="heaterDieselCo2Mass",
                    title="CO2 From Heater Diesel",
                    unit=Unit.TONS,
                    query=EmissionQuery(
                        installation_category="FIXED",
                        fuel_type_category="DIESEL",
                        consumer_categories=["HEATER"],
                        emission_type="co2",
                    ),
                ),
                Applier(
                    name="co2VentingMass",
                    title="CO2 From Cold Venting Fugitives",
                    unit=Unit.TONS,
                    query=EmissionQuery(
                        installation_category="FIXED",
                        consumer_categories=["COLD-VENTING-FUGITIVE"],
                        emission_type="co2",
                    ),
                ),
                Applier(
                    name="turbineFuelGasNoxMass",
                    title="NOX From Fuel Gas",
                    unit=Unit.TONS,
                    query=EmissionQuery(
                        installation_category="FIXED",
                        fuel_type_category="FUEL-GAS",
                        consumer_categories=["TURBINE-GENERATOR", "GAS-DRIVEN-COMPRESSOR"],
                        emission_type="nox",
                    ),
                ),
                Applier(
                    name="flareGasNoxMass",
                    title="NOX From Flare",
                    unit=Unit.TONS,
                    query=EmissionQuery(
                        installation_category="FIXED",
                        consumer_categories=["FLARE"],
                        emission_type="nox",
                    ),
                ),
                Applier(
                    name="engineDieselNoxMass",
                    title="NOX From Diesel",
                    unit=Unit.TONS,
                    query=EmissionQuery(
                        installation_category="FIXED",
                        fuel_type_category="DIESEL",
                        emission_type="nox",
                    ),
                ),
                Applier(
                    name="engineNoCo2TaxDieselNoxMass",
                    title="NOX From Diesel",
                    unit=Unit.TONS,
                    query=EmissionQuery(
                        installation_category="MOBILE",
                        fuel_type_category="DIESEL",
                        emission_type="nox",
                    ),
                ),
                Applier(
                    name="boilerFuelGasNoxMass",
                    title="NOX From Boiler Fuel Gas",
                    unit=Unit.TONS,
                    query=EmissionQuery(
                        installation_category="FIXED",
                        fuel_type_category="FUEL-GAS",
                        consumer_categories=["BOILER"],
                        emission_type="nox",
                    ),
                ),
                Applier(
                    name="boilerDieselNoxMass",
                    title="NOX From Boiler Diesel",
                    unit=Unit.TONS,
                    query=EmissionQuery(
                        installation_category="FIXED",
                        fuel_type_category="DIESEL",
                        consumer_categories=["BOILER"],
                        emission_type="nox",
                    ),
                ),
                Applier(
                    name="heaterFuelGasNoxMass",
                    title="NOX From Heater Fuel Gas",
                    unit=Unit.TONS,
                    query=EmissionQuery(
                        installation_category="FIXED",
                        fuel_type_category="FUEL-GAS",
                        consumer_categories=["HEATER"],
                        emission_type="nox",
                    ),
                ),
                Applier(
                    name="heaterDieselNoxMass",
                    title="NOX From Heater Diesel",
                    unit=Unit.TONS,
                    query=EmissionQuery(
                        installation_category="FIXED",
                        fuel_type_category="DIESEL",
                        consumer_categories=["HEATER"],
                        emission_type="nox",
                    ),
                ),
                Applier(
                    name="turbineFuelGasNmvocMass",
                    title="NMVOC From Fuel Gas",
                    unit=Unit.TONS,
                    query=EmissionQuery(
                        installation_category="FIXED",
                        fuel_type_category="FUEL-GAS",
                        consumer_categories=["TURBINE-GENERATOR", "GAS-DRIVEN-COMPRESSOR"],
                        emission_type="nmvoc",
                    ),
                ),
                Applier(
                    name="flareGasNmvocMass",
                    title="NMVOC From Flare",
                    unit=Unit.TONS,
                    query=EmissionQuery(
                        installation_category="FIXED",
                        consumer_categories=["FLARE"],
                        emission_type="nmvoc",
                    ),
                ),
                Applier(
                    name="engineDieselNmvocMass",
                    title="NMVOC From Diesel",
                    unit=Unit.TONS,
                    query=EmissionQuery(
                        installation_category="FIXED",
                        fuel_type_category="DIESEL",
                        emission_type="nmvoc",
                    ),
                ),
                Applier(
                    name="engineNoCo2TaxDieselNmvocMass",
                    title="NMVOC From Diesel",
                    unit=Unit.TONS,
                    query=EmissionQuery(
                        installation_category="MOBILE",
                        fuel_type_category="DIESEL",
                        emission_type="nmvoc",
                    ),
                ),
                Applier(
                    name="boilerFuelGasNmvocMass",
                    title="NMVOC From Boiler Fuel Gas",
                    unit=Unit.TONS,
                    query=EmissionQuery(
                        installation_category="FIXED",
                        fuel_type_category="FUEL-GAS",
                        consumer_categories=["BOILER"],
                        emission_type="nmvoc",
                    ),
                ),
                Applier(
                    name="boilerDieselNmvocMass",
                    title="NMVOC From Boiler Diesel",
                    unit=Unit.TONS,
                    query=EmissionQuery(
                        installation_category="FIXED",
                        fuel_type_category="DIESEL",
                        consumer_categories=["BOILER"],
                        emission_type="nmvoc",
                    ),
                ),
                Applier(
                    name="heaterFuelGasNmvocMass",
                    title="NMVOC From Heater Fuel Gas",
                    unit=Unit.TONS,
                    query=EmissionQuery(
                        installation_category="FIXED",
                        fuel_type_category="FUEL-GAS",
                        consumer_categories=["HEATER"],
                        emission_type="nmvoc",
                    ),
                ),
                Applier(
                    name="heaterDieselNmvocMass",
                    title="NMVOC From Heater Diesel",
                    unit=Unit.TONS,
                    query=EmissionQuery(
                        installation_category="FIXED",
                        fuel_type_category="DIESEL",
                        consumer_categories=["HEATER"],
                        emission_type="nmvoc",
                    ),
                ),
                Applier(
                    name="coldVentAndFugitivesNmvocMass",
                    title="NMVOC From Cold Venting Fugitives",
                    unit=Unit.TONS,
                    query=EmissionQuery(
                        installation_category="FIXED",
                        consumer_categories=["COLD-VENTING-FUGITIVE"],
                        emission_type="nmvoc",
                    ),
                ),
                Applier(
                    name="coldVentAndFugitivesNoCo2TaxNmvocMass",
                    title="NMVOC From Cold Venting Fugitives",
                    unit=Unit.TONS,
                    query=EmissionQuery(
                        installation_category="MOBILE",
                        consumer_categories=["COLD-VENTING-FUGITIVE"],
                        emission_type="nmvoc",
                    ),
                ),
                Applier(
                    name="storageNmvocMass",
                    title="NMVOC From Storage",
                    unit=Unit.TONS,
                    query=EmissionQuery(
                        installation_category="FIXED",
                        consumer_categories=["STORAGE"],
                        emission_type="nmvoc",
                    ),
                ),
                Applier(
                    name="loadingNmvocMass",
                    title="NMVOC From Loading",
                    unit=Unit.TONS,
                    query=EmissionQuery(
                        installation_category="FIXED",
                        consumer_categories=["LOADING"],
                        emission_type="nmvoc",
                    ),
                ),
                Applier(
                    name="turbineFuelGasCh4Mass",
                    title="CH4 From Fuel Gas",
                    unit=Unit.TONS,
                    query=EmissionQuery(
                        installation_category="FIXED",
                        fuel_type_category="FUEL-GAS",
                        consumer_categories=["TURBINE-GENERATOR", "GAS-DRIVEN-COMPRESSOR"],
                        emission_type="ch4",
                    ),
                ),
                Applier(
                    name="flareGasCh4Mass",
                    title="CH4 From Flare",
                    unit=Unit.TONS,
                    query=EmissionQuery(
                        installation_category="FIXED",
                        consumer_categories=["FLARE"],
                        emission_type="ch4",
                    ),
                ),
                Applier(
                    name="engineDieselCh4Mass",
                    title="CH4 From Diesel",
                    unit=Unit.TONS,
                    query=EmissionQuery(
                        installation_category="FIXED",
                        fuel_type_category="DIESEL",
                        emission_type="ch4",
                    ),
                ),
                Applier(
                    name="engineNoCo2TaxDieselCh4Mass",
                    title="CH4 From Diesel No CO2 Tax",
                    unit=Unit.TONS,
                    query=EmissionQuery(
                        installation_category="MOBILE",
                        fuel_type_category="DIESEL",
                        emission_type="ch4",
                    ),
                ),
                Applier(
                    name="boilerFuelGasCh4Mass",
                    title="CH4 From Boiler Fuel Gas",
                    unit=Unit.TONS,
                    query=EmissionQuery(
                        installation_category="FIXED",
                        fuel_type_category="FUEL-GAS",
                        consumer_categories=["BOILER"],
                        emission_type="ch4",
                    ),
                ),
                Applier(
                    name="boilerDieselCh4Mass",
                    title="CH4 From Boiler Diesel",
                    unit=Unit.TONS,
                    query=EmissionQuery(
                        installation_category="FIXED",
                        fuel_type_category="DIESEL",
                        consumer_categories=["BOILER"],
                        emission_type="ch4",
                    ),
                ),
                Applier(
                    name="heaterFuelGasCh4Mass",
                    title="CH4 From Heater Fuel Gas",
                    unit=Unit.TONS,
                    query=EmissionQuery(
                        installation_category="FIXED",
                        fuel_type_category="FUEL-GAS",
                        consumer_categories=["HEATER"],
                        emission_type="ch4",
                    ),
                ),
                Applier(
                    name="heaterDieselCh4Mass",
                    title="CH4 From Heater Diesel",
                    unit=Unit.TONS,
                    query=EmissionQuery(
                        installation_category="FIXED",
                        fuel_type_category="DIESEL",
                        consumer_categories=["HEATER"],
                        emission_type="ch4",
                    ),
                ),
                Applier(
                    name="coldVentAndFugitivesCh4Mass",
                    title="CH4 From Cold Venting Fugitives",
                    unit=Unit.TONS,
                    query=EmissionQuery(
                        installation_category="FIXED",
                        consumer_categories=["COLD-VENTING-FUGITIVE"],
                        emission_type="ch4",
                    ),
                ),
                Applier(
                    name="coldVentAndFugitivesNoCo2TaxCh4Mass",
                    title="CH4 From Cold Venting Fugitives",
                    unit=Unit.TONS,
                    query=EmissionQuery(
                        installation_category="MOBILE",
                        consumer_categories=["COLD-VENTING-FUGITIVE"],
                        emission_type="ch4",
                    ),
                ),
                Applier(
                    name="storageCh4Mass",
                    title="CH4 From Storage",
                    unit=Unit.TONS,
                    query=EmissionQuery(
                        installation_category="FIXED",
                        consumer_categories=["STORAGE"],
                        emission_type="ch4",
                    ),
                ),
                Applier(
                    name="loadingCh4Mass",
                    title="CH4 From Loading",
                    unit=Unit.TONS,
                    query=EmissionQuery(
                        installation_category="FIXED",
                        consumer_categories=["LOADING"],
                        emission_type="ch4",
                    ),
                ),
                Applier(
                    name="loadedAndStoredOil",
                    title="Total Oil Loaded/Stored",
                    unit=Unit.STANDARD_CUBIC_METER,
                    query=FuelQuery(
                        installation_category="FIXED",
                        consumer_categories=["LOADING"],
                    ),
                ),
                Applier(
                    name="loadedAndStoredOil",  # TODO: Get correct Centuries name here
                    title="Total Oil Loaded/Stored",
                    unit=Unit.STANDARD_CUBIC_METER,
                    query=StorageVolumeQuery(
                        installation_category="FIXED",
                        consumer_categories=["LOADING"],
                    ),
                ),
                Applier(
                    name="gasTurbineGeneratorConsumption",
                    title="Total Electricity Generated",
                    unit=Unit.GIGA_WATT_HOURS,
                    query=ElectricityGeneratedQuery(
                        installation_category="FIXED",
                        producer_categories=["TURBINE-GENERATOR"],
                    ),
                ),
                Applier(
                    name="gasTurbineCompressorConsumption",
                    title="Total Power Consumed By Gas-Turbine Driven Compressors",
                    unit=Unit.GIGA_WATT_HOURS,
                    query=PowerConsumptionQuery(
                        installation_category="FIXED",
                        consumer_categories=["GAS-DRIVEN-COMPRESSOR"],
                    ),
                ),
                Applier(
                    name="offshoreWindConsumption",
                    title="Total Electricity Consumed From Offshore Wind",
                    unit=Unit.GIGA_WATT_HOURS,
                    query=PowerConsumptionQuery(
                        installation_category="FIXED",
                        consumer_categories=["OFFSHORE-WIND"],
                    ),
                    modifier=FormatValuesToPrecisionModifier(InvertValuesModifier()),
                ),
                Applier(
                    name="fromShoreConsumption",
                    title="Total Electricity Consumed From Power-From-Shore",
                    unit=Unit.GIGA_WATT_HOURS,
                    query=PowerConsumptionQuery(
                        producer_categories=["POWER-FROM-SHORE"],
                    ),
                ),
                Applier(
                    name="powerSupplyOnshore",
                    title="Power Supply Onshore",
                    unit=Unit.GIGA_WATT_HOURS,
                    query=ElectricityGeneratedQuery(
                        producer_categories=["POWER-FROM-SHORE"],
                    ),
                ),
                Applier(
                    name="fromShorePeakMaximum",
                    title="Max Usage from Shore",
                    unit=Unit.MEGA_WATT,
                    query=MaxUsageFromShoreQuery(
                        producer_categories=["POWER-FROM-SHORE"],
                    ),
                ),
                Applier(
                    name="steamTurbineGeneratorConsumption",
                    title="Total Electricity Consumed From Steam Turbine Generators",
                    unit=Unit.GIGA_WATT_HOURS,
                    query=PowerConsumptionQuery(
                        installation_category="FIXED",
                        consumer_categories=["STEAM-TURBINE-GENERATOR"],
                    ),
                    modifier=FormatValuesToPrecisionModifier(InvertValuesModifier()),
                ),
            ],
        )


class STPConfig(ResultConfig):
    """Default configuration for Short Term Prognosis (STP) TSV Export
    Defines columns and queries to run against the eCalc result data structure, to
    get a cleaner to-the-point dataset customized for STP.
    """

    @staticmethod
    def filter(frequency: Frequency) -> Filter:
        return Filter(
            aggregator=STPConfig.aggregator(frequency=frequency),
        )

    @staticmethod
    def aggregator(frequency: Frequency) -> Aggregator:
        return InstallationAggregator(
            frequency=frequency,
            appliers=[
                Applier(
                    name="co2Emission",
                    title="Total CO2",
                    unit=Unit.TONS,
                    query=EmissionQuery(installation_category="FIXED", emission_type="co2"),
                ),
                Applier(
                    name="co2FromMobileUnits",
                    title="Total CO2",
                    unit=Unit.TONS,
                    query=EmissionQuery(installation_category="MOBILE", emission_type="co2"),
                ),
                Applier(
                    name="methaneEmission",
                    title="Total CH4",
                    unit=Unit.TONS,
                    query=EmissionQuery(
                        installation_category="FIXED",
                        emission_type="ch4",
                    ),
                ),
            ],
        )
