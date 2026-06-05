import abc
from collections.abc import Sequence

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_pipeline.process_unit import ProcessUnitId
from libecalc.process.process_solver.configuration import (
    Configuration,
    ConfigurationHandlerId,
    OperatingConfiguration,
)


class ProcessRunner(abc.ABC):
    @abc.abstractmethod
    def apply_configuration(self, configuration: Configuration[OperatingConfiguration]):
        """Apply the given configuration to the process system."""
        ...

    def apply_configurations(self, configurations: Sequence[Configuration[OperatingConfiguration]]):
        """Apply the given configurations to the process system."""
        for configuration in configurations:
            self.apply_configuration(configuration)

    @abc.abstractmethod
    def reset_configuration_handler(self, handler_id: ConfigurationHandlerId) -> None:
        """Reset a single configuration handler to its default state.

        The default state is owned by the handler itself; this only dispatches to it.
        The caller (a strategy) decides which handler to reset and when, so no state
        from a previous evaluation leaks into the next one.
        """
        ...

    @abc.abstractmethod
    def run(self, inlet_stream: FluidStream, to_id: ProcessUnitId | None = None) -> FluidStream:
        """
        Simulate the process
        Args:
            inlet_stream: inlet stream to the process.
            to_id: If provided, simulates the process up to, not including, the specified simulation unit id. If None, simulates the entire process.

        Returns: The outlet stream

        """
        ...
