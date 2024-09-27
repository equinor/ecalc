from datetime import datetime
from typing import Union

from libecalc.common.time_utils import Period
from libecalc.dto.types import ConsumerUserDefinedCategoryType
from libecalc.dto.utils.validators import ExpressionType


def validate_generator_set_power_from_shore(
    cable_loss: ExpressionType,
    max_usage_from_shore: ExpressionType,
    model_fields: dict,
    category: Union[dict, ConsumerUserDefinedCategoryType],
):
    if cable_loss is not None or max_usage_from_shore is not None:
        feedback_text = (
            f"{model_fields['cable_loss'].title} and " f"{model_fields['max_usage_from_shore'].title} are only valid"
        )
        if cable_loss is None:
            feedback_text = f"{model_fields['max_usage_from_shore'].title} is only valid"
        if max_usage_from_shore is None:
            feedback_text = f"{model_fields['cable_loss'].title} is only valid"

        if isinstance(category, ConsumerUserDefinedCategoryType):
            if category is not ConsumerUserDefinedCategoryType.POWER_FROM_SHORE:
                message = f"{feedback_text} for the category {ConsumerUserDefinedCategoryType.POWER_FROM_SHORE.value}, not for {category}."
                raise ValueError(message)
        else:
            if ConsumerUserDefinedCategoryType.POWER_FROM_SHORE not in category.values():
                message = (
                    f"{feedback_text} for the category {ConsumerUserDefinedCategoryType.POWER_FROM_SHORE.value}"
                    f", not for {category[Period(datetime(1900, 1, 1))].value}."
                )
                raise ValueError(message)
