import numpy as np
import pandas as pd
import pytest

import libecalc.common.energy_usage_type
import libecalc.common.fixed_speed_pressure_control
import libecalc.common.serializable_chart
import libecalc.dto.fuel_type
from libecalc import dto
from libecalc.core.models.chart import SingleSpeedChart, VariableSpeedChart
from libecalc.core.models.compressor.sampled import CompressorModelSampled
from libecalc.core.models.pump import PumpSingleSpeed, PumpVariableSpeed
from libecalc.core.models.turbine import TurbineModel
from libecalc.expression import Expression
from libecalc.presentation.yaml.mappers.fluid_mapper import DRY_MW_18P3, MEDIUM_MW_19P4, RICH_MW_21P4


@pytest.fixture
def medium_fluid() -> dto.FluidModel:
    return dto.FluidModel(
        eos_model=dto.types.EoSModel.SRK, composition=dto.FluidComposition.model_validate(MEDIUM_MW_19P4)
    )


@pytest.fixture
def rich_fluid() -> dto.FluidModel:
    return dto.FluidModel(
        eos_model=dto.types.EoSModel.SRK, composition=dto.FluidComposition.model_validate(RICH_MW_21P4)
    )


@pytest.fixture
def dry_fluid() -> dto.FluidModel:
    return dto.FluidModel(
        eos_model=dto.types.EoSModel.SRK, composition=dto.FluidComposition.model_validate(DRY_MW_18P3)
    )


@pytest.fixture
def fuel_dto() -> libecalc.dto.fuel_type.FuelType:
    return libecalc.dto.fuel_type.FuelType(
        name="fuel_gas",
        emissions=[
            dto.Emission(
                name="CO2",
                factor=Expression.setup_from_expression(value=1),
            )
        ],
    )


@pytest.fixture
def pump_single_speed() -> PumpSingleSpeed:
    chart_curve = SingleSpeedChart(
        libecalc.common.serializable_chart.SingleSpeedChartDTO(
            rate_actual_m3_hour=[277, 524, 666, 832, 834, 927],
            polytropic_head_joule_per_kg=[10415.277000000002, 9845.316, 9254.754, 8308.089, 8312.994, 7605.693],
            efficiency_fraction=[0.4759, 0.6426, 0.6871, 0.7052, 0.7061, 0.6908],
            speed_rpm=1,
        )
    )
    return PumpSingleSpeed(pump_chart=chart_curve)


@pytest.fixture
def pump_variable_speed() -> PumpVariableSpeed:
    df = pd.DataFrame(
        [  # speed, rate, head, efficiency
            [2650, 277, 1061, 0.47],
            [2650, 524, 1003, 0.64],
            [2650, 666, 943, 0.68],
            [2650, 832, 846, 0.70],
            [2650, 834, 847, 0.70],
            [2650, 927, 775, 0.69],
            [3425, 336, 1778, 0.47],
            [3425, 577, 1718, 0.62],
            [3425, 708, 1665, 0.66],
            [3425, 842, 1587, 0.69],
            [3425, 824, 1601, 0.69],
            [3425, 826, 1601, 0.69],
            [3425, 825, 1602, 0.69],
            [3425, 1028, 1460, 0.71],
        ],
        columns=[
            "speed",
            "rate",
            "head",
            "efficiency",
        ],
    )

    chart_curves = []
    for speed, data in df.groupby("speed"):
        chart_curve = libecalc.common.serializable_chart.ChartCurveDTO(
            rate_actual_m3_hour=data["rate"].tolist(),
            polytropic_head_joule_per_kg=[x * 9.81 for x in data["head"].tolist()],  # meter liquid column to joule /kg
            efficiency_fraction=data["efficiency"].tolist(),
            speed_rpm=float(speed),
        )
        chart_curves.append(chart_curve)

    return PumpVariableSpeed(
        pump_chart=VariableSpeedChart(libecalc.common.serializable_chart.VariableSpeedChartDTO(curves=chart_curves))
    )


