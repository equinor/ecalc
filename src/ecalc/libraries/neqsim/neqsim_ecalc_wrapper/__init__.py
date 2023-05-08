from neqsim_ecalc_wrapper.java_service import start_server

java_gateway = start_server()
neqsim = java_gateway.jvm.neqsim

from neqsim_ecalc_wrapper.thermo import NeqsimEoSModelType, NeqsimFluid  # noqa


def methods(checkClass):  # noqa
    methods = checkClass.getClass().getMethods()
    for method in methods:
        print(method.getName())


def setDatabase(connectionString):  # noqa
    neqsim.util.database.NeqSimDataBase.setConnectionString(connectionString)
    neqsim.util.database.NeqSimDataBase.setCreateTemporaryTables(True)
