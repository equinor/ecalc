from collections.abc import Mapping, Sequence

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.common.variables import ExpressionEvaluator
from libecalc.domain.resource import Resource
from libecalc.energy.dispatch import DispatchStrategy, PriorityDispatch
from libecalc.energy.energy_network_topology import EnergyNetworkTopology
from libecalc.energy.energy_types import DieselRate, ElectricalPower, Energy, FuelGasRate, MechanicalPower
from libecalc.energy.energy_unit import EnergyUnitId
from libecalc.energy.energy_units import ElectricalBus, FuelGasManifold
from libecalc.energy.errors import InvalidEnergyNetworkInputError
from libecalc.expression.expression import ExpressionType
from libecalc.presentation.yaml.domain.energy import (
    CompressorSampledDemand,
    ExpressionDemand,
    TimeSeriesConsumer,
    TimeSeriesDieselSourceFactory,
    TimeSeriesElectricalCableFactory,
    TimeSeriesElectricalMotorFactory,
    TimeSeriesElectricalSourceFactory,
    TimeSeriesEnergyUnit,
    TimeSeriesEnergyUnitFactory,
    TimeSeriesFuelGasSourceFactory,
    TimeSeriesGasTurbineFactory,
    TimeSeriesGeneratorSetFactory,
    TimeSeriesJunctionFactory,
)
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression
from libecalc.presentation.yaml.mappers.energy.compressor_sampled_expansion import (
    ConsumerSpec,
    Expansion,
    NodeKey,
    TurbineSpec,
    expand,
    unit_key,
)
from libecalc.presentation.yaml.yaml_types.energy.yaml_energy_network import (
    OUTPUT_ENERGY,
    SOURCE_OUTPUT_ENERGY,
    EnergyType,
    YamlComponent,
    YamlCompressorSampled,
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

_ENERGY_CLASSES: dict[EnergyType, type[Energy]] = {
    EnergyType.FUEL_GAS: FuelGasRate,
    EnergyType.ELECTRICAL: ElectricalPower,
    EnergyType.MECHANICAL: MechanicalPower,
    EnergyType.DIESEL: DieselRate,
}


class EnergyNetworkMapper:
    def map_energy_network(
        self,
        yaml_energy_network: YamlEnergyNetwork,
        expression_evaluator: ExpressionEvaluator,
        resources: Mapping[str, Resource] | None = None,
    ) -> tuple[
        EnergyNetworkTopology,
        Sequence[TimeSeriesEnergyUnitFactory],
        Sequence[TimeSeriesConsumer],
    ]:
        """Return topology, node factories (including junctions), and consumers.

        References may point to units declared later. A COMPRESSOR_SAMPLED unit expands
        into more than one node: its consumer, and - when its model has a fuel/power
        relation - a turbine generated to feed it. Each of those derived nodes gets its
        own key and id, resolved up front alongside every plain unit's, so forward
        references work the same way regardless of how many nodes a unit becomes.
        """
        resources = resources or {}
        output_types = self._yaml_output_types(yaml_energy_network)

        expansions: dict[str, Expansion] = {
            unit.name: self._expand_sampled_compressor(unit, resources, output_types)
            for unit in yaml_energy_network.units
            if isinstance(unit, YamlCompressorSampled)
        }

        node_ids_by_key: dict[NodeKey, EnergyUnitId] = {
            unit_key(source.name): EnergyUnitId(ecalc_id_generator()) for source in yaml_energy_network.sources
        }
        for unit in yaml_energy_network.units:
            expansion = expansions.get(unit.name)
            keys = [node_spec.key for node_spec in expansion.nodes] if expansion is not None else [unit_key(unit.name)]
            for key in keys:
                node_ids_by_key[key] = EnergyUnitId(ecalc_id_generator())

        mapped_nodes: list[tuple[NodeKey, TimeSeriesEnergyUnit, type[Energy] | None, type[Energy] | None]] = []
        connections: list[tuple[EnergyUnitId, EnergyUnitId]] = []

        for source in yaml_energy_network.sources:
            key = unit_key(source.name)
            node, input_type, output_type = self._map_source(source, node_ids_by_key[key], expression_evaluator)
            mapped_nodes.append((key, node, input_type, output_type))

        for unit in yaml_energy_network.units:
            expansion = expansions.get(unit.name)
            if expansion is not None:
                assert isinstance(unit, YamlCompressorSampled)
                for node_spec in expansion.nodes:
                    node_id = node_ids_by_key[node_spec.key]
                    if isinstance(node_spec, TurbineSpec):
                        node, input_type, output_type = self._map_turbine_spec(node_spec, node_id)
                    else:
                        node, input_type, output_type = self._map_consumer_spec(
                            node_spec, node_id, unit, expression_evaluator
                        )
                    mapped_nodes.append((node_spec.key, node, input_type, output_type))
                connections.extend(
                    (node_ids_by_key[from_key], node_ids_by_key[to_key]) for from_key, to_key in expansion.connections
                )
            else:
                key = unit_key(unit.name)
                node, input_type, output_type = self._map_unit(
                    unit, node_ids_by_key[key], node_ids_by_key, expression_evaluator
                )
                mapped_nodes.append((key, node, input_type, output_type))
                connections.extend(
                    (node_ids_by_key[unit_key(input_name)], node_ids_by_key[key])
                    for input_name in get_input_names(unit)
                )

        topology = EnergyNetworkTopology.create(
            node_input_types={node.get_id(): input_type for _, node, input_type, _ in mapped_nodes},
            node_output_types={node.get_id(): output_type for _, node, _, output_type in mapped_nodes},
            connections=connections,
        )

        energy_unit_factories = [
            node for _, node, _, _ in mapped_nodes if isinstance(node, TimeSeriesEnergyUnitFactory)
        ]
        consumers = [node for _, node, _, _ in mapped_nodes if isinstance(node, TimeSeriesConsumer)]
        return topology, energy_unit_factories, consumers

    @staticmethod
    def _yaml_output_types(yaml_energy_network: YamlEnergyNetwork) -> dict[str, type[Energy]]:
        output_types = {
            source.name: _ENERGY_CLASSES[SOURCE_OUTPUT_ENERGY[source.type]] for source in yaml_energy_network.sources
        }
        output_types.update(
            {
                unit.name: _ENERGY_CLASSES[OUTPUT_ENERGY[unit.type]]
                for unit in yaml_energy_network.units
                if unit.type in OUTPUT_ENERGY
            }
        )
        return output_types

    @staticmethod
    def _expand_sampled_compressor(
        unit: YamlCompressorSampled,
        resources: Mapping[str, Resource],
        output_types: Mapping[str, type[Energy]],
    ) -> Expansion:
        resource = resources.get(unit.file)
        if resource is None:
            raise EcalcValidationException(f"'{unit.name}': FILE '{unit.file}' not found.")
        return expand(unit, resource, output_types[unit.input])

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
        energy_unit_id: EnergyUnitId,
        expression_evaluator: ExpressionEvaluator,
    ) -> tuple[TimeSeriesEnergyUnit, type[Energy] | None, type[Energy] | None]:
        capacity = self._time_series(source.capacity, expression_evaluator)
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

    def _map_consumer_spec(
        self,
        spec: ConsumerSpec,
        energy_unit_id: EnergyUnitId,
        unit: YamlCompressorSampled,
        expression_evaluator: ExpressionEvaluator,
    ) -> tuple[TimeSeriesEnergyUnit, type[Energy] | None, type[Energy] | None]:
        consumer = TimeSeriesConsumer(
            name=spec.name,
            energy_unit_id=energy_unit_id,
            demand=CompressorSampledDemand(
                energy_type=spec.input_energy_type,
                model=spec.model,
                rate=self._time_series(unit.rate, expression_evaluator),
                suction_pressure=self._time_series(unit.suction_pressure, expression_evaluator),
                discharge_pressure=self._time_series(unit.discharge_pressure, expression_evaluator),
            ),
        )
        return consumer, consumer.get_input_energy_type(), None

    @staticmethod
    def _map_turbine_spec(
        spec: TurbineSpec, energy_unit_id: EnergyUnitId
    ) -> tuple[TimeSeriesEnergyUnit, type[Energy] | None, type[Energy] | None]:
        turbine = TimeSeriesGasTurbineFactory(
            name=spec.name, energy_unit_id=energy_unit_id, power_to_fuel=spec.fuel_power_curve.fuel_for_power
        )
        return turbine, FuelGasRate, MechanicalPower

    def _map_unit(
        self,
        unit: YamlComponent,
        energy_unit_id: EnergyUnitId,
        node_ids_by_key: Mapping[NodeKey, EnergyUnitId],
        expression_evaluator: ExpressionEvaluator,
    ) -> tuple[TimeSeriesEnergyUnit, type[Energy] | None, type[Energy] | None]:
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
                    unit, node_ids_by_key, expression_evaluator
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
                    unit, node_ids_by_key, expression_evaluator
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
                expression = self._time_series(unit.load, expression_evaluator)
                consumer = TimeSeriesConsumer(
                    name=unit.name,
                    energy_unit_id=energy_unit_id,
                    demand=ExpressionDemand(energy_type=ElectricalPower, expression=expression),
                )
                return consumer, consumer.get_input_energy_type(), None
            case YamlMechanicalConsumer():
                if unit.process_simulation is not None:
                    raise EcalcValidationException(
                        f"'{unit.name}': PROCESS_SIMULATION-driven demand is not supported yet."
                    )
                expression = self._time_series(unit.load, expression_evaluator)
                consumer = TimeSeriesConsumer(
                    name=unit.name,
                    energy_unit_id=energy_unit_id,
                    demand=ExpressionDemand(energy_type=MechanicalPower, expression=expression),
                )
                return consumer, consumer.get_input_energy_type(), None
            case YamlFuelGasConsumer():
                expression = self._time_series(unit.rate, expression_evaluator)
                consumer = TimeSeriesConsumer(
                    name=unit.name,
                    energy_unit_id=energy_unit_id,
                    demand=ExpressionDemand(energy_type=FuelGasRate, expression=expression),
                )
                return consumer, consumer.get_input_energy_type(), None
            case YamlDieselConsumer():
                expression = self._time_series(unit.rate, expression_evaluator)
                consumer = TimeSeriesConsumer(
                    name=unit.name,
                    energy_unit_id=energy_unit_id,
                    demand=ExpressionDemand(energy_type=DieselRate, expression=expression),
                )
                return consumer, consumer.get_input_energy_type(), None
            case YamlCompressorSampled():
                raise AssertionError("COMPRESSOR_SAMPLED units are expanded, never mapped directly.")

    def _map_junction_inputs(
        self,
        junction: YamlJunctionBase,
        node_ids_by_key: Mapping[NodeKey, EnergyUnitId],
        expression_evaluator: ExpressionEvaluator,
    ) -> tuple[DispatchStrategy, dict[EnergyUnitId, TimeSeriesExpression]]:
        inputs = junction.get_inputs()
        input_capacities = {
            node_ids_by_key[unit_key(junction_input.name)]: TimeSeriesExpression(
                expression=junction_input.capacity, expression_evaluator=expression_evaluator
            )
            for junction_input in inputs
            if junction_input.capacity is not None
        }
        # The declared order is the priority; the topology stores connections unordered.
        candidate_ids = tuple(node_ids_by_key[unit_key(junction_input.name)] for junction_input in inputs)
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
