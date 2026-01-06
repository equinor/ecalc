from textwrap import indent

from pydantic import ValidationError as PydanticValidationError

from libecalc.common.errors.exceptions import EcalcError
from libecalc.presentation.yaml.file_context import FileContext
from libecalc.presentation.yaml.validation_errors import Location, ModelValidationError, custom_errors


class ModelValidationException(EcalcError):
    def __init__(self, errors: list[ModelValidationError]):
        self._errors = errors
        super().__init__(title="Invalid model", message="Model is not valid")

    def error_count(self) -> int:
        return len(self._errors)

    def errors(self) -> list[ModelValidationError]:
        return self._errors

    def __str__(self):
        msg = "Validation error\n\n"
        errors = "\n\n".join(map(str, self._errors))
        errors = indent(errors, "\t")
        msg += errors
        return msg

    @classmethod
    def from_pydantic(cls, validation_error: PydanticValidationError, file_context: FileContext | None):
        model_validation_errors = []
        for error in custom_errors(e=validation_error):
            model_validation_errors.append(
                ModelValidationError(
                    message=error["msg"], location=Location.from_pydantic_loc(error["loc"]), file_context=file_context
                )
            )
        return cls(errors=model_validation_errors)
