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
