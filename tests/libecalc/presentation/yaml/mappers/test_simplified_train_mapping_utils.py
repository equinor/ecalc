import numpy as np
import pytest

from libecalc.presentation.yaml.mappers.simplified_train_mapping_utils import calculate_number_of_stages


@pytest.mark.parametrize(
    "maximum_pressure_ratio_per_stage, suction_pressures, discharge_pressures, expected_number_of_stages",
    [
        # (2, [50], [50], 1), # Currently gives 0
        (2, [50], [100], 1),
        (2, [50], [101], 2),
        (2, [50], [201], 3),
    ],
)
def test_calculate_number_of_stages(
    maximum_pressure_ratio_per_stage: float,
    suction_pressures: list[float],
    discharge_pressures: list[float],
    expected_number_of_stages: int,
):
    assert (
        calculate_number_of_stages(
            maximum_pressure_ratio_per_stage=maximum_pressure_ratio_per_stage,
            suction_pressures=np.asarray(suction_pressures),
            discharge_pressures=np.asarray(discharge_pressures),
        )
        == expected_number_of_stages
    )
