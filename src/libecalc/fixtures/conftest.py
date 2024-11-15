from datetime import datetime

import pytest

from libecalc.common.fluid import EoSModel, FluidComposition, FluidModel
from libecalc.common.serializable_chart import ChartCurveDTO, VariableSpeedChartDTO
from libecalc.common.time_utils import Period
from libecalc.dto import Emission, FuelType
from libecalc.dto.types import FuelTypeUserDefinedCategoryType
from libecalc.expression import Expression
from libecalc.presentation.yaml.mappers.fluid_mapper import MEDIUM_MW_19P4, RICH_MW_21P4


@pytest.fixture
def medium_fluid_dto() -> FluidModel:
    return FluidModel(eos_model=EoSModel.SRK, composition=FluidComposition.model_validate(MEDIUM_MW_19P4))


@pytest.fixture
def rich_fluid_dto() -> FluidModel:
    return FluidModel(eos_model=EoSModel.SRK, composition=FluidComposition.model_validate(RICH_MW_21P4))


@pytest.fixture
def fuel_gas() -> dict[Period, FuelType]:
    return {
        Period(datetime(1900, 1, 1), datetime(2021, 1, 1)): FuelType(
            name="fuel_gas",
            user_defined_category=FuelTypeUserDefinedCategoryType.FUEL_GAS,
            emissions=[
                Emission(
                    name="co2",
                    factor=Expression.setup_from_expression(value="2.20"),
                )
            ],
        )
    }


@pytest.fixture
def predefined_variable_speed_compressor_chart_dto() -> VariableSpeedChartDTO:
    return VariableSpeedChartDTO(
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
