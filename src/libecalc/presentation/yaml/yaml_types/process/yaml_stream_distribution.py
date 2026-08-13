from pydantic import Field
from typing import Literal, Annotated

from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import YamlExpressionType
from libecalc.presentation.yaml.yaml_types.process.yaml_process_references import InstanceReference
from libecalc.presentation.yaml.yaml_types.streams.yaml_inlet_stream import YamlInletStream


class YamlOverflow(YamlBase):
    from_reference: InstanceReference
    to_reference: InstanceReference


class YamlCommonStreamSetting(YamlBase):
    rate_fractions: list[YamlExpressionType]
    overflow: list[YamlOverflow] | None = None


class YamlCommonStreamDistribution(YamlBase):
    method: Literal["COMMON_STREAM"]
    inlet_stream: InstanceReference | YamlInletStream
    settings: list[YamlCommonStreamSetting]


class YamlIndividualStreamDistribution(YamlBase):
    method: Literal["INDIVIDUAL_STREAMS"]
    inlet_streams: list[InstanceReference | YamlInletStream]


YamlStreamDistribution = Annotated[
    YamlCommonStreamDistribution | YamlIndividualStreamDistribution, Field(discriminator="method")
]
