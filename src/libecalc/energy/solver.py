from libecalc.common.ddd import value_object
from libecalc.energy.consumer import Consumer
from libecalc.energy.energy_types import Energy
from libecalc.energy.energy_unit import EnergyUnitId
from libecalc.energy.energy_units import Junction
from libecalc.energy.errors import EnergySolverError
from libecalc.energy.network import EnergyNetwork
from libecalc.energy.provider import Converter, Provider


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


class EnergySolver:
    """Calculates energy through a network for one operating point."""

    def solve(self, network: EnergyNetwork) -> EnergyNetworkResult:
        output_energy_by_unit: dict[EnergyUnitId, Energy] = {}
        unit_results_by_id: dict[EnergyUnitId, EnergyUnitResult] = {}

        for unit_id in reversed(network.topological_order()):
            unit = network.get_node(unit_id)
            input_energy: Energy | None = None
            output_energy: Energy | None = None

            if isinstance(unit, Consumer):
                input_energy = unit.get_input_energy()

            elif isinstance(unit, (Provider, Junction)):
                output_energy = self._get_output_energy(
                    unit=unit,
                    unit_id=unit_id,
                    output_energy_by_unit=output_energy_by_unit,
                )
                if isinstance(unit, Junction):
                    input_energy = output_energy
                elif isinstance(unit, Converter):
                    input_energy = unit.get_input_energy(output_energy)
            else:
                raise EnergySolverError(f"Unsupported energy unit type: {type(unit).__name__}")

            capacity_exceeded = (
                isinstance(unit, Provider)
                and output_energy is not None
                and self._is_capacity_exceeded(provider=unit, output_energy=output_energy)
            )

            unit_results_by_id[unit_id] = EnergyUnitResult(
                energy_unit_id=unit_id,
                input_energy=input_energy,
                output_energy=output_energy,
                capacity_exceeded=capacity_exceeded,
            )

            # A unit's input energy contributes to its predecessor's output energy.
            if input_energy is not None and input_energy.value > 0:
                predecessor_id = self._get_single_predecessor_id(
                    network=network,
                    unit_id=unit_id,
                )
                predecessor_output_energy = output_energy_by_unit.get(predecessor_id)

                output_energy_by_unit[predecessor_id] = (
                    input_energy if predecessor_output_energy is None else predecessor_output_energy + input_energy
                )

        return EnergyNetworkResult(
            unit_results=tuple(unit_results_by_id[unit_id] for unit_id in network.topological_order())
        )

    @staticmethod
    def _get_output_energy(
        unit: Provider | Junction,
        unit_id: EnergyUnitId,
        output_energy_by_unit: dict[EnergyUnitId, Energy],
    ) -> Energy:
        output_energy = output_energy_by_unit.get(unit_id)
        if output_energy is not None:
            return output_energy

        return unit.get_output_energy_type()(value=0)

    @staticmethod
    def _is_capacity_exceeded(
        provider: Provider,
        output_energy: Energy,
    ) -> bool:
        capacity = provider.capacity()
        return capacity is not None and output_energy.value > capacity.value

    @staticmethod
    def _get_single_predecessor_id(
        network: EnergyNetwork,
        unit_id: EnergyUnitId,
    ) -> EnergyUnitId:
        predecessors = network.predecessors(unit_id)

        if not predecessors:
            raise EnergySolverError(f"Energy unit {unit_id} has no predecessor")

        if len(predecessors) > 1:
            raise EnergySolverError(
                f"Energy unit {unit_id} cannot be evaluated with multiple predecessors without an allocation strategy"
            )

        (predecessor_id,) = predecessors
        return predecessor_id
