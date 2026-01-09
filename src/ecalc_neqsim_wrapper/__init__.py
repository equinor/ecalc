from ecalc_neqsim_wrapper.cache_service import CacheConfig, CacheService, LRUCache

# Import last to avoid circular import (fluid_service depends on thermo)
from ecalc_neqsim_wrapper.fluid_service import NeqSimFluidService
from ecalc_neqsim_wrapper.java_service import NeqsimService
from ecalc_neqsim_wrapper.thermo import NeqsimFluid

__all__ = [
    "CacheConfig",
    "CacheService",
    "LRUCache",
    "NeqSimFluidService",
    "NeqsimFluid",
    "NeqsimService",
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
