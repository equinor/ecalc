from datetime import datetime
from typing import Union

import numpy as np
import pandas as pd
import pytest

from libecalc.application.energy_calculator import EnergyCalculator
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period
from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    TimeSeriesBoolean,
    TimeSeriesFloat,
    TimeSeriesStreamDayRate,
)
from libecalc.common.variables import VariablesMap
from libecalc.core.consumers.generator_set import Genset
from libecalc.core.models.generator import GeneratorModelSampled
from libecalc.core.result.results import GenericComponentResult
from libecalc.dto.types import FuelTypeUserDefinedCategoryType, ConsumerUserDefinedCategoryType
from libecalc.presentation.yaml.yaml_entities import MemoryResource
from libecalc.testing.yaml_builder import (
    YamlGeneratorSetBuilder,
    YamlFuelTypeBuilder,
    YamlEnergyUsageModelDirectBuilder,
    YamlElectricityConsumerBuilder,
    YamlElectricity2fuelBuilder,
)


class GensetTestHelper:
    def __init__(self):
        self.d1900 = datetime(1900, 1, 1)
        self.d2020 = datetime(2020, 1, 1)
        self.d2021 = datetime(2021, 1, 1)
        self.d2022 = datetime(2022, 1, 1)
        self.d2023 = datetime(2023, 1, 1)

        self.p1900 = Period(self.d1900)
        self.p2020 = Period(self.d2020, self.d2021)
        self.p2021 = Period(self.d2021, self.d2022)
        self.p2022 = Period(self.d2022, self.d2023)
        self.p2023 = Period(self.d2023)

    def memory_resource_factory(self, data: list[list[Union[float, int, str]]], headers: list[str]) -> MemoryResource:
        return MemoryResource(
            data=data,
            headers=headers,
        )

    def generator_el2fuel_2mw_resource(self):
        return self.memory_resource_factory(
            data=[[0, 0.5, 1, 2], [0, 0.6, 1, 2]],
            headers=[
                "POWER",
                "FUEL",
            ],
        )

    def generator_fuel_energy_function(self):
        return (
            YamlElectricity2fuelBuilder()
            .with_name("generator_fuel_energy_function")
            .with_file("generator_fuel_energy_function")
        ).validate()

    def fuel(self):
        return (
            YamlFuelTypeBuilder()
            .with_name("fuel_gas")
            .with_category(FuelTypeUserDefinedCategoryType.FUEL_GAS)
            .with_emission_names_and_factors(names=["co2"], factors=[1])
        ).validate()

    def direct_electricity_consumer(self, request):
        energy_usage_model_direct_load_factory = request.getfixturevalue("energy_usage_model_direct_load_factory")
        return (
            YamlElectricityConsumerBuilder()
            .with_name("direct_consumer")
            .with_category({self.d1900: ConsumerUserDefinedCategoryType.FIXED_PRODUCTION_LOAD})
            .with_energy_usage_model(
                {
                    self.d2020: energy_usage_model_direct_load_factory(1),
                    self.d2021: energy_usage_model_direct_load_factory(2),
                    self.d2022: energy_usage_model_direct_load_factory(10),
                    self.d2023: energy_usage_model_direct_load_factory(0),
                }
            )
        ).validate()

    def genset_2mw(self, request):
        return (
            YamlGeneratorSetBuilder()
            .with_name("genset")
            .with_category({self.d1900: "TURBINE-GENERATOR"})
            .with_fuel({self.d1900: self.fuel().name})
            .electricity2fuel(self.generator_fuel_energy_function().name)
            .with_consumers([self.direct_electricity_consumer(request)])
        ).validate()


@pytest.fixture
def genset_test_helper():
    return GensetTestHelper()


