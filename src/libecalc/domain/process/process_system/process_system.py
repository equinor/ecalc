import abc

from libecalc.domain.process.process_system.stream_propagator import StreamPropagator

PORT_ID = str


class ProcessSystem(StreamPropagator, abc.ABC):
    @abc.abstractmethod
    def get_process_units(self): ...
