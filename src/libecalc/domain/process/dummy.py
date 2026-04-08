"""
Dummy process implementation for testing purposes.
"""
import uuid
from datetime import datetime

from libecalc.domain.process.entities.process_units.compressor import Compressor
from libecalc.domain.process.entities.process_units.legacy_compressor.legacy_compressor import LegacyCompressor
from libecalc.domain.process.process_simulation import ProcessScenario, PressureControlConfig, AntiSurgeConfig, \
    Constraint, IndividualStreamDistributionConfig, ProcessPipeline, create_process_scenario_id, ProcessProblem, \
    ProcessSolution
from libecalc.domain.process.process_solver.anti_surge import anti_surge_strategy
from libecalc.domain.process.process_system.serial_process_system import SerialProcessSystem
from libecalc.domain.process.value_objects.fluid_stream.fluid_stream import SimpleStream
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression
from libecalc.presentation.yaml.mappers.fluid_mapper import MEDIUM_MW_19P4

"""
Prototyping...
"""
from ecalc_neqsim_wrapper import NeqSimFluidService
from libecalc.domain.process.compressor.core.train.stage import CompressorTrainStage
from libecalc.domain.process.entities.process_units.choke import Choke
from libecalc.domain.process.entities.process_units.rate_modifier.rate_modifier import RateModifier
from libecalc.domain.process.entities.process_units.temperature_setter import TemperatureSetter
from libecalc.domain.process.entities.shaft import Shaft, VariableSpeedShaft
from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_system.process_error import OutsideCapacityError, RateTooHighError, RateTooLowError
from libecalc.domain.process.process_system.process_system import ProcessSystem, create_process_system_id, \
    ProcessSystemId
from libecalc.domain.process.process_system.process_unit import ProcessUnitId, create_process_unit_id
from libecalc.domain.process.value_objects.chart import ChartCurve
from libecalc.domain.process.value_objects.chart.chart import ChartData
from libecalc.domain.process.value_objects.chart.chart_area_flag import ChartAreaFlag
from libecalc.domain.process.value_objects.fluid_stream import FluidStream, FluidModel, EoSModel
from libecalc.presentation.yaml.mappers.charts.user_defined_chart_data import UserDefinedChartData


dummy_process_pipeline_id = uuid.uuid4()
process_scenario_id = create_process_scenario_id()
process_problem_id = uuid.uuid4()

def process_solution_dummy() -> ProcessSolution:
    # Find solution! (For now we "say" that we only have 1 solution, and we return the first good solution we find (or no solution, if exhaustive search
    # for a solution yields no solution)

    # TODO: We could and should load domain model from db, but for simplicity we wait


    return ProcessSolution(
        id=uuid.uuid4(),
        process_problem_id=process_problem_id,
        configuration={}
    )

def process_problem_dummy() -> ProcessProblem:
    return ProcessProblem(
        id=process_problem_id,
        process_scenario_id=process_scenario_id
    )

def process_scenario_dummy() -> ProcessScenario:
    return ProcessScenario(
        id=process_scenario_id,
        process_pipeline_id=dummy_process_pipeline_id,
        pressure_control_strategy=PressureControlConfig(
            type="DOWNSTREAM_CHOKE"
        ),
        anti_surge_strategy=AntiSurgeConfig(
            type="COMMON_ASV",
        ),
        constraint=Constraint(
            outlet_pressure=200.0
        ),
        inlet_stream=process_system_dummy_stream()
    )

def shaft_dummy() -> Shaft:
    return VariableSpeedShaft(
        speed_rpm=10500.0
    )  # TODO: Should not set speed here, but we may want to set min and max here ...(from data or explicit)


def chart_data_dummy() -> ChartData:
    # TODO: 2 compressors use this chart data - is it sharable in db; but in domain objs it is VO?
    # Should we enforce this in YAML too?
    return UserDefinedChartData(
        curves=[
            ChartCurve(
                rate_actual_m3_hour=[3000.0, 3500.0, 4000.0, 4500.0],
                polytropic_head_joule_per_kg=[8500.0, 8000.0, 7500.0, 6500.0],
                efficiency_fraction=[0.72, 0.75, 0.74, 0.70],
                speed_rpm=7500.0,
            ),
            ChartCurve(
                rate_actual_m3_hour=[4100.0, 4600.0, 5000.0, 5500.0, 6000.0, 6500.0],
                polytropic_head_joule_per_kg=[16500.0, 16500.0, 15500.0, 14500.0, 13500.0, 12000.0],
                efficiency_fraction=[0.72, 0.73, 0.74, 0.74, 0.72, 0.70],
                speed_rpm=10500.0,
            ),
        ],
        control_margin=0.0,
    )


def compressors_dummy() -> list[Compressor]:
    common_shaft = shaft_dummy()
    return [
        Compressor(
            process_unit_id=create_process_unit_id(),
            compressor_chart=chart_data_dummy(),
            fluid_service=NeqSimFluidService.instance(),
            shaft=common_shaft,
        ),
        Compressor(
            process_unit_id=create_process_unit_id(),
            compressor_chart=chart_data_dummy(),
            fluid_service=NeqSimFluidService.instance(),
            shaft=common_shaft,
        )
    ]

def process_pipeline_dummy() -> ProcessPipeline:
    # TODO: Process system ..?
    propagators = [*compressors_dummy(),
                   Choke(  # DownStreamChoke - default PressureControlMechanism when not specified
                    process_unit_id=create_process_unit_id(),
                    fluid_service=NeqSimFluidService.instance(),
                    pressure_change=0.0,  # No need to choke...we meet outlet target pressure perfectly...
                    ),
                ]
    return ProcessPipeline(
       id=dummy_process_pipeline_id,
       stream_propagators=propagators
    )

def process_system_dummy_stream() -> SimpleStream:
    fluid_model = FluidModel(eos_model=EoSModel.SRK, composition=MEDIUM_MW_19P4)
    pressure = 20.0
    temperature_kelvin = 273.15 + 30
    standard_rate_m3_per_day = 4000000

    return SimpleStream(
            fluid_model=fluid_model,
            pressure_bara=pressure,
            temperature_kelvin=temperature_kelvin,
            standard_rate_m3_per_day=standard_rate_m3_per_day,
        )

def process_system_dummy_streams() -> dict[datetime, SimpleStream | FluidStream]:
    fluid_model = FluidModel(eos_model=EoSModel.SRK, composition=MEDIUM_MW_19P4)
    pressure = 20.0
    temperature_kelvin = 273.15 + 30
    standard_rates_m3_per_day = [
        4000000,
        4000000,
        4000000,
        4000000,
        4500000,
        5000000,
        5500000,
        6000000,
        6000000,
        5500000,
        5000000,
        3000000,
        3000000,
        2000000,
        1000000,
        1000000,
        500000,
        500000,
        500000,
        200000,
        200000,
        0
    ]
    # 1st of january every year from 2020 to 2040
    timestamps = [
        datetime(year, 1, 1) for year in range(2020, 2040)
    ]

    return {
        timestamp: SimpleStream(
            fluid_model=fluid_model,
            pressure_bara=pressure,
            temperature_kelvin=temperature_kelvin,
            standard_rate_m3_per_day=standard_rate,
        )
        for timestamp, standard_rate in zip(timestamps, standard_rates_m3_per_day)
    }