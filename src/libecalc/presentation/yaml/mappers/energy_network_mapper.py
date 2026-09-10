from libecalc.energy.energy_types import DieselRate, ElectricalPower, FuelGasRate, MechanicalPower
from libecalc.energy.network import EnergyConnection, EnergyNetwork
from libecalc.energy.network_unit import EnergyNetworkUnit
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
        nodes_by_name: dict[str, EnergyNetworkUnit] = {}

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
    def _map_source(source: YamlEnergySource) -> EnergyNetworkUnit:
        match source.type:
            case YamlEnergySourceType.FUEL_GAS_SOURCE:
                return EnergyNetworkUnit(source.name, None, FuelGasRate)
            case YamlEnergySourceType.ELECTRICAL_SOURCE:
                return EnergyNetworkUnit(source.name, None, ElectricalPower)
            case YamlEnergySourceType.DIESEL_SOURCE:
                return EnergyNetworkUnit(source.name, None, DieselRate)

    @staticmethod
    def _map_unit(unit: YamlComponent) -> EnergyNetworkUnit:
        match unit:
            case YamlGeneratorSet():
                return EnergyNetworkUnit(unit.name, FuelGasRate, ElectricalPower)
            case YamlGasTurbine():
                return EnergyNetworkUnit(unit.name, FuelGasRate, MechanicalPower)
            case YamlElectricalMotor():
                return EnergyNetworkUnit(unit.name, ElectricalPower, MechanicalPower)
            case YamlElectricalCable():
                return EnergyNetworkUnit(unit.name, ElectricalPower, ElectricalPower)
            case YamlElectricalBus():
                return EnergyNetworkUnit(unit.name, ElectricalPower, ElectricalPower)
            case YamlFuelGasManifold():
                return EnergyNetworkUnit(unit.name, FuelGasRate, FuelGasRate)
            case YamlElectricalConsumer():
                return EnergyNetworkUnit(unit.name, ElectricalPower, None)
            case YamlMechanicalConsumer():
                return EnergyNetworkUnit(unit.name, MechanicalPower, None)
            case YamlFuelGasConsumer():
                return EnergyNetworkUnit(unit.name, FuelGasRate, None)
            case YamlDieselConsumer():
                return EnergyNetworkUnit(unit.name, DieselRate, None)

    @staticmethod
    def _get_input_names(unit: YamlComponent) -> list[str]:
        return unit.input if isinstance(unit.input, list) else [unit.input]
