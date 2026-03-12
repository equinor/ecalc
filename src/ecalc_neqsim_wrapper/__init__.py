# Import last to avoid circular import (fluid_service depends on thermo)
from ecalc_neqsim_wrapper.fluid_service import NeqSimFluidService
from ecalc_neqsim_wrapper.java_service import NeqsimService, Py4JConfig
from ecalc_neqsim_wrapper.thermo import NeqsimFluid
from libecalc.infrastructure.cache_service import CacheConfig, CacheService, LRUCache

__all__ = [
    "CacheConfig",
    "CacheService",
    "LRUCache",
    "NeqSimFluidService",
    "NeqsimFluid",
    "NeqsimService",
    "Py4JConfig",
]


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
