from typing import Literal, Union

from pydantic import ConfigDict, Field
from typing_extensions import Annotated

from libecalc.presentation.yaml.yaml_types import YamlBase


class YamlTimeSeriesCollectionBase(YamlBase):
    model_config = ConfigDict(title="TimeSeries", use_enum_values=True)

    name: str = Field(
        ...,
        title="NAME",
        description="Name of the time series.\n\n$ECALC_DOCS_KEYWORDS_URL/NAME",
    )
    file: str = Field(
        ...,
        title="FILE",
        description="Specifies the name of a time series input file.\n\n$ECALC_DOCS_KEYWORDS_URL/FILE",
    )
    type: Literal["DEFAULT", "MISCELLANEOUS"] = Field(
        ...,
        title="TYPE",
        description="Defines the type of time series input file.\n\n$ECALC_DOCS_KEYWORDS_URL/TYPE",
    )
    influence_time_vector: bool = Field(
        True,
        title="INFLUENCE_TIME_VECTOR",
        description="Determines if the time steps in this input source will contribute to the global time vector.\n\n$ECALC_DOCS_KEYWORDS_URL/INFLUENCE_TIME_VECTOR",
    )


class YamlDefaultTimeSeriesCollection(YamlTimeSeriesCollectionBase):
    type: Literal["DEFAULT"] = Field(
        ...,
        title="TYPE",
        description="Defines the type of time series input file.\n\n$ECALC_DOCS_KEYWORDS_URL/TYPE",
    )

    interpolation_type: Literal["RIGHT"] = Field(
        None,
        title="INTERPOLATION_TYPE",
        description="Defines how the time series are interpolated between input time steps.\n\n$ECALC_DOCS_KEYWORDS_URL/INTERPOLATION_TYPE",
    )


class YamlMiscellaneousTimeSeriesCollection(YamlTimeSeriesCollectionBase):
    type: Literal["MISCELLANEOUS"] = Field(
        ...,
        title="TYPE",
        description="Defines the type of time series input file.\n\n$ECALC_DOCS_KEYWORDS_URL/TYPE",
    )
    extrapolation: bool = Field(
        False,
        title="EXTRAPOLATION",
        description="Defines whether the rates in the source should be set to 0 after last time step or constant equal to value at last time step after time interval.\n\n$ECALC_DOCS_KEYWORDS_URL/EXTRAPOLATION",
    )
    interpolation_type: Literal["LEFT", "RIGHT", "LINEAR"] = Field(
        ...,
        title="INTERPOLATION_TYPE",
        description="Defines how the time series are interpolated between input time steps.\n\n$ECALC_DOCS_KEYWORDS_URL/INTERPOLATION_TYPE",
    )


YamlTimeSeriesCollection = Annotated[
    Union[YamlDefaultTimeSeriesCollection, YamlMiscellaneousTimeSeriesCollection],
    Field(discriminator="type"),
]
