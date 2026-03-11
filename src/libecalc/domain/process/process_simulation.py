from abc import ABC, abstractmethod

from libecalc.domain.process.process_system.process_system import ProcessSystem


class ProcessSimulation(ABC):

    @abstractmethod
    def get_process_systems(self) -> list[ProcessSystem]: ...