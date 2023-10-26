import numpy as np
from libecalc.core.models import ModelInputFailureStatus, validate_model_input


def test_validate_model_input():
    #  test that valid single stream input is not changed
    [
        rate,
        suction_pressure,
        discharge_pressure,
        intermediate_pressure,
        failure_status,
    ] = validate_model_input(
        rate=np.asarray([1000, 1000]),
        suction_pressure=np.asarray([1, 1]),
        intermediate_pressure=np.asarray([2, 2]),
        discharge_pressure=np.asarray([3, 3]),
    )
    assert np.all(rate == 1000)
    assert np.all(suction_pressure == 1)
    assert np.all(intermediate_pressure == 2)
    assert np.all(discharge_pressure == 3)
    assert failure_status == [
        ModelInputFailureStatus.NO_FAILURE,
        ModelInputFailureStatus.NO_FAILURE,
    ]

    #  test that valid multiple stream input is not changed
    [
        rate,
        suction_pressure,
        discharge_pressure,
        intermediate_pressure,
        failure_status,
    ] = validate_model_input(
        rate=np.asarray([[1000, 1000], [1000, 1000]]),
        suction_pressure=np.asarray([1, 1]),
        intermediate_pressure=np.asarray([2, 2]),
        discharge_pressure=np.asarray([3, 3]),
    )
    assert np.all(rate == 1000)
    assert np.all(suction_pressure == 1)
    assert np.all(intermediate_pressure == 2)
    assert np.all(discharge_pressure == 3)
    assert failure_status == [
        ModelInputFailureStatus.NO_FAILURE,
        ModelInputFailureStatus.NO_FAILURE,
    ]

    # test that suction pressure <= 0 is set to 1 and that the corresponding rate is set to 0
    [
        rate,
        suction_pressure,
        discharge_pressure,
        intermediate_pressure,
        failure_status,
    ] = validate_model_input(
        rate=np.asarray([1000, 1000]),
        suction_pressure=np.asarray([-1, 0]),
        intermediate_pressure=np.asarray([2, 2]),
        discharge_pressure=np.asarray([3, 3]),
    )
    assert np.all(rate == 0)
    assert np.all(suction_pressure == 1)
    assert np.all(intermediate_pressure == 2)
    assert np.all(discharge_pressure == 3)
    assert failure_status == [
        ModelInputFailureStatus.INVALID_SUCTION_PRESSURE_INPUT,
        ModelInputFailureStatus.INVALID_SUCTION_PRESSURE_INPUT,
    ]

    # test that discharge pressure <= 0 is set to 1 and that the corresponding rate is set to 0
    [
        rate,
        suction_pressure,
        discharge_pressure,
        intermediate_pressure,
        failure_status,
    ] = validate_model_input(
        rate=np.asarray([1000, 1000]),
        suction_pressure=np.asarray([1, 1]),
        intermediate_pressure=np.asarray([2, 2]),
        discharge_pressure=np.asarray([-1, 0]),
    )
    assert np.all(rate == 0)
    assert np.all(suction_pressure == 1)
    assert np.all(intermediate_pressure == 2)
    assert np.all(discharge_pressure == 1)
    assert failure_status == [
        ModelInputFailureStatus.INVALID_DISCHARGE_PRESSURE_INPUT,
        ModelInputFailureStatus.INVALID_DISCHARGE_PRESSURE_INPUT,
    ]

    # test that intermediate prressure <= 0 is set to 1 and that the corresponding rate is set to 0
    [
        rate,
        suction_pressure,
        discharge_pressure,
        intermediate_pressure,
        failure_status,
    ] = validate_model_input(
        rate=np.asarray([1000, 1000]),
        suction_pressure=np.asarray([1, 1]),
        intermediate_pressure=np.asarray([-1, 0]),
        discharge_pressure=np.asarray([3, 3]),
    )
    assert np.all(rate == 0)
    assert np.all(suction_pressure == 1)
    assert np.all(intermediate_pressure == 1)
    assert np.all(discharge_pressure == 3)
    assert failure_status == [
        ModelInputFailureStatus.INVALID_INTERMEDIATE_PRESSURE_INPUT,
        ModelInputFailureStatus.INVALID_INTERMEDIATE_PRESSURE_INPUT,
    ]

    # test that rate < 0 is set to 0 for multiple stream
    [
        rate,
        suction_pressure,
        discharge_pressure,
        intermediate_pressure,
        failure_status,
    ] = validate_model_input(
        rate=np.asarray([[-1, 1000, 1000], [1000, -1, 1000]]),
        suction_pressure=np.asarray([1, 1, 1]),
        intermediate_pressure=np.asarray([2, 2, 2]),
        discharge_pressure=np.asarray([3, 3, 3]),
    )
    assert np.all(rate[:, 0] == 0)
    assert np.all(rate[:, 1] == 0)
    assert np.all(rate[:, 2] == 1000)
    assert np.all(suction_pressure == 1)
    assert np.all(intermediate_pressure == 2)
    assert np.all(discharge_pressure == 3)
    assert failure_status == [
        ModelInputFailureStatus.INVALID_RATE_INPUT,
        ModelInputFailureStatus.INVALID_RATE_INPUT,
        ModelInputFailureStatus.NO_FAILURE,
    ]
    # test that rate < 0 is set to 0 for single stream
    [
        rate,
        suction_pressure,
        discharge_pressure,
        intermediate_pressure,
        failure_status,
    ] = validate_model_input(
        rate=np.asarray([-1, 1000]),
        suction_pressure=np.asarray([1, 1]),
        intermediate_pressure=np.asarray([2, 2]),
        discharge_pressure=np.asarray([3, 3]),
    )
    assert rate[0] == 0
    assert rate[1] == 1000
    assert np.all(suction_pressure == 1)
    assert np.all(intermediate_pressure == 2)
    assert np.all(discharge_pressure == 3)
    assert failure_status == [
        ModelInputFailureStatus.INVALID_RATE_INPUT,
        ModelInputFailureStatus.NO_FAILURE,
    ]

    # test that suction_pressure, when suction_pressure > discharge_pressure, is set to discharge_pressure,
    # and that rate at the same time is set to 0.
    [
        rate,
        suction_pressure,
        discharge_pressure,
        intermediate_pressure,
        failure_status,
    ] = validate_model_input(
        rate=np.asarray([1000, 1000]),
        suction_pressure=np.asarray([4, 3]),
        intermediate_pressure=np.asarray([2, 2]),
        discharge_pressure=np.asarray([3, 3]),
    )
    assert rate[0] == 0
    assert rate[1] == 1000
    assert suction_pressure[0] == 4
    assert suction_pressure[1] == 3
    assert np.all(intermediate_pressure == 2)
    assert np.all(discharge_pressure == 3)
    assert failure_status == [
        ModelInputFailureStatus.INVALID_SUCTION_PRESSURE_INPUT,
        ModelInputFailureStatus.NO_FAILURE,
    ]
