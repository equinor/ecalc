"""Identifier types for process pipeline entities.

Kept in a dependency-free module so other modules (notably
``propagation_failure``) can reference these identifier types without
pulling in ``process_unit`` / ``process_pipeline`` and creating import
cycles.
"""

from typing import NewType
from uuid import UUID

ProcessUnitId = NewType("ProcessUnitId", UUID)
ProcessPipelineId = NewType("ProcessPipelineId", UUID)
