import pytest
from pydantic import ValidationError

from libecalc.presentation.yaml.yaml_types.components.yaml_asset import YamlAsset
from libecalc.presentation.yaml.yaml_types.energy.yaml_energy_network import YamlEnergyNetwork
from libecalc.presentation.yaml.yaml_types.energy.yaml_turbine_definition import YamlTurbineCurve, YamlTurbineDefinition
from libecalc.presentation.yaml.yaml_types.process.yaml_process_pipeline import (
    YamlCompressorProcessUnitInstance,
    YamlProcessPipeline,
)
from libecalc.presentation.yaml.yaml_types.yaml_shaft import YamlShaft
from libecalc.testing.energy_builders import YamlDriveTrainBuilder, YamlEnergyNetworkBuilder
from libecalc.testing.process_builders import (
    YamlCommonStreamDistributionBuilder,
    YamlCompressorModelChartBuilder,
    YamlDefinitionsBuilder,
    YamlProcessPipelineBuilder,
    YamlProcessSimulationBuilder,
    compressors_in,
)
from libecalc.testing.yaml_builder import YamlAssetBuilder

TURBINE_MODEL = YamlTurbineDefinition(curve=YamlTurbineCurve(load=[10, 20], efficiency=[0.2, 0.3]))


def _pipeline(name: str, *compressors: str) -> YamlProcessPipeline:
    builder = YamlProcessPipelineBuilder().with_name(name)
    for compressor in compressors:
        builder.with_compressor_item(compressor=compressor)
    return builder.validate()


def _pipeline_with_shaft_on_process_unit(name: str, compressor: str, shaft: str) -> YamlProcessPipeline:
    process_unit = YamlCompressorProcessUnitInstance.model_construct(
        type="COMPRESSOR",
        compressor=compressor,
        model=YamlCompressorModelChartBuilder().with_test_data().validate(),
        shaft=shaft,
    )
    return YamlProcessPipeline.model_construct(name=name, process_units=[process_unit])


def test_rejects_shaft_on_compressor_process_unit_from_v3():
    pipeline = _pipeline_with_shaft_on_process_unit("export_pipeline", "lp_compressor", "export_shaft")

    with pytest.raises(
        ValidationError,
        match=r"PROCESS_PIPELINES > export_pipeline > PROCESS_UNITS\[0\] > SHAFT",
    ):
        (
            YamlAssetBuilder()
            .with_yaml_version(3)
            .with_end("2025-01-01")
            .with_shafts([YamlShaft(name="export_shaft", compressors=["lp_compressor"])])
            .with_compressors(compressors_in(pipeline))
            .with_definitions(YamlDefinitionsBuilder().with_test_data().validate())
            .with_process_pipelines({pipeline.name: pipeline})
            .validate()
        )


def _drive_train_network(*shafts: str) -> YamlEnergyNetwork:
    builder = YamlEnergyNetworkBuilder().with_test_data().with_gas_turbine("turbine", "fuel_gas", TURBINE_MODEL)
    for shaft in shafts:
        builder.with_drive_train(name=f"{shaft} drive", input="turbine", shaft=shaft)
    return builder.validate()


def _asset(
    *,
    shafts: list[YamlShaft],
    pipelines: list[YamlProcessPipeline],
    targeted: list[YamlProcessPipeline] | None = None,
    energy_network: YamlEnergyNetwork | None = None,
) -> YamlAsset:
    simulations = [
        YamlProcessSimulationBuilder()
        .with_name(f"{pipeline.name} simulation")
        .with_pipeline(pipeline)
        .with_stream_distribution(YamlCommonStreamDistributionBuilder().with_test_data().validate())
        .validate()
        for pipeline in targeted or []
    ]
    builder = (
        YamlAssetBuilder()
        .with_end("2025-01-01")
        .with_shafts(shafts)
        .with_compressors(compressors_in(*pipelines))
        .with_definitions(YamlDefinitionsBuilder().with_test_data().validate())
        .with_process_pipelines({pipeline.name: pipeline for pipeline in pipelines})
        .with_process_simulations(simulations)
    )
    if energy_network is not None:
        builder.with_energy_network(energy_network)
    return builder.validate()


