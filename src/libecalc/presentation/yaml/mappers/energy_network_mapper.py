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
)
from libecalc.energy.network import EnergyConnection, EnergyNetwork, EnergyNetworkNode
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
    def map_energy_network(self, yaml_energy_network: YamlEnergyNetwork) -> EnergyNetwork:
        nodes_by_name: dict[str, EnergyNetworkNode] = {}

        for source in yaml_energy_network.sources:
            nodes_by_name[source.name] = self._map_source(source)
        for unit in yaml_energy_network.units:
            nodes_by_name[unit.name] = self._map_unit(unit)

        connections = [
            EnergyConnection(
                source_id=nodes_by_name[input_name].get_id(),
                target_id=nodes_by_name[unit.name].get_id(),
            )
            for unit in yaml_energy_network.units
            for input_name in self._get_input_names(unit)
        ]
        return EnergyNetwork(nodes=nodes_by_name.values(), connections=connections)

    @staticmethod
    def _map_source(source: YamlEnergySource) -> FuelGasSource | ElectricalSource | DieselSource:
        match source.type:
            case YamlEnergySourceType.FUEL_GAS_SOURCE:
                return FuelGasSource(name=source.name)
            case YamlEnergySourceType.ELECTRICAL_SOURCE:
                return ElectricalSource(name=source.name)
            case YamlEnergySourceType.DIESEL_SOURCE:
                return DieselSource(name=source.name)

    @staticmethod
    def _map_unit(unit: YamlComponent) -> EnergyNetworkNode:
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

    @staticmethod
    def _get_input_names(unit: YamlComponent) -> list[str]:
        return unit.input if isinstance(unit.input, list) else [unit.input]
