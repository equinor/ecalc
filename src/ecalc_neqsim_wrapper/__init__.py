from ecalc_neqsim_wrapper.java_service import NeqsimService
from ecalc_neqsim_wrapper.thermo import NeqsimFluid


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
