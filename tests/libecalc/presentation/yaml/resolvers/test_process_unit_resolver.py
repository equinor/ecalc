from libecalc.presentation.yaml.resolvers.process_unit_resolver import ProcessUnitResolver
from libecalc.presentation.yaml.yaml_types.process.yaml_process_pipeline import YamlProcessUnitInstance
from libecalc.presentation.yaml.yaml_types.process.yaml_process_references import (
    ProcessUnitDefinitionReference,
    ProcessUnitInstanceName,
)
from libecalc.presentation.yaml.yaml_types.process.yaml_process_units import YamlLiquidRemover
from libecalc.testing.direct_reference_service import DirectReferenceService


def test_resolves_process_unit_definition_reference():
    """Resolve a global unit definition while preserving its local instance name."""
    specification = YamlLiquidRemover(type="LIQUID_REMOVER")
    reference_service = DirectReferenceService(references={"scrubber": specification})
    definition_reference = ProcessUnitDefinitionReference("scrubber")
    instance_name = ProcessUnitInstanceName("first_stage_scrubber")

    # Simulate the global definition lookup: "scrubber" -> specification.
    resolved = ProcessUnitResolver(reference_service).resolve(
        YamlProcessUnitInstance(
            name=instance_name,
            target=definition_reference,
        )
    )

    # Resolution replaces the definition reference but preserves local identity.
    assert resolved.name == instance_name
    assert resolved.specification == specification
