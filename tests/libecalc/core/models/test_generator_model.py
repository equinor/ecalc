import numpy as np
import pandas as pd

from libecalc.domain.process.generator_set import GeneratorSetProcessUnit


class TestGeneratorModelSampled:
    def test_evaluate(self):
        df = pd.DataFrame(
            [
                [0, 0],
                [0.1, 50400],
                [5, 50400],
                [10, 76320],
                [15, 99888],
                [20, 123480],
                [21, 129000],
                [21.5, 160080],
                [25, 176640],
                [30, 199800],
            ],
            columns=["POWER", "FUEL"],
        )

        headers = df.columns.tolist()
        data = [list(row) for row in zip(*df.values.tolist())]

        el2fuel = GeneratorSetProcessUnit(
            name="el2fuel",
            headers=headers,
            data=data,
            energy_usage_adjustment_factor=1,
            energy_usage_adjustment_constant=0,
        )

        x_input = np.asarray([-1, 0, 5, 7, 10, 30, 31])
        expected = np.asarray([0, 0, 50400.0, 60768.0, 76320.0, 199800, 199800])

        result = np.array([el2fuel.evaluate_fuel_usage(value) for value in x_input])
        np.testing.assert_allclose(result, expected)

    def test_capacity_margin(self):
        # Testing the capacity factor when using sampled genset.
        df = pd.DataFrame(
            {
                "POWER": [1, 2, 3],
                "FUEL": [1, 2, 3],
            }
        )
        headers = df.columns.tolist()
        data = [list(row) for row in zip(*df.values.tolist())]

        el2fuel_function = GeneratorSetProcessUnit(
            name="el2fuel",
            headers=headers,
            data=data,
            energy_usage_adjustment_factor=1,
            energy_usage_adjustment_constant=0,
        )
        x_input = np.asarray([0, 1, 2, 3, 4, 5])
        capacity_margin = np.array([el2fuel_function.evaluate_power_capacity_margin(value) for value in x_input])
        np.testing.assert_allclose(capacity_margin, np.asarray([3, 2, 1, 0, -1, -2]))

    def test_energy_adjustment(self):
        # Testing adjustment of energy usage according to factor and constant specified in facility input.

        df = pd.DataFrame(
            {
                "POWER": [1, 2, 3],
                "FUEL": [1, 2, 3],
            }
        )
        headers = df.columns.tolist()
        data = [list(row) for row in zip(*df.values.tolist())]

        adjustment_factor = 1.5
        adjustment_constant = 0.5

        el2fuel = GeneratorSetProcessUnit(
            name="el2fuel",
            headers=headers,
            data=data,
            energy_usage_adjustment_factor=adjustment_factor,
            energy_usage_adjustment_constant=adjustment_constant,
        )

        fuel_values = df["FUEL"].tolist()
        power_values = df["POWER"].tolist()

        expected_adjusted_fuel = list(np.array(fuel_values) * adjustment_factor + adjustment_constant)
        result = np.array([el2fuel.evaluate_fuel_usage(value) for value in np.asarray(power_values)])
        assert result.tolist() == expected_adjusted_fuel
