from jpype import JException  # pyright: ignore[reportMissingTypeStubs]
from py4j.protocol import Py4JError  # pyright: ignore[reportMissingTypeStubs]

from libecalc.process.fluid_stream.exceptions import FluidFlashCalculationError

# Unified tuple of Java bridge exception types for except clauses.
# Py4JError is the base for all Py4J exceptions (including Py4JJavaError, Py4JNetworkError).
# JException is the base for all Java exceptions when using JPype.
JAVA_ERRORS: tuple[type[Exception], ...] = (Py4JError, JException)


class NeqsimError(Exception):
    """Base class for NeqSim related errors"""

    pass


class NeqsimPhaseError(NeqsimError):
    """Error raised when there's an issue with phase handling in NeqSim"""

    pass


class NeqsimComponentError(NeqsimError):
    """Error raised when there's an issue with component handling in NeqSim"""

    def __init__(self, component_name: str):
        self.component_name = component_name
        message = f"Unknown component '{component_name}' from NeqSim. Check if the component is supported in eCalc."
        super().__init__(message)


class NeqsimFlashCalculationError(NeqsimError, FluidFlashCalculationError):
    """Error raised when a NeqSim flash calculation fails or returns an unusable state."""

    def __init__(self, message: str):
        super().__init__(message)
