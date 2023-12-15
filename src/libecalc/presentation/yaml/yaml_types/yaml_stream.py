try:
    from pydantic.v1 import Field
except ImportError:
    from pydantic import Field

from libecalc.presentation.yaml.yaml_types import YamlBase


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
        description="Source component for crossover",
        alias="FROM",
    )
    to: str = Field(
        ...,
        title="TO",
        description="Target component for crossover",
    )


class YamlStream(YamlBase):
    class Config:
        allow_population_by_field_name = True

    name: str = Field(
        None,
        title="NAME",
        description="The name of the stream. ",
    )
    from_: str = Field(
        ...,
        title="FROM",
        description="The component the stream comes from.",
        alias="FROM",
    )
    to: str = Field(
        ...,
        title="TO",
        description="The component the stream goes to.",
    )