class TestGenset:
    def test_genset_out_of_capacity2(self, genset_test_helper, request):
        """Testing a genset at capacity, at zero and above capacity.

        Note that extrapcorrection does not have any effect on the Genset itself - but may have an effect on the elconsumer.
        """
        energy_model_from_dto_factory = request.getfixturevalue("energy_model_from_dto_factory")
        time_vector = pd.date_range(datetime(2020, 1, 1), datetime(2026, 1, 1), freq="YS").to_pydatetime().tolist()
        variables = VariablesMap(time_vector=time_vector)
        generator = genset_test_helper.genset_2mw(request)
        energy_calculator = EnergyCalculator(
            energy_model=energy_model_from_dto_factory(generator), expression_evaluator=variables
        )


def test_genset_out_of_capacity(genset_2mw_dto, fuel_dto, energy_model_from_dto_factory):
    """Testing a genset at capacity, at zero and above capacity.

    Note that extrapcorrection does not have any effect on the Genset itself - but may have an effect on the elconsumer.
    """
    time_vector = pd.date_range(datetime(2020, 1, 1), datetime(2026, 1, 1), freq="YS").to_pydatetime().tolist()

    variables = VariablesMap(time_vector=time_vector)
    energy_calculator = EnergyCalculator(
        energy_model=energy_model_from_dto_factory(genset_2mw_dto), expression_evaluator=variables
    )
    consumer_results = energy_calculator.evaluate_energy_usage()

    graph = genset_2mw_dto.get_graph()
    generator_set_result = consumer_results[genset_2mw_dto.id].component_result
    components = [consumer_results[successor].component_result for successor in graph.get_successors(genset_2mw_dto.id)]

    # Note that this discrepancy between power rate and fuel rate will normally not happen, since the el-consumer
    # will also interpolate the same way as the genset does.
    assert generator_set_result.power == TimeSeriesStreamDayRate(
        periods=variables.periods,
        values=[1, 2, 10, 0, 0, 0],
        unit=Unit.MEGA_WATT,
    )
    assert generator_set_result.is_valid == TimeSeriesBoolean(
        periods=variables.periods,
        values=[True, True, False, True, True, True],
        unit=Unit.NONE,
    )
    assert isinstance(components[0], GenericComponentResult)

    emission_results = energy_calculator.evaluate_emissions()

    genset_emissions = emission_results[genset_2mw_dto.id]
    assert genset_emissions["co2"].rate.values == [0.001, 0.002, 0.002, 0, 0, 0]
    assert generator_set_result.periods == variables.periods


def test_genset_with_elconsumer_nan_results(genset_2mw_dto, fuel_dto):
    """Testing what happens when the el-consumers has nan-values in power. -> Genset should not do anything."""
    time_vector = pd.date_range(datetime(2020, 1, 1), datetime(2026, 1, 1), freq="YS").to_pydatetime().tolist()
    genset = Genset(
        id=genset_2mw_dto.id,
        name=genset_2mw_dto.name,
        temporal_generator_set_model=TemporalModel(
            {
                start_time: GeneratorModelSampled(
                    fuel_values=model.fuel_values,
                    power_values=model.power_values,
                    energy_usage_adjustment_constant=model.energy_usage_adjustment_constant,
                    energy_usage_adjustment_factor=model.energy_usage_adjustment_factor,
                )
                for start_time, model in genset_2mw_dto.generator_set_model.items()
            }
        ),
    )
    variables = VariablesMap(time_vector=time_vector)
    results = genset.evaluate(
        expression_evaluator=variables,
        power_requirement=TimeSeriesFloat(
            values=[np.nan, np.nan, 0.5, 0.5, np.nan, np.nan],
            periods=variables.get_periods(),
            unit=Unit.MEGA_WATT,
        ),
    )

    # The Genset is not supposed to handle NaN-values from the el-consumers.
    np.testing.assert_equal(results.power.values, [np.nan, np.nan, 0.5, 0.5, np.nan, np.nan])
    assert results.power.unit == Unit.MEGA_WATT
    assert results.power.periods == variables.periods

    # The resulting fuel rate will be zero and the result is invalid for the NaN periods.
    assert results.energy_usage == TimeSeriesStreamDayRate(
        periods=variables.periods,
        values=[0, 0, 0.6, 0.6, 0.0, 0.0],
        unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
    )
    assert results.is_valid == TimeSeriesBoolean(
        periods=variables.periods,
        values=[False, False, True, True, False, False],
        unit=Unit.NONE,
    )


