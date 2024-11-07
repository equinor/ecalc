from dataclasses import dataclass

import numpy as np

from libecalc.common.string.string_utils import generate_id
from libecalc.core.consumers.consumer_system import ConsumerSystem
from libecalc.core.consumers.legacy_consumer.consumer_function.utils import (
    apply_condition,
)
from libecalc.dto.components import Crossover


@dataclass
class ConsumerMock:
    name: str

    @property
    def id(self):
        return generate_id(self.name)


def test_topologically_sort_consumers_by_crossover():
    unsorted_consumer_names = [
        "Consumer 1 with no crossover",
        "Consumer 2 with crossover to consumer 3",
        "Consumer 3 with crossover to consumer 1",
    ]

    sorted_consumer_names = [
        "Consumer 2 with crossover to consumer 3",
        "Consumer 3 with crossover to consumer 1",
        "Consumer 1 with no crossover",
    ]

    unsorted_consumers = [ConsumerMock(name=name) for name in unsorted_consumer_names]
    sorted_consumers = [ConsumerMock(name=name) for name in sorted_consumer_names]

    assert (
        ConsumerSystem._topologically_sort_consumers_by_crossover(
            crossover=[
                Crossover(
                    from_component_id=generate_id("Consumer 2 with crossover to consumer 3"),
                    to_component_id=generate_id("Consumer 3 with crossover to consumer 1"),
                ),
                Crossover(
                    from_component_id=generate_id("Consumer 3 with crossover to consumer 1"),
                    to_component_id=generate_id("Consumer 1 with no crossover"),
                ),
            ],
            consumers=unsorted_consumers,
        )
        == sorted_consumers
    )


def test_apply_condition() -> None:
    """Test that apply_condition sets elements in 1D array and columns in 2D array to zero"""
    condition = np.asarray([1, 0, 1, 0])
    input_array_1D = np.asarray([10, 10, 10, 10])
    input_array_2D = np.asarray([[10, 10, 10, 10], [10, 10, 10, 10]])

    input_array_1D_after_condition = apply_condition(input_array=input_array_1D, condition=condition)
    input_array_2D_after_condition = apply_condition(input_array=input_array_2D, condition=condition)

    expected_input_array_1D_after_condition = np.asarray([10, 0, 10, 0])
    expected_input_array_2D_after_condition = np.asarray([[10, 0, 10, 0], [10, 0, 10, 0]])

    assert np.array_equal(input_array_1D_after_condition, expected_input_array_1D_after_condition)
    assert np.array_equal(input_array_2D_after_condition, expected_input_array_2D_after_condition)
