import io

import numpy as np
import pandas as pd
import pytest
from libecalc import dto
from libecalc.common.units import Unit
from libecalc.core.models.compressor.train.chart import SingleSpeedCompressorChart
from libecalc.core.models.compressor.train.fluid import FluidStream
from libecalc.core.models.compressor.train.single_speed_compressor_train_common_shaft import (
    SingleSpeedCompressorTrainCommonShaft,
)
from libecalc.core.models.compressor.train.stage import CompressorTrainStage
from libecalc.core.models.compressor.train.types import (
    FluidStreamObjectForMultipleStreams,
)
from libecalc.core.models.compressor.train.variable_speed_compressor_train_common_shaft import (
    VariableSpeedCompressorTrainCommonShaft,
)
from libecalc.core.models.compressor.train.variable_speed_compressor_train_common_shaft_multiple_streams_and_pressures import (
    VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures,
)
from libecalc.dto.types import FixedSpeedPressureControl
from libecalc.input.mappers.fluid_mapper import (
    DRY_MW_18P3,
    MEDIUM_MW_19P4,
    RICH_MW_21P4,
)


@pytest.fixture
def medium_fluid() -> dto.FluidModel:
    return dto.FluidModel(eos_model=dto.types.EoSModel.SRK, composition=dto.FluidComposition.parse_obj(MEDIUM_MW_19P4))


@pytest.fixture
def rich_fluid() -> dto.FluidModel:
    return dto.FluidModel(eos_model=dto.types.EoSModel.SRK, composition=dto.FluidComposition.parse_obj(RICH_MW_21P4))


@pytest.fixture
def dry_fluid() -> dto.FluidModel:
    return dto.FluidModel(eos_model=dto.types.EoSModel.SRK, composition=dto.FluidComposition.parse_obj(DRY_MW_18P3))


@pytest.fixture
def variable_speed_compressor_train_stage_dto(
    process_simulator_variable_compressor_data,
) -> dto.CompressorStage:
    return dto.CompressorStage(
        compressor_chart=process_simulator_variable_compressor_data.compressor_chart,
        pressure_drop_before_stage=0.0,
        remove_liquid_after_cooling=False,
        inlet_temperature_kelvin=303.15,
        control_margin=0,
    )


@pytest.fixture
def test_data_compressor_train_common_shaft():
    class Data:
        pass

    test_data_set = Data()
    test_data_set.kappa_values = np.asarray([1.08, 1.15, 1.2, 1.28], dtype=float)
    test_data_set.polytropic_efficiency_values = np.asarray([0.7, 0.9, 0.85, 0.75], dtype=float)
    test_data_set.polytropic_head_fluid_Joule_per_kg_values = np.asarray([119.9, 47.96, 153.8, 177.3], dtype=float)
    test_data_set.molar_mass_values = np.asarray([0.03, 0.58, 0.016, 0.44], dtype=float)  # etan, butan, metan, propan
    test_data_set.z_inlet_values = np.asarray([0.9523, 0.8953, 0.8130, 0.8166], dtype=float)
    test_data_set.inlet_temperature_K_values = np.asarray([303.15, 293.15, 323.15, 350.15], dtype=float)
    test_data_set.inlet_pressure_bara_values = np.asarray([200.0, 30.0, 15.0, 70.0], dtype=float)

    return test_data_set


@pytest.fixture
def single_speed_chart_dto() -> dto.SingleSpeedChart:
    return dto.SingleSpeedChart(
        rate_actual_m3_hour=[1735, 1882, 2027, 2182, 2322, 2467, 2615, 2762, 2907, 3054, 3201],
        polytropic_head_joule_per_kg=[
            95941.8,
            92998.8,
            89663.4,
            86426.1,
            81324.9,
            76125.6,
            70141.5,
            63568.8,
            56603.7,
            49638.6,
            42477.3,
        ],
        efficiency_fraction=[
            0.7121,
            0.7214,
            0.7281,
            0.7286,
            0.7194,
            0.7108,
            0.7001,
            0.6744,
            0.6364,
            0.5859,
            0.5185,
        ],
        speed_rpm=1,
    )


