from dataclasses import dataclass
from typing import Optional

import yaml

from libecalc.presentation.yaml.file_context import FileContext
from libecalc.presentation.yaml.validation_errors import Location


@dataclass
class ModelValidationError:
    message: str
    name: Optional[str] = None
    location: Optional[Location] = None
    data: Optional[dict] = None
    file_context: Optional[FileContext] = None

    @property
    def yaml(self) -> Optional[str]:
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


class ComponentValidationException(Exception):
    def __init__(self, errors: list[ModelValidationError]):
        self._errors = errors

    def errors(self) -> list[ModelValidationError]:
        return self._errors


class ComponentDtoValidationError(Exception):
    def __init__(self, errors: list[ModelValidationError]):
        self.errors = errors
        messages = [str(error) for error in errors]
        super().__init__("\n".join(messages))

    def error_count(self):
        return len(self.errors)
