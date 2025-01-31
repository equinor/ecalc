from typing import TypeVar, Union

from libecalc.presentation.yaml.yaml_types.components.train.yaml_train import YamlTrain
from libecalc.presentation.yaml.yaml_types.components.yaml_compressor import (
    YamlCompressor,
)
from libecalc.presentation.yaml.yaml_types.components.yaml_pump import YamlPump

TYamlConsumer = TypeVar("TYamlConsumer", bound=Union[YamlCompressor, YamlPump, YamlTrain])
