class FormatterError(Exception):
    pass


class IncorrectInput(FormatterError):
    def __init__(self, message: str = "Incorrect input"):
        super().__init__(message)


class IncompatibleData(IncorrectInput):
    def __init__(self, message: str = "Incompatible data"):
        super().__init__(message)
