from typing import Annotated, Literal

from pydantic import ConfigDict, Field

from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_chart import UnitsField, YamlCurve, YamlUnits
from libecalc.presentation.yaml.yaml_types.yaml_data_or_file import DataOrFile


class YamlPumpChart(YamlBase):
    model_config = ConfigDict(title="PUMP_CHART")

    curves: Annotated[
        DataOrFile[list[YamlCurve]],
        Field(
            title="CURVES",
            description="Pump chart curves, one per speed. A single speed gives a single-speed pump.",
        ),
    ]
    units: YamlUnits = UnitsField()


class YamlPumpModel(YamlBase):
    """A pump model: a pump chart and an optional minimum flow rate."""

    model_config = ConfigDict(title="PUMP_MODEL")

    type: Literal["PUMP_CHART"]
    chart: Annotated[YamlPumpChart, Field(title="CHART", description="The pump chart.")]
    minimum_flow_rate: Annotated[
        float | None,
        Field(
            title="MINIMUM_FLOW_RATE",
            description="Minimum pump flow [m3/h]. Defaults to the chart minimum. The pump recirculates up to it.",
        ),
    ] = None
