import logging
from functools import cached_property

import pandas as pd

from libecalc.common.chart_type import ChartType
from libecalc.common.errors.exceptions import HeaderNotFoundException, InvalidColumnException
from libecalc.domain.process.value_objects.chart import ChartCurve
from libecalc.domain.process.value_objects.chart.chart import ChartData
from libecalc.domain.resource import Resource
from libecalc.presentation.yaml.mappers.utils import (
    YAML_UNIT_MAPPING,
    convert_efficiency_to_fraction,
    convert_head_to_joule_per_kg,
    convert_rate_to_am3_per_hour,
)
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords
from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_chart import YamlCurve, YamlUnits

logger = logging.getLogger(__name__)


def _all_numbers_equal(values: list[int | float]) -> bool:
    return len(set(values)) == 1


class UserDefinedChartData(ChartData):
    def __init__(self, curves: list[ChartCurve], control_margin: float | None):
        self._curves = sorted(curves, key=lambda x: x.speed)
        self._control_margin = control_margin  # TODO: Set to 0 if not set? Default: 0?
        self._origin_of_chart_data = ChartType.SINGLE_SPEED if len(curves) == 1 else ChartType.VARIABLE_SPEED

    @property
    def origin_of_chart_data(self) -> ChartType:
        return self._origin_of_chart_data

    @property
    def control_margin(self) -> float | None:
        return self._control_margin

    @cached_property
    def _adjusted_curves(self) -> list[ChartCurve]:
        return [curve.adjust_for_control_margin(self._control_margin) for curve in self._curves]

    @cached_property
    def _original_curves(self) -> list[ChartCurve]:
        return [curve.deep_copy() for curve in self._curves]

    def get_original_curves(self) -> list[ChartCurve]:
        return self._original_curves

    def get_adjusted_curves(self) -> list[ChartCurve]:
        return self._adjusted_curves

    @classmethod
    def from_resource(
        cls, resource: Resource, units: YamlUnits, is_single_speed: bool, control_margin: float | None = None
    ) -> "UserDefinedChartData":
        rate_unit = YAML_UNIT_MAPPING[units.rate]
        head_unit = YAML_UNIT_MAPPING[units.head]
        efficiency_unit = YAML_UNIT_MAPPING[units.efficiency]
        if is_single_speed:
            try:
                speed_values = resource.get_float_column(EcalcYamlKeywords.consumer_chart_speed)

                if not _all_numbers_equal(speed_values):
                    raise InvalidColumnException(
                        header=EcalcYamlKeywords.consumer_chart_speed,
                        message="All speeds should be equal when creating a single-speed chart.",
                    )
                # Get first speed, all are equal.
                speed = speed_values[0]
            except HeaderNotFoundException:
                logger.debug("Speed not specified for single speed chart, setting speed to 1.")
                speed = 1

            efficiency_values = resource.get_float_column(EcalcYamlKeywords.consumer_chart_efficiency)
            rate_values = resource.get_float_column(EcalcYamlKeywords.consumer_chart_rate)
            head_values = resource.get_float_column(EcalcYamlKeywords.consumer_chart_head)
            curves = [
                ChartCurve(
                    speed_rpm=speed,
                    rate_actual_m3_hour=convert_rate_to_am3_per_hour(rate_values, rate_unit),
                    polytropic_head_joule_per_kg=convert_head_to_joule_per_kg(head_values, head_unit),
                    efficiency_fraction=convert_efficiency_to_fraction(efficiency_values, efficiency_unit),
                )
            ]
        else:
            resource_headers = resource.get_headers()

            if "SPEED" not in resource_headers:
                raise InvalidColumnException(message="Resource is missing SPEED header!", header="SPEED")

            resource_data = []
            for header in resource_headers:
                column = resource.get_float_column(header)
                resource_data.append(column)
            df = pd.DataFrame(data=resource_data, index=resource_headers).transpose().astype(float)
            grouped_by_speed = df.groupby(EcalcYamlKeywords.consumer_chart_speed, sort=False)
            curves = [
                ChartCurve(
                    speed_rpm=group,  # type: ignore[arg-type]
                    rate_actual_m3_hour=convert_rate_to_am3_per_hour(
                        list(grouped_by_speed.get_group(group)[EcalcYamlKeywords.consumer_chart_rate]), rate_unit
                    ),
                    polytropic_head_joule_per_kg=convert_head_to_joule_per_kg(
                        list(grouped_by_speed.get_group(group)[EcalcYamlKeywords.consumer_chart_head]), head_unit
                    ),
                    efficiency_fraction=convert_efficiency_to_fraction(
                        list(grouped_by_speed.get_group(group)[EcalcYamlKeywords.consumer_chart_efficiency]),
                        efficiency_unit,
                    ),
                )
                for group in grouped_by_speed.groups
            ]

        return cls(curves=curves, control_margin=control_margin)

    @classmethod
    def from_yaml_curves(
        cls,
        curves: list[YamlCurve],
        units: YamlUnits,
        control_margin: float | None = None,
    ) -> "UserDefinedChartData":
        rate_unit = YAML_UNIT_MAPPING[units.rate]
        head_unit = YAML_UNIT_MAPPING[units.head]
        efficiency_unit = YAML_UNIT_MAPPING[units.efficiency]

        return cls(
            curves=[
                ChartCurve(
                    speed_rpm=curve.speed,
                    rate_actual_m3_hour=convert_rate_to_am3_per_hour(curve.rate, rate_unit),
                    polytropic_head_joule_per_kg=convert_head_to_joule_per_kg(curve.head, head_unit),
                    efficiency_fraction=convert_efficiency_to_fraction(curve.efficiency, efficiency_unit),
                )
                for curve in curves
            ],
            control_margin=control_margin,
        )
