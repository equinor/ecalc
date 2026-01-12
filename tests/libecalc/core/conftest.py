from uuid import uuid4

import pytest

import libecalc.common.energy_usage_type
import libecalc.dto.fuel_type
from libecalc.common.variables import ExpressionEvaluator
from libecalc.domain.infrastructure.energy_components.legacy_consumer.tabulated import TabularConsumerFunction
from libecalc.domain.infrastructure.energy_components.turbine import Turbine
from libecalc.domain.regularity import Regularity
from libecalc.dto.emission import Emission
from libecalc.expression import Expression
from libecalc.presentation.yaml.domain.expression_time_series_variable import ExpressionTimeSeriesVariable
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression
from libecalc.presentation.yaml.yaml_types.models import YamlTurbine
from libecalc.testing.yaml_builder import YamlTurbineBuilder


@pytest.fixture
def fuel_dto() -> libecalc.dto.fuel_type.FuelType:
    return libecalc.dto.fuel_type.FuelType(
        id=uuid4(),
        name="fuel_gas",
        emissions=[
            Emission(
                name="CO2",
                factor=Expression.setup_from_expression(value=1),
            )
        ],
    )


@pytest.fixture
def yaml_turbine() -> YamlTurbine:
    return (
        YamlTurbineBuilder()
        .with_name("compressor_train_turbine")
        .with_turbine_loads([0, 2.352, 4.589, 6.853, 9.125, 11.399, 13.673, 15.947, 18.223, 20.496, 22.767])
        .with_turbine_efficiencies([0, 0.138, 0.210, 0.255, 0.286, 0.310, 0.328, 0.342, 0.353, 0.360, 0.362])
        .with_lower_heating_value(38.0)
        .with_power_adjustment_constant(0.0)
        .with_power_adjustment_factor(1.0)
    ).validate()


@pytest.fixture
def turbine_factory(yaml_turbine):
    def create_turbine(
        loads: list[float] = None,
        lower_heating_value: float = None,
        efficiency_fractions: list[float] = None,
        energy_usage_adjustment_factor: float = None,
        energy_usage_adjustment_constant: float = None,
    ) -> Turbine:
        return Turbine(
            loads=loads if loads is not None else yaml_turbine.turbine_loads,
            lower_heating_value=lower_heating_value
            if lower_heating_value is not None
            else yaml_turbine.lower_heating_value,
            efficiency_fractions=efficiency_fractions
            if efficiency_fractions is not None
            else yaml_turbine.turbine_efficiencies,
            energy_usage_adjustment_constant=energy_usage_adjustment_constant
            if energy_usage_adjustment_constant is not None
            else yaml_turbine.power_adjustment_constant,
            energy_usage_adjustment_factor=energy_usage_adjustment_factor
            if energy_usage_adjustment_factor is not None
            else yaml_turbine.power_adjustment_factor,
        )

    return create_turbine


@pytest.fixture
def tabular_consumer_function_factory():
    def create_tabular_consumer_function(
        function_values: list[float],
        variables: dict[str, list[float]],
        expression_evaluator: ExpressionEvaluator,
        regularity: Regularity | None = None,
        energy_usage_adjustment_constant: float = 0.0,
        energy_usage_adjustment_factor: float = 1.0,
    ) -> TabularConsumerFunction:
        if regularity is None:
            regularity = Regularity(
                expression_evaluator=expression_evaluator,
                target_period=expression_evaluator.get_period(),
                expression_input=1,
            )

        variable_objs = [
            ExpressionTimeSeriesVariable(
                name=name,
                time_series_expression=TimeSeriesExpression(expression=name, expression_evaluator=expression_evaluator),
                regularity=regularity,
            )
            for name in variables.keys()
        ]

        return TabularConsumerFunction(
            headers=[*variables.keys(), "FUEL"],
            data=[*variables.values(), function_values],
            energy_usage_adjustment_factor=energy_usage_adjustment_factor,
            energy_usage_adjustment_constant=energy_usage_adjustment_constant,
            variables=variable_objs,
            power_loss_factor=None,
        )

    return create_tabular_consumer_function
