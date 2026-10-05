import logging
import math
from dataclasses import dataclass

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.common.errors.exceptions import (
    EcalcError,
    HeaderNotFoundException,
    InvalidColumnException,
    InvalidResourceException,
    ResourceFileMark,
)
from libecalc.domain.process.value_objects.chart import ChartCurve
from libecalc.domain.process.value_objects.chart.base import (
    ChartCurveEfficiencyOutOfRangeError,
    ChartCurveHeadNotDecreasingError,
)
from libecalc.domain.process.value_objects.chart.user_defined_chart_data import UserDefinedChartData
from libecalc.domain.resource import Resource
from libecalc.presentation.yaml.mappers.utils import (
    YAML_UNIT_MAPPING,
    convert_efficiency_to_fraction,
    convert_head_to_joule_per_kg,
    convert_rate_to_am3_per_hour,
)
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords
from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_chart import YamlCurve, YamlEfficiencyUnits, YamlUnits

logger = logging.getLogger(__name__)

_EFFICIENCY_RANGE = {YamlEfficiencyUnits.FRACTION: "0 and 1", YamlEfficiencyUnits.PERCENTAGE: "0 and 100"}


@dataclass(frozen=True)
class ChartCurveInput:
    """Curve values as given in the file or YAML. `file_rows` are 1-based data rows, None for inline YAML."""

    speed: float
    rate: list[float]
    head: list[float]
    efficiency: list[float]
    units: YamlUnits
    file_rows: list[int] | None
    show_speed: bool


def _point_name(curve: ChartCurveInput, index: int) -> str:
    if curve.file_rows is not None:
        return f"row {curve.file_rows[index]}"
    return f"point {index + 1}"


def _chart_error(curve: ChartCurveInput, message: str, index: int, column: str) -> EcalcError:
    if curve.file_rows is None:
        return EcalcValidationException(message)
    return InvalidResourceException(
        title="Invalid chart",
        message=message,
        file_mark=ResourceFileMark(row=curve.file_rows[index], column=column),
    )


def _efficiency_error(curve: ChartCurveInput, error: ChartCurveEfficiencyOutOfRangeError) -> EcalcError:
    speed_text = f" at speed {curve.speed}" if curve.show_speed else ""
    invalid_indices = error.indices
    invalid_text = "; ".join(
        f"{_point_name(curve, index).capitalize()} has {curve.efficiency[index]}" for index in invalid_indices
    )
    return _chart_error(
        curve,
        f"Efficiency must be between {_EFFICIENCY_RANGE[curve.units.efficiency]} {curve.units.efficiency.value}"
        f"{speed_text}. {invalid_text}.",
        invalid_indices[0],
        EcalcYamlKeywords.consumer_chart_efficiency,
    )


def _head_error(curve: ChartCurveInput, error: ChartCurveHeadNotDecreasingError) -> EcalcError:
    speed_text = f" at speed {curve.speed}" if curve.show_speed else ""
    offending_pairs = error.pairs

    def describe(index: int) -> str:
        return (
            f"{_point_name(curve, index)} (rate {curve.rate[index]} {curve.units.rate.value}, "
            f"head {curve.head[index]} {curve.units.head.value})"
        )

    pairs_text = "; ".join(
        f"{describe(current)} does not have a lower head than {describe(previous)}"
        for previous, current in offending_pairs
    )
    previous, current = offending_pairs[0]
    marked_index = previous if math.isnan(curve.head[previous]) else current
    return _chart_error(
        curve,
        f"Head must decrease as rate increases{speed_text}. {pairs_text[0].upper()}{pairs_text[1:]}.",
        marked_index,
        EcalcYamlKeywords.consumer_chart_head,
    )


def _all_numbers_equal(values: list[int | float]) -> bool:
    return len(set(values)) == 1


def _create_curve(curve: ChartCurveInput) -> ChartCurve:
    try:
        return ChartCurve(
            speed_rpm=curve.speed,
            rate_actual_m3_hour=convert_rate_to_am3_per_hour(curve.rate, YAML_UNIT_MAPPING[curve.units.rate]),
            polytropic_head_joule_per_kg=convert_head_to_joule_per_kg(curve.head, YAML_UNIT_MAPPING[curve.units.head]),
            efficiency_fraction=convert_efficiency_to_fraction(
                curve.efficiency, YAML_UNIT_MAPPING[curve.units.efficiency]
            ),
        )
    except ChartCurveEfficiencyOutOfRangeError as e:
        raise _efficiency_error(curve, e) from e
    except ChartCurveHeadNotDecreasingError as e:
        raise _head_error(curve, e) from e


def user_defined_chart_from_resource(
    resource: Resource, units: YamlUnits, is_single_speed: bool, control_margin: float | None = None
) -> UserDefinedChartData:
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
        try:
            curves = [
                _create_curve(
                    ChartCurveInput(
                        speed,
                        rate_values,
                        head_values,
                        efficiency_values,
                        units,
                        file_rows=list(range(1, len(rate_values) + 1)),
                        show_speed=False,
                    )
                )
            ]
        except EcalcValidationException as e:
            raise InvalidResourceException(title="Invalid chart", message=str(e)) from e
    else:
        # Will raise error if a column does not exist
        speeds = resource.get_float_column(EcalcYamlKeywords.consumer_chart_speed)
        rates = resource.get_float_column(EcalcYamlKeywords.consumer_chart_rate)
        heads = resource.get_float_column(EcalcYamlKeywords.consumer_chart_head)
        efficiencies = resource.get_float_column(EcalcYamlKeywords.consumer_chart_efficiency)

        if not len(speeds) == len(rates) == len(heads) == len(efficiencies):
            raise InvalidResourceException(
                title="Invalid chart", message="All chart curve data must have equal number of points"
            )

        for row_index, speed in enumerate(speeds):
            if math.isnan(speed):
                raise InvalidColumnException(
                    header=EcalcYamlKeywords.consumer_chart_speed,
                    message="Speed is missing.",
                    row_index=row_index,
                )

        rows_by_speed: dict[float, list[tuple[float, float, float, int]]] = {}
        for row, (speed, rate, head, efficiency) in enumerate(zip(speeds, rates, heads, efficiencies), start=1):
            rows_by_speed.setdefault(speed, []).append((rate, head, efficiency, row))

        try:
            curves = []
            for speed, rows in rows_by_speed.items():
                rate_values, head_values, efficiency_values, row_numbers = (list(values) for values in zip(*rows))
                curves.append(
                    _create_curve(
                        ChartCurveInput(
                            speed,
                            rate_values,
                            head_values,
                            efficiency_values,
                            units,
                            file_rows=row_numbers,
                            show_speed=True,
                        )
                    )
                )
        except EcalcValidationException as e:
            raise InvalidResourceException(title="Invalid chart", message=str(e)) from e

    return UserDefinedChartData(curves=curves, control_margin=control_margin)


def user_defined_chart_from_yaml_curves(
    curves: list[YamlCurve],
    units: YamlUnits,
    control_margin: float | None = None,
) -> UserDefinedChartData:
    return UserDefinedChartData(
        curves=[
            _create_curve(
                ChartCurveInput(
                    curve.speed,
                    curve.rate,
                    curve.head,
                    curve.efficiency,
                    units,
                    file_rows=None,
                    show_speed=len(curves) > 1,
                )
            )
            for curve in curves
        ],
        control_margin=control_margin,
    )
