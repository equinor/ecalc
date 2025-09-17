from uuid import uuid4

import numpy as np
import pandas as pd
import pytest

import libecalc.common.energy_usage_type
import libecalc.common.serializable_chart
import libecalc.dto.fuel_type

from libecalc.common.serializable_chart import ChartCurveDTO, ChartDTO
from libecalc.common.variables import ExpressionEvaluator
from libecalc.domain.infrastructure.energy_components.legacy_consumer.tabulated import TabularConsumerFunction
from libecalc.domain.infrastructure.energy_components.turbine import Turbine
from libecalc.domain.process.compressor.core.sampled import CompressorModelSampled
from libecalc.domain.process.pump.pump import PumpModel
from libecalc.domain.process.value_objects.chart import Chart
from libecalc.domain.process.value_objects.fluid_stream.fluid_model import EoSModel, FluidComposition, FluidModel
from libecalc.domain.regularity import Regularity
from libecalc.dto.emission import Emission
from libecalc.expression import Expression
from libecalc.infrastructure.neqsim_fluid_provider.neqsim_fluid_factory import NeqSimFluidFactory
from libecalc.presentation.yaml.domain.expression_time_series_variable import ExpressionTimeSeriesVariable
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression
from libecalc.presentation.yaml.mappers.fluid_mapper import DRY_MW_18P3, MEDIUM_MW_19P4, RICH_MW_21P4
from libecalc.presentation.yaml.yaml_types.models import YamlTurbine
from libecalc.testing.yaml_builder import YamlTurbineBuilder


@pytest.fixture
def fluid_model_medium() -> FluidModel:
    return FluidModel(
        eos_model=EoSModel.SRK,
        composition=FluidComposition.model_validate(MEDIUM_MW_19P4),
    )


@pytest.fixture
def fluid_model_rich() -> FluidModel:
    return FluidModel(
        eos_model=EoSModel.SRK,
        composition=FluidComposition.model_validate(RICH_MW_21P4),
    )


@pytest.fixture
def fluid_model_dry() -> FluidModel:
    return FluidModel(
        eos_model=EoSModel.SRK,
        composition=FluidComposition.model_validate(DRY_MW_18P3),
    )


@pytest.fixture
def fluid_factory_medium(fluid_model_medium) -> NeqSimFluidFactory:
    return NeqSimFluidFactory(fluid_model_medium)


@pytest.fixture
def fluid_factory_rich(fluid_model_rich) -> NeqSimFluidFactory:
    return NeqSimFluidFactory(fluid_model_rich)


@pytest.fixture
def fluid_factory_dry(fluid_model_dry) -> NeqSimFluidFactory:
    return NeqSimFluidFactory(fluid_model_dry)


@pytest.fixture
def fuel_dto() -> libecalc.dto.fuel_type.FuelType:
    return libecalc.dto.fuel_type.FuelType(
        id=uuid4(),
        name="fuel_gas",
        emissions=[
            Emission(
                name="CO2",
                factor=Expression.setup_from_expression(value=1),
            )
        ],
    )


@pytest.fixture
def pump_single_speed() -> PumpModel:
    chart_curve = Chart(
        libecalc.common.serializable_chart.ChartDTO(
            curves=[
                ChartCurveDTO(
                    rate_actual_m3_hour=[277, 524, 666, 832, 834, 927],
                    polytropic_head_joule_per_kg=[10415.277000000002, 9845.316, 9254.754, 8308.089, 8312.994, 7605.693],
                    efficiency_fraction=[0.4759, 0.6426, 0.6871, 0.7052, 0.7061, 0.6908],
                    speed_rpm=1,
                )
            ]
        )
    )
    return PumpModel(
        pump_chart=chart_curve,
        head_margin=0.0,
        energy_usage_adjustment_constant=0.0,
        energy_usage_adjustment_factor=1.0,
    )


@pytest.fixture
def pump_variable_speed() -> PumpModel:
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

    return PumpModel(
        pump_chart=Chart(libecalc.common.serializable_chart.ChartDTO(curves=chart_curves)),
        head_margin=0.0,
        energy_usage_adjustment_constant=0.0,
        energy_usage_adjustment_factor=1.0,
    )


