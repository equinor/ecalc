from datetime import datetime

import pandas as pd

import libecalc.common.energy_usage_type
import libecalc.dto.fuel_type
import libecalc.dto.types
from libecalc.domain.hydrocarbon_export import HydrocarbonExport
from libecalc.domain.regularity import Regularity
from libecalc.dto.emission import Emission
from libecalc.domain.process import dto
from libecalc.common.component_type import ComponentType
from libecalc.domain.infrastructure.energy_components.asset.asset import Asset
from libecalc.domain.infrastructure.energy_components.installation.installation import Installation
from libecalc.domain.infrastructure.energy_components.fuel_consumer.fuel_consumer import FuelConsumer
from libecalc.application.energy_calculator import EnergyCalculator
from libecalc.application.graph_result import GraphResult
from libecalc.common.time_utils import Period, Periods
from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    TimeSeriesFloat,
    TimeSeriesStreamDayRate,
)
from libecalc.common.variables import VariablesMap
from libecalc.core.result.emission import EmissionResult
from libecalc.expression import Expression
from libecalc.presentation.json_result.aggregators import aggregate_emissions
from libecalc.presentation.json_result.mapper import get_asset_result
from libecalc.presentation.json_result.result.emission import PartialEmissionResult


def get_installation(
    name_inst: str, name_consumer: str, name_fuel: str, co2_factor: float, fuel_rate: float, variables: VariablesMap
) -> Installation:
    """Creates a simple installation object for use in asset setup
    Args:
        name_inst (str): Name of installation
        name_consumer (str): Name of direct fuel consumer
        name_fuel (str): Name of fuel
        co2_factor (float): CO2 factor for emission calculations
        fuel_rate (float): Rate of fuel (Sm3/d)

    Returns:
        components.Installation
    """
    inst = Installation(
        name=name_inst,
        regularity=Regularity.create(expression_evaluator=variables),
        hydrocarbon_export=HydrocarbonExport.create(expression_evaluator=variables),
        fuel_consumers=[
            direct_fuel_consumer(
                name=name_consumer, name_fuel=name_fuel, co2_factor=co2_factor, fuel_rate=fuel_rate, variables=variables
            )
        ],
        expression_evaluator=variables,
    )
    return inst


def fuel(name: str, co2_factor: float) -> libecalc.dto.fuel_type.FuelType:
    """Creates a simple fuel type object for use in fuel consumer setup
    Args:
        name (str): Name of fuel
        co2_factor (str): CO2 factor used for emission calculations

    Returns:
        dto.types.FuelType
    """

    return libecalc.dto.fuel_type.FuelType(
        name=name,
        emissions=[
            Emission(
                name="co2",
                factor=Expression.setup_from_expression(value=co2_factor),
            )
        ],
        user_defined_category=libecalc.dto.types.FuelTypeUserDefinedCategoryType.FUEL_GAS,
    )


def direct_fuel_consumer(
    name: str, name_fuel: str, co2_factor: float, fuel_rate: float, variables: VariablesMap
) -> FuelConsumer:
    """Creates a simple direct fuel consumer object for use in installation setup
    Args:
        name (str): Name of direct fuel consumer
        name_fuel (str): Name of fuel
        co2_factor (float): CO2 factor for emission calculations
        fuel_rate (float): Rate of fuel (Sm3/d)

    Returns:
        components.FuelConsumer
    """

    return FuelConsumer(
        name=name,
        component_type=ComponentType.GENERIC,
        fuel={Period(datetime(2024, 1, 1)): fuel(name=name_fuel, co2_factor=co2_factor)},
        regularity=Regularity.create(expression_input=1),
        user_defined_category={
            Period(datetime(2024, 1, 1)): libecalc.dto.types.ConsumerUserDefinedCategoryType.MISCELLANEOUS
        },
        energy_usage_model={
            Period(datetime(2024, 1, 1)): dto.DirectConsumerFunction(
                fuel_rate=fuel_rate,
                energy_usage_type=libecalc.common.energy_usage_type.EnergyUsageType.FUEL,
            )
        },
        expression_evaluator=variables,
    )


def get_emission_with_only_rate(rates: list[float], name: str):
    timesteps = pd.date_range(datetime(2020, 1, 1), datetime(2023, 1, 1), freq="YS").to_pydatetime().tolist()
    periods = Periods.create_periods(
        times=timesteps,
        include_before=False,
        include_after=False,
    )
    return EmissionResult(
        rate=TimeSeriesStreamDayRate(
            periods=periods,
            values=rates,
            unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
        ),
        periods=periods,
        name=name,
    )