@pytest.fixture
def single_speed_compressor_train(medium_fluid_dto, single_speed_chart_dto) -> dto.SingleSpeedCompressorTrain:
    stage = dto.CompressorStage(
        compressor_chart=single_speed_chart_dto,
        inlet_temperature_kelvin=303.15,
        remove_liquid_after_cooling=True,
        pressure_drop_before_stage=0,
        control_margin=0,
    )
    return dto.SingleSpeedCompressorTrain(
        fluid_model=medium_fluid_dto,
        stages=[stage] * 2,
        pressure_control=FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
        maximum_discharge_pressure=None,
        energy_usage_adjustment_constant=0,
        energy_usage_adjustment_factor=1,
        calculate_max_rate=True,
    )


@pytest.fixture
def single_speed_compressor_train_stage(single_speed_chart_dto) -> CompressorTrainStage:
    return CompressorTrainStage(
        compressor_chart=SingleSpeedCompressorChart(
            dto.SingleSpeedChart(
                rate_actual_m3_hour=single_speed_chart_dto.rate_actual_m3_hour,
                polytropic_head_joule_per_kg=single_speed_chart_dto.polytropic_head_joule_per_kg,
                efficiency_fraction=single_speed_chart_dto.efficiency_fraction,
                speed_rpm=single_speed_chart_dto.speed_rpm,
            )
        ),
        inlet_temperature_kelvin=303.15,
        remove_liquid_after_cooling=True,
        pressure_drop_ahead_of_stage=0.0,
    )


@pytest.fixture
def variable_speed_compressor_chart_unisim_methane() -> dto.VariableSpeedChart:
    """Some variable speed compressor chart used in UniSim to compare single speed and variable speed
    compressor trains using UniSim vs. eCalc.

    Using simple conditions:
        * 1 stage. Not a train
        * Pure methane fluid
        * SRK Equation of State
        * Compressor chart values does not have any specific meaning other than
          being a realistic chart for this simulation.
    """
    data = io.StringIO(
        """
speed	rate	head	efficiency
7689	2900.0666	8412.9156	0.723
7689	3503.8068	7996.2541	0.7469
7689	4002.5554	7363.8161	0.7449
7689	4595.0148	6127.1702	0.7015
8787	3305.5723	10950.9557	0.7241
8787	4000.1546	10393.3867	0.7449
8787	4499.2342	9707.491	0.7464
8787	4996.8728	8593.8586	0.722
8787	5241.9892	7974.6002	0.7007
9886	3708.8713	13845.3808	0.723
9886	4502.2531	13182.6922	0.7473
9886	4993.5959	12425.3699	0.748
9886	5507.8114	11276.3984	0.7306
9886	5924.3308	10054.3539	0.704
10435	3928.0389	15435.484	0.7232
10435	4507.4654	14982.7351	0.7437
10435	5002.1249	14350.2222	0.7453
10435	5498.9912	13361.3245	0.7414
10435	6248.5937	11183.0276	0.701
10984	4138.6974	17078.8952	0.7226
10984	5002.4758	16274.9249	0.7462
10984	5494.3704	15428.5063	0.7468
10984	6008.6962	14261.7156	0.7349
10984	6560.148	12382.7538	0.7023
11533	4327.9175	18882.3055	0.7254
11533	4998.517	18235.1912	0.7444
11533	5505.8851	17531.6259	0.745
11533	6027.6167	16489.7195	0.7466
11533	6506.9064	15037.1474	0.7266
11533	6908.2832	13618.7919	0.7019
10767	4052.9057	16447	0.724
10767	4500.6637	16081	0.738
10767	4999.41	15546	0.7479
10767	5492.822	14640	0.74766
10767	6000.6263	13454	0.7298
10767	6439.4876	11973	0.7014
"""
    )
    df = pd.read_csv(data, sep="\t")

    # Head given in meter liquid column. We need the data to be in Polytropic head J/kg.
    df.loc[:, "head"] = Unit.POLYTROPIC_HEAD_METER_LIQUID_COLUMN.to(Unit.POLYTROPIC_HEAD_JOULE_PER_KG)(
        df["head"].values
    )

    chart_curves = []
    for speed, data in df.groupby("speed"):
        chart_curve = dto.ChartCurve(
            rate_actual_m3_hour=data["rate"].tolist(),
            polytropic_head_joule_per_kg=data["head"].tolist(),
            efficiency_fraction=data["efficiency"].tolist(),
            speed_rpm=speed,
        )
        chart_curves.append(chart_curve)

    return dto.VariableSpeedChart(curves=chart_curves)


