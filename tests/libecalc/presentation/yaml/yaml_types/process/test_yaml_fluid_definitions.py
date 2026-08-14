from libecalc.presentation.yaml.mappers.yaml_path import YamlPath
from libecalc.presentation.yaml.yaml_reference_service import YamlReferenceService
from libecalc.presentation.yaml.yaml_types.components.yaml_asset import YamlDefinitions
from libecalc.testing.process_builders import YamlInletStreamBuilder, YamlPredefinedFluidDefinitionBuilder
from libecalc.testing.yaml_builder import YamlAssetBuilder


def test_inlet_stream_fluid_reference_resolves_definition(
    yaml_asset_configuration_service_factory,
):
    """Fluids declared in DEFINITIONS are parsed and resolvable from INLET_STREAMS."""
    fluid_definition = YamlPredefinedFluidDefinitionBuilder().with_test_data().validate()
    inlet_stream = YamlInletStreamBuilder().with_test_data().with_name("main_stream").with_fluid("feed_gas").validate()
    asset = (
        YamlAssetBuilder()
        .with_test_data()
        .with_definitions(
            YamlDefinitions(
                fluids={"feed_gas": fluid_definition},
            )
        )
        .with_inlet_streams(
            {"main_stream": inlet_stream},
        )
        .validate()
    )

    configuration = yaml_asset_configuration_service_factory(
        asset,
        name="model.yaml",
    ).get_configuration()

    parsed_fluid = configuration.definitions.fluids["feed_gas"]
    parsed_stream = configuration.inlet_streams["main_stream"]

    reference_service = YamlReferenceService(configuration)
    resolved_fluid = reference_service.get_fluid_definition(
        parsed_stream.fluid,
    )

    # The fluid was parsed from the DEFINITIONS.FLUIDS dictionary.
    assert parsed_fluid == fluid_definition

    # The inlet-stream reference resolves to that parsed definition.
    assert resolved_fluid == parsed_fluid

    # Validation errors can be associated with the correct YAML location.
    assert reference_service.get_yaml_path("feed_gas") == YamlPath(
        keys=("DEFINITIONS", "FLUIDS", "feed_gas"),
    )
