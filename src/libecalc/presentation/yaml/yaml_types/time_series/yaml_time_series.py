from typing import Annotated, Literal, Union

from pydantic import ConfigDict, Field, field_validator

from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_validators.file_validators import (
    file_exists_validator,
)


class YamlTimeSeriesCollectionBase(YamlBase):
    model_config = ConfigDict(title="TimeSeries", use_enum_values=True)

    name: Annotated[
        str,
        Field(
            title="NAME",
            pattern=r"^[A-Za-z][A-Za-z0-9_]*$",
            description="Name of the time series.\n\n$ECALC_DOCS_KEYWORDS_URL/NAME",
        ),
    ]
    file: Annotated[
        str,
        Field(
            title="FILE",
            description="Specifies the name of a time series input file.\n\n$ECALC_DOCS_KEYWORDS_URL/FILE",
        ),
    ]
    type: Annotated[
        Literal["DEFAULT", "MISCELLANEOUS"],
        Field(
            title="TYPE",
            description="Defines the type of time series input file.\n\n$ECALC_DOCS_KEYWORDS_URL/TYPE",
        ),
    ]
    influence_time_vector: Annotated[
        bool,
        Field(
            title="INFLUENCE_TIME_VECTOR",
            description="Determines if the time steps in this input source will contribute to the global time vector.\n\n$ECALC_DOCS_KEYWORDS_URL/INFLUENCE_TIME_VECTOR",
        ),
    ] = True

    validate_file_exists = field_validator("file", mode="after")(file_exists_validator)


class YamlDefaultTimeSeriesCollection(YamlTimeSeriesCollectionBase):
    type: Annotated[
        Literal["DEFAULT"],
        Field(
            title="TYPE",
            description="Defines the type of time series input file.\n\n$ECALC_DOCS_KEYWORDS_URL/TYPE",
        ),
    ]


class YamlMiscellaneousTimeSeriesCollection(YamlTimeSeriesCollectionBase):
    type: Annotated[
        Literal["MISCELLANEOUS"],
        Field(
            title="TYPE",
            description="Defines the type of time series input file.\n\n$ECALC_DOCS_KEYWORDS_URL/TYPE",
        ),
    ]
    extrapolation: Annotated[
        bool,
        Field(
            title="EXTRAPOLATION",
            description="Defines whether the rates in the source should be set to 0 after last time step or constant equal to value at last time step after time interval.\n\n$ECALC_DOCS_KEYWORDS_URL/EXTRAPOLATION",
        ),
    ] = False
    interpolation_type: Annotated[
        Literal["LEFT", "RIGHT", "LINEAR"],
        Field(
            title="INTERPOLATION_TYPE",
            description="Defines how the time series are interpolated between input time steps.\n\n$ECALC_DOCS_KEYWORDS_URL/INTERPOLATION_TYPE",
        ),
    ]


YamlTimeSeriesCollection = Annotated[
    Union[YamlDefaultTimeSeriesCollection, YamlMiscellaneousTimeSeriesCollection],
    Field(discriminator="type"),
]
