from typing import Union

from pydantic import Field
from typing_extensions import Annotated

from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_chart import (
    YamlCompressorChart,
)
from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_trains import (
    YamlCompressorTrain,
)
from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_with_turbine import (
    YamlCompressorWithTurbine,
)
from libecalc.presentation.yaml.yaml_types.models.yaml_fluid import YamlFluidModel
from libecalc.presentation.yaml.yaml_types.models.yaml_turbine import YamlTurbine

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
