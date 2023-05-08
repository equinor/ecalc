from libecalc.core.consumers.consumer_system import ConsumerSystem


def test_topologically_sort_consumers_by_crossover():
    unsorted_consumers = [
        "Consumer 1 with no crossover",
        "Consumer 2 with crossover to consumer 3",
        "Consumer 3 with crossover to consumer 1",
    ]

    sorted_consumers = [
        "Consumer 2 with crossover to consumer 3",
        "Consumer 3 with crossover to consumer 1",
        "Consumer 1 with no crossover",
    ]

    assert (
        ConsumerSystem._topologically_sort_consumers_by_crossover(crossover=[0, 3, 1], consumers=unsorted_consumers)
        == sorted_consumers
    )
