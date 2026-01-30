import abc

from libecalc.domain.process.value_objects.fluid_stream import FluidStream

PORT_ID = str


class DriveTrain(abc.ABC):
    @abc.abstractmethod
    def get_minimum_speed(self) -> float: ...

    @abc.abstractmethod
    def get_maximum_speed(self) -> float: ...

    @abc.abstractmethod
    def get_speed(self) -> float: ...

    @abc.abstractmethod
    def set_speed(self, speed: float): ...


class ProcessSystem(abc.ABC):
    @abc.abstractmethod
    def get_drive_train(self) -> DriveTrain: ...

    @abc.abstractmethod
    def propagate_stream(self, inlet_stream: FluidStream) -> FluidStream: ...
