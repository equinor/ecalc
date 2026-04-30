import abc
from collections.abc import Sequence

from libecalc.domain.process.process_pipeline.process_unit import ProcessUnitId
from libecalc.domain.process.process_solver.configuration import Configuration, OperatingConfiguration
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


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
    def reset_to(
        self,
        configurations: Sequence[Configuration] = (),
    ) -> None:
        """Establish a clean starting state for the next evaluation.

        Clears all configuration-handler state on the runner (e.g. shaft speed,
        recirculation rates, choke pressure changes) and then applies the given
        configurations as the new starting point.

        Call this whenever a solver begins a new attempt so that no state from a
        previous run leaks into the next one.
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
