from typing import Union

from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_trains import (
    YamlCompressorTrain,
)
from libecalc.presentation.yaml.yaml_types.models.yaml_turbine import YamlTurbine

try:
    from pydantic.v1 import Field
except ImportError:
    from pydantic import Field
from typing_extensions import Annotated

from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_chart import (
    YamlCompressorChart,
)
from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_with_turbine import (
    YamlCompressorWithTurbine,
)
from libecalc.presentation.yaml.yaml_types.models.yaml_fluid import YamlFluidModel

YamlModel = Annotated[
    Union[
        YamlCompressorChart,
        YamlCompressorWithTurbine,
        YamlFluidModel,
        YamlTurbine,
        YamlCompressorTrain,
    ],
    Field(discriminator="type"),
]