@pytest.mark.parametrize(
    "shafts, pipelines, message",
    [
        pytest.param(
            [YamlShaft(name="export_shaft", compressors=["lp_compressor"]), YamlShaft(name="export_shaft")],
            [_pipeline("export_pipeline", "lp_compressor")],
            "SHAFTS names must be unique",
            id="duplicate shaft names",
        ),
        pytest.param(
            [YamlShaft(name="export_shaft", compressors=["lp_compressor", "missing_compressor"])],
            [_pipeline("export_pipeline", "lp_compressor")],
            "referenced in shaft 'export_shaft' is not defined",
            id="unknown compressor on shaft",
        ),
        pytest.param(
            [
                YamlShaft(name="shaft_a", compressors=["lp_compressor"]),
                YamlShaft(name="shaft_b", compressors=["lp_compressor"]),
            ],
            [_pipeline("export_pipeline", "lp_compressor")],
            "listed more than once in SHAFTS",
            id="compressor on two shafts",
        ),
        pytest.param(
            [YamlShaft(name="export_shaft", compressors=["lp_compressor"])],
            [_pipeline("export_pipeline", "lp_compressor", "hp_compressor")],
            "'hp_compressor' .* is not on a shaft",
            id="placed compressor on no shaft",
        ),
        pytest.param(
            [
                YamlShaft(name="shaft_a", compressors=["lp_compressor"]),
                YamlShaft(name="shaft_b", compressors=["hp_compressor"]),
            ],
            [_pipeline("export_pipeline", "lp_compressor", "hp_compressor")],
            "has compressors on multiple shafts",
            id="pipeline on two shafts",
        ),
        pytest.param(
            [YamlShaft(name="common_shaft", compressors=["export_compressor", "injection_compressor"])],
            [
                _pipeline("export_pipeline", "export_compressor"),
                _pipeline("injection_pipeline", "injection_compressor"),
            ],
            "has compressors in multiple process pipelines",
            id="shaft in two pipelines",
        ),
        pytest.param(
            [YamlShaft(name="export_shaft", compressors=["lp_compressor"])],
            [_pipeline("export_pipeline", "lp_compressor", "lp_compressor")],
            "'lp_compressor' is modelled more than once in the process domain",
            id="compressor placed twice",
        ),
    ],
)
def test_rejects_invalid_shaft_membership(shafts, pipelines, message):
    with pytest.raises(ValidationError, match=message):
        _asset(shafts=shafts, pipelines=pipelines)


@pytest.mark.parametrize(
    "shafts, targeted, message",
    [
        pytest.param(
            [YamlShaft(name="export_shaft"), YamlShaft(name="lp_shaft", compressors=["lp_compressor"])],
            True,
            "which has no compressors",
            id="driven shaft without compressors",
        ),
        pytest.param(
            [YamlShaft(name="export_shaft", compressors=["lp_compressor"])],
            False,
            "which no process simulation targets",
            id="compressor in untargeted pipeline",
        ),
    ],
)
def test_rejects_driven_shaft_without_solved_compressors(shafts, targeted, message):
    pipeline = _pipeline("export_pipeline", "lp_compressor")

    with pytest.raises(ValidationError, match=message):
        _asset(
            shafts=shafts,
            pipelines=[pipeline],
            targeted=[pipeline] if targeted else [],
            energy_network=_drive_train_network(*(shaft.name for shaft in shafts)),
        )


def test_rejects_unknown_shaft_reference_from_drive_train():
    with pytest.raises(
        ValidationError,
        match="Drive train 'missing_shaft drive' references unknown shaft 'missing_shaft'. "
        "Available shafts in SHAFTS: export_shaft.",
    ):
        (
            YamlAssetBuilder()
            .with_end("2025-01-01")
            .with_shafts([YamlShaft(name="export_shaft")])
            .with_energy_network(_drive_train_network("missing_shaft"))
            .validate()
        )


def test_rejects_same_shaft_in_multiple_drive_trains(energy_network_builder_factory):
    energy_network = (
        energy_network_builder_factory()
        .with_test_data()
        .with_gas_turbine(name="export_turbine", input="fuel_gas", model=TURBINE_MODEL)
        .with_gas_turbine(name="injection_turbine", input="fuel_gas", model=TURBINE_MODEL)
        .with_drive_train(name="export_load", input="export_turbine", shaft="common_shaft")
        .with_drive_train(name="injection_load", input="injection_turbine", shaft="common_shaft")
        .construct()
    )

    with pytest.raises(
        ValidationError,
        match="Shaft 'common_shaft' is referenced by multiple drive trains: export_load, injection_load",
    ):
        (
            YamlAssetBuilder()
            .with_end("2025-01-01")
            .with_shafts([YamlShaft(name="common_shaft")])
            .with_energy_network(energy_network)
            .validate()
        )


def test_rejects_mechanical_efficiency_for_compressor_not_on_the_drive_trains_shaft():
    pipeline = _pipeline("export_pipeline", "export_compressor")
    drive_train = (
        YamlDriveTrainBuilder()
        .with_name("export_drive")
        .with_input("turbine")
        .with_shaft("export_shaft")
        .with_mechanical_efficiency("injection_compressor", 0.95)
        .validate()
    )
    energy_network = (
        YamlEnergyNetworkBuilder()
        .with_test_data()
        .with_gas_turbine("turbine", "fuel_gas", TURBINE_MODEL)
        .with_unit(drive_train)
        .validate()
    )

    with pytest.raises(
        ValidationError,
        match="Drive train 'export_drive' gives a mechanical efficiency for compressor 'injection_compressor', "
        "which is not on its shaft 'export_shaft'. Compressors on this shaft: export_compressor.",
    ):
        _asset(
            shafts=[YamlShaft(name="export_shaft", compressors=["export_compressor"])],
            pipelines=[pipeline],
            targeted=[pipeline],
            energy_network=energy_network,
        )