@pytest.fixture
def compressor_model_sampled():
    # Case with 1D function (rate vs fuel)
    # CompressorModelSampled with comp/pump extrapolations
    return CompressorModelSampled(
        energy_usage_values=[146750.0, 148600.0, 150700.0, 153150.0, 156500.0, 166350.0, 169976.0],
        energy_usage_type=libecalc.common.energy_usage_type.EnergyUsageType.POWER,
        rate_values=(1000000 * np.asarray([2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 7.26])).tolist(),
        energy_usage_adjustment_constant=0,
        energy_usage_adjustment_factor=1,
    )


@pytest.fixture
def compressor_model_sampled_2():
    return CompressorModelSampled(
        energy_usage_values=[0.0, 10.0, 11.0, 12.0],
        energy_usage_type=libecalc.common.energy_usage_type.EnergyUsageType.POWER,
        rate_values=[0.0, 0.01, 1.0, 2.0],
        energy_usage_adjustment_constant=0,
        energy_usage_adjustment_factor=1,
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
        energy_usage_values=df["FUEL"].tolist(),
        energy_usage_type=libecalc.common.energy_usage_type.EnergyUsageType.FUEL,
        rate_values=df["RATE"].tolist(),
        suction_pressure_values=df["SUCTION_PRESSURE"].tolist(),
        discharge_pressure_values=df["DISCHARGE_PRESSURE"].tolist(),
        energy_usage_adjustment_constant=0,
        energy_usage_adjustment_factor=1,
    )


@pytest.fixture
def turbine_dto() -> Turbine:
    return Turbine(
        loads=[0, 2.352, 4.589, 6.853, 9.125, 11.399, 13.673, 15.947, 18.223, 20.496, 22.767],
        efficiency_fractions=[0, 0.138, 0.210, 0.255, 0.286, 0.310, 0.328, 0.342, 0.353, 0.360, 0.362],
        lower_heating_value=38.0,
        energy_usage_adjustment_constant=0.0,
        energy_usage_adjustment_factor=1.0,
    )


@pytest.fixture
def yaml_turbine() -> YamlTurbine:
    return (
        YamlTurbineBuilder()
        .with_name("compressor_train_turbine")
        .with_turbine_loads([0, 2.352, 4.589, 6.853, 9.125, 11.399, 13.673, 15.947, 18.223, 20.496, 22.767])
        .with_turbine_efficiencies([0, 0.138, 0.210, 0.255, 0.286, 0.310, 0.328, 0.342, 0.353, 0.360, 0.362])
        .with_lower_heating_value(38.0)
        .with_power_adjustment_constant(0.0)
        .with_power_adjustment_factor(1.0)
    ).validate()


@pytest.fixture
def turbine_factory(yaml_turbine):
    def create_turbine(
        loads: list[float] = None,
        lower_heating_value: float = None,
        efficiency_fractions: list[float] = None,
        energy_usage_adjustment_factor: float = None,
        energy_usage_adjustment_constant: float = None,
    ) -> Turbine:
        return Turbine(
            loads=loads if loads is not None else yaml_turbine.turbine_loads,
            lower_heating_value=lower_heating_value
            if lower_heating_value is not None
            else yaml_turbine.lower_heating_value,
            efficiency_fractions=efficiency_fractions
            if efficiency_fractions is not None
            else yaml_turbine.turbine_efficiencies,
            energy_usage_adjustment_constant=energy_usage_adjustment_constant
            if energy_usage_adjustment_constant is not None
            else yaml_turbine.power_adjustment_constant,
            energy_usage_adjustment_factor=energy_usage_adjustment_factor
            if energy_usage_adjustment_factor is not None
            else yaml_turbine.power_adjustment_factor,
        )

    return create_turbine


