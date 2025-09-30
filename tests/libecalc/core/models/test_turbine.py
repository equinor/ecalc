import numpy as np


def test_turbine(turbine_factory):
    turbine = turbine_factory()
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
