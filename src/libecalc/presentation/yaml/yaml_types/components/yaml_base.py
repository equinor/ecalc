from typing import Optional

from pydantic import Field

from libecalc.dto.utils.validators import ComponentNameStr
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import (
    YamlExpressionType,
)


class YamlConsumerBase(YamlBase):
    name: ComponentNameStr = Field(
        ...,
        title="NAME",
        description="Consumer name",
    )
    category: Optional[str] = Field(
        None,
        title="CATEGORY",
        description="User defined category",
    )


opt_expr_list = Optional[list[YamlExpressionType]]
