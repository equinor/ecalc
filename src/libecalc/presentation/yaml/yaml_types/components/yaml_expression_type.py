from typing import Annotated

from pydantic import AfterValidator
from pydantic_core import PydanticCustomError
from pydantic_core.core_schema import ValidationInfo

from libecalc.expression.expression import (
    Expression,
    ExpressionType,
    InvalidExpressionError,
)
from libecalc.expression.expression_evaluator import TokenTag
from libecalc.presentation.yaml.yaml_validation_context import (
    YamlModelValidationContextNames,
)


def validate_expression(value: ExpressionType, info: ValidationInfo) -> ExpressionType:
    if info.context is None or YamlModelValidationContextNames.expression_tokens not in info.context:
        # Skip if context not provided
        return value

    available_expression_tokens = info.context[YamlModelValidationContextNames.expression_tokens]
    unknown_tokens = []
    try:
        tokens = Expression.validate(expression=value)
        for token in tokens:
            if token.tag == TokenTag.reference and token.value not in available_expression_tokens:
                unknown_tokens.append(token.value)

        if len(unknown_tokens) > 0:
            expression_references_string = ", ".join(unknown_tokens)
            raise PydanticCustomError(
                "expression_reference_not_found",
                "Expression reference(s) {expression_references_string} does not exist.",
                {
                    "expression_references_string": expression_references_string,
                    "expression_references": unknown_tokens,
                },
            )
    except InvalidExpressionError as e:
        raise ValueError(str(e)) from e

    return value


YamlExpressionType = Annotated[
    ExpressionType,
    AfterValidator(validate_expression),
]
