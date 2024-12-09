import pytest
from inline_snapshot import snapshot
from pydantic import ValidationError

from libecalc.testing.yaml_builder import YamlEmissionBuilder, YamlFuelTypeBuilder


@pytest.mark.snapshot
@pytest.mark.inlinesnapshot
def test_duplicate_emission_names():
    with pytest.raises(ValidationError) as exc_info:
        YamlFuelTypeBuilder().with_test_data().with_emissions(
            [
                YamlEmissionBuilder().with_test_data().with_name("co2").validate(),
                YamlEmissionBuilder().with_test_data().with_name("co2").validate(),
            ]
        ).validate()

    errors = exc_info.value.errors()
    assert len(errors) == 1

    assert errors[0]["msg"] == snapshot("Value error, EMISSIONS names must be unique. Duplicated names are: co2")
