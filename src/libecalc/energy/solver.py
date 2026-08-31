from libecalc.common.ddd import value_object
from libecalc.energy.consumer import Consumer
from libecalc.energy.energy_types import Energy
from libecalc.energy.energy_unit import EnergyUnitId
from libecalc.energy.energy_units import Junction
from libecalc.energy.errors import EnergySolverError
from libecalc.energy.network import EnergyNetwork
from libecalc.energy.provider import Converter, Provider, Source


@value_object
class EnergyUnitResult:
    """Calculated energy and capacity status for one energy unit."""

    energy_unit_id: EnergyUnitId
    input_energy: Energy | None
    output_energy: Energy | None
    capacity_exceeded: bool


@value_object
class EnergyNetworkResult:
    """Results from solving an energy network for one operating point."""

    unit_results: tuple[EnergyUnitResult, ...]

    def is_feasible(self) -> bool:
        return not any(result.capacity_exceeded for result in self.unit_results)

    def get_unit_result(
        self,
        unit_id: EnergyUnitId,
    ) -> EnergyUnitResult:
        for unit_result in self.unit_results:
            if unit_result.energy_unit_id == unit_id:
                return unit_result
        raise KeyError(unit_id)


class EnergySolver:
    """Calculates energy through a network for one operating point."""

    def solve(self, network: EnergyNetwork) -> EnergyNetworkResult:
        unit_ids = network.topological_order()
        unit_results_by_id: dict[
            EnergyUnitId,
            EnergyUnitResult,
        ] = {}

        for unit_id in reversed(unit_ids):
            unit = network.get_node(unit_id)
            input_energy: Energy | None = None
            output_energy: Energy | None = None

            if isinstance(unit, Consumer):
                # A consumer defines its own input energy and has no output energy.
                input_energy = unit.get_input_energy()

            elif isinstance(unit, (Provider, Junction)):
                # For a provider or junction, output equals the total input energy of its successors.
                output_energy = self._sum_successor_input_energy(
                    energy_type=unit.get_output_energy_type(),
                    successor_ids=network.successors(unit_id),
                    unit_results_by_id=unit_results_by_id,
                )

                if isinstance(unit, Junction):
                    # A junction passes energy through without conversion.
                    input_energy = output_energy

                elif isinstance(unit, Converter):
                    # A converter derives its input energy from its output energy.
                    input_energy = unit.get_input_energy(output_energy)

                elif isinstance(unit, Source):
                    # A source has no input energy.
                    input_energy = None

            else:
                raise EnergySolverError(f"Unsupported energy unit type: {type(unit).__name__}")

            if input_energy is not None and input_energy.value > 0:
                self._validate_single_predecessor(
                    network=network,
                    unit_id=unit_id,
                )

            capacity_exceeded = (
                isinstance(unit, Provider)
                and output_energy is not None
                and self._is_capacity_exceeded(
                    provider=unit,
                    output_energy=output_energy,
                )
            )

            unit_results_by_id[unit_id] = EnergyUnitResult(
                energy_unit_id=unit_id,
                input_energy=input_energy,
                output_energy=output_energy,
                capacity_exceeded=capacity_exceeded,
            )

        return EnergyNetworkResult(unit_results=tuple(unit_results_by_id[unit_id] for unit_id in unit_ids))

    @staticmethod
    def _sum_successor_input_energy(
        energy_type: type[Energy],
        successor_ids: frozenset[EnergyUnitId],
        unit_results_by_id: dict[EnergyUnitId, EnergyUnitResult],
    ) -> Energy:
        total_successor_input_energy = energy_type(value=0)

        for successor_id in successor_ids:
            successor_input_energy = unit_results_by_id[successor_id].input_energy

            if successor_input_energy is None:
                raise EnergySolverError(f"Energy unit {successor_id} has no input energy")

            total_successor_input_energy += successor_input_energy

        return total_successor_input_energy

    @staticmethod
    def _is_capacity_exceeded(
        provider: Provider,
        output_energy: Energy,
    ) -> bool:
        capacity = provider.capacity()
        return capacity is not None and output_energy.value > capacity.value

    @staticmethod
    def _validate_single_predecessor(
        network: EnergyNetwork,
        unit_id: EnergyUnitId,
    ) -> None:
        predecessors = network.predecessors(unit_id)

        if not predecessors:
            raise EnergySolverError(f"Energy unit {unit_id} has no predecessor")

        if len(predecessors) > 1:
            raise EnergySolverError(
                f"Energy unit {unit_id} cannot be evaluated with multiple predecessors without an allocation strategy"
            )
