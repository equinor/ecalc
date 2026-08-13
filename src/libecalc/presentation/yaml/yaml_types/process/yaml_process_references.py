"""
Shared reference type aliases for YAML process types.
"""

from typing import NewType

type StreamRef = str
type ProcessPipelineReference = str  # TODO: validate correct reference
type ProcessUnitReference = str
type EcalcEventReference = str
type ProcessEventReference = str
type PumpChartReference = str

ProcessUnitInstanceName = NewType("ProcessUnitInstanceName", str)
ProcessUnitInstanceReference = NewType("ProcessUnitInstanceReference", str)
ProcessUnitDefinitionReference = NewType("ProcessUnitDefinitionReference", str)

ProcessPipelineInstanceName = NewType("ProcessPipelineInstanceName", str)
ProcessPipelineInstanceReference = NewType("ProcessPipelineInstanceReference", str)
ProcessPipelineDefinitionReference = NewType("ProcessPipelineDefinitionReference", str)
