from datetime import datetime

import pytest

from libecalc.common.time_utils import Period
from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.ecalc_model.input_schedule import InputSchedule
from libecalc.ecalc_model.scheduled_energy_network import ScheduledEnergyNetwork
from libecalc.energy.energy_network_topology import EnergyNetworkTopology
from libecalc.energy.energy_types import ElectricalPower
from libecalc.energy.errors import InvalidEnergyNetworkError
from libecalc.energy.ids import EnergyUnitId

FIRST_YEAR = Period(start=datetime(2020, 1, 1), end=datetime(2021, 1, 1))
SECOND_YEAR = Period(start=datetime(2021, 1, 1), end=datetime(2022, 1, 1))


def _node_id() -> EnergyUnitId:
    return EnergyUnitId(ecalc_id_generator())


def _topology(
    first_candidate: EnergyUnitId,
    second_candidate: EnergyUnitId,
    consumer: EnergyUnitId,
) -> EnergyNetworkTopology:
    return EnergyNetworkTopology.create(
        node_input_types={first_candidate: None, second_candidate: None, consumer: ElectricalPower},
        node_output_types={first_candidate: ElectricalPower, second_candidate: ElectricalPower, consumer: None},
        connections=[(first_candidate, consumer), (second_candidate, consumer)],
        exclusive_input_nodes=[consumer],
    )


class TestScheduledEnergyNetworkValidation:
    def test_rejects_a_missing_schedule_for_an_exclusive_input_node(self):
        first_candidate, second_candidate, consumer = _node_id(), _node_id(), _node_id()
        topology = _topology(first_candidate, second_candidate, consumer)

        with pytest.raises(InvalidEnergyNetworkError, match="Missing input schedules"):
            ScheduledEnergyNetwork(topology=topology, schedules={})

    def test_rejects_a_schedule_for_a_node_that_is_not_exclusive_input(self):
        first_candidate, second_candidate, consumer = _node_id(), _node_id(), _node_id()
        topology = _topology(first_candidate, second_candidate, consumer)

        with pytest.raises(InvalidEnergyNetworkError, match="not exclusive-input nodes"):
            ScheduledEnergyNetwork(
                topology=topology,
                schedules={
                    consumer: InputSchedule(initial=first_candidate, changes=((FIRST_YEAR.start, second_candidate),)),
                    first_candidate: InputSchedule(initial=second_candidate, changes=()),
                },
            )

    def test_rejects_a_schedule_whose_candidates_do_not_match_the_predecessors(self):
        first_candidate, second_candidate, consumer = _node_id(), _node_id(), _node_id()
        topology = _topology(first_candidate, second_candidate, consumer)

        with pytest.raises(InvalidEnergyNetworkError, match="does not exactly match its predecessors"):
            ScheduledEnergyNetwork(
                topology=topology,
                # Missing a change to `second_candidate`: never covers one of the two predecessors.
                schedules={consumer: InputSchedule(initial=first_candidate, changes=())},
            )

    def test_accepts_a_schedule_covering_exactly_the_predecessors(self):
        first_candidate, second_candidate, consumer = _node_id(), _node_id(), _node_id()
        topology = _topology(first_candidate, second_candidate, consumer)

        scheduled_network = ScheduledEnergyNetwork(
            topology=topology,
            schedules={
                consumer: InputSchedule(initial=first_candidate, changes=((SECOND_YEAR.start, second_candidate),))
            },
        )

        assert scheduled_network.active_connections_at(FIRST_YEAR) == {consumer: first_candidate}
        assert scheduled_network.active_connections_at(SECOND_YEAR) == {consumer: second_candidate}


class TestScheduledEnergyNetworkImmutability:
    def test_mutating_the_caller_s_dict_after_construction_does_not_affect_schedules(self):
        first_candidate, second_candidate, consumer = _node_id(), _node_id(), _node_id()
        topology = _topology(first_candidate, second_candidate, consumer)
        schedules = {consumer: InputSchedule(initial=first_candidate, changes=((SECOND_YEAR.start, second_candidate),))}

        scheduled_network = ScheduledEnergyNetwork(topology=topology, schedules=schedules)
        schedules[_node_id()] = InputSchedule(initial=first_candidate, changes=())

        assert set(scheduled_network.schedules) == {consumer}

    def test_schedules_cannot_be_mutated_directly(self):
        first_candidate, second_candidate, consumer = _node_id(), _node_id(), _node_id()
        topology = _topology(first_candidate, second_candidate, consumer)
        scheduled_network = ScheduledEnergyNetwork(
            topology=topology,
            schedules={
                consumer: InputSchedule(initial=first_candidate, changes=((SECOND_YEAR.start, second_candidate),))
            },
        )

        with pytest.raises(TypeError):
            scheduled_network.schedules[consumer] = InputSchedule(initial=second_candidate, changes=())

    def test_is_hashable(self):
        first_candidate, second_candidate, consumer = _node_id(), _node_id(), _node_id()
        topology = _topology(first_candidate, second_candidate, consumer)
        scheduled_network = ScheduledEnergyNetwork(
            topology=topology,
            schedules={
                consumer: InputSchedule(initial=first_candidate, changes=((SECOND_YEAR.start, second_candidate),))
            },
        )

        assert isinstance(hash(scheduled_network), int)
