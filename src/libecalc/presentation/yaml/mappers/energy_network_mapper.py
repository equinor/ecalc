from collections.abc import Sequence

from libecalc.common.variables import ExpressionEvaluator
from libecalc.energy.energy_network_topology import EnergyNetworkTopology
from libecalc.energy.energy_types import DieselRate, ElectricalPower, Energy, FuelGasRate, MechanicalPower
from libecalc.expression.expression import ExpressionType
from libecalc.presentation.yaml.domain.energy import (
    TimeSeriesConsumer,
    TimeSeriesDieselSourceFactory,
    TimeSeriesElectricalBus,
    TimeSeriesElectricalCableFactory,
    TimeSeriesElectricalMotorFactory,
    TimeSeriesElectricalSourceFactory,
    TimeSeriesEnergyUnit,
    TimeSeriesEnergyUnitFactory,
    TimeSeriesFuelGasManifold,
    TimeSeriesFuelGasSourceFactory,
    TimeSeriesGasTurbineFactory,
    TimeSeriesGeneratorSetFactory,
    TimeSeriesJunction,
)
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression
from libecalc.presentation.yaml.yaml_types.energy.yaml_energy_network import (
    YamlComponent,
    YamlDieselConsumer,
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
    YamlMechanicalConsumer,
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
        Sequence[TimeSeriesJunction],
    ]:
        mapped_nodes = [
            *(self._map_source(source, expression_evaluator) for source in yaml_energy_network.sources),
            *(self._map_unit(unit, expression_evaluator) for unit in yaml_energy_network.units),
        ]
        node_ids_by_name = {node.get_name(): node.get_id() for node, _, _ in mapped_nodes}

        connections = [
            (node_ids_by_name[input_name], node_ids_by_name[unit.name])
            for unit in yaml_energy_network.units
            for input_name in self._get_input_names(unit)
        ]
        topology = EnergyNetworkTopology.create(
            node_input_types={node.get_id(): input_type for node, input_type, _ in mapped_nodes},
            node_output_types={node.get_id(): output_type for node, _, output_type in mapped_nodes},
            connections=connections,
        )

        energy_unit_factories = [node for node, _, _ in mapped_nodes if isinstance(node, TimeSeriesEnergyUnitFactory)]
        consumers = [node for node, _, _ in mapped_nodes if isinstance(node, TimeSeriesConsumer)]
        junctions = [node for node, _, _ in mapped_nodes if isinstance(node, TimeSeriesJunction)]
        return topology, energy_unit_factories, consumers, junctions

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
        expression_evaluator: ExpressionEvaluator,
    ) -> tuple[TimeSeriesEnergyUnit, type[Energy] | None, type[Energy] | None]:
        capacity = self._time_series(source.capacity, expression_evaluator)
        match source.type:
            case YamlEnergySourceType.FUEL_GAS_SOURCE:
                return TimeSeriesFuelGasSourceFactory(name=source.name, capacity=capacity), None, FuelGasRate
            case YamlEnergySourceType.ELECTRICAL_SOURCE:
                return TimeSeriesElectricalSourceFactory(name=source.name, capacity=capacity), None, ElectricalPower
            case YamlEnergySourceType.DIESEL_SOURCE:
                return TimeSeriesDieselSourceFactory(name=source.name, capacity=capacity), None, DieselRate

    def _map_unit(
        self,
        unit: YamlComponent,
        expression_evaluator: ExpressionEvaluator,
    ) -> tuple[TimeSeriesEnergyUnit, type[Energy] | None, type[Energy] | None]:
        match unit:
            case YamlGeneratorSet():
                capacity = self._time_series(unit.capacity, expression_evaluator)
                return TimeSeriesGeneratorSetFactory(name=unit.name, capacity=capacity), FuelGasRate, ElectricalPower
            case YamlGasTurbine():
                capacity = self._time_series(unit.capacity, expression_evaluator)
                return TimeSeriesGasTurbineFactory(name=unit.name, capacity=capacity), FuelGasRate, MechanicalPower
            case YamlElectricalMotor():
                capacity = self._time_series(unit.capacity, expression_evaluator)
                efficiency = self._time_series(unit.efficiency, expression_evaluator)
                return (
                    TimeSeriesElectricalMotorFactory(name=unit.name, capacity=capacity, efficiency=efficiency),
                    ElectricalPower,
                    MechanicalPower,
                )
            case YamlElectricalCable():
                capacity = self._time_series(unit.capacity, expression_evaluator)
                # YAML specifies transmission efficiency, but the domain models loss.
                loss_expression = f"1 {{-}} ({unit.efficiency})" if unit.efficiency is not None else None
                loss_fraction = self._time_series(loss_expression, expression_evaluator)
                return (
                    TimeSeriesElectricalCableFactory(name=unit.name, capacity=capacity, loss_fraction=loss_fraction),
                    ElectricalPower,
                    ElectricalPower,
                )
            case YamlElectricalBus():
                return TimeSeriesElectricalBus(name=unit.name), ElectricalPower, ElectricalPower
            case YamlFuelGasManifold():
                return TimeSeriesFuelGasManifold(name=unit.name), FuelGasRate, FuelGasRate
            case YamlElectricalConsumer():
                energy_type = ElectricalPower
                expression = self._time_series(unit.load, expression_evaluator)
                consumer = TimeSeriesConsumer.from_expression(
                    name=unit.name, expression=expression, energy_type=energy_type
                )
                return consumer, energy_type, None
            case YamlMechanicalConsumer():
                energy_type = MechanicalPower
                if unit.process_simulation is not None:
                    consumer = TimeSeriesConsumer.from_process_simulation(name=unit.name, energy_type=energy_type)
                else:
                    expression = self._time_series(unit.load, expression_evaluator)
                    consumer = TimeSeriesConsumer.from_expression(
                        name=unit.name, expression=expression, energy_type=energy_type
                    )
                return consumer, energy_type, None
            case YamlFuelGasConsumer():
                energy_type = FuelGasRate
                expression = self._time_series(unit.rate, expression_evaluator)
                consumer = TimeSeriesConsumer.from_expression(
                    name=unit.name, expression=expression, energy_type=energy_type
                )
                return consumer, energy_type, None
            case YamlDieselConsumer():
                energy_type = DieselRate
                expression = self._time_series(unit.rate, expression_evaluator)
                consumer = TimeSeriesConsumer.from_expression(
                    name=unit.name, expression=expression, energy_type=energy_type
                )
                return consumer, energy_type, None

    @staticmethod
    def _get_input_names(unit: YamlComponent) -> list[str]:
        return unit.input if isinstance(unit.input, list) else [unit.input]
