from dataclasses import dataclass

import yaml

from libecalc.presentation.yaml.file_context import FileContext
from libecalc.presentation.yaml.validation_errors import Location


@dataclass
class ModelValidationError:
    message: str
    location: Location
    name: str | None = None
    data: dict | None = None
    file_context: FileContext | None = None

    @property
    def yaml(self) -> str | None:
        if self.data is None:
            return None

        return yaml.dump(self.data, sort_keys=False).strip()

    def error_message(self):
        msg = ""
        if self.file_context is not None:
            msg += f"Object starting on line {self.file_context.start.line_number}\n"
        yaml = self.yaml
        if yaml is not None:
            msg += "...\n"
            msg += yaml
            msg += "\n...\n\n"

        if self.location is not None and not self.location.is_empty():
            msg += f"Location: {self.location.as_dot_separated()}\n"

        if self.name is not None:
            msg += f"Name: {self.name}\n"

        msg += f"Message: {self.message}\n"
        return msg

    def __str__(self):
        return self.error_message()


class DomainValidationException(Exception):
    def __init__(self, errors: list[ModelValidationError] = None, message: str = None):
        self.message = message
        self._errors = errors or []
        super().__init__(message or "\n".join(str(error) for error in self._errors))

    def errors(self) -> list[ModelValidationError]:
        return self._errors

    def __str__(self):
        if self.message:
            return self.message
        return "\n".join(str(error) for error in self._errors)


class ComponentValidationException(DomainValidationException):
    pass


class InvalidRegularityException(DomainValidationException):
    def __init__(self, message: str):
        super().__init__(message=message)


class ProcessEqualLengthValidationException(DomainValidationException):
    pass


class ProcessNegativeValuesValidationException(DomainValidationException):
    pass


class ProcessMissingVariableValidationException(DomainValidationException):
    pass


class ProcessChartTypeValidationException(DomainValidationException):
    pass


class ProcessChartValueValidationException(DomainValidationException):
    pass


class ProcessPressureRatioValidationException(DomainValidationException):
    pass


class ProcessDischargePressureValidationException(DomainValidationException):
    pass


class ProcessDirectConsumerFunctionValidationException(DomainValidationException):
    pass


class ProcessHeaderValidationException(DomainValidationException):
    pass


class ProcessTurbineEfficiencyValidationException(DomainValidationException):
    pass


class ProcessCompressorEfficiencyValidationException(DomainValidationException):
    pass


class ProcessFluidModelValidationException(DomainValidationException):
    pass


class GeneratorSetHeaderValidationException(DomainValidationException):
    pass


class GeneratorSetEqualLengthValidationException(DomainValidationException):
    pass


class ComponentDtoValidationError(Exception):
    def __init__(self, errors: list[ModelValidationError]):
        self.errors = errors
        messages = [str(error) for error in errors]
        super().__init__("\n".join(messages))

    def error_count(self):
        return len(self.errors)
