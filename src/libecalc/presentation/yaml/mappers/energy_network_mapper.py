from collections.abc import Sequence

from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.common.variables import ExpressionEvaluator
from libecalc.energy.dispatch import DispatchStrategy, PriorityDispatch
from libecalc.energy.energy_network_topology import EnergyNetworkTopology
from libecalc.energy.energy_types import DieselRate, ElectricalPower, Energy, FuelGasRate, MechanicalPower
from libecalc.energy.energy_unit import EnergyUnitId
from libecalc.energy.energy_units import ElectricalBus, FuelGasManifold
from libecalc.energy.errors import InvalidEnergyNetworkInputError
from libecalc.expression.expression import ExpressionType
from libecalc.presentation.yaml.domain.energy import (
    TimeSeriesConsumer,
    TimeSeriesDieselConsumer,
    TimeSeriesDieselSourceFactory,
    TimeSeriesElectricalCableFactory,
    TimeSeriesElectricalConsumer,
    TimeSeriesElectricalMotorFactory,
    TimeSeriesElectricalSourceFactory,
    TimeSeriesEnergyUnit,
    TimeSeriesEnergyUnitFactory,
    TimeSeriesFuelGasConsumer,
    TimeSeriesFuelGasSourceFactory,
    TimeSeriesGasTurbineFactory,
    TimeSeriesGeneratorSetFactory,
    TimeSeriesJunctionFactory,
    TimeSeriesMechanicalConsumer,
)
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression
from libecalc.presentation.yaml.yaml_types.energy.yaml_energy_network import (
    YamlComponent,
    YamlDieselConsumer,
    YamlDispatchStrategy,
    YamlElectricalBus,
    YamlElectricalCable,
    YamlElectricalConsumer,
    YamlElectricalMotor,
    YamlEnergyNetwork,
    YamlEnergySource,
    YamlEnergySourceType,
    YamlFuelGasConsumer,
    YamlFuelGasManifold,
    YamlGasTurbine,
    YamlGeneratorSet,
    YamlJunctionBase,
    YamlMechanicalConsumer,
    get_input_names,
)


