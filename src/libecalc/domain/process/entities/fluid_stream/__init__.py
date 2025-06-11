from libecalc.domain.process.entities.fluid_stream.conditions import ProcessConditions

# Use __getattr__ for lazy loading to break circular imports
__all__ = [
    "Stream",
    "ProcessConditions",
    "NeqSimThermoSystem",
    "SimplifiedStreamMixing",
]


def __getattr__(name):
    """Lazy load modules to prevent circular imports."""
    if name == "Stream":
        from libecalc.domain.process.entities.fluid_stream.fluid_stream import FluidStream

        return FluidStream
    elif name == "SimplifiedStreamMixing":
        from libecalc.domain.process.entities.fluid_stream.mixing import SimplifiedStreamMixing

        return SimplifiedStreamMixing
    elif name == "NeqSimThermoSystem":
        from libecalc.domain.process.entities.fluid_stream.thermo_system import NeqSimThermoSystem

        return NeqSimThermoSystem
    raise AttributeError(f"module {__name__} has no attribute {name}")
