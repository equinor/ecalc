from libecalc.domain.process.adapters.process_result_adapter import (
    EcalcModelResultEnergyComponent,
    EcalcModelResultEnergyModel,
    EcalcModelResultCompressorTrainProcessSystem,
    EcalcChokeProcessUnit,
    EcalcModelResultCompressorProcessUnit,
)
from libecalc.fixtures import YamlCase
from libecalc.presentation.json_result.mapper import get_asset_result


class EnergyModelResultEnergyModel:
    pass


def test_get_process_results_returns_energy_model(all_energy_usage_models_yaml: YamlCase):
    """
    Test that the process results can be retrieved from the energy model.

    It is probably not needed to use all_energy_usage_models_yaml fixture.

    """

    model = all_energy_usage_models_yaml.get_yaml_model()
    model.validate_for_run()
    model.evaluate_energy_usage()
    model.evaluate_emissions()
    asset_result = get_asset_result(model.get_graph_result())
    process_result = model.get_process_results(asset_result)
    energy_components = process_result.get_energy_components()

    energy_component_result = energy_components[7]
    events = energy_component_result.get_process_changed_events()
    train_process_system = energy_component_result.get_process_system(events[0])
    process_units = train_process_system.get_process_units()
    upstream_choke = process_units[0]
    downstream_choke = process_units[3]
    stage1_result = process_units[1]
    stage2_result = process_units[2]

    assert isinstance(process_result, EcalcModelResultEnergyModel)
    assert isinstance(energy_components[0], EcalcModelResultEnergyComponent)
    assert isinstance(train_process_system, EcalcModelResultCompressorTrainProcessSystem)
    assert all(isinstance(obj, EcalcChokeProcessUnit) for obj in (upstream_choke, downstream_choke))
    assert all(isinstance(obj, EcalcModelResultCompressorProcessUnit) for obj in (stage1_result, stage2_result))
