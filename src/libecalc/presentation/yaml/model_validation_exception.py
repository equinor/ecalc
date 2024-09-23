from textwrap import indent
from typing import List

from libecalc.presentation.yaml.validation_errors import ModelValidationError, ValidationError


class ModelValidationException(ValidationError):
    def __init__(self, errors: List[ModelValidationError]):
        self._errors = errors
        super().__init__("Model is not valid")

    def error_count(self) -> int:
        return len(self._errors)

    def errors(self) -> List[ModelValidationError]:
        return self._errors

    def __str__(self):
        msg = "Validation error\n\n"
        errors = "\n\n".join(map(str, self._errors))
        errors = indent(errors, "\t")
        msg += errors
        return msg
