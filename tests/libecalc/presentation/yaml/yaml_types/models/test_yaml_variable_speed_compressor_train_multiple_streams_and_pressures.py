import pytest

from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_stages import (
    YamlCompressorStageMultipleStreams,
    YamlControlMarginUnits,
    YamlInterstageControlPressure,
)
from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_trains import (
    YamlMultipleStreamsStream,
    YamlVariableSpeedCompressorTrainMultipleStreamsAndPressures,
)
from libecalc.presentation.yaml.yaml_types.models.yaml_enums import YamlModelType, YamlPressureControl


def make_stage(interstage_control_pressure: YamlInterstageControlPressure = None):
    return YamlCompressorStageMultipleStreams(
        compressor_chart="chart1",
        stream=["stream1"],
        inlet_temperature=300,
        interstage_control_pressure=interstage_control_pressure,
        control_margin=0.0,
        control_margin_unit=YamlControlMarginUnits.FRACTION,
        pressure_drop_ahead_of_stage=0.0,
    )


def make_pressure():
    return YamlInterstageControlPressure(
        upstream_pressure_control=YamlPressureControl.UPSTREAM_CHOKE,
        downstream_pressure_control=YamlPressureControl.DOWNSTREAM_CHOKE,
    )


def compressor_train(stages: list[YamlCompressorStageMultipleStreams]):
    return YamlVariableSpeedCompressorTrainMultipleStreamsAndPressures(
        name="train1",
        type=YamlModelType.VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES,
        streams=[YamlMultipleStreamsStream(type="INGOING", name="stream1", fluid_model=None)],
        stages=stages,
        pressure_control=YamlPressureControl.DOWNSTREAM_CHOKE,
        power_adjustment_constant=0.0,
        power_adjustment_factor=1.0,
        maximum_power=10.0,
    )


def test_check_interstage_control_pressure_valid():
    """
    Test that a compressor train with a valid interstage control pressure configuration does not raise an error.
    """
    compressor_train(stages=[make_stage(), make_stage(interstage_control_pressure=make_pressure())])


def test_check_interstage_control_pressure_invalid():
    """
    Test that a compressor train with more than one stage having interstage control pressure raises a ValueError.
    """
    with pytest.raises(ValueError) as e:
        compressor_train(
            stages=[
                make_stage(),
                make_stage(interstage_control_pressure=make_pressure()),
                make_stage(interstage_control_pressure=make_pressure()),
            ]
        )
    assert "Only one stage can have interstage control pressure defined." in str(e.value)
