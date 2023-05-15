from neqsim_ecalc_wrapper.java_service import start_server

java_gateway = start_server()
neqsim = java_gateway.jvm.neqsim

from neqsim_ecalc_wrapper.thermo import NeqsimEoSModelType, NeqsimFluid


def methods(check_class):
    """
    Print list of available methods for a java class
    """
    try:
        list_of_methods = check_class.getClass().getMethods()
        for method in list_of_methods:
            print(method.getName())
    except AttributeError:
        print(f"Unknown attribute for {check_class}, the class might not be a java class")
