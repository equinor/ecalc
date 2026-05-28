from typing import Literal, TypeVar

from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.process.yaml_process_units import (
    YamlProcessUnit,
)

type ProcessPipelineReference = str  # TODO: validate correct reference


TTarget = TypeVar("TTarget")


class YamlItem[TTarget](YamlBase):
    target: TTarget | ProcessPipelineReference


class YamlProcessPipeline(YamlBase):
    type: Literal["SERIAL"]
    name: ProcessPipelineReference
    items: list[YamlItem[YamlProcessUnit]]
