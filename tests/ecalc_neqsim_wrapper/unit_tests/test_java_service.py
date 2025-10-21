import pytest
from ecalc_neqsim_wrapper.java_service import (
    NeqsimService,
    NeqsimJPypeService,
    NeqsimPy4JService,
    ProgrammingError,
)


@pytest.fixture
def neqsim_module(with_neqsim_service):
    yield with_neqsim_service.get_neqsim_module()


def test_py4j_service(neqsim_module):
    """Testing the most simple case to ensure that the java service is running and working."""
    thermo_system = neqsim_module.thermo.system.SystemSrkEos(280.0, 10.0)
    thermo_system.addComponent("methane", 10.0)
    thermo_system.addComponent("water", 4.0)

    thermo_dynamic_operations = neqsim_module.thermodynamicoperations.ThermodynamicOperations(thermo_system)
    thermo_dynamic_operations.TPflash()

    gas_enthalpy = thermo_system.getPhase(0).getEnthalpy()

    thermo_system.initPhysicalProperties("Viscosity")
    gas_viscosity = thermo_system.getPhase(0).getViscosity("kg/msec")

    assert gas_enthalpy
    assert gas_viscosity


def test_get_new_py4j_instance():
    """
    Default, and set in conftest.py is to use Py4J implementation.
    Returns:

    """
    neqsim_service = NeqsimService.instance()
    assert isinstance(neqsim_service, NeqsimPy4JService)


def test_same_instance():
    neqsim_service = NeqsimService.instance()
    neqsim_service_2 = NeqsimService.instance()
    assert neqsim_service is neqsim_service_2


def test_init_not_allowed():
    with pytest.raises(ProgrammingError):
        NeqsimJPypeService()


def test_reinitialize_not_allowed():
    # We have already set jpype=False in the conftest fixture, not allowed to change!
    with pytest.raises(ProgrammingError):
        NeqsimService.factory(use_jpype=True).initialize()
