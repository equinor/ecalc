import math
from collections.abc import Callable, Mapping, Sequence
from typing import overload

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.common.variables import ExpressionEvaluator
from libecalc.domain.resource import Resource
from libecalc.energy.dispatch import DispatchStrategy, PriorityDispatch
from libecalc.energy.energy_network_topology import EnergyNetworkTopology
from libecalc.energy.energy_types import DieselRate, ElectricalPower, Energy, FuelGasRate, MechanicalPower
from libecalc.energy.energy_unit import EnergyUnitId
from libecalc.energy.errors import InvalidEnergyNetworkInputError
from libecalc.energy.models.generator_set_fuel_model import GeneratorSetFuelModel
from libecalc.energy.models.turbine_fuel_model import TurbineFuelModel
from libecalc.expression.expression import ExpressionType
from libecalc.presentation.yaml.domain.energy import (
    CompressorSampledDemand,
    ExpressionDemand,
    TimeSeriesConsumer,
    TimeSeriesElectricalCableFactory,
    TimeSeriesElectricalMotorFactory,
    TimeSeriesEnergyUnit,
    TimeSeriesEnergyUnitFactory,
    TimeSeriesGasTurbineFactory,
    TimeSeriesGeneratorSetFactory,
    TimeSeriesJunctionFactory,
    TimeSeriesSourceFactory,
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
from libecalc.presentation.yaml.mappers.energy.generator_set_fuel_model_mapper import map_generator_set_fuel_model
from libecalc.presentation.yaml.mappers.energy.turbine_fuel_model_mapper import map_turbine_fuel_model
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
from libecalc.presentation.yaml.yaml_types.energy.yaml_generator_set_definition import YamlGeneratorSetDefinition
from libecalc.presentation.yaml.yaml_types.energy.yaml_turbine_definition import YamlTurbineDefinition

YamlKeys = tuple[str | int, ...]

_FuelModel = TurbineFuelModel | GeneratorSetFuelModel


class EnergyNetworkValidationError(EcalcValidationException):
    """Invalid energy network input, located at `yaml_keys` in the model YAML."""

    def __init__(self, message: str, yaml_keys: YamlKeys):
        super().__init__(message)
        self.yaml_keys = yaml_keys


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
        turbine_definitions: Mapping[str, YamlTurbineDefinition] | None = None,
        generator_set_definitions: Mapping[str, YamlGeneratorSetDefinition] | None = None,
    ) -> tuple[
        EnergyNetworkTopology,
        Sequence[TimeSeriesEnergyUnitFactory],
        Sequence[TimeSeriesConsumer],
    ]:
        """Return topology, node factories (including junctions), and consumers.

        References may point to units declared later.
        """
        resources = resources or {}
        turbine_models: dict[str, _FuelModel] = {
            name: self._map_definition(
                map_turbine_fuel_model, name, definition, resources, ("DEFINITIONS", "TURBINES", name)
            )
            for name, definition in (turbine_definitions or {}).items()
        }
        generator_set_models: dict[str, _FuelModel] = {
            name: self._map_definition(
                map_generator_set_fuel_model, name, definition, resources, ("DEFINITIONS", "GENERATOR_SETS", name)
            )
            for name, definition in (generator_set_definitions or {}).items()
        }
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

        for index, unit in enumerate(yaml_energy_network.units):
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
                yaml_keys = ("ENERGY_NETWORK", "UNITS", index)
                if isinstance(unit, YamlGasTurbine):
                    node, input_type, output_type = self._map_gas_turbine(
                        unit, node_ids_by_key[key], yaml_keys, turbine_models, resources, expression_evaluator
                    )
                elif isinstance(unit, YamlGeneratorSet):
                    node, input_type, output_type = self._map_generator_set(
                        unit, node_ids_by_key[key], yaml_keys, generator_set_models, resources, expression_evaluator
                    )
                else:
                    node, input_type, output_type = self._map_unit(
                        unit, node_ids_by_key[key], node_ids_by_key, expression_evaluator
                    )
                mapped_nodes.append((key, node, input_type, output_type))
                connections.extend(
                    (node_ids_by_key[unit_key(input_name)], node_ids_by_key[key])
                    for input_name in get_input_names(unit)
                )

        self._check_no_duplicate_generated_names(mapped_nodes)

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
    def _check_no_duplicate_generated_names(
        mapped_nodes: list[tuple[NodeKey, TimeSeriesEnergyUnit, type[Energy] | None, type[Energy] | None]],
    ) -> None:
        seen: set[str] = set()
        duplicates: set[str] = set()
        for _, node, _, _ in mapped_nodes:
            name = node.get_name()
            if name in seen:
                duplicates.add(name)
            seen.add(name)
        if duplicates:
            raise EcalcValidationException(
                f"Duplicate names: {duplicates}. Note that a COMPRESSOR_SAMPLED unit with both FUEL and POWER "
                "samples generates a turbine named '{unit_name} turbine' - this may be an unintended collision "
                "with that generated name rather than a name declared directly in UNITS."
            )

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
    @overload
    def _time_series(
        expression: ExpressionType,
        expression_evaluator: ExpressionEvaluator,
    ) -> TimeSeriesExpression: ...

    @staticmethod
    @overload
    def _time_series(
        expression: None,
        expression_evaluator: ExpressionEvaluator,
    ) -> None: ...

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
                energy_type = FuelGasRate
            case YamlEnergySourceType.ELECTRICAL_SOURCE:
                energy_type = ElectricalPower
            case YamlEnergySourceType.DIESEL_SOURCE:
                energy_type = DieselRate
        return (
            TimeSeriesSourceFactory(name=source.name, energy_unit_id=energy_unit_id, capacity=capacity),
            None,
            energy_type,
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
                demand_source=spec.demand_source,
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

    @staticmethod
    def _map_definition[D](
        mapper: Callable[[str, D, Mapping[str, Resource]], _FuelModel],
        name: str,
        definition: D,
        resources: Mapping[str, Resource],
        yaml_keys: YamlKeys,
    ) -> _FuelModel:
        try:
            return mapper(name, definition, resources)
        except EcalcValidationException as e:
            raise EnergyNetworkValidationError(str(e), yaml_keys) from e

    def _map_gas_turbine(
        self,
        unit: YamlGasTurbine,
        energy_unit_id: EnergyUnitId,
        yaml_keys: YamlKeys,
        turbine_models: Mapping[str, _FuelModel],
        resources: Mapping[str, Resource],
        expression_evaluator: ExpressionEvaluator,
    ) -> tuple[TimeSeriesEnergyUnit, type[Energy] | None, type[Energy] | None]:
        fuel_model, capacity = self._resolve_fuel_model_and_capacity(
            unit,
            yaml_keys,
            turbine_models,
            map_turbine_fuel_model,
            "TURBINES",
            "turbine",
            resources,
            expression_evaluator,
        )
        return (
            TimeSeriesGasTurbineFactory(
                name=unit.name,
                energy_unit_id=energy_unit_id,
                capacity=capacity,
                power_to_fuel=fuel_model.fuel_for_power,
            ),
            FuelGasRate,
            MechanicalPower,
        )

    def _map_generator_set(
        self,
        unit: YamlGeneratorSet,
        energy_unit_id: EnergyUnitId,
        yaml_keys: YamlKeys,
        generator_set_models: Mapping[str, _FuelModel],
        resources: Mapping[str, Resource],
        expression_evaluator: ExpressionEvaluator,
    ) -> tuple[TimeSeriesEnergyUnit, type[Energy] | None, type[Energy] | None]:
        fuel_model, capacity = self._resolve_fuel_model_and_capacity(
            unit,
            yaml_keys,
            generator_set_models,
            map_generator_set_fuel_model,
            "GENERATOR_SETS",
            "generator set",
            resources,
            expression_evaluator,
        )
        return (
            TimeSeriesGeneratorSetFactory(
                name=unit.name,
                energy_unit_id=energy_unit_id,
                capacity=capacity,
                power_to_fuel=fuel_model.fuel_for_power,
            ),
            FuelGasRate,
            ElectricalPower,
        )

    def _resolve_fuel_model_and_capacity(
        self,
        unit: YamlGasTurbine | YamlGeneratorSet,
        yaml_keys: YamlKeys,
        models: Mapping[str, _FuelModel],
        mapper: Callable[..., _FuelModel],
        section: str,
        description: str,
        resources: Mapping[str, Resource],
        expression_evaluator: ExpressionEvaluator,
    ) -> tuple[_FuelModel, TimeSeriesExpression]:
        model_keys = (*yaml_keys, "MODEL")
        if isinstance(unit.model, str):
            if unit.model not in models:
                raise EnergyNetworkValidationError(
                    f"'{unit.name}': MODEL '{unit.model}' is not a {description} in DEFINITIONS.{section}. "
                    f"Available {description}s: {sorted(models)}",
                    model_keys,
                )
            fuel_model = models[unit.model]
        else:
            fuel_model = self._map_definition(mapper, unit.name, unit.model, resources, model_keys)
        capacity = self._time_series(
            fuel_model.max_power if unit.capacity is None else unit.capacity, expression_evaluator
        )
        if unit.capacity is not None:
            self._check_capacity_within_curve(
                unit.name, capacity, fuel_model.max_power, description, (*yaml_keys, "CAPACITY")
            )
        return fuel_model, capacity

    @staticmethod
    def _check_capacity_within_curve(
        unit_name: str, capacity: TimeSeriesExpression, curve_max_power: float, curve_name: str, yaml_keys: YamlKeys
    ) -> None:
        for period, value in capacity.get_masked_items().items():
            if value > curve_max_power and not math.isclose(value, curve_max_power, rel_tol=1e-9):
                raise EnergyNetworkValidationError(
                    f"'{unit_name}': CAPACITY {value} for period {period} exceeds the {curve_name} curve maximum "
                    f"of {curve_max_power}.",
                    yaml_keys,
                )

    def _map_unit(
        self,
        unit: YamlComponent,
        energy_unit_id: EnergyUnitId,
        node_ids_by_key: Mapping[NodeKey, EnergyUnitId],
        expression_evaluator: ExpressionEvaluator,
    ) -> tuple[TimeSeriesEnergyUnit, type[Energy] | None, type[Energy] | None]:
        match unit:
            case YamlGeneratorSet() | YamlGasTurbine():
                raise AssertionError("GAS_TURBINE and GENERATOR_SET units are mapped with their YAML location.")
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
                        energy_type=ElectricalPower,
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
                        energy_type=FuelGasRate,
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
                if unit.load is None:
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
