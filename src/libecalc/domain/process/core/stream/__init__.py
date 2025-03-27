from libecalc.domain.process.core.stream.conditions import ProcessConditions

# Define all classes in the public API
__all__ = ["Stream", "ProcessConditions", "Fluid"]


# Lazily import classes to avoid circular imports
def __getattr__(name):
    if name == "Fluid":
        from libecalc.domain.process.core.stream.fluid import Fluid

        return Fluid
    elif name == "Stream":
        from libecalc.domain.process.core.stream.stream import Stream

        return Stream
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
