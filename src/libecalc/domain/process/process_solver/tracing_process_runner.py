from __future__ import annotations

from libecalc.domain.process.process_solver.event_service import ConfigurationAppliedEvent, EventService
from libecalc.domain.process.process_solver.process_runner import Configuration, ProcessRunner, SimulationUnitId
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class TracingProcessRunner(ProcessRunner):
    """A ``ProcessRunner`` wrapper that publishes a
    :class:`ConfigurationAppliedEvent` to an :class:`EventService` each time
    a configuration is applied.

    All ``run()`` calls are forwarded transparently to the inner runner.

    Example::

        events = EventService()
        inner = ProcessSystemRunner(units=..., shaft=...)
        tracer = TracingProcessRunner(inner, events)
        solver = OutletPressureSolver(..., runner=tracer, ...)
        solution = solver.find_asv_solution(...)

        for event in events.get_events():
            print(event)
    """

    def __init__(self, inner: ProcessRunner, event_service: EventService) -> None:
        self._inner = inner
        self._event_service = event_service

    def apply_configuration(self, configuration: Configuration) -> None:
        self._inner.apply_configuration(configuration)
        self._event_service.publish(ConfigurationAppliedEvent(configuration=configuration))

    def run(self, inlet_stream: FluidStream, to_id: SimulationUnitId | None = None) -> FluidStream:
        return self._inner.run(inlet_stream=inlet_stream, to_id=to_id)
