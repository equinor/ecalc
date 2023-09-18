from typing import Union

from libecalc.dto import Turbine
from libecalc.input.yaml_types.models.yaml_compressor_chart import YamlCompressorChart
from libecalc.input.yaml_types.models.yaml_compressor_with_turbine import (
    YamlCompressorWithTurbine,
)
from libecalc.input.yaml_types.models.yaml_fluid import YamlFluidModel
from pydantic import Field
from typing_extensions import Annotated

YamlModel = Annotated[
    Union[YamlCompressorChart, YamlCompressorWithTurbine, YamlFluidModel, Turbine], Field(discriminator="type")
]