@pytest.fixture
def compressor_model_sampled():
    # Case with 1D function (rate vs fuel)
    # CompressorModelSampled with comp/pump extrapolations
    return CompressorModelSampled(
        data_transfer_object=dto.CompressorSampled(
            energy_usage_values=[146750.0, 148600.0, 150700.0, 153150.0, 156500.0, 166350.0, 169976.0],
            energy_usage_type=libecalc.common.energy_usage_type.EnergyUsageType.POWER,
            rate_values=(1000000 * np.asarray([2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 7.26])).tolist(),
            energy_usage_adjustment_constant=0,
            energy_usage_adjustment_factor=1,
        ),
    )


@pytest.fixture
def compressor_model_sampled_2():
    return CompressorModelSampled(
        data_transfer_object=dto.CompressorSampled(
            energy_usage_values=[0.0, 10.0, 11.0, 12.0],
            energy_usage_type=libecalc.common.energy_usage_type.EnergyUsageType.POWER,
            rate_values=[0.0, 0.01, 1.0, 2.0],
            energy_usage_adjustment_constant=0,
            energy_usage_adjustment_factor=1,
        ),
    )


@pytest.fixture
def compressor_model_sampled_3d():
    df = pd.DataFrame(
        [
            [1000000, 50, 162, 52765],
            [1000000, 50, 258, 76928],
            [1000000, 50, 394, 118032],
            [1000000, 50, 471, 145965],
            [3000000, 50, 237, 71918],
            [3000000, 50, 258, 109823],
            [3000000, 50, 449, 137651],
            [7000000, 50, 322, 139839],
            [1000000, 52, 171, 54441],
            [1000000, 52, 215, 65205],
            [1000000, 52, 336, 98692],
            [1000000, 52, 487, 151316],
            [3000000, 52, 249, 74603],
            [3000000, 52, 384, 114277],
            [3000000, 52, 466, 143135],
            [7000000, 52, 362, 144574],
        ],
        columns=["RATE", "SUCTION_PRESSURE", "DISCHARGE_PRESSURE", "FUEL"],
    )

    return CompressorModelSampled(
        data_transfer_object=dto.CompressorSampled(
            energy_usage_values=df["FUEL"].tolist(),
            energy_usage_type=libecalc.common.energy_usage_type.EnergyUsageType.FUEL,
            rate_values=df["RATE"].tolist(),
            suction_pressure_values=df["SUCTION_PRESSURE"].tolist(),
            discharge_pressure_values=df["DISCHARGE_PRESSURE"].tolist(),
            energy_usage_adjustment_constant=0,
            energy_usage_adjustment_factor=1,
        ),
    )