class TestAggregateEmissions:
    def test_aggregate_emissions(self):
        """Test that emissions are aggregated correctly and that order is preserved."""
        timesteps = pd.date_range(datetime(2020, 1, 1), datetime(2023, 1, 1), freq="YS").to_pydatetime().tolist()
        periods = Periods.create_periods(
            times=timesteps,
            include_before=False,
            include_after=False,
        )
        emissions1 = {
            "CO2": PartialEmissionResult.from_emission_core_result(
                get_emission_with_only_rate([1, 2, 3], name="CO2"),
                regularity=TimeSeriesFloat(values=[1.0] * 3, periods=periods, unit=Unit.NONE),
            ),
            "CH4": PartialEmissionResult.from_emission_core_result(
                get_emission_with_only_rate([2, 3, 4], name="CH4"),
                regularity=TimeSeriesFloat(values=[1.0] * 3, periods=periods, unit=Unit.NONE),
            ),
        }
        emissions2 = {
            "CO2:": PartialEmissionResult.from_emission_core_result(
                get_emission_with_only_rate([3, 6, 9], name="CO2"),
                regularity=TimeSeriesFloat(values=[1.0] * 3, periods=periods, unit=Unit.NONE),
            ),
            "CH4": PartialEmissionResult.from_emission_core_result(
                get_emission_with_only_rate([4, 8, 12], name="CH4"),
                regularity=TimeSeriesFloat(values=[1.0] * 3, periods=periods, unit=Unit.NONE),
            ),
        }
        aggregated = aggregate_emissions(
            emissions_lists=[emissions1, emissions2],
        )

        assert aggregated["CO2"].rate.values == [4.0, 8.0, 12.0]
        assert aggregated["CH4"].rate.values == [6.0, 11.0, 16.0]

        aggregated_emission_names = list(aggregated)

        assert aggregated_emission_names[0] == "CO2"
        assert aggregated_emission_names[1] == "CH4"

    def test_aggregate_emissions_installations(self, energy_model_from_dto_factory):
        """Test that emissions are aggregated correctly with multiple installations. Check that all installations
        are not summed for each installation
        """

        time_vector = pd.date_range(datetime(2024, 1, 1), datetime(2025, 1, 1), freq="MS").to_pydatetime().tolist()
        variables = VariablesMap(time_vector=time_vector, variables={"RATE": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]})

        inst_a = get_installation(
            name_inst="INSTA",
            name_consumer="cons1",
            name_fuel="fuel1",
            co2_factor=1,
            fuel_rate=100,
            variables=variables,
        )

        inst_b = get_installation(
            name_inst="INSTB",
            name_consumer="cons2",
            name_fuel="fuel2",
            co2_factor=10,
            fuel_rate=100,
            variables=variables,
        )

        asset = Asset(
            name="Main asset",
            installations=[inst_a, inst_b],
        )

        # generate eCalc results
        energy_calculator = EnergyCalculator(
            energy_model=energy_model_from_dto_factory(asset), expression_evaluator=variables
        )

        consumer_results = energy_calculator.evaluate_energy_usage()
        emission_results = energy_calculator.evaluate_emissions()

        graph_result = GraphResult(
            graph=asset.get_graph(),
            variables_map=variables,
            consumer_results=consumer_results,
            emission_results=emission_results,
        )

        ecalc_result = get_asset_result(graph_result)

        # Extract eCalc results for total asset and for individual installations
        ecalc_asset_emissions = ecalc_result.component_result.emissions["co2"].rate.values

        # Manual aggregation - test two methods, one is correct and one is wrong
        installation_results_correct = []
        installation_results_wrong = []

        for installation in asset.installations:
            aggregated_emissions_correct = aggregate_emissions(
                [
                    {
                        emission_name: PartialEmissionResult.from_emission_core_result(
                            emission,
                            regularity=TimeSeriesFloat(
                                values=[1.0] * len(emission.periods), periods=emission.periods, unit=Unit.NONE
                            ),
                        )
                        for fuel_consumer_id in graph_result.graph.get_successors(installation.id)
                        for emission_name, emission in graph_result.emission_results[fuel_consumer_id].items()
                    }
                ]
            )

            # The method below aggregates all installations for each installation, which is wrong.
            # It was not captured in any test previously.
            aggregated_emissions_wrong = aggregate_emissions(
                [
                    {
                        emission_name: PartialEmissionResult.from_emission_core_result(
                            emission_result=emission_result,
                            regularity=TimeSeriesFloat(
                                values=[1.0] * len(emission_result.periods),
                                periods=emission_result.periods,
                                unit=Unit.NONE,
                            ),
                        )
                        for emission_name, emission_result in emission_results.items()
                    }
                    for consumer_name, emission_results in graph_result.emission_results.items()
                ]
            )

            installation_results_correct.append(aggregated_emissions_correct["co2"].rate.values)
            installation_results_wrong.append(aggregated_emissions_wrong["co2"].rate.values)

        asset_emissions_wrong = [sum(emission) for emission in zip(*installation_results_wrong)]

        asset_emissions_correct = [sum(emission) for emission in zip(*installation_results_correct)]

        # Show that the wrong method aggregate the whole asset for each installation,
        # i.e. the total asset aggregation is doubled with two installations:
        assert ecalc_asset_emissions == [i / 2 for i in asset_emissions_wrong]

        # Show that the correct method (used by eCalc) only aggregates correct:
        assert ecalc_asset_emissions == asset_emissions_correct
