from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.pressure_control.policies import PressureControlPolicy
from libecalc.domain.process.process_solver.pressure_control.types import PressureControlConfiguration
from libecalc.domain.process.value_objects.fluid_stream import Fluid, FluidStream
from tests.libecalc.domain.process.conftest import create_mock_fluid_properties


def with_pressure(stream: FluidStream, *, pressure_bara: float) -> FluidStream:
    """
    Create a new FluidStream with identical properties as `stream`, except for pressure_bara.
    This avoids NeqSim flash and is suitable for unit tests that only need pressure signals.
    """
    props0 = stream.fluid.properties
    new_props = create_mock_fluid_properties(
        pressure_bara=pressure_bara,
        temperature_kelvin=props0.temperature_kelvin,
        density=props0.density,
        enthalpy_joule_per_kg=props0.enthalpy_joule_per_kg,
        z=props0.z,
        kappa=props0.kappa,
        vapor_fraction_molar=props0.vapor_fraction_molar,
        molar_mass=props0.molar_mass,
        standard_density=props0.standard_density,
    )
    new_fluid = Fluid(fluid_model=stream.fluid_model, properties=new_props)
    return FluidStream(fluid=new_fluid, mass_rate_kg_per_h=stream.mass_rate_kg_per_h)


class PressurePolicySpy(PressureControlPolicy):
    """
    Test spy wrapper for a PressureControlPolicy.

    Delegates all work to an inner policy, but increments `calls` for each `apply(...)` invocation.
    Used in solver-stage unit tests to assert whether the pressure-control policy was called
    (e.g. ensuring it is not invoked inside the speed loop / Step A).
    """

    def __init__(self, inner: PressureControlPolicy):
        self.inner = inner
        self.calls = 0

    def apply(self, *, input_cfg: PressureControlConfiguration, target_pressure: FloatConstraint, evaluate_system):
        self.calls += 1
        return self.inner.apply(
            input_cfg=input_cfg,
            target_pressure=target_pressure,
            evaluate_system=evaluate_system,
        )
