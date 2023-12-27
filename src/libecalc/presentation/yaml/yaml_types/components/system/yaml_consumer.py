from typing import Dict

from libecalc.presentation.yaml.yaml_types.yaml_stream_conditions import (
    YamlStreamConditions,
)

StreamID = str
YamlConsumerStreamConditions = Dict[StreamID, YamlStreamConditions]
