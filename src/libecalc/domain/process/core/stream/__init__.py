from libecalc.domain.process.core.stream.conditions import ProcessConditions

# Use __getattr__ for lazy loading to break circular imports
__all__ = [
    "Stream",
    "ProcessConditions",
    "NeqSimThermoSystem",
    "ThermoSystemInterface",
    "StreamMixingStrategy",
    "SimplifiedStreamMixing",
]


def __getattr__(name):
    """Lazy load modules to prevent circular imports."""
    if name == "Stream":
        from libecalc.domain.process.core.stream.stream import Stream

        return Stream
    elif name in ("StreamMixingStrategy", "SimplifiedStreamMixing"):
        from libecalc.domain.process.core.stream.mixing import SimplifiedStreamMixing, StreamMixingStrategy

        return locals()[name]
    elif name in ("NeqSimThermoSystem", "ThermoSystemInterface"):
        from libecalc.domain.process.core.stream.thermo_system import NeqSimThermoSystem, ThermoSystemInterface

        return locals()[name]
    raise AttributeError(f"module {__name__} has no attribute {name}")
