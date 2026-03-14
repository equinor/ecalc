from libecalc.domain.process.entities.process_units.recirculation_loop import RecirculationLoop
from libecalc.domain.process.process_solver.anti_surge.anti_surge_strategy import AntiSurgeStrategy
from libecalc.domain.process.process_system.process_unit import ProcessUnit
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class IndividualASVAntiSurgeStrategy(AntiSurgeStrategy):
    """Anti-surge strategy for INDIVIDUAL ASV topology (one recirculation loop per stage).

    Propagates stage-by-stage through the propagation_chain, setting each
    RecirculationLoop's recirculation to the minimum feasible value based on that
    loop's actual inlet stream, and returns the final outlet stream.

    Non-RecirculationLoop items in the chain (conditioning units, PressureTarget
    pass-throughs, etc.) are propagated straight through without any recirculation
    control.

    Contract:
      - Mutates each RecirculationLoop by setting its recirculation rate.
      - Returns the outlet stream after the full chain has been propagated with
        minimum feasible recirculation on each loop.
    """

    def __init__(
        self,
        propagation_chain: list[ProcessUnit | RecirculationLoop],
        recirculation_loops: list[RecirculationLoop],
    ):
        self._propagation_chain = propagation_chain
        self._recirculation_loops = recirculation_loops

    def reset(self) -> None:
        for loop in self._recirculation_loops:
            loop.set_recirculation_rate(0.0)

    def apply(self, inlet_stream: FluidStream) -> FluidStream:
        current_stream = inlet_stream
        for item in self._propagation_chain:
            if isinstance(item, RecirculationLoop):
                boundary = item.get_recirculation_range(inlet_stream=current_stream)
                item.set_recirculation_rate(boundary.min)
            current_stream = item.propagate_stream(inlet_stream=current_stream)
        return current_stream
