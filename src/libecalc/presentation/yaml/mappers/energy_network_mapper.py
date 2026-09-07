from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.energy.energy_types import DieselRate, ElectricalPower, Energy, FuelGasRate, MechanicalPower
from libecalc.energy.energy_unit import EnergyUnitId
from libecalc.energy.network import EnergyNetwork
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
    def map_energy_network(self, yaml_energy_network: YamlEnergyNetwork) -> EnergyNetwork:
        node_energy_types_by_name: dict[str, tuple[type[Energy] | None, type[Energy] | None]] = {}

        for source in yaml_energy_network.sources:
            node_energy_types_by_name[source.name] = self._map_source(source)
        for unit in yaml_energy_network.units:
            node_energy_types_by_name[unit.name] = self._map_unit(unit)

        node_ids_by_name: dict[str, EnergyUnitId] = {
            name: EnergyUnitId(ecalc_id_generator()) for name in node_energy_types_by_name
        }

        connections = [
            (node_ids_by_name[input_name], node_ids_by_name[unit.name])
            for unit in yaml_energy_network.units
            for input_name in self._get_input_names(unit)
        ]
        return EnergyNetwork.create(
            node_input_types={
                node_ids_by_name[name]: input_type for name, (input_type, _) in node_energy_types_by_name.items()
            },
            node_output_types={
                node_ids_by_name[name]: output_type for name, (_, output_type) in node_energy_types_by_name.items()
            },
            connections=connections,
        )

    @staticmethod
    def _map_source(source: YamlEnergySource) -> tuple[None, type[Energy]]:
        match source.type:
            case YamlEnergySourceType.FUEL_GAS_SOURCE:
                return None, FuelGasRate
            case YamlEnergySourceType.ELECTRICAL_SOURCE:
                return None, ElectricalPower
            case YamlEnergySourceType.DIESEL_SOURCE:
                return None, DieselRate

    @staticmethod
    def _map_unit(unit: YamlComponent) -> tuple[type[Energy], type[Energy] | None]:
        match unit:
            case YamlGeneratorSet():
                return FuelGasRate, ElectricalPower
            case YamlGasTurbine():
                return FuelGasRate, MechanicalPower
            case YamlElectricalMotor():
                return ElectricalPower, MechanicalPower
            case YamlElectricalCable():
                return ElectricalPower, ElectricalPower
            case YamlElectricalBus():
                return ElectricalPower, ElectricalPower
            case YamlFuelGasManifold():
                return FuelGasRate, FuelGasRate
            case YamlElectricalConsumer():
                return ElectricalPower, None
            case YamlMechanicalConsumer():
                return MechanicalPower, None
            case YamlFuelGasConsumer():
                return FuelGasRate, None
            case YamlDieselConsumer():
                return DieselRate, None
            case _SampledFuelGasConsumer():
                return FuelGasRate, None
            case _SampledElectricalConsumer():
                return ElectricalPower, None
            case _SampledGasTurbine():
                return FuelGasRate, MechanicalPower
            case _SampledMechanicalConsumer():
                return MechanicalPower, None
            case YamlSampledCompressor():
                raise AssertionError("SAMPLED_COMPRESSOR must be resolved by expand_sampled_compressors before mapping")

    @staticmethod
    def _get_input_names(unit: YamlComponent) -> list[str]:
        return unit.input if isinstance(unit.input, list) else [unit.input]
