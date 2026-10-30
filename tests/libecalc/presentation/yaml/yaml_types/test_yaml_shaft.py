import pytest
from pydantic import ValidationError

from libecalc.presentation.yaml.yaml_types.components.yaml_asset import YamlAsset, YamlDefinitions
from libecalc.presentation.yaml.yaml_types.energy.yaml_energy_network import YamlEnergyNetwork
from libecalc.presentation.yaml.yaml_types.energy.yaml_turbine_definition import YamlTurbineCurve, YamlTurbineDefinition
from libecalc.presentation.yaml.yaml_types.process.yaml_process_pipeline import YamlProcessPipeline
from libecalc.presentation.yaml.yaml_types.yaml_shaft import YamlShaft
from libecalc.testing.energy_builders import YamlEnergyNetworkBuilder
from libecalc.testing.process_builders import (
    YamlCommonStreamDistributionBuilder,
    YamlCompressorBuilder,
    YamlDefinitionsBuilder,
    YamlProcessPipelineBuilder,
    YamlProcessSimulationBuilder,
    compressors_in,
)
from libecalc.testing.yaml_builder import YamlAssetBuilder

TURBINE_MODEL = YamlTurbineDefinition(
    lower_heating_value=38, curve=YamlTurbineCurve(load=[10, 20], efficiency=[0.2, 0.3])
)


def _pipeline(name: str, *compressors: str) -> YamlProcessPipeline:
    builder = YamlProcessPipelineBuilder().with_name(name)
    for compressor in compressors:
        builder.with_compressor_item(compressor=compressor, target="compressor")
    return builder.validate()


def _compressor_definitions() -> YamlDefinitions:
    return (
        YamlDefinitionsBuilder()
        .with_process_unit("compressor", YamlCompressorBuilder().with_test_data().validate())
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
        .with_definitions(_compressor_definitions())
        .with_process_pipelines({pipeline.name: pipeline for pipeline in pipelines})
        .with_process_simulations(simulations)
    )
    if energy_network is not None:
        builder.with_energy_network(energy_network)
    return builder.validate()


def test_rejects_shaft_on_compressor_process_unit():
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        YamlProcessPipeline.model_validate(
            {
                "NAME": "export_pipeline",
                "PROCESS_UNITS": [{"TARGET": "compressor", "COMPRESSOR": "lp_compressor", "SHAFT": "export_shaft"}],
            }
        )


def test_rejects_compressor_definition_without_compressor_reference(
    yaml_process_pipeline_builder_factory, yaml_compressor_builder_factory
):
    with pytest.raises(ValidationError):
        (
            yaml_process_pipeline_builder_factory()
            .with_name("export_pipeline")
            .with_compressor_item(compressor="lp_compressor", target="compressor")
            .with_item(name="hp_compressor", target=yaml_compressor_builder_factory().with_test_data().validate())
            .validate()
        )


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
