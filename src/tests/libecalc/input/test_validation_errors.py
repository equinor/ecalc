import pytest
from inline_snapshot import snapshot
from yaml import Mark

from libecalc.presentation.yaml.validation_errors import (
    DataValidationError,
    Location,
    _mark_error_lines,
)
from libecalc.presentation.yaml.yaml_entities import YamlDict


class TestDictValidationError:
    @pytest.mark.snapshot
    def test_dict(self):
        error = DataValidationError(data={"KEY": {"SUBKEY1": [1, 2, 3], "SUBKEY2": 1}}, message="SUBKEY1 is not valid")
        assert error.extended_message == snapshot("""\
Validation error

...
    KEY:
      SUBKEY1: [1, 2, 3]
      SUBKEY2: 1
...


Error Message(s):
SUBKEY1 is not valid\
""")

    @pytest.mark.snapshot
    def test_dict_node(self):
        data = YamlDict(
            {"KEY": {"SUBKEY1": [1, 2, 3], "SUBKEY2": 1}},
            start_mark=Mark(name="main.yaml", line=5, index=0, pointer=None, buffer=None, column=0),
        )
        error = DataValidationError(data=data, message="SUBKEY1 is not valid")
        assert error.extended_message == snapshot("""\
Validation error

...
    KEY:
      SUBKEY1: [1, 2, 3]
      SUBKEY2: 1
...

Object starting on line 6 in main.yaml

Error Message(s):
SUBKEY1 is not valid\
""")


@pytest.fixture
def yaml_text() -> str:
    return """NAME: test
ENERGY_USAGE_MODEL:
  TYPE: DIRECT
  LOAD: 5"""


class TestMarkErrorLines:
    def test_single_key(self, yaml_text):
        locs = [Location(keys=["models"])]
        actual = _mark_error_lines(yaml_text, locs=locs)
        assert (
            actual
            == """  NAME: test
  ENERGY_USAGE_MODEL:
    TYPE: DIRECT
    LOAD: 5"""
        )

    def test_remove_root_key(self, yaml_text):
        locs = [
            Location(
                keys=[
                    "__root__",
                    "models",
                ]
            )
        ]
        actual = _mark_error_lines(yaml_text, locs=locs)
        assert (
            actual
            == """  NAME: test
  ENERGY_USAGE_MODEL:
    TYPE: DIRECT
    LOAD: 5"""
        )
