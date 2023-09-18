import numpy as np
import pytest
from libecalc.core.consumers.consumer_system import ConsumerSystem


class TestCrossover:
    parameterized_crossover_rates = [
        ([], [], [], []),  # All empty
        ([4, 4], [[2, 2], [2, 2]], [0, 0], [[2, 2], [2, 2]]),  # All rates within capacity
        ([4, 4], [[3, 3], [1, 1]], [0, 0], [[3, 3], [1, 1]]),  # All rates within capacity
        (  # Exceeds capacity, cross over required
            [4, 4],  # 4 for both timesteps
            [[4, 4], [1, 1]],  # 4 in rate + 1 crossover, 1 exceeding
            [1, 1],  # 1 exceeding
            [[4, 4], [0, 0]],  # we have capacity for first stream, but not 2nd stream
        ),
        (  # Exceeds capacity, cross over required
            [4, 4],  # 4 for both timesteps
            [[5, 5]],  # 4 in rate
            [1, 1],  # 1 exceeding
            [[4, 4]],
        ),
        (  # Exceeds capacity two times, cross over required
            [4, 4],  # 4 for both timesteps
            [[5, 5], [2, 2]],  # 4 in rate
            [3, 3],  # 1 exceeding
            [[4, 4], [0, 0]],
        ),
        (  # Exceeds capacity two times, cross over required
            [4, 4],  # 4 for both timesteps
            [[5, 5], [0, 0]],  # 4 in rate
            [1, 1],  # 1 exceeding
            [[4, 4], [0, 0]],
        ),
        (  # Exceeds capacity three times, cross over required
            [2, 2],  # 4 for both timesteps
            [[3, 3], [1, 1], [1, 1]],
            [3, 3],  # 1 exceeding
            [[2, 2], [0, 0], [0, 0]],
        ),
        (  # Under capacity
            [4, 4],  # 4 for both timesteps
            [[2, 2], [1, 1]],  # 3 in rate, below 4
            [0, 0],
            [[2, 2], [1, 1]],
        ),
    ]

    @pytest.mark.parametrize(
        "max_rate, rates, expected_crossover_rate, expected_rates_within_capacity",
        parameterized_crossover_rates,
    )
    def test_get_crossover_rates(
        self,
        max_rate,
        rates,
        expected_crossover_rate,
        expected_rates_within_capacity,
    ):
        crossover_rate, rates_within_capacity = ConsumerSystem._get_crossover_rates(max_rate, rates)
        assert np.array_equal(crossover_rate, expected_crossover_rate)
        assert np.array_equal(rates_within_capacity, expected_rates_within_capacity)
