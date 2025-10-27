import numpy as np


def test_turbine(turbine_factory):
    turbine = turbine_factory()
    fuel_zero_load = turbine.evaluate(load=np.asarray([0.0])).get_energy_result().energy_usage.values[0]
    assert fuel_zero_load == 0

    np.testing.assert_allclose(
        actual=turbine.evaluate(load=np.asarray([2.352 / 2, 11.399])).efficiency,
        desired=[0.138 / 2, 0.310],
    )
    np.testing.assert_allclose(
        actual=turbine.evaluate(load=np.asarray([2.352 / 2, 11.399])).get_energy_result().energy_usage.values,
        desired=[38751.487414187635, 83605.5687606112],
    )
    np.testing.assert_allclose(
        actual=turbine.evaluate(load=np.asarray([2.352 / 2, 11.399]), fuel_lower_heating_value=40)
        .get_energy_result()
        .energy_usage.values,
        desired=np.asarray([38751.487414187635, 83605.5687606112]) * 38 / 40,
    )

    # make sure that too high load returns is_valid == False
    np.testing.assert_allclose(
        actual=turbine.evaluate(load=np.asarray([0.99, 1, 1.01]) * turbine._maximum_load).get_energy_result().is_valid,
        desired=[True, True, False],
    )


def test_turbine_with_power_adjustment_constant(turbine_factory):
    adjustment_constant = 10

    turbine = turbine_factory()
    result_comparison = turbine.evaluate(load=np.asarray([2.352 / 2, 11.399]))

    turbine_adjusted = turbine_factory(energy_usage_adjustment_constant=adjustment_constant)
    result = turbine_adjusted.evaluate(load=np.asarray([2.352 / 2, 11.399]))

    energy_result_comparison = result_comparison.get_energy_result()
    energy_result = result.get_energy_result()

    np.testing.assert_allclose(
        np.asarray(energy_result_comparison.power.values) + adjustment_constant, energy_result.power.values
    )


def test_turbine_with_power_adjustment_factor(turbine_factory):
    # Result without any adjustment:
    turbine = turbine_factory()
    result = turbine.evaluate(load=np.asarray([2.352 / 2, 11.399]))

    # Set adjustment factor
    energy_usage_adjustment_factor = 0.9
    turbine_adjusted = turbine_factory(energy_usage_adjustment_factor=energy_usage_adjustment_factor)

    # Result with adjustment:
    result_adjusted = turbine_adjusted.evaluate(load=np.asarray([2.352 / 2, 11.399]))

    energy_result = result.get_energy_result()
    energy_result_adjusted = result_adjusted.get_energy_result()

    # Compare: linear transformation is used to adjust (y = a*x + b. In this case b=0).
    np.testing.assert_allclose(
        np.asarray(energy_result.power.values) / energy_usage_adjustment_factor, energy_result_adjusted.power.values
    )


def test_turbine_with_power_adjustment_constant_and_factor(turbine_factory):
    # Result without any adjustment:
    turbine = turbine_factory()
    result = turbine.evaluate(load=np.asarray([2.352 / 2, 11.399]))

    # Set adjustment constant and factor
    energy_usage_adjustment_constant = 1
    energy_usage_adjustment_factor = 2
    turbine_adjusted = turbine_factory(
        energy_usage_adjustment_constant=energy_usage_adjustment_constant,
        energy_usage_adjustment_factor=energy_usage_adjustment_factor,
    )

    # Result with adjustment:
    result_adjusted = turbine_adjusted.evaluate(load=np.asarray([2.352 / 2, 11.399]))

    energy_result = result.get_energy_result()
    energy_result_adjusted = result_adjusted.get_energy_result()

    # Compare: linear transformation is used to adjust (y = a*x + b).
    np.testing.assert_allclose(
        (np.asarray(energy_result.power.values) + energy_usage_adjustment_constant) / energy_usage_adjustment_factor,
        energy_result_adjusted.power.values,
    )
