from libecalc.presentation.yaml.file_context import FileContext


class YamlError(Exception):
    def __init__(self, problem: str, file_context: FileContext | None = None):
        self.problem = problem
        self.file_context = file_context
        message = f"{problem}"
        if file_context is not None:
            message += str(file_context)

        super().__init__(message)


class DuplicateKeyError(YamlError):
    def __init__(self, key: str, file_context: FileContext):
        self.key = key
        super().__init__(f"Duplicate key {key!r} is found", file_context)
