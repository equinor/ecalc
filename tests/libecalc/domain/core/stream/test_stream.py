from unittest.mock import Mock, patch

import pytest

from libecalc.common.fluid import EoSModel
from libecalc.domain.process.core.stream.conditions import ProcessConditions
from libecalc.domain.process.core.stream.exceptions import NegativeMassRateException
from libecalc.domain.process.core.stream.fluid_factory import create_fluid_with_neqsim_engine
from libecalc.domain.process.core.stream.stream import Stream


@pytest.fixture
def mock_fluid():
    """Create a mock fluid for testing."""
    fluid = Mock(spec=create_fluid_with_neqsim_engine)
    return fluid


@pytest.fixture
def basic_stream(medium_composition):
    """Create a basic stream for testing."""
    eos_model = EoSModel.SRK
    fluid = create_fluid_with_neqsim_engine(composition=medium_composition, eos_model=eos_model)
    conditions = ProcessConditions(temperature_kelvin=300.0, pressure_bara=10.0)
    return Stream(fluid=fluid, conditions=conditions, mass_rate=1000.0)


class TestStream:
    """Test suite for the Stream class."""

    def test_init_and_basic_properties(self, mock_fluid):
        """Test initialization and basic property accessors."""
        conditions = ProcessConditions(temperature_kelvin=310.0, pressure_bara=20.0)
        stream = Stream(fluid=mock_fluid, conditions=conditions, mass_rate=100.0)

        # Verify basic attributes
        assert stream.fluid is mock_fluid
        assert stream.conditions is conditions
        assert stream.mass_rate == 100.0

        # Verify property accessors
        assert stream.temperature == 310.0
        assert stream.pressure == 20.0

    def test_create_stream_with_new_conditions(self, basic_stream):
        """Test creating a new stream with modified conditions."""
        new_conditions = ProcessConditions(temperature_kelvin=350.0, pressure_bara=15.0)

        new_stream = basic_stream.create_stream_with_new_conditions(new_conditions)

        # Verify new stream has the new conditions but same fluid
        assert new_stream.temperature == 350.0
        assert new_stream.pressure == 15.0
        assert new_stream.fluid is basic_stream.fluid

    @patch("libecalc.domain.process.core.stream.stream.Stream._stream_mixing_strategy")
    def test_mix(self, mock_mixing_strategy, basic_stream):
        """Test the static mix method."""
        streams = [basic_stream, basic_stream]  # Just mix the same stream for simplicity

        # Configure the mock
        mock_result = Mock(spec=Stream)
        mock_mixing_strategy.mix_streams.return_value = mock_result

        result = Stream.mix(streams)

        # Verify mixing strategy was called
        mock_mixing_strategy.mix_streams.assert_called_once_with(streams)
        assert result is mock_result

    def test_negative_mass_rate_exception(self, mock_fluid):
        """Test that NegativeMassRateException is raised for negative mass rate."""
        conditions = ProcessConditions(temperature_kelvin=310.0, pressure_bara=20.0)
        with pytest.raises(NegativeMassRateException):
            Stream(fluid=mock_fluid, conditions=conditions, mass_rate=-100.0)
