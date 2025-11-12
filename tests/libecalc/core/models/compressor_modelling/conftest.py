import io

import numpy as np
import pandas as pd
import pytest

from libecalc.common.fixed_speed_pressure_control import FixedSpeedPressureControl, InterstagePressureControl
from libecalc.common.units import Unit
from libecalc.domain.process.compressor.core.train.compressor_train_common_shaft import (
    CompressorTrainCommonShaft,
)
from libecalc.domain.process.compressor.core.train.compressor_train_common_shaft_multiple_streams_and_pressures import (
    CompressorTrainCommonShaftMultipleStreamsAndPressures,
)
from libecalc.domain.process.compressor.core.train.stage import CompressorTrainStage
from libecalc.domain.process.compressor.core.train.types import FluidStreamObjectForMultipleStreams
from libecalc.domain.process.entities.shaft import VariableSpeedShaft, SingleSpeedShaft
from libecalc.domain.process.value_objects.chart import ChartCurve
from libecalc.domain.process.value_objects.chart.chart import ChartData
from libecalc.domain.process.value_objects.chart.compressor import CompressorChart
from libecalc.domain.process.value_objects.fluid_stream.fluid_model import EoSModel, FluidComposition, FluidModel
from libecalc.infrastructure.neqsim_fluid_provider.neqsim_fluid_factory import NeqSimFluidFactory
from libecalc.presentation.yaml.mappers.charts.user_defined_chart_data import UserDefinedChartData


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
def single_speed_chart_curve_factory(chart_curve_factory):
    def create_single_speed_chart_curve(
        rate: list[float] | None = None,
        head: list[float] | None = None,
        efficiency: list[float] | None = None,
        speed: float | None = None,
    ):
        if rate is None:
            rate = [1735, 1882, 2027, 2182, 2322, 2467, 2615, 2762, 2907, 3054, 3201]
        if head is None:
            head = [
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
            ]
        if efficiency is None:
            efficiency = [
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
            ]
        if speed is None:
            speed = 1
        return chart_curve_factory(
            speed_rpm=speed,
            efficiency_fraction=efficiency,
            polytropic_head_joule_per_kg=head,
            rate_actual_m3_hour=rate,
        )

    return create_single_speed_chart_curve


@pytest.fixture
def single_speed_chart_data(single_speed_chart_curve_factory, chart_data_factory) -> ChartData:
    return chart_data_factory.from_curves(curves=[single_speed_chart_curve_factory()])


@pytest.fixture
def single_speed_compressor_train_stage(single_speed_chart_data) -> CompressorTrainStage:
    return CompressorTrainStage(
        compressor_chart=CompressorChart(single_speed_chart_data),
        inlet_temperature_kelvin=303.15,
        remove_liquid_after_cooling=True,
        pressure_drop_ahead_of_stage=0.0,
    )


@pytest.fixture
def variable_speed_compressor_chart_unisim_methane() -> ChartData:
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
    for speed, curve_data in df.groupby("speed"):
        chart_curve = ChartCurve(
            rate_actual_m3_hour=curve_data["rate"].tolist(),
            polytropic_head_joule_per_kg=curve_data["head"].tolist(),
            efficiency_fraction=curve_data["efficiency"].tolist(),
            speed_rpm=float(speed),
        )
        chart_curves.append(chart_curve)

    return UserDefinedChartData(curves=chart_curves, control_margin=None)


@pytest.fixture
def single_speed_stages(single_speed_chart_data, compressor_stage_factory):
    stages = [
        compressor_stage_factory(
            compressor_chart_data=single_speed_chart_data,
            remove_liquid_after_cooling=True,
            pressure_drop_ahead_of_stage=0.0,
        ),
        compressor_stage_factory(
            compressor_chart_data=single_speed_chart_data,
            remove_liquid_after_cooling=True,
            pressure_drop_ahead_of_stage=0.0,
        ),
    ]
    return stages


@pytest.fixture
def single_speed_compressor_train_common_shaft(single_speed_stages, fluid_model_medium):
    def create_single_speed_compressor_train(
        stages: list[CompressorTrainStage] | None = None,
        energy_usage_adjustment_constant: float = 0,
        energy_usage_adjustment_factor: float = 1,
        pressure_control: FixedSpeedPressureControl | None = None,
        maximum_power: float | None = None,
        maximum_discharge_pressure: float | None = None,
        calculate_max_rate: bool = True,
    ) -> CompressorTrainCommonShaft:
        if stages is None:
            stages = single_speed_stages

        return CompressorTrainCommonShaft(
            shaft=SingleSpeedShaft(),
            energy_usage_adjustment_constant=energy_usage_adjustment_constant,
            energy_usage_adjustment_factor=energy_usage_adjustment_factor,
            stages=stages,
            pressure_control=pressure_control,
            calculate_max_rate=calculate_max_rate,
            maximum_power=maximum_power,
            maximum_discharge_pressure=maximum_discharge_pressure,
        )

    return create_single_speed_compressor_train


