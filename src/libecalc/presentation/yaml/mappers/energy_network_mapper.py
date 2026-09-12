from collections.abc import Mapping, Sequence

from libecalc.common.variables import ExpressionEvaluator
from libecalc.domain.resource import Resource
from libecalc.energy import EnergyUnit, EnergyUnitId
from libecalc.energy.energy_network_topology import EnergyNetworkTopology
from libecalc.energy.energy_units import (
    DieselConsumer,
    DieselSource,
    ElectricalBus,
    ElectricalCable,
    ElectricalConsumer,
    ElectricalMotor,
    ElectricalSource,
    FuelGasConsumer,
    FuelGasManifold,
    FuelGasSource,
    GasTurbine,
    GeneratorSet,
    MechanicalConsumer,
    SampledCompressorElectricalConsumer,
    SampledCompressorFuelGasConsumer,
    SampledCompressorMechanicalConsumer,
)
from libecalc.energy.models.sampled_compressor_units import build_gas_turbine
from libecalc.expression.expression import ExpressionType
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression
from libecalc.presentation.yaml.mappers.energy.sampled_compressor_mapper import (
    SampledCompressorModel,
    build_sampled_compressor_model,
)
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
    YamlSampledCompressor,
    _SampledElectricalConsumer,
    _SampledFuelGasConsumer,
    _SampledGasTurbine,
    _SampledMechanicalConsumer,
)


class EnergyNetworkMapper:
    def map_energy_network(
        self,
        yaml_energy_network: YamlEnergyNetwork,
        expression_evaluator: ExpressionEvaluator,
        facility_resources: Mapping[str, Resource] | None = None,
    ) -> tuple[EnergyNetworkTopology, Sequence[EnergyUnit], dict[EnergyUnitId, TimeSeriesExpression]]:
        facility_resources = facility_resources or {}
        energy_units = [
            *(self._map_source(source) for source in yaml_energy_network.sources),
            *(self._map_unit(unit, facility_resources) for unit in yaml_energy_network.units),
        ]
        node_ids_by_name = {energy_unit.get_name(): energy_unit.get_id() for energy_unit in energy_units}

        connections = [
            (node_ids_by_name[input_name], node_ids_by_name[unit.name])
            for unit in yaml_energy_network.units
            for input_name in self._get_input_names(unit)
        ]
        topology = EnergyNetworkTopology.create(
            node_input_types={
                energy_unit.get_id(): energy_unit.get_input_energy_type() for energy_unit in energy_units
            },
            node_output_types={
                energy_unit.get_id(): energy_unit.get_output_energy_type() for energy_unit in energy_units
            },
            connections=connections,
        )
        consumer_expressions = {
            energy_unit.get_id(): TimeSeriesExpression(expression=expression, expression_evaluator=expression_evaluator)
            for unit, energy_unit in zip(yaml_energy_network.units, energy_units[len(yaml_energy_network.sources) :])
            if (expression := self._get_consumer_expression(unit)) is not None
        }
        return topology, energy_units, consumer_expressions

    @staticmethod
    def _map_source(source: YamlEnergySource) -> EnergyUnit:
        match source.type:
            case YamlEnergySourceType.FUEL_GAS_SOURCE:
                return FuelGasSource(name=source.name)
            case YamlEnergySourceType.ELECTRICAL_SOURCE:
                return ElectricalSource(name=source.name)
            case YamlEnergySourceType.DIESEL_SOURCE:
                return DieselSource(name=source.name)

    @staticmethod
    def _map_unit(
        unit: YamlComponent,
        facility_resources: Mapping[str, Resource],
    ) -> EnergyUnit:
        def _get_model(file: str) -> SampledCompressorModel:
            return build_sampled_compressor_model(facility_resources[file])

        match unit:
            case YamlGeneratorSet():
                return GeneratorSet(name=unit.name)
            case YamlGasTurbine():
                return GasTurbine(name=unit.name)
            case YamlElectricalMotor():
                return ElectricalMotor(name=unit.name)
            case YamlElectricalCable():
                return ElectricalCable(name=unit.name)
            case YamlElectricalBus():
                return ElectricalBus(name=unit.name)
            case YamlFuelGasManifold():
                return FuelGasManifold(name=unit.name)
            case YamlElectricalConsumer():
                return ElectricalConsumer(name=unit.name)
            case YamlMechanicalConsumer():
                return MechanicalConsumer(name=unit.name)
            case YamlFuelGasConsumer():
                return FuelGasConsumer(name=unit.name)
            case YamlDieselConsumer():
                return DieselConsumer(name=unit.name)
            case _SampledFuelGasConsumer():
                model = _get_model(unit.file)
                return SampledCompressorFuelGasConsumer(name=unit.name, compressor=model.compressor)
            case _SampledElectricalConsumer():
                model = _get_model(unit.file)
                return SampledCompressorElectricalConsumer(name=unit.name, compressor=model.compressor)
            case _SampledGasTurbine():
                model = _get_model(unit.file)
                return build_gas_turbine(unit.name, model.compressor)
            case _SampledMechanicalConsumer():
                model = _get_model(unit.file)
                # consumes_fuel (FILE had FUEL+POWER) means a turbine was split off -
                # this consumer must report resolved power, not the fuel-valued
                # energy_usage_values.
                return SampledCompressorMechanicalConsumer(
                    name=unit.name, compressor=model.compressor, reports_power=model.consumes_fuel
                )
            case YamlSampledCompressor():
                raise AssertionError(
                    f"'{unit.name}': unresolved SAMPLED_COMPRESSOR reached _map_unit - "
                    "expand_sampled_compressors must run before mapping."
                )

    @staticmethod
    def _get_input_names(unit: YamlComponent) -> list[str]:
        return unit.input if isinstance(unit.input, list) else [unit.input]

    @staticmethod
    def _get_consumer_expression(unit: YamlComponent) -> ExpressionType | None:
        match unit:
            case YamlElectricalConsumer() | YamlMechanicalConsumer():
                return unit.load
            case YamlFuelGasConsumer() | YamlDieselConsumer():
                return unit.rate
        return None
