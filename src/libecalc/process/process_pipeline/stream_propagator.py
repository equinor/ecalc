import abc


class StreamPropagator[TStream](abc.ABC):
    @abc.abstractmethod
    def propagate_stream(self, inlet_stream: TStream) -> TStream: ...
