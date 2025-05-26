import numpy as np
import pandas as pd

from libecalc.domain.infrastructure.energy_components.generator_set import GeneratorSetModel
from libecalc.presentation.yaml.yaml_entities import MemoryResource


class TestGeneratorModelSampled:
    def test_evaluate(self):
        resource = MemoryResource(
            headers=["POWER", "FUEL"],
            data=[
                [0, 0.1, 5, 10, 15, 20, 21, 21.5, 25, 30],
                [0, 50400, 50400, 76320, 99888, 123480, 129000, 160080, 176640, 199800],
            ],
        )

        el2fuel = GeneratorSetModel(
            name="el2fuel",
            resource=resource,
            energy_usage_adjustment_factor=1,
            energy_usage_adjustment_constant=0,
        )

        x_input = np.asarray([-1, 0, 5, 7, 10, 30, 31])
        expected = np.asarray([0, 0, 50400.0, 60768.0, 76320.0, 199800, 199800])

        result = np.array([el2fuel.evaluate_fuel_usage(value) for value in x_input])
        np.testing.assert_allclose(result, expected)

    def test_capacity_margin(self):
        # Testing the capacity factor when using sampled genset.
        resource = MemoryResource(
            headers=["POWER", "FUEL"],
            data=[[1, 2, 3], [1, 2, 3]],
        )

        el2fuel_function = GeneratorSetModel(
            name="el2fuel",
            resource=resource,
            energy_usage_adjustment_factor=1,
            energy_usage_adjustment_constant=0,
        )
        x_input = np.asarray([0, 1, 2, 3, 4, 5])
        capacity_margin = np.array([el2fuel_function.evaluate_power_capacity_margin(value) for value in x_input])
        np.testing.assert_allclose(capacity_margin, np.asarray([3, 2, 1, 0, -1, -2]))

    def test_energy_adjustment(self):
        # Testing adjustment of energy usage according to factor and constant specified in facility input.

        resource = MemoryResource(
            headers=["POWER", "FUEL"],
            data=[[1, 2, 3], [1, 2, 3]],
        )

        adjustment_factor = 1.5
        adjustment_constant = 0.5

        el2fuel = GeneratorSetModel(
            name="el2fuel",
            resource=resource,
            energy_usage_adjustment_factor=adjustment_factor,
            energy_usage_adjustment_constant=adjustment_constant,
        )

        fuel_values = resource.get_column("FUEL")
        power_values = resource.get_column("POWER")

        expected_adjusted_fuel = list(np.array(fuel_values) * adjustment_factor + adjustment_constant)
        result = np.array([el2fuel.evaluate_fuel_usage(value) for value in np.asarray(power_values)])
        assert result.tolist() == expected_adjusted_fuel
