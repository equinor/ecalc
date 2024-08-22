import pytest
from pydantic import ValidationError

from libecalc.presentation.yaml.yaml_types.components.system.yaml_system_component_conditions import (
    YamlSystemComponentConditions,
)
from libecalc.presentation.yaml.yaml_types.yaml_stream import YamlCrossover


class TestSystemComponentConditions:
    def test_validation_error_on_several_crossover_out_for_one_consumer(self):
        """
        Currently not allowed to have several crossover out from a consumer, as we have not implemented any logic to
        pick which stream/pipe to fill.
        """

        with pytest.raises(ValidationError) as exc_info:
            YamlSystemComponentConditions(
                crossover=[
                    YamlCrossover(
                        from_="consumer1",
                        to="consumer2",
                    ),
                    YamlCrossover(
                        from_="consumer1",
                        to="consumer3",
                    ),
                    YamlCrossover(
                        from_="consumer2",
                        to="consumer3",
                    ),
                    YamlCrossover(
                        from_="consumer2",
                        to="consumer4",
                    ),
                ]
            )
        assert (
            "Only one crossover out per consumer is currently supported. Component(s) with several crossover streams are consumer1, consumer2"
            in str(exc_info.value)
        )

    def test_valid_crossover(self):
        YamlSystemComponentConditions(
            crossover=[
                YamlCrossover(
                    from_="consumer1",
                    to="consumer2",
                ),
                YamlCrossover(
                    from_="consumer2",
                    to="consumer3",
                ),
            ]
        )
