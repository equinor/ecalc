import enum
from dataclasses import dataclass


class EcalcErrorType(str, enum.Enum):
    """Valid error types in libecalc."""

    CLIENT_ERROR = "User error"
    """The user made an error"""

    SERVER_ERROR = "Server error"  # TODO: Does not make sense in a library, rename?
    """ The eCalc library failed"""


class EcalcError(Exception):
    """Base eCalc library exception."""

    def __init__(self, title: str, message: str, error_type: EcalcErrorType = EcalcErrorType.CLIENT_ERROR):
        super().__init__()

        self.title: str = title
        self.message: str = message
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


@dataclass
class ResourceFileMark:
    row: int
    column: str


class InvalidResourceException(EcalcError):
    """
    Base exception for resource
    """

    def __init__(self, title: str, message: str, file_mark: ResourceFileMark = None):
        self.title = title
        self.message = message
        self.file_mark = file_mark
        super().__init__(title=title, message=message, error_type=EcalcErrorType.CLIENT_ERROR)


class InvalidHeaderException(InvalidResourceException):
    def __init__(self, message: str):
        super().__init__(
            "Invalid header",
            message,
        )


class HeaderNotFoundException(InvalidResourceException):
    """Resource is missing header."""

    def __init__(self, header: str):
        self.header = header
        super().__init__(
            "Missing header(s)", f"Header '{header}' not found", file_mark=ResourceFileMark(row=0, column=header)
        )


class ColumnNotFoundException(InvalidResourceException):
    """Resource is missing column"""

    def __init__(self, header: str):
        self.header = header
        super().__init__(
            "Missing column",
            f"Column matching header '{header}' is missing.",
            file_mark=ResourceFileMark(row=0, column=header),
        )


class InvalidColumnException(InvalidResourceException):
    def __init__(self, header: str, message: str, row_index: int = None):
        self.header = header
        if row_index is not None:
            self.row = row_index + 1
        else:
            self.row = 0
        super().__init__(
            title="Invalid column", message=message, file_mark=ResourceFileMark(row=self.row, column=header)
        )


class NoColumnsException(InvalidResourceException):
    """Resource contains no columns"""

    def __init__(self):
        super().__init__("No columns", "The resource contains no columns, it should have at least one.")
