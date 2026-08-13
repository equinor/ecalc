from unittest.mock import Mock

from libecalc.presentation.yaml.domain.reference_service import ReferenceService
from libecalc.presentation.yaml.resolvers.process_unit_resolver import ProcessUnitResolver
from libecalc.presentation.yaml.yaml_types.process.yaml_process_pipeline import YamlProcessUnitItem
from libecalc.presentation.yaml.yaml_types.process.yaml_process_references import (
    ProcessUnitDefinitionReference,
    ProcessUnitInstanceName,
)
from libecalc.presentation.yaml.yaml_types.process.yaml_process_units import YamlLiquidRemover


def test_resolves_process_unit_definition_reference():
    """Resolve a global unit definition while preserving its local instance name."""
    reference_service = Mock(spec=ReferenceService)
    specification = YamlLiquidRemover(type="LIQUID_REMOVER")
    definition_reference = ProcessUnitDefinitionReference("scrubber")
    instance_name = ProcessUnitInstanceName("first_stage_scrubber")
    reference_service.get_process_unit.return_value = specification

    # Simulate the global definition lookup: "scrubber" -> specification.
    resolved = ProcessUnitResolver(reference_service).resolve(
        YamlProcessUnitItem(
            name=instance_name,
            target=definition_reference,
        )
    )

    # Resolution replaces the definition reference but preserves local identity.
    assert resolved.name == instance_name
    assert resolved.specification == specification
    reference_service.get_process_unit.assert_called_once_with(definition_reference)
