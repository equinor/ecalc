import abc

from libecalc.domain.process.process_pipeline.process_unit import ProcessUnitId
from libecalc.domain.process.value_objects.liquid_stream import LiquidStream


class LiquidProcessUnit(abc.ABC):
    """A process unit that operates on a liquid stream.

    Distinct from GasProcessUnit (gas/FluidStream path). Liquid units are incompressible —
    density is constant through the unit, no thermodynamic flash required.

    Current implementations: Pump
    """

    @abc.abstractmethod
    def get_id(self) -> ProcessUnitId: ...

    @abc.abstractmethod
    def propagate_stream(self, inlet_stream: LiquidStream) -> LiquidStream: ...
