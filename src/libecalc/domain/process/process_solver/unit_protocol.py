from typing import Any, Protocol

from libecalc.domain.process.process_pipeline.process_unit import ProcessUnitId
from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.value_objects.stream_protocol import StreamWithPressure


class RecirculatingUnit(Protocol):
    """Protocol for process units that support recirculation-based capacity control.

    Satisfied by both Compressor (anti-surge) and Pump (minimum-flow bypass).
    Used by IndividualASV strategies to stay decoupled from concrete unit types.
    """

    def get_id(self) -> ProcessUnitId: ...

    @property
    def maximum_flow_rate(self) -> float: ...

    def get_recirculation_range(self, inlet_stream: Any) -> Boundary: ...

    def propagate_stream(self, inlet_stream: Any) -> StreamWithPressure: ...
