import pytest
from pydantic import ValidationError

from libecalc.presentation.json_result.serializable_chart import ChartCurveDTO, ChartDTO


class TestVariableSpeedCompressorChart:
    def test_variable_speed_compressor_chart(self):
        ChartDTO(
            curves=[
                ChartCurveDTO(
                    speed_rpm=1,
                    rate_actual_m3_hour=[1, 2, 3],
                    polytropic_head_joule_per_kg=[4, 5, 6],
                    efficiency_fraction=[0.7, 0.8, 0.9],
                ),
                ChartCurveDTO(
                    speed_rpm=1,
                    rate_actual_m3_hour=[4, 5, 6],
                    polytropic_head_joule_per_kg=[7, 8, 9],
                    efficiency_fraction=[0.101, 0.82, 0.9],
                ),
            ],
        )

    def test_invalid_curves(self):
        with pytest.raises(ValidationError) as e:
            ChartDTO(
                curves=[
                    ChartCurveDTO(
                        speed_rpm=1,
                        rate_actual_m3_hour=[4, 5, 6],
                        polytropic_head_joule_per_kg=[7, 8, 9],
                        efficiency_fraction=[101, 0.82, 0.9],
                    )
                ],
            )
        assert "Input should be less than or equal to 1" in str(e.value)

        with pytest.raises(ValidationError) as e:
            ChartDTO(
                curves=[
                    ChartCurveDTO(
                        speed_rpm=1,
                        rate_actual_m3_hour="invalid data",
                        polytropic_head_joule_per_kg=[7, 8, 9],
                        efficiency_fraction=[0.7, 0.82, 0.9],
                    )
                ],
            )
        assert "Input should be a valid list" in str(e.value)

        with pytest.raises(ValidationError) as e:
            ChartDTO(
                curves=[
                    ChartCurveDTO(
                        speed_rpm=1,
                        rate_actual_m3_hour=[1, 2, "invalid"],
                        polytropic_head_joule_per_kg=[7, 8, 9],
                        efficiency_fraction=[0.7, 0.82, 0.9],
                    )
                ],
            )
        assert "Input should be a valid number, unable to parse string as a number" in str(e.value)
