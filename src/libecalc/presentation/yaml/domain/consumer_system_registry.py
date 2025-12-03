from uuid import UUID

from libecalc.common.errors.exceptions import ProgrammingError
from libecalc.common.time_utils import Period
from libecalc.domain.process.evaluation_input import ConsumerSystemOperationalInput


class ConsumerSystemRegistry:
    def __init__(self):
        self._system_to_component_ids: dict[UUID, list[UUID]] = {}
        self._system_to_consumer_map: dict[UUID, UUID] = {}
        self._system_to_period: dict[UUID, Period] = {}
        self._system_operational_input: dict[UUID, ConsumerSystemOperationalInput] = {}

    def get_consumer_system_to_component_ids(self) -> dict[UUID, list[UUID]]:
        return self._system_to_component_ids

    def get_consumer_system_to_consumer_map(self) -> dict[UUID, UUID]:
        return self._system_to_consumer_map

    def get_consumer_system_to_period_map(self) -> dict[UUID, Period]:
        return self._system_to_period

    def get_consumer_system_operational_input(self) -> dict[UUID, ConsumerSystemOperationalInput]:
        return self._system_operational_input

    def register_consumer_system(self, system_id: UUID, component_ids: list[UUID], consumer_id: UUID):
        self._system_to_component_ids[system_id] = component_ids
        self._system_to_consumer_map[system_id] = consumer_id

    def register_consumer_system_operational_input(
        self, system_id: UUID, operational_input: ConsumerSystemOperationalInput
    ):
        self._system_operational_input[system_id] = operational_input

    def register_consumer_system_period(self, system_id: UUID, period: Period):
        """
        Register the period for a given consumer system.
        """
        self._system_to_period[system_id] = period

    def components_in_system(self, component_ids: list[UUID]) -> bool:
        """
        Returns True if any of the given component_ids are part of any system.
        """
        system_component_ids = {cid for ids in self.get_consumer_system_to_component_ids().values() for cid in ids}
        return all(cid in system_component_ids for cid in component_ids)

    def get_system_id_by_component_ids(self, component_ids: list[UUID]) -> UUID:
        """
        Returns the system ID that contains exactly all the given component IDs.
        """
        component_ids_set = set(component_ids)
        for system_id, ids in self.get_consumer_system_to_component_ids().items():
            if set(ids) == component_ids_set:
                return system_id
        raise ProgrammingError(f"No system found with the given component IDs: {component_ids}")
