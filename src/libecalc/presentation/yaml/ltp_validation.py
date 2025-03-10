from datetime import datetime

from libecalc.common.time_utils import Period
from libecalc.dto.types import ConsumerUserDefinedCategoryType
from libecalc.dto.utils.validators import ExpressionType


def validate_generator_set_power_from_shore(
    cable_loss: ExpressionType,
    max_usage_from_shore: ExpressionType,
    category: dict | ConsumerUserDefinedCategoryType,
):
    if cable_loss is not None or max_usage_from_shore is not None:
        CABLE_LOSS = "CABLE_LOSS"
        MAX_USAGE_FROM_SHORE = "MAX_USAGE_FROM_SHORE"
        feedback_text = f"{CABLE_LOSS} and " f"{MAX_USAGE_FROM_SHORE} are only valid"
        if cable_loss is None:
            feedback_text = f"{MAX_USAGE_FROM_SHORE} is only valid"
        if max_usage_from_shore is None:
            feedback_text = f"{CABLE_LOSS} is only valid"

        if isinstance(category, ConsumerUserDefinedCategoryType):
            if category is not ConsumerUserDefinedCategoryType.POWER_FROM_SHORE:
                message = f"{feedback_text} for the category {ConsumerUserDefinedCategoryType.POWER_FROM_SHORE.value}, not for {category.value}."
                raise ValueError(message)
        else:
            if ConsumerUserDefinedCategoryType.POWER_FROM_SHORE not in category.values():
                message = (
                    f"{feedback_text} for the category {ConsumerUserDefinedCategoryType.POWER_FROM_SHORE.value}"
                    f", not for {category[Period(datetime(1900, 1, 1))].value}."
                )
                raise ValueError(message)
