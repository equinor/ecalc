import abc

from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_system.process_unit import ProcessUnitId
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class PressureRatioUnit(abc.ABC):
    """A process unit evaluated at a given pressure ratio rather than a shaft speed.

    Distinct from ProcessUnit (StreamPropagator) — there is no shaft, no speed,
    and propagate_stream() is not part of the contract. The operating point is
    fully determined by inlet conditions and the target pressure ratio.
    """

    @abc.abstractmethod
    def get_id(self) -> ProcessUnitId: ...

    @abc.abstractmethod
    def propagate_stream_at_pressure_ratio(
        self,
        inlet_stream: FluidStream,
        pressure_ratio: float,
    ) -> FluidStream: ...

    @abc.abstractmethod
    def get_recirculation_range_at_pressure_ratio(
        self,
        inlet_stream: FluidStream,
        pressure_ratio: float,
    ) -> Boundary: ...
