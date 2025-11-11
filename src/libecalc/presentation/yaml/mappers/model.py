from libecalc.common.errors.exceptions import InvalidResourceException, ResourceFileMark
from libecalc.common.fixed_speed_pressure_control import FixedSpeedPressureControl
from libecalc.domain.component_validation_error import DomainValidationException
from libecalc.domain.process.value_objects.chart.chart import ChartData
from libecalc.domain.process.value_objects.chart.compressor.chart_creator import CompressorChartCreator
from libecalc.domain.resource import Resources
from libecalc.presentation.yaml.file_context import FileContext, FileMark
from libecalc.presentation.yaml.mappers.charts.user_defined_chart_data import UserDefinedChartData
from libecalc.presentation.yaml.mappers.utils import (
    YAML_UNIT_MAPPING,
    convert_efficiency_to_fraction,
    convert_head_to_joule_per_kg,
    convert_rate_to_am3_per_hour,
)
from libecalc.presentation.yaml.validation_errors import (
    Location,
)
from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_chart import (
    YamlGenericFromDesignPointChart,
    YamlSingleSpeedChart,
    YamlVariableSpeedChart,
)
from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_trains import (
    YamlSingleSpeedCompressorTrain,
    YamlVariableSpeedCompressorTrain,
    YamlVariableSpeedCompressorTrainMultipleStreamsAndPressures,
)
from libecalc.presentation.yaml.yaml_types.models.yaml_enums import YamlPressureControl
from libecalc.presentation.yaml.yaml_types.yaml_data_or_file import YamlFile


def _pressure_control_mapper(
    model_config: (
        YamlVariableSpeedCompressorTrain
        | YamlSingleSpeedCompressorTrain
        | YamlVariableSpeedCompressorTrainMultipleStreamsAndPressures
    ),
) -> FixedSpeedPressureControl:
    return FixedSpeedPressureControl(model_config.pressure_control.value)


class InvalidChartResourceException(Exception):
    def __init__(self, message: str, file_mark: ResourceFileMark | None, resource_name: str):
        self.message = message
        self._resource_file_mark = file_mark
        self.resource_name = resource_name
        super().__init__(message)

    @property
    def location(self) -> Location:
        return Location([self.resource_name])

    @property
    def file_context(self) -> FileContext:
        return FileContext(
            name=self.resource_name,
            start=self._file_mark,
        )

    @property
    def _file_mark(self) -> FileMark | None:
        if self._resource_file_mark is not None:
            return FileMark(
                line_number=self._resource_file_mark.row,
                column=self._resource_file_mark.column,
            )
        else:
            return None


def _single_speed_compressor_chart_mapper(
    model_config: YamlSingleSpeedChart,
    resources: Resources,
    control_margin: float | None,
) -> ChartData:
    curve_config = model_config.curve

    if isinstance(curve_config, YamlFile):
        resource_name = curve_config.file
        resource = resources.get(resource_name)
        if resource is None:
            raise ValueError(f"Resource '{resource_name}' not found for single speed chart.")

        try:
            chart_data = UserDefinedChartData.from_resource(
                resource,
                units=model_config.units,
                is_single_speed=True,
                control_margin=control_margin,
            )
        except InvalidResourceException as e:
            raise InvalidChartResourceException(
                message=str(e), file_mark=e.file_mark, resource_name=resource_name
            ) from e
    else:
        chart_data = UserDefinedChartData.from_yaml_curves(
            [curve_config], units=model_config.units, control_margin=control_margin
        )

    return chart_data


def _variable_speed_compressor_chart_mapper(
    model_config: YamlVariableSpeedChart,
    resources: Resources,
    control_margin: float | None,
) -> ChartData:
    curve_config = model_config.curves

    if isinstance(curve_config, YamlFile):
        resource_name = curve_config.file
        resource = resources.get(resource_name)
        if resource is None:
            raise DomainValidationException(f"Resource '{resource_name}' not found for variable speed chart.")
        try:
            chart_data = UserDefinedChartData.from_resource(
                resource, units=model_config.units, is_single_speed=False, control_margin=control_margin
            )
        except InvalidResourceException as e:
            raise InvalidChartResourceException(
                message=str(e), file_mark=e.file_mark, resource_name=resource_name
            ) from e
    else:
        chart_data = UserDefinedChartData.from_yaml_curves(
            curve_config, units=model_config.units, control_margin=control_margin
        )

    return chart_data


def _generic_from_design_point_compressor_chart_mapper(
    model_config: YamlGenericFromDesignPointChart,
) -> ChartData:
    design_rate = model_config.design_rate
    design_polytropic_head = model_config.design_head
    polytropic_efficiency = model_config.polytropic_efficiency

    units = model_config.units
    design_rate_actual_m3_per_hour = convert_rate_to_am3_per_hour(
        rate_values=[design_rate], input_unit=YAML_UNIT_MAPPING[units.rate]
    )[0]
    design_polytropic_head_joule_per_kg = convert_head_to_joule_per_kg(
        head_values=[design_polytropic_head], input_unit=YAML_UNIT_MAPPING[units.head]
    )[0]
    polytropic_efficiency_fraction = convert_efficiency_to_fraction(
        efficiency_values=[polytropic_efficiency],
        input_unit=YAML_UNIT_MAPPING[units.efficiency],
    )[0]

    return CompressorChartCreator.from_rate_and_head_design_point(
        design_actual_rate_m3_per_hour=design_rate_actual_m3_per_hour,
        design_head_joule_per_kg=design_polytropic_head_joule_per_kg,
        polytropic_efficiency=polytropic_efficiency_fraction,
    )


def map_yaml_to_fixed_speed_pressure_control(yaml_control: YamlPressureControl) -> FixedSpeedPressureControl:
    mapping = {
        YamlPressureControl.UPSTREAM_CHOKE: FixedSpeedPressureControl.UPSTREAM_CHOKE,
        YamlPressureControl.DOWNSTREAM_CHOKE: FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
        YamlPressureControl.INDIVIDUAL_ASV_PRESSURE: FixedSpeedPressureControl.INDIVIDUAL_ASV_PRESSURE,
        YamlPressureControl.INDIVIDUAL_ASV_RATE: FixedSpeedPressureControl.INDIVIDUAL_ASV_RATE,
        YamlPressureControl.COMMON_ASV: FixedSpeedPressureControl.COMMON_ASV,
    }
    return mapping[yaml_control]
