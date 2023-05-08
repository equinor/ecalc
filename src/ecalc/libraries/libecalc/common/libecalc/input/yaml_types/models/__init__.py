from typing import Union

from libecalc.dto import Turbine
from libecalc.input.yaml_types.models.compressor_chart import CompressorChart
from libecalc.input.yaml_types.models.compressor_with_turbine import (
    CompressorWithTurbine,
)
from libecalc.input.yaml_types.models.fluid import FluidModel
from pydantic import Field
from typing_extensions import Annotated

Model = Annotated[Union[CompressorChart, CompressorWithTurbine, FluidModel, Turbine], Field(discriminator="type")]
