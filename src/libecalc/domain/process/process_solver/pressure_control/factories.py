from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_solver.pressure_control.capacity_policies import (
    CapacityPolicy,
    CommonASVMinFlowPolicy,
    NoCapacityPolicy,
)
from libecalc.domain.process.process_solver.pressure_control.pressure_control_policies import (
    CommonASVPressureControlPolicy,
    DownstreamChokePressureControlPolicy,
    NoPressureControlPolicy,
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

    if name == CapacityPolicyName.NONE:
        return NoCapacityPolicy()
    if name == CapacityPolicyName.COMMON_ASV_MIN_FLOW:
        return CommonASVMinFlowPolicy(
            recirculation_rate_boundary=recirculation_rate_boundary,
            search_strategy=search_strategy,
            root_finding_strategy=root_finding_strategy,
        )
    if name == CapacityPolicyName.INDIVIDUAL_ASV_MIN_FLOW:
        raise NotImplementedError("Individual ASV min flow policy is not implemented yet")
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

    if name == PressureControlPolicyName.NONE:
        return NoPressureControlPolicy()

    if name == PressureControlPolicyName.COMMON_ASV:
        return CommonASVPressureControlPolicy(
            recirculation_rate_boundary=recirculation_rate_boundary,
            search_strategy=search_strategy,
            root_finding_strategy=root_finding_strategy,
        )
    if name == PressureControlPolicyName.INDIVIDUAL_ASV_PRESSURE:
        raise NotImplementedError("Individual ASV pressure control policy is not implemented yet")
    if name == PressureControlPolicyName.INDIVIDUAL_ASV_RATE:
        raise NotImplementedError("Individual ASV rate control policy is not implemented yet")
    if name == PressureControlPolicyName.DOWNSTREAM_CHOKE:
        return DownstreamChokePressureControlPolicy()
    if name == PressureControlPolicyName.UPSTREAM_CHOKE:
        return UpstreamChokePressureControlPolicy(
            upstream_delta_pressure_boundary=upstream_delta_pressure_boundary,
            root_finding_strategy=root_finding_strategy,
        )
    raise ValueError(f"Unsupported pressure control policy: {name}")
