"""Process solver concept draft v3.

A unit is a dataclass with parameters and a pure ``compute``; topology is dumb;
evaluation is a pure function returning streams at every port with violations as
data. See ``README.md`` and
``_context/studies/process-solver-concept-draft/improved-draft-v3/plan.md``.
"""

from libecalc.process_concept_draft_v3.display import (
    DisplayConnection,
    DisplayLoop,
    DisplayShaft,
    DisplayTopology,
    DisplayUnit,
    DisplayUnitKind,
    display_topology,
)
from libecalc.process_concept_draft_v3.params import UNSET, Param, Unset
from libecalc.process_concept_draft_v3.system import (
    CapacityViolation,
    ProcessSystem,
    State,
    ViolationKind,
    chain,
)
from libecalc.process_concept_draft_v3.units import (
    Choke,
    CommonASVLoop,
    CompressorStage,
    Cooler,
    Ctx,
    LiquidRemover,
    Mixer,
    OperatingPoint,
    Shaft,
    Splitter,
    Unit,
    add_rate,
    remove_rate,
)

__all__ = [
    "UNSET",
    "CapacityViolation",
    "Choke",
    "CompressorStage",
    "Cooler",
    "Ctx",
    "DisplayConnection",
    "DisplayLoop",
    "DisplayShaft",
    "DisplayTopology",
    "DisplayUnit",
    "DisplayUnitKind",
    "LiquidRemover",
    "Mixer",
    "OperatingPoint",
    "Param",
    "ProcessSystem",
    "CommonASVLoop",
    "Shaft",
    "Splitter",
    "State",
    "Unit",
    "Unset",
    "ViolationKind",
    "add_rate",
    "chain",
    "display_topology",
    "remove_rate",
]
