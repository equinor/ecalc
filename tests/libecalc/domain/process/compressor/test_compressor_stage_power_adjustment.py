from libecalc.domain.process.compressor.core.results import (
    CompressorTrainResultSingleTimeStep,
    CompressorTrainStageResultSingleTimeStep,
)


def test_stage_power_adjustment_applied_correctly():
    power = [
        [0.0, 1.0],  # stage 1
        [3.0, 4.0],  # stage 2
    ]
    unit_power_adjustment_factor = [
        [1.0, 1.0],  # stage 1
        [2.0, 1.0],  # stage 2
    ]
    unit_power_adjustment_constant = [
        [1.0, 0.0],  # stage 1
        [1.0, 0.0],  # stage 2
    ]

    nr_timesteps = len(power[0])
    nr_stages = len(power)

    results_list = []
    for t in range(nr_timesteps):
        stage_results = [CompressorTrainStageResultSingleTimeStep.create_empty() for _ in range(nr_stages)]
        for s in range(nr_stages):
            stage_results[s].power_megawatt = power[s][t]
        train_result = CompressorTrainResultSingleTimeStep.create_empty(nr_stages)
        train_result.stage_results = stage_results
        results_list.append(train_result)

    _, _, stage_results = CompressorTrainResultSingleTimeStep.from_result_list_to_dto(
        result_list=results_list,
        unit_power_adjustment_factor=unit_power_adjustment_factor,
        unit_power_adjustment_constant=unit_power_adjustment_constant,
        compressor_charts=None,
    )
    # Only power > 0 is adjusted: Check that stage 1 result is unchanged, even with adjustment constant > 0:
    assert stage_results[0].power == [0.0, 1.0]

    # Check that stage 2 result is adjusted correctly - power * factor + constant: 3 *2 + 1 = 7.0 , 4 *1 + 0 = 4.0
    assert stage_results[1].power == [7.0, 4.0]
