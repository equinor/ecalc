import enum


class EcalcErrorType(str, enum.Enum):
    """Valid error types in libecalc."""

    CLIENT_ERROR = "User error"
    """The user made an error"""

    SERVER_ERROR = "Server error"  # TODO: Does not make sense in a library, rename?
    """ The eCalc library failed"""


class EcalcError(Exception):
    """Base eCalc library exception."""

    title: str | None = None
    message: str | None = None

    def __init__(self, title: str, message: str, error_type: EcalcErrorType = EcalcErrorType.CLIENT_ERROR):
        super().__init__()

        self.title = title
        self.message = message
        self.error_type = error_type

    def __str__(self):
        return f"{self.title}: {self.message}"


class IncompatibleDataError(EcalcError):
    """The data provided by the user is invalid."""

    def __init__(self, message: str, title: str = "Incompatible Data"):
        super().__init__(title, message, error_type=EcalcErrorType.CLIENT_ERROR)


class DifferentLengthsError(IncompatibleDataError):
    """The data provided has incompatible lengths."""

    def __init__(self, message: str):
        super().__init__(title="Different Lengths", message=message)


class MissingKeyError(IncompatibleDataError):
    """The data provided is missing a required key."""

    def __init__(self, message: str):
        super().__init__(title="Missing Key", message=message)


class ProgrammingError(EcalcError):
    """The eCalc library has caused an error, and reached an invalid state. Likely a bug."""

    def __init__(self, message: str):
        super().__init__("Violation of programming rules", message, error_type=EcalcErrorType.SERVER_ERROR)


class IllegalStateException(EcalcError):
    """This exception should hopefully never occur, and indicates a bug in the code."""

    def __init__(self, message: str):
        super().__init__("Illegal state", message, error_type=EcalcErrorType.SERVER_ERROR)


class InvalidDateException(EcalcError): ...


class InvalidResourceException(EcalcError):
    """
    Base exception for resource
    """

    pass


class InvalidHeaderException(InvalidResourceException):
    def __init__(self, message: str):
        super().__init__("Invalid header", message, error_type=EcalcErrorType.CLIENT_ERROR)


class HeaderNotFoundException(InvalidResourceException):
    """Resource is missing header."""

    def __init__(self, header: str):
        self.header = header
        super().__init__("Missing header(s)", f"Header '{header}' not found", error_type=EcalcErrorType.CLIENT_ERROR)


class ColumnNotFoundException(InvalidResourceException):
    """Resource is missing column"""

    def __init__(self, header: str):
        self.header = header
        super().__init__(
            "Missing column", f"Column matching header '{header}' is missing.", error_type=EcalcErrorType.CLIENT_ERROR
        )


class InvalidColumnException(InvalidResourceException):
    def __init__(self, header: str, message: str, row: int = None):
        self.header = header
        self.row = row
        super().__init__(title="Invalid column", message=message)


class NoColumnsException(InvalidResourceException):
    """Resource contains no columns"""

    def __init__(self):
        super().__init__("No columns", "The resource contains no columns, it should have at least one.")
