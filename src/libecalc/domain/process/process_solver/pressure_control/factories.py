from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_solver.pressure_control.policies import (
    CapacityPolicy,
    CommonASVMinCapacityPolicy,
    CommonASVPressureControlPolicy,
    DownstreamChokePressureControlPolicy,
    NoCapacityPolicy,
    PressureControlPolicy,
    UpstreamChokePressureControlPolicy,
)
from libecalc.domain.process.process_solver.pressure_control.types import CapacityPolicyName, PressureControlPolicyName
from libecalc.domain.process.process_solver.search_strategies import (
    BinarySearchStrategy,
    RootFindingStrategy,
    ScipyRootFindingStrategy,
    SearchStrategy,
)

_DEFAULT_BINARY_SEARCH_TOLERANCE = 10e-3
_DEFAULT_ROOT_FINDING_TOLERANCE = 1e-5


def create_capacity_policy(
    name: CapacityPolicyName,
    *,
    recirculation_rate_boundary: Boundary,
    search_strategy: SearchStrategy | None = None,
    root_finding_strategy: RootFindingStrategy | None = None,
) -> CapacityPolicy:
    """
    Create a concrete CapacityPolicy instance from a policy name.

    The strategy parameters are optional; if not provided, reasonable defaults are used.
    """
    search_strategy = search_strategy or BinarySearchStrategy(tolerance=_DEFAULT_BINARY_SEARCH_TOLERANCE)
    root_finding_strategy = root_finding_strategy or ScipyRootFindingStrategy(tolerance=_DEFAULT_ROOT_FINDING_TOLERANCE)

    if name == "NONE":
        return NoCapacityPolicy()
    if name == "COMMON_ASV_MIN_FLOW":
        return CommonASVMinCapacityPolicy(
            recirculation_rate_boundary=recirculation_rate_boundary,
            search_strategy=search_strategy,
            root_finding_strategy=root_finding_strategy,
        )
    raise ValueError(f"Unsupported capacity policy: {name}")


def create_pressure_control_policy(
    name: PressureControlPolicyName,
    *,
    recirculation_rate_boundary: Boundary,
    upstream_delta_pressure_boundary: Boundary,
    search_strategy: SearchStrategy | None = None,
    root_finding_strategy: RootFindingStrategy | None = None,
) -> PressureControlPolicy:
    """
    Create a concrete PressureControlPolicy instance from a policy name.

    The strategy parameters are optional; if not provided, reasonable defaults are used.
    """
    search_strategy = search_strategy or BinarySearchStrategy(tolerance=_DEFAULT_BINARY_SEARCH_TOLERANCE)
    root_finding_strategy = root_finding_strategy or ScipyRootFindingStrategy(tolerance=_DEFAULT_ROOT_FINDING_TOLERANCE)

    if name == "COMMON_ASV":
        return CommonASVPressureControlPolicy(
            recirculation_rate_boundary=recirculation_rate_boundary,
            search_strategy=search_strategy,
            root_finding_strategy=root_finding_strategy,
        )
    if name == "DOWNSTREAM_CHOKE":
        return DownstreamChokePressureControlPolicy()
    if name == "UPSTREAM_CHOKE":
        return UpstreamChokePressureControlPolicy(
            upstream_delta_pressure_boundary=upstream_delta_pressure_boundary,
            root_finding_strategy=root_finding_strategy,
        )
    raise ValueError(f"Unsupported pressure control policy: {name}")