class EnergyNetworkMapper:
    def map_energy_network(
        self,
        yaml_energy_network: YamlEnergyNetwork,
        expression_evaluator: ExpressionEvaluator,
    ) -> tuple[
        EnergyNetworkTopology,
        Sequence[TimeSeriesEnergyUnitFactory],
        Sequence[TimeSeriesConsumer],
    ]:
        """Return topology, node factories (including junctions), and consumers.

        References may point to units declared later.
        """
        node_ids_by_name = {
            name: EnergyUnitId(ecalc_id_generator())
            for name in [
                *(source.name for source in yaml_energy_network.sources),
                *(unit.name for unit in yaml_energy_network.units),
            ]
        }
        mapped_nodes = [
            *(
                self._map_source(source, node_ids_by_name, expression_evaluator)
                for source in yaml_energy_network.sources
            ),
            *(self._map_unit(unit, node_ids_by_name, expression_evaluator) for unit in yaml_energy_network.units),
        ]

        connections = [
            (node_ids_by_name[input_name], node_ids_by_name[unit.name])
            for unit in yaml_energy_network.units
            for input_name in get_input_names(unit)
        ]
        topology = EnergyNetworkTopology.create(
            node_input_types={node.get_id(): input_type for node, input_type, _ in mapped_nodes},
            node_output_types={node.get_id(): output_type for node, _, output_type in mapped_nodes},
            connections=connections,
        )

        energy_unit_factories = [node for node, _, _ in mapped_nodes if isinstance(node, TimeSeriesEnergyUnitFactory)]
        consumers = [node for node, _, _ in mapped_nodes if isinstance(node, TimeSeriesConsumer)]
        return topology, energy_unit_factories, consumers

    @staticmethod
    def _time_series(
        expression: ExpressionType | None,
        expression_evaluator: ExpressionEvaluator,
    ) -> TimeSeriesExpression | None:
        if expression is None:
            return None
        return TimeSeriesExpression(expression=expression, expression_evaluator=expression_evaluator)

    def _map_source(
        self,
        source: YamlEnergySource,
        node_ids_by_name: dict[str, EnergyUnitId],
        expression_evaluator: ExpressionEvaluator,
    ) -> tuple[TimeSeriesEnergyUnit, type[Energy] | None, type[Energy] | None]:
        capacity = self._time_series(source.capacity, expression_evaluator)
        energy_unit_id = node_ids_by_name[source.name]
        match source.type:
            case YamlEnergySourceType.FUEL_GAS_SOURCE:
                return (
                    TimeSeriesFuelGasSourceFactory(name=source.name, energy_unit_id=energy_unit_id, capacity=capacity),
                    None,
                    FuelGasRate,
                )
            case YamlEnergySourceType.ELECTRICAL_SOURCE:
                return (
                    TimeSeriesElectricalSourceFactory(
                        name=source.name, energy_unit_id=energy_unit_id, capacity=capacity
                    ),
                    None,
                    ElectricalPower,
                )
            case YamlEnergySourceType.DIESEL_SOURCE:
                return (
                    TimeSeriesDieselSourceFactory(name=source.name, energy_unit_id=energy_unit_id, capacity=capacity),
                    None,
                    DieselRate,
                )

    def _map_unit(
        self,
        unit: YamlComponent,
        node_ids_by_name: dict[str, EnergyUnitId],
        expression_evaluator: ExpressionEvaluator,
    ) -> tuple[TimeSeriesEnergyUnit, type[Energy] | None, type[Energy] | None]:
        energy_unit_id = node_ids_by_name[unit.name]
        match unit:
            case YamlGeneratorSet():
                capacity = self._time_series(unit.capacity, expression_evaluator)
                return (
                    TimeSeriesGeneratorSetFactory(name=unit.name, energy_unit_id=energy_unit_id, capacity=capacity),
                    FuelGasRate,
                    ElectricalPower,
                )
            case YamlGasTurbine():
                capacity = self._time_series(unit.capacity, expression_evaluator)
                return (
                    TimeSeriesGasTurbineFactory(name=unit.name, energy_unit_id=energy_unit_id, capacity=capacity),
                    FuelGasRate,
                    MechanicalPower,
                )
            case YamlElectricalMotor():
                capacity = self._time_series(unit.capacity, expression_evaluator)
                efficiency = self._time_series(unit.efficiency, expression_evaluator)
                return (
                    TimeSeriesElectricalMotorFactory(
                        name=unit.name, energy_unit_id=energy_unit_id, capacity=capacity, efficiency=efficiency
                    ),
                    ElectricalPower,
                    MechanicalPower,
                )
            case YamlElectricalCable():
                capacity = self._time_series(unit.capacity, expression_evaluator)
                # YAML specifies transmission efficiency, but the domain models loss.
                loss_expression = f"1 {{-}} ({unit.efficiency})" if unit.efficiency is not None else None
                loss_fraction = self._time_series(loss_expression, expression_evaluator)
                return (
                    TimeSeriesElectricalCableFactory(
                        name=unit.name, energy_unit_id=energy_unit_id, capacity=capacity, loss_fraction=loss_fraction
                    ),
                    ElectricalPower,
                    ElectricalPower,
                )
            case YamlElectricalBus():
                dispatch_strategy, input_capacities = self._map_junction_inputs(
                    unit, node_ids_by_name, expression_evaluator
                )
                return (
                    TimeSeriesJunctionFactory(
                        name=unit.name,
                        energy_unit_id=energy_unit_id,
                        junction_class=ElectricalBus,
                        dispatch_strategy=dispatch_strategy,
                        input_capacities=input_capacities,
                    ),
                    ElectricalPower,
                    ElectricalPower,
                )
            case YamlFuelGasManifold():
                dispatch_strategy, input_capacities = self._map_junction_inputs(
                    unit, node_ids_by_name, expression_evaluator
                )
                return (
                    TimeSeriesJunctionFactory(
                        name=unit.name,
                        energy_unit_id=energy_unit_id,
                        junction_class=FuelGasManifold,
                        dispatch_strategy=dispatch_strategy,
                        input_capacities=input_capacities,
                    ),
                    FuelGasRate,
                    FuelGasRate,
                )
            case YamlElectricalConsumer():
                demand = self._time_series(unit.load, expression_evaluator)
                return (
                    TimeSeriesElectricalConsumer(name=unit.name, energy_unit_id=energy_unit_id, demand=demand),
                    ElectricalPower,
                    None,
                )
            case YamlMechanicalConsumer():
                demand = self._time_series(unit.load, expression_evaluator)
                return (
                    TimeSeriesMechanicalConsumer(name=unit.name, energy_unit_id=energy_unit_id, demand=demand),
                    MechanicalPower,
                    None,
                )
            case YamlFuelGasConsumer():
                demand = self._time_series(unit.rate, expression_evaluator)
                return (
                    TimeSeriesFuelGasConsumer(name=unit.name, energy_unit_id=energy_unit_id, demand=demand),
                    FuelGasRate,
                    None,
                )
            case YamlDieselConsumer():
                demand = self._time_series(unit.rate, expression_evaluator)
                return (
                    TimeSeriesDieselConsumer(name=unit.name, energy_unit_id=energy_unit_id, demand=demand),
                    DieselRate,
                    None,
                )

    def _map_junction_inputs(
        self,
        junction: YamlJunctionBase,
        node_ids_by_name: dict[str, EnergyUnitId],
        expression_evaluator: ExpressionEvaluator,
    ) -> tuple[DispatchStrategy, dict[EnergyUnitId, TimeSeriesExpression]]:
        inputs = junction.get_inputs()
        input_capacities = {
            node_ids_by_name[junction_input.name]: TimeSeriesExpression(
                expression=junction_input.capacity, expression_evaluator=expression_evaluator
            )
            for junction_input in inputs
            if junction_input.capacity is not None
        }
        # The declared order is the priority; the topology stores connections unordered.
        candidate_ids = tuple(node_ids_by_name[junction_input.name] for junction_input in inputs)
        return self._map_dispatch_strategy(junction, candidate_ids), input_capacities

    @staticmethod
    def _map_dispatch_strategy(
        junction: YamlJunctionBase,
        candidate_ids: tuple[EnergyUnitId, ...],
    ) -> DispatchStrategy:
        match junction.dispatch_strategy:
            case YamlDispatchStrategy.PRIORITY:
                return PriorityDispatch(order=candidate_ids)
            case YamlDispatchStrategy.EQUAL_SPLIT:
                raise InvalidEnergyNetworkInputError(
                    f"'{junction.name}': DISPATCH_STRATEGY {junction.dispatch_strategy} is not supported yet"
                )
