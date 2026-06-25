from typing import Literal, TypeVar

from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.process.yaml_process_references import ProcessPipelineReference
from libecalc.presentation.yaml.yaml_types.process.yaml_process_units import (
    YamlProcessUnit,
)

TTarget = TypeVar("TTarget")


class YamlItem[TTarget](YamlBase):
    target: TTarget | ProcessPipelineReference


class YamlProcessPipeline(YamlBase):
    type: Literal["SERIAL"]
    name: str
    items: list[YamlItem[YamlProcessUnit]]
