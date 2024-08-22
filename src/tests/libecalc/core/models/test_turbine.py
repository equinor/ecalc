import numpy as np

from libecalc.core.models.turbine import TurbineModel


def test_turbine(turbine: TurbineModel):
    fuel_zero_load = turbine.evaluate(load=np.asarray([0.0])).fuel_rate[0]
    assert fuel_zero_load == 0

    np.testing.assert_allclose(
        actual=turbine.evaluate(load=np.asarray([2.352 / 2, 11.399])).efficiency,
        desired=[0.138 / 2, 0.310],
    )
    np.testing.assert_allclose(
        actual=turbine.evaluate(load=np.asarray([2.352 / 2, 11.399])).fuel_rate,
        desired=[38751.487414187635, 83605.5687606112],
    )
    np.testing.assert_allclose(
        actual=turbine.evaluate(load=np.asarray([2.352 / 2, 11.399]), fuel_lower_heating_value=40).fuel_rate,
        desired=np.asarray([38751.487414187635, 83605.5687606112]) * 38 / 40,
    )

    # make sure that too high load returns is_valid == False
    np.testing.assert_allclose(
        actual=turbine.evaluate(load=np.asarray([0.99, 1, 1.01]) * turbine._maximum_load).is_valid,
        desired=[True, True, False],
    )


def test_turbine_with_power_adjustment_constant(turbine: TurbineModel):
    energy_usage_adjustment_constant = 10
    result_comparison = turbine.evaluate(load=np.asarray([2.352 / 2, 11.399]))

    turbine.data_transfer_object.energy_usage_adjustment_constant = energy_usage_adjustment_constant
    result = turbine.evaluate(load=np.asarray([2.352 / 2, 11.399]))

    np.testing.assert_allclose(np.asarray(result_comparison.load) + energy_usage_adjustment_constant, result.load)


def test_turbine_with_power_adjustment_factor(turbine: TurbineModel):
    energy_usage_adjustment_factor = 0.9
    result_comparison = turbine.evaluate(load=np.asarray([2.352 / 2, 11.399]))

    turbine.data_transfer_object.energy_usage_adjustment_factor = energy_usage_adjustment_factor
    result = turbine.evaluate(load=np.asarray([2.352 / 2, 11.399]))

    np.testing.assert_allclose(np.asarray(result_comparison.load) / energy_usage_adjustment_factor, result.load)