@pytest.fixture
def single_speed_compressor_train_unisim_methane(
    variable_speed_compressor_chart_unisim_methane,
    compressor_stage_factory,
) -> CompressorTrainCommonShaft:
    """10 435 RPM was used in the UniSim simulation. No special meaning or thought behind this."""
    curves = [x for x in variable_speed_compressor_chart_unisim_methane.get_curves() if x.speed_rpm == 10435]
    chart_data = UserDefinedChartData(
        curves=curves,
        control_margin=0,
    )

    fluid_factory = NeqSimFluidFactory(FluidModel(composition=FluidComposition(methane=1.0), eos_model=EoSModel.SRK))
    stages = [
        compressor_stage_factory(
            compressor_chart_data=chart_data,
            inlet_temperature_kelvin=293.15,  # 20 C.
            pressure_drop_ahead_of_stage=0,
            remove_liquid_after_cooling=True,
        )
    ]
    shaft = SingleSpeedShaft()
    return CompressorTrainCommonShaft(
        energy_usage_adjustment_constant=0,
        energy_usage_adjustment_factor=1,
        stages=stages,
        shaft=shaft,
        pressure_control=FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
        calculate_max_rate=False,
    )


@pytest.fixture
def variable_speed_compressor_train_unisim_methane(
    variable_speed_compressor_chart_unisim_methane,
    compressor_stage_factory,
) -> CompressorTrainCommonShaft:
    shaft = VariableSpeedShaft()
    stages = [
        compressor_stage_factory(
            compressor_chart_data=variable_speed_compressor_chart_unisim_methane,
            inlet_temperature_kelvin=293.15,
            pressure_drop_ahead_of_stage=0,
            remove_liquid_after_cooling=True,
        )
    ]
    return CompressorTrainCommonShaft(
        shaft=shaft,
        energy_usage_adjustment_constant=0,
        energy_usage_adjustment_factor=1,
        stages=stages,
        pressure_control=FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
        calculate_max_rate=False,
    )


@pytest.fixture
def variable_speed_compressor_train_two_compressors_one_stream(
    fluid_model_medium,
    variable_speed_compressor_chart_data,
    compressor_stage_factory,
) -> CompressorTrainCommonShaftMultipleStreamsAndPressures:
    """Train with only two compressors, and standard medium fluid, one stream in per stage, no liquid off take."""
    fluid_streams = [
        FluidStreamObjectForMultipleStreams(
            fluid_model=fluid_model_medium,
            is_inlet_stream=True,
            connected_to_stage_no=0,
        ),
    ]
    fluid_factory = NeqSimFluidFactory(fluid_model_medium)
    stage1 = compressor_stage_factory(
        compressor_chart_data=variable_speed_compressor_chart_data,
        inlet_temperature_kelvin=303.15,
        remove_liquid_after_cooling=True,
        pressure_drop_ahead_of_stage=0,
        interstage_pressure_control=None,
    )
    stage2 = compressor_stage_factory(
        compressor_chart_data=variable_speed_compressor_chart_data,
        inlet_temperature_kelvin=303.15,
        remove_liquid_after_cooling=True,
        pressure_drop_ahead_of_stage=0,
        interstage_pressure_control=InterstagePressureControl(
            downstream_pressure_control=FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
            upstream_pressure_control=FixedSpeedPressureControl.UPSTREAM_CHOKE,
        ),
    )
    stages = [stage1, stage2]
    has_interstage_pressure = any(stage.interstage_pressure_control is not None for stage in stages)
    stage_number_interstage_pressure = (
        [i for i, stage in enumerate(stages) if stage.interstage_pressure_control is not None][0]
        if has_interstage_pressure
        else None
    )
    return CompressorTrainCommonShaftMultipleStreamsAndPressures(
        shaft=VariableSpeedShaft(),
        streams=fluid_streams,
        energy_usage_adjustment_constant=0.0,
        energy_usage_adjustment_factor=1.0,
        stages=stages,
        stage_number_interstage_pressure=stage_number_interstage_pressure,
        pressure_control=FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
        calculate_max_rate=False,
    )


@pytest.fixture
def generic_compressor_chart_factory(chart_data_factory):
    def create_generic_compressor_chart(
        design_actual_rate_m3_per_hour: float,
        design_head_joule_per_kg: float,
        polytropic_efficiency: float,
    ):
        return CompressorChart(
            chart_data_factory.from_design_point(
                rate=design_actual_rate_m3_per_hour,
                head=design_head_joule_per_kg,
                efficiency=polytropic_efficiency,
            )
        )

    return create_generic_compressor_chart
