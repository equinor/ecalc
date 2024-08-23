from io import StringIO

import pytest

from libecalc.presentation.yaml.yaml_entities import ResourceStream
from libecalc.presentation.yaml.yaml_models.exceptions import YamlError
from libecalc.presentation.yaml.yaml_models.yaml_model import ReaderType, YamlConfiguration

invalid_models = [
    (
        """
`INSTALLATIONS: []
""",
        "invalid_token_start",
    ),
    (
        """
{}INSTALLATIONS: []
""",
        "invalid_object_start",
    ),
    (
        """
VARIABLES:
    some_var: 1
    some_var: 2
""",
        "duplicate_keys",
    ),
]


@pytest.mark.parametrize("invalid_model,description", invalid_models)
@pytest.mark.parametrize("yaml_model_type", ReaderType)
def test_invalid_models(invalid_model: str, description: str, yaml_model_type: ReaderType):
    yaml_reader = YamlConfiguration.Builder.get_yaml_reader(yaml_model_type)
    with pytest.raises(YamlError) as exc_info:
        yaml_reader.read(ResourceStream(name=description, stream=StringIO(invalid_model)))

    assert str(exc_info.value)
