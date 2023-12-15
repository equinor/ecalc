from typing import Union

try:
    from pydantic.v1 import Field
except ImportError:
    from pydantic import Field
from typing_extensions import Annotated

from libecalc.dto import Turbine
from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_chart import (
    YamlCompressorChart,
)
from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_with_turbine import (
    YamlCompressorWithTurbine,
)
from libecalc.presentation.yaml.yaml_types.models.yaml_fluid import YamlFluidModel

YamlModel = Annotated[
    Union[YamlCompressorChart, YamlCompressorWithTurbine, YamlFluidModel, Turbine], Field(discriminator="type")
]
