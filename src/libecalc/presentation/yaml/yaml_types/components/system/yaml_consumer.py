from typing import Dict

from libecalc.presentation.yaml.yaml_types.yaml_stream_conditions import (
    YamlStreamConditions,
)

# Currently we have the same stream conditions for consumer and consumer system
# This may change, as there may be different requirements and we may want to
# write different docs for them, but for now they share
StreamID = str
YamlConsumerStreamConditions = Dict[StreamID, YamlStreamConditions]