@pytest.fixture
def variable_speed_compressor_chart_dto() -> libecalc.common.serializable_chart.VariableSpeedChartDTO:
    df = pd.DataFrame(
        [
            [10767, 4053.0, 161345.0, 0.72],
            [10767, 4501.0, 157754.0, 0.73],
            [10767, 4999.0, 152506.0, 0.74],
            [10767, 5493.0, 143618.0, 0.74],
            [10767, 6001.0, 131983.0, 0.72],
            [10767, 6439.0, 117455.0, 0.70],
            [11533, 4328.0, 185232.0, 0.72],
            [11533, 4999.0, 178885.0, 0.74],
            [11533, 5506.0, 171988.0, 0.74],
            [11533, 6028.0, 161766.0, 0.74],
            [11533, 6507.0, 147512.0, 0.72],
            [11533, 6908.0, 133602.0, 0.70],
            [10984, 4139.0, 167544.0, 0.72],
            [10984, 5002.0, 159657.0, 0.74],
            [10984, 5494.0, 151358.0, 0.74],
            [10984, 6009.0, 139910.0, 0.73],
            [10984, 6560.0, 121477.0, 0.70],
            [10435, 3928.0, 151417.0, 0.72],
            [10435, 4507.0, 146983.0, 0.74],
            [10435, 5002.0, 140773.0, 0.74],
            [10435, 5499.0, 131071.0, 0.74],
            [10435, 6249.0, 109705.0, 0.70],
            [9886, 3709.0, 135819.0, 0.72],
            [9886, 4502.0, 129325.0, 0.74],
            [9886, 4994.0, 121889.0, 0.74],
            [9886, 5508.0, 110617.0, 0.73],
            [9886, 5924.0, 98629.70, 0.70],
            [8787, 3306.0, 107429.0, 0.72],
            [8787, 4000.0, 101955.0, 0.74],
            [8787, 4499.0, 95225.60, 0.74],
            [8787, 4997.0, 84307.10, 0.72],
            [8787, 5242.0, 78234.70, 0.70],
            [7689, 2900.0, 82531.50, 0.72],
            [7689, 3504.0, 78440.70, 0.74],
            [7689, 4003.0, 72240.80, 0.74],
            [7689, 4595.0, 60105.80, 0.70],
        ],
        columns=["speed", "rate", "head", "efficiency"],
    )
    chart_curves = [
        libecalc.common.serializable_chart.ChartCurveDTO(
            polytropic_head_joule_per_kg=data["head"].tolist(),
            rate_actual_m3_hour=data["rate"].tolist(),
            efficiency_fraction=data["efficiency"].tolist(),
            speed_rpm=float(speed),
        )
        for speed, data in df.groupby("speed")
    ]

    return libecalc.common.serializable_chart.VariableSpeedChartDTO(curves=chart_curves)


@pytest.fixture
def variable_speed_compressor_train_dto(
    medium_fluid_dto, variable_speed_compressor_chart_dto
) -> dto.VariableSpeedCompressorTrain:
    return dto.VariableSpeedCompressorTrain(
        fluid_model=medium_fluid_dto,
        stages=[
            dto.CompressorStage(
                compressor_chart=variable_speed_compressor_chart_dto,
                inlet_temperature_kelvin=303.15,
                remove_liquid_after_cooling=True,
                pressure_drop_before_stage=0,
                control_margin=0,
            )
        ],
        energy_usage_adjustment_constant=0,
        energy_usage_adjustment_factor=1,
        pressure_control=libecalc.common.fixed_speed_pressure_control.FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
    )


@pytest.fixture
def variable_speed_compressor_train_two_stages_dto(
    medium_fluid_dto, variable_speed_compressor_chart_dto
) -> dto.VariableSpeedCompressorTrain:
    return dto.VariableSpeedCompressorTrain(
        fluid_model=medium_fluid_dto,
        stages=[
            dto.CompressorStage(
                compressor_chart=variable_speed_compressor_chart_dto,
                inlet_temperature_kelvin=303.15,
                remove_liquid_after_cooling=True,
                pressure_drop_before_stage=0,
                control_margin=0,
            )
        ]
        * 2,
        energy_usage_adjustment_constant=0,
        energy_usage_adjustment_factor=1,
        pressure_control=libecalc.common.fixed_speed_pressure_control.FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
    )


@pytest.fixture
def turbine_dto() -> dto.Turbine:
    return dto.Turbine(
        turbine_loads=[0, 2.352, 4.589, 6.853, 9.125, 11.399, 13.673, 15.947, 18.223, 20.496, 22.767],
        turbine_efficiency_fractions=[0, 0.138, 0.210, 0.255, 0.286, 0.310, 0.328, 0.342, 0.353, 0.360, 0.362],
        lower_heating_value=38.0,
        energy_usage_adjustment_constant=0.0,
        energy_usage_adjustment_factor=1.0,
    )


@pytest.fixture
def turbine(turbine_dto) -> TurbineModel:
    return TurbineModel(data_transfer_object=turbine_dto)