@pytest.fixture
def single_speed_compressor_train_unisim_methane(
    variable_speed_compressor_chart_unisim_methane,
) -> SingleSpeedCompressorTrainCommonShaft:
    """10 435 RPM was used in the UniSim simulation. No special meaning or thought behind this."""
    curve = [x for x in variable_speed_compressor_chart_unisim_methane.curves if x.speed_rpm == 10435][0]
    chart = dto.SingleSpeedChart(
        polytropic_head_joule_per_kg=curve.polytropic_head_joule_per_kg,
        rate_actual_m3_hour=curve.rate_actual_m3_hour,
        efficiency_fraction=curve.efficiency_fraction,
        speed_rpm=curve.speed_rpm,
    )
    compressor_train_dto = dto.SingleSpeedCompressorTrain(
        fluid_model=dto.FluidModel(composition=dto.FluidComposition(methane=1.0), eos_model=dto.types.EoSModel.SRK),
        stages=[
            dto.CompressorStage(
                compressor_chart=chart,
                inlet_temperature_kelvin=293.15,  # 20 C.
                pressure_drop_before_stage=0,
                remove_liquid_after_cooling=True,
                control_margin=0,
            )
        ],
        pressure_control=dto.types.FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
        calculate_max_rate=False,
        energy_usage_adjustment_constant=0,
        energy_usage_adjustment_factor=1,
    )

    return SingleSpeedCompressorTrainCommonShaft(data_transfer_object=compressor_train_dto)


@pytest.fixture
def variable_speed_compressor_train_unisim_methane(
    variable_speed_compressor_chart_unisim_methane: dto.VariableSpeedChart,
) -> VariableSpeedCompressorTrainCommonShaft:
    compressor_train_dto = dto.VariableSpeedCompressorTrain(
        fluid_model=dto.FluidModel(composition=dto.FluidComposition(methane=1), eos_model=dto.types.EoSModel.SRK),
        stages=[
            dto.CompressorStage(
                compressor_chart=variable_speed_compressor_chart_unisim_methane,
                inlet_temperature_kelvin=293.15,
                pressure_drop_before_stage=0,
                remove_liquid_after_cooling=True,
                control_margin=0,
            )
        ],
        pressure_control=dto.types.FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
        calculate_max_rate=False,
        energy_usage_adjustment_constant=0,
        energy_usage_adjustment_factor=1,
    )

    return VariableSpeedCompressorTrainCommonShaft(data_transfer_object=compressor_train_dto)


@pytest.fixture
def variable_speed_compressor_train_two_compressors_one_stream(
    medium_fluid,
    variable_speed_compressor_train_two_compressors_one_stream_dto,
) -> VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures:
    """Train with only two compressors, and standard medium fluid, one stream in per stage, no liquid off take."""
    fluid_streams = [
        FluidStreamObjectForMultipleStreams(
            fluid=FluidStream(medium_fluid),
            is_inlet_stream=True,
            connected_to_stage_no=0,
        ),
    ]
    return VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures(
        streams=fluid_streams,
        data_transfer_object=variable_speed_compressor_train_two_compressors_one_stream_dto,
    )


@pytest.fixture
def variable_speed_compressor_train_two_compressors_one_stream_dto(
    medium_fluid_dto,
    variable_speed_compressor_chart_dto,
) -> dto.VariableSpeedCompressorTrainMultipleStreamsAndPressures:
    stream = dto.MultipleStreamsAndPressureStream(
        fluid_model=medium_fluid_dto,
        name="in_stream_stage_1",
        typ=dto.types.FluidStreamType.INGOING,
    )
    stage1 = dto.MultipleStreamsCompressorStage(
        compressor_chart=variable_speed_compressor_chart_dto,
        inlet_temperature_kelvin=303.15,
        remove_liquid_after_cooling=True,
        pressure_drop_before_stage=0,
        stream_reference=["in_stream_stage_1"],
        interstage_pressure_control=None,
    )
    stage2 = dto.MultipleStreamsCompressorStage(
        compressor_chart=variable_speed_compressor_chart_dto,
        inlet_temperature_kelvin=303.15,
        remove_liquid_after_cooling=True,
        pressure_drop_before_stage=0,
        interstage_pressure_control=dto.InterstagePressureControl(
            downstream_pressure_control=FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
            upstream_pressure_control=FixedSpeedPressureControl.UPSTREAM_CHOKE,
        ),
    )
    return dto.VariableSpeedCompressorTrainMultipleStreamsAndPressures(
        streams=[stream],
        stages=[stage1, stage2],
        calculate_max_rate=False,
        energy_usage_adjustment_constant=0.0,
        energy_usage_adjustment_factor=1.0,
        pressure_control=FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
    )