def test_genset_outside_capacity(genset_2mw_dto, fuel_dto):
    """Testing what happens when the power rate is outside of genset capacity. -> Genset will extrapolate (forward fill)."""
    time_vector = pd.date_range(datetime(2020, 1, 1), datetime(2026, 1, 1), freq="YS").to_pydatetime().tolist()
    genset = Genset(
        id=genset_2mw_dto.id,
        name=genset_2mw_dto.name,
        temporal_generator_set_model=TemporalModel(
            {
                start_time: GeneratorModelSampled(
                    fuel_values=model.fuel_values,
                    power_values=model.power_values,
                    energy_usage_adjustment_constant=model.energy_usage_adjustment_constant,
                    energy_usage_adjustment_factor=model.energy_usage_adjustment_factor,
                )
                for start_time, model in genset_2mw_dto.generator_set_model.items()
            }
        ),
    )
    variables = VariablesMap(time_vector=time_vector)
    results = genset.evaluate(
        expression_evaluator=variables,
        power_requirement=TimeSeriesFloat(
            values=[1, 2, 3, 4, 5, 6],
            periods=variables.get_periods(),
            unit=Unit.MEGA_WATT,
        ),
    )

    # The genset will still report power rate
    assert results.power == TimeSeriesStreamDayRate(
        periods=variables.periods,
        values=[1, 2, 3, 4, 5, 6],
        unit=Unit.MEGA_WATT,
    )

    # But the fuel rate will only be valid for the first step. The rest is extrapolated.
    assert results.energy_usage == TimeSeriesStreamDayRate(
        periods=variables.periods,
        values=[1, 2, 2, 2, 2, 2],
        unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
    )
    assert results.is_valid == TimeSeriesBoolean(
        periods=variables.periods,
        values=[True, True, False, False, False, False],
        unit=Unit.NONE,
    )


def test_genset_late_startup(genset_1000mw_late_startup_dto, fuel_dto, energy_model_from_dto_factory):
    time_vector = pd.date_range(datetime(2020, 1, 1), datetime(2026, 1, 1), freq="YS").to_pydatetime().tolist()
    variables = VariablesMap(time_vector=time_vector)
    energy_calculator = EnergyCalculator(
        energy_model=energy_model_from_dto_factory(genset_1000mw_late_startup_dto), expression_evaluator=variables
    )
    consumer_results = energy_calculator.evaluate_energy_usage()

    graph = genset_1000mw_late_startup_dto.get_graph()
    generator_set_result = consumer_results[genset_1000mw_late_startup_dto.id].component_result
    components = [
        consumer_results[successor].component_result
        for successor in graph.get_successors(genset_1000mw_late_startup_dto.id)
    ]

    assert generator_set_result.power == TimeSeriesStreamDayRate(
        periods=variables.periods,
        values=[1.0, 2.0, 10.0, 0.0, 0.0, 0.0],
        unit=Unit.MEGA_WATT,
    )

    # Note that the genset is not able to deliver the power rate demanded by the el-consumer(s) for the two
    # first time-steps before the genset is activated in 2022.
    assert generator_set_result.energy_usage == TimeSeriesStreamDayRate(
        periods=variables.periods,
        values=[0.0, 0.0, 10.0, 0.0, 0.0, 0.0],
        unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
    )
    assert generator_set_result.is_valid == TimeSeriesBoolean(
        periods=variables.periods,
        values=[False, False, True, True, True, True],
        unit=Unit.NONE,
    )
    np.testing.assert_equal(components[0].power.values, [1.0, 2.0, 10.0, 0.0, 0.0, 0.0])
