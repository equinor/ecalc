from datetime import datetime
from typing import List

import pandas as pd

from libecalc import dto
from libecalc.application.energy_calculator import EnergyCalculator
from libecalc.application.graph_result import GraphResult
from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    TimeSeriesFloat,
    TimeSeriesStreamDayRate,
)
from libecalc.core.result.emission import EmissionResult
from libecalc.expression import Expression
from libecalc.presentation.json_result.aggregators import aggregate_emissions
from libecalc.presentation.json_result.mapper import get_asset_result
from libecalc.presentation.json_result.result.emission import PartialEmissionResult


def get_installation(
    name_inst: str, name_consumer: str, name_fuel: str, co2_factor: float, fuel_rate: float
) -> dto.Installation:
    """Creates a simple installation object for use in asset setup
    Args:
        name_inst (str): Name of installation
        name_consumer (str): Name of direct fuel consumer
        name_fuel (str): Name of fuel
        co2_factor (float): CO2 factor for emission calculations
        fuel_rate (float): Rate of fuel (Sm3/d)

    Returns:
        dto.Installation
    """

    inst = dto.Installation(
        name=name_inst,
        regularity={datetime(1900, 1, 1): Expression.setup_from_expression(1)},
        hydrocarbon_export={datetime(1900, 1, 1): Expression.setup_from_expression(1)},
        fuel_consumers=[
            direct_fuel_consumer(name=name_consumer, name_fuel=name_fuel, co2_factor=co2_factor, fuel_rate=fuel_rate)
        ],
    )
    return inst


def fuel(name: str, co2_factor: float) -> dto.types.FuelType:
    """Creates a simple fuel type object for use in fuel consumer setup
    Args:
        name (str): Name of fuel
        co2_factor (str): CO2 factor used for emission calculations

    Returns:
        dto.types.FuelType
    """

    return dto.types.FuelType(
        name=name,
        emissions=[
            dto.Emission(
                name="co2",
                factor=Expression.setup_from_expression(value=co2_factor),
            )
        ],
        user_defined_category=dto.types.FuelTypeUserDefinedCategoryType.FUEL_GAS,
    )


def direct_fuel_consumer(name: str, name_fuel: str, co2_factor: float, fuel_rate: float) -> dto.FuelConsumer:
    """Creates a simple direct fuel consumer object for use in installation setup
    Args:
        name (str): Name of direct fuel consumer
        name_fuel (str): Name of fuel
        co2_factor (float): CO2 factor for emission calculations
        fuel_rate (float): Rate of fuel (Sm3/d)

    Returns:
        dto.FuelConsumer
    """

    return dto.FuelConsumer(
        name=name,
        component_type=dto.components.ComponentType.GENERIC,
        fuel={datetime(2024, 1, 1): fuel(name=name_fuel, co2_factor=co2_factor)},
        regularity={datetime(1900, 1, 1): Expression.setup_from_expression(1)},
        user_defined_category={datetime(2024, 1, 1): dto.components.ConsumerUserDefinedCategoryType.MISCELLANEOUS},
        energy_usage_model={
            datetime(2024, 1, 1): dto.DirectConsumerFunction(
                fuel_rate=fuel_rate,
                energy_usage_type=dto.types.EnergyUsageType.FUEL,
            )
        },
    )


def get_emission_with_only_rate(rates: List[float], name: str):
    timesteps = list(pd.date_range(start="2020-01-01", freq="Y", periods=len(rates)))
    return EmissionResult(
        rate=TimeSeriesStreamDayRate(
            timesteps=timesteps,
            values=rates,
            unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
        ),
        timesteps=timesteps,
        name=name,
    )


class TestAggregateEmissions:
    def test_aggregate_emissions(self):
        """Test that emissions are aggregated correctly and that order is preserved."""
        timesteps = list(pd.date_range(start="2020-01-01", freq="Y", periods=3))
        emissions1 = {
            "CO2": PartialEmissionResult.from_emission_core_result(
                get_emission_with_only_rate([1, 2, 3], name="CO2"),
                regularity=TimeSeriesFloat(values=[1.0] * 3, timesteps=timesteps, unit=Unit.NONE),
            ),
            "CH4": PartialEmissionResult.from_emission_core_result(
                get_emission_with_only_rate([2, 3, 4], name="CH4"),
                regularity=TimeSeriesFloat(values=[1.0] * 3, timesteps=timesteps, unit=Unit.NONE),
            ),
        }
        emissions2 = {
            "CO2:": PartialEmissionResult.from_emission_core_result(
                get_emission_with_only_rate([3, 6, 9], name="CO2"),
                regularity=TimeSeriesFloat(values=[1.0] * 3, timesteps=timesteps, unit=Unit.NONE),
            ),
            "CH4": PartialEmissionResult.from_emission_core_result(
                get_emission_with_only_rate([4, 8, 12], name="CH4"),
                regularity=TimeSeriesFloat(values=[1.0] * 3, timesteps=timesteps, unit=Unit.NONE),
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

    def test_aggregate_emissions_installations(self):
        """Test that emissions are aggregated correctly with multiple installations. Check that all installations
        are not summed for each installation
        """

        time_vector = pd.date_range(datetime(2024, 1, 1), datetime(2025, 1, 1), freq="M").to_pydatetime().tolist()
        variables = dto.VariablesMap(time_vector=time_vector, variables={"RATE": [1, 1, 1, 1, 1, 1]})

        inst_a = get_installation(
            name_inst="INSTA", name_consumer="cons1", name_fuel="fuel1", co2_factor=1, fuel_rate=100
        )

        inst_b = get_installation(
            name_inst="INSTB", name_consumer="cons2", name_fuel="fuel2", co2_factor=10, fuel_rate=100
        )

        asset = dto.Asset(
            name="Main asset",
            installations=[inst_a, inst_b],
        )

        # generate eCalc results
        graph = asset.get_graph()
        energy_calculator = EnergyCalculator(graph=graph)

        consumer_results = energy_calculator.evaluate_energy_usage(variables)
        emission_results = energy_calculator.evaluate_emissions(variables, consumer_results)

        graph_result = GraphResult(
            graph=graph,
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
                                values=[1.0] * len(emission.timesteps), timesteps=emission.timesteps, unit=Unit.NONE
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
                                values=[1.0] * len(emission_result.timesteps),
                                timesteps=emission_result.timesteps,
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