@pytest.fixture
def tabular_consumer_function_factory():
    def create_tabular_consumer_function(
        function_values: list[float],
        variables: dict[str, list[float]],
        expression_evaluator: ExpressionEvaluator,
        regularity: Regularity | None = None,
        energy_usage_adjustment_constant: float = 0.0,
        energy_usage_adjustment_factor: float = 1.0,
    ) -> TabularConsumerFunction:
        if regularity is None:
            regularity = Regularity(
                expression_evaluator=expression_evaluator,
                target_period=expression_evaluator.get_period(),
                expression_input=1,
            )

        variable_objs = [
            ExpressionTimeSeriesVariable(
                name=name,
                time_series_expression=TimeSeriesExpression(expression=name, expression_evaluator=expression_evaluator),
                regularity=regularity,
            )
            for name in variables.keys()
        ]

        return TabularConsumerFunction(
            headers=[*variables.keys(), "FUEL"],
            data=[*variables.values(), function_values],
            energy_usage_adjustment_factor=energy_usage_adjustment_factor,
            energy_usage_adjustment_constant=energy_usage_adjustment_constant,
            variables=variable_objs,
            power_loss_factor=None,
        )

    return create_tabular_consumer_function


@pytest.fixture
def predefined_variable_speed_compressor_chart_dto() -> ChartDTO:
    """NOT USED CURRENTLY, KEPT FOR FUTURE REFERENCE"""
    return ChartDTO(
        curves=[
            ChartCurveDTO(
                speed_rpm=7689.0,
                rate_actual_m3_hour=[2900.0666, 3503.8068, 4002.5554, 4595.0148],
                polytropic_head_joule_per_kg=[82530.702036, 78443.25272100001, 72239.03594100001, 60107.539661999996],
                efficiency_fraction=[0.723, 0.7469, 0.7449, 0.7015],
            ),
            ChartCurveDTO(
                speed_rpm=8787.0,
                rate_actual_m3_hour=[3305.5723, 4000.1546, 4499.2342, 4996.8728, 5241.9892],
                polytropic_head_joule_per_kg=[
                    107428.875417,
                    101959.123527,
                    95230.48671000001,
                    84305.752866,
                    78230.827962,
                ],
                efficiency_fraction=[0.7241, 0.7449, 0.7464, 0.722, 0.7007],
            ),
            ChartCurveDTO(
                speed_rpm=9886.0,
                rate_actual_m3_hour=[3708.8713, 4502.2531, 4993.5959, 5507.8114, 5924.3308],
                polytropic_head_joule_per_kg=[
                    135823.185648,
                    129322.210482,
                    121892.878719,
                    110621.46830400001,
                    98633.21175900001,
                ],
                efficiency_fraction=[0.723, 0.7473, 0.748, 0.7306, 0.704],
            ),
            ChartCurveDTO(
                speed_rpm=10435.0,
                rate_actual_m3_hour=[3928.0389, 4507.4654, 5002.1249, 5498.9912, 6248.5937],
                polytropic_head_joule_per_kg=[
                    151422.09804,
                    146980.631331,
                    140775.67978200002,
                    131074.593345,
                    109705.500756,
                ],
                efficiency_fraction=[0.7232, 0.7437, 0.7453, 0.7414, 0.701],
            ),
            ChartCurveDTO(
                speed_rpm=10984.0,
                rate_actual_m3_hour=[4138.6974, 5002.4758, 5494.3704, 6008.6962, 6560.148],
                polytropic_head_joule_per_kg=[
                    167543.961912,
                    159657.01326900002,
                    151353.646803,
                    139907.430036,
                    121474.81477800001,
                ],
                efficiency_fraction=[0.7226, 0.7462, 0.7468, 0.7349, 0.7023],
            ),
            ChartCurveDTO(
                speed_rpm=11533.0,
                rate_actual_m3_hour=[4327.9175, 4998.517, 5505.8851, 6027.6167, 6506.9064, 6908.2832],
                polytropic_head_joule_per_kg=[
                    185235.416955,
                    178887.22567200003,
                    171985.250079,
                    161764.148295,
                    147514.415994,
                    133600.348539,
                ],
                efficiency_fraction=[0.7254, 0.7444, 0.745, 0.7466, 0.7266, 0.7019],
            ),
            ChartCurveDTO(
                speed_rpm=10767.0,
                rate_actual_m3_hour=[4052.9057, 4500.6637, 4999.41, 5492.822, 6000.6263, 6439.4876],
                polytropic_head_joule_per_kg=[
                    161345.07,
                    157754.61000000002,
                    152506.26,
                    143618.4,
                    131983.74000000002,
                    117455.13,
                ],
                efficiency_fraction=[0.724, 0.738, 0.7479, 0.74766, 0.7298, 0.7014],
            ),
        ],
    )
