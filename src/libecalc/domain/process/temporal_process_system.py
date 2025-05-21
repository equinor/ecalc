import abc

from libecalc.domain.process.process_change_event import ProcessChangedEvent
from libecalc.domain.process.process_system import ProcessSystem, ProcessUnit


class TemporalProcessSystem(abc.ABC):
    @abc.abstractmethod
    def get_process_changed_events(self) -> list[ProcessChangedEvent]: ...

    @abc.abstractmethod
    def get_process_system(self, event: ProcessChangedEvent) -> ProcessSystem | ProcessUnit | None:
        """
        Get the process system that is active from the given event.
        Args:
            event: the process changed event we want a process system from

        Returns: a process system representing the process after the given event

        """
        ...
