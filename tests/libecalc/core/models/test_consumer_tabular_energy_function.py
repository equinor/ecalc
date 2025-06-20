import numpy as np
import pytest

from libecalc.domain.infrastructure.energy_components.tabulated.tabular_energy_function import Variable


def test_ConsumerTabularEnergyFunction(tabular_consumer_factory):
    variable_name = "Qg"
    variables = {
        variable_name: [
            0.0,
            1.0,
            500000.0,
            1000000.0,
            1500000.0,
            2000000.0,
            2500000.0,
            3000000.0,
            3500000.0,
            4000000.0,
            4500000.0,
            5000000.0,
            5500000.0,
            6000000.0,
            6500000.0,
            6800000.0,
            10000000.0,
        ],
    }
    function_values = [0.0, 1.3, 1.3, 1.3, 1.3, 1.3, 1.3, 1.3, 1.9, 2.5, 3.1, 3.7, 4.3, 4.9, 5.4, 5.8, 5.8]

    tab_1d = tabular_consumer_factory(
        function_values=function_values,
        variables=variables,
    )
    x_input = [Variable(name=variable_name, values=[-1, 0, 3e6, 3.2e6, 3.5e6, 1e8])]
    expected = np.asarray([np.nan, 0, 1.3, 1.54, 1.9, np.nan])
    np.testing.assert_allclose(tab_1d.evaluate_variables(x_input).energy_usage, expected)

    constant = -200
    factor = 1.3
    tab_1d_adjusted = tabular_consumer_factory(
        function_values=function_values,
        variables=variables,
        energy_usage_adjustment_constant=constant,
        energy_usage_adjustment_factor=factor,
    )
    np.testing.assert_allclose(
        tab_1d_adjusted.evaluate_variables(x_input).energy_usage,
        expected * factor + constant,
    )

    variable_headers = ["RATE", "PS", "PD"]
    function_values_3d = np.asarray(
        [
            101007.39,
            105526.99,
            106330.27,
            108684.77,
            105361.67,
            105356.05,
            106723.97,
            111559.59,
            114267.36,
            104969.79,
            104993.52,
            107074.69,
            112847.46,
            109809.4,
            109823.1,
            110334.21,
            115346.82,
            119679.75,
        ]
    )
    variables_3d = {
        variable_headers[0]: [
            2000000.0,
            3000000.0,
            4000000.0,
            5000000.0,
            2000000.0,
            3000000.0,
            4000000.0,
            5000000.0,
            6000000.0,
            2000000.0,
            3000000.0,
            4000000.0,
            5000000.0,
            2000000.0,
            3000000.0,
            4000000.0,
            5000000.0,
            6000000.0,
        ],
        variable_headers[1]: [40, 40, 40, 40, 44, 44, 44, 44, 44, 40, 40, 40, 40, 44, 44, 44, 44, 44],
        variable_headers[2]: [
            220.69,
            209.3,
            193.24,
            157.57,
            249.84,
            238.76,
            225.74,
            203.95,
            156.16,
            242.88,
            230.12,
            215.39,
            187.06,
            274.29,
            262.18,
            249.37,
            231.03,
            190.12,
        ],
    }
    tab_3d = tabular_consumer_factory(
        function_values=function_values_3d,
        variables=variables_3d,
    )

    x_input = [
        Variable(name=variable_headers[0], values=[0, 2e6, 2e6, 2e6]),
        Variable(name=variable_headers[1], values=[0, 40, 40, 40]),
        Variable(name=variable_headers[2], values=[300, 220.69, 230.0, 242.88]),
    ]

    expected = np.asarray([np.nan, 101007.4, 102669.8, 104969.8])
    assert list(tab_3d.evaluate_variables(x_input).energy_usage) == pytest.approx(expected, nan_ok=True)

    tab_3d_adjusted = tabular_consumer_factory(
        function_values=function_values_3d,
        variables=variables_3d,
        energy_usage_adjustment_constant=constant,
        energy_usage_adjustment_factor=factor,
    )
    np.testing.assert_allclose(
        tab_3d_adjusted.evaluate_variables(x_input).energy_usage, expected * factor + constant, rtol=0.01
    )
