import pytest
from libecalc.input.yaml_types.components.compressor import Compressor
from libecalc.input.yaml_types.components.compressor_system import (
    CompressorSystem,
    OperationalSettings,
)
from pydantic import ValidationError


class TestCompressorSystem:
    def test_show_bad_error_message_temporal_model(self):
        """Test that shows how a temporal model (or any union without discriminator) will be difficult to parse with a
        good error message in the yaml models. The user would not expect to get 'value is not a valid dict' for
        operational settings if not specifying a date in the yaml model. Pydantic still shows an error for that.
        """
        with pytest.raises(ValidationError) as exc_info:
            CompressorSystem(
                name="name",
                category="category",
                consumers=[
                    Compressor(
                        category="category",
                        name="Compressor",
                        energy_usage_model="ref",
                    )
                ],
                operational_settings=[OperationalSettings(**{"wrong_key": "wrong_value"})],
            )

        assert (
            str(exc_info.value) == "1 validation error for OperationalSettings\n"
            "wrong_key\n"
            "  extra fields not permitted (type=value_error.extra)"
        )
