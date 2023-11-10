from typing import List, Optional

from pydantic import Field

from libecalc.expression.expression import ExpressionType
from libecalc.presentation.yaml.yaml_types import YamlBase


class YamlConsumerBase(YamlBase):
    name: str = Field(
        ...,
        title="NAME",
        description="Consumer name",
    )
    category: Optional[str] = Field(
        None,
        title="CATEGORY",
        description="User defined category",
    )


opt_expr_list = Optional[List[ExpressionType]]
