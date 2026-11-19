from io import StringIO
from typing import cast

from libecalc.presentation.yaml.yaml_entities import ResourceStream
from libecalc.presentation.yaml.yaml_models.yaml_model import ReaderType, YamlConfiguration, YamlValidator

yaml_with_lowercase_dict_keys = """
DEFINITIONS:
  FLUIDS:
    other_fluid:
      TYPE: PREDEFINED
      EOS_MODEL: SRK
      GAS_TYPE: MEDIUM
    dup_name:
      TYPE: PREDEFINED
      EOS_MODEL: SRK
      GAS_TYPE: MEDIUM
"""


def test_get_file_context_resolves_user_chosen_dict_keys():
    yaml_reader = YamlConfiguration.Builder.get_yaml_reader(ReaderType.PYYAML)
    model = cast(
        YamlValidator, yaml_reader.read(ResourceStream(name="test", stream=StringIO(yaml_with_lowercase_dict_keys)))
    )

    other_fluid_context = model.get_file_context(("DEFINITIONS", "FLUIDS", "other_fluid"))
    dup_name_context = model.get_file_context(("DEFINITIONS", "FLUIDS", "dup_name"))
    fluids_section_context = model.get_file_context(("DEFINITIONS", "FLUIDS"))

    assert other_fluid_context is not None
    assert dup_name_context is not None
    assert other_fluid_context != dup_name_context
    assert other_fluid_context != fluids_section_context
    assert dup_name_context != fluids_section_context
