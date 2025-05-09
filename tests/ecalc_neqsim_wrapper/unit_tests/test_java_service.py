import pytest


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
