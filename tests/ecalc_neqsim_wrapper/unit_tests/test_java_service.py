from ecalc_neqsim_wrapper import neqsim


def test_py4j_service():
    """Testing the most simple case to ensure that the java service is running and working."""
    thermo_system = neqsim.thermo.system.SystemSrkEos(280.0, 10.0)
    thermo_system.addComponent("methane", 10.0)
    thermo_system.addComponent("water", 4.0)

    thermo_dynamic_operations = neqsim.thermodynamicoperations.ThermodynamicOperations(thermo_system)
    thermo_dynamic_operations.TPflash()

    gas_enthalpy = thermo_system.getPhase(0).getEnthalpy()

    thermo_system.initPhysicalProperties("Viscosity")
    gas_viscosity = thermo_system.getPhase(0).getViscosity("kg/msec")

    assert gas_enthalpy
    assert gas_viscosity
