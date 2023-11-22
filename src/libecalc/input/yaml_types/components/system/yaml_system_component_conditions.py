from typing import List, Optional

from libecalc.common.string_utils import get_duplicates
from libecalc.input.yaml_types import YamlBase
from pydantic import Field, validator


class YamlCrossover(YamlBase):
    class Config:
        allow_population_by_field_name = True

    name: str = Field(
        None,
        title="NAME",
        description="The name of the stream. "
        "Can be used to identify the crossover stream in multiple streams compressor train",
    )
    from_: str = Field(
        ...,
        title="FROM",
        description="Target component for crossover",
        alias="FROM",
    )
    to: str = Field(
        ...,
        title="TO",
        description="Target component for crossover",
    )


class YamlSystemComponentConditions(YamlBase):
    crossover: Optional[List[YamlCrossover]] = Field(
        None,
        title="Crossover",
        description=(
            "CROSSOVER specifies if rates are to be crossed over to another consumer if rate capacity is exceeded. If the energy"
            " consumption calculation is not successful for a consumer, and the consumer has a valid cross-over defined, the"
            " consumer will be allocated its maximum rate and the exceeding rate will be added to the cross-over consumer.\n"
            "To avoid loops, a consumer can only be either receiving or giving away rate. For a cross-over to be valid, the"
            ' discharge pressure at the consumer "receiving" overshooting rate must be higher than or equal to the discharge'
            ' pressure of the "sending" consumer. This is because it is possible to choke pressure down to meet the outlet pressure'
            ' in a flow line with lower pressure, but not possible to "pressure up" in the crossover flow line.\n'
            "Some examples show how the crossover logic works:\n"
            "Crossover is given as and list of integer values for the first position is the first consumer, second position is"
            " the second consumer, etc. The number specifies which consumer to send cross-over flow to, and 0 signifies no"
            " cross-over possible. Note that we use 1-index here.\n"
            "Example 1:\n"
            "Two consumers where there is a cross-over such that if the rate for the first consumer exceeds its capacity,"
            " the excess rate will be processed by the second consumer. The second consumer can not cross-over to anyone.\n"
            "CROSSOVER: \n"
            "  - FROM: consumer1 \n"
            "    TO: consumer2 \n"
            "Example 2:\n"
            "The first and second consumers may both send exceeding rate to the third consumer if their capacity is exceeded.\n"
            "CROSSOVER: \n"
            "  - FROM: consumer1 \n"
            "    TO: consumer3 \n"
            "  - FROM: consumer2 \n"
            "    TO: consumer3 \n"
        ),
    )

    @validator("crossover")
    def ensure_one_crossover_out(cls, crossover: Optional[List[YamlCrossover]]):
        if crossover is None:
            return None
        crossover_out = [c.from_ for c in crossover]
        unique_crossover_out = set(crossover_out)
        if len(unique_crossover_out) != len(crossover_out):
            raise ValueError(
                f"Only one crossover per consumer is currently supported. Component(s) with several crossover streams "
                f"are {', '.join(sorted(get_duplicates(crossover_out)))}"
            )

        return crossover
