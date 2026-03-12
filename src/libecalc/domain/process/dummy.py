"""
Dummy process implementation for testing purposes.
"""
from libecalc.domain.process.process_system.serial_process_system import SerialProcessSystem

"""
Prototyping...
"""
from ecalc_neqsim_wrapper import NeqSimFluidService
from libecalc.domain.process.compressor.core.train.stage import CompressorTrainStage
from libecalc.domain.process.entities.process_units.choke import Choke
from libecalc.domain.process.entities.process_units.compressor.compressor import Compressor
from libecalc.domain.process.entities.process_units.rate_modifier.rate_modifier import RateModifier
from libecalc.domain.process.entities.process_units.temperature_setter import TemperatureSetter
from libecalc.domain.process.entities.shaft import Shaft, VariableSpeedShaft
from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_system.compressor_stage_process_unit import CompressorStageProcessUnit
from libecalc.domain.process.process_system.process_error import RateTooHighError, RateTooLowError, OutsideCapacityError
from libecalc.domain.process.process_system.process_system import ProcessSystem
from libecalc.domain.process.process_system.process_unit import create_process_unit_id, ProcessUnitId
from libecalc.domain.process.value_objects.chart import ChartCurve
from libecalc.domain.process.value_objects.chart.chart import ChartData
from libecalc.domain.process.value_objects.chart.chart_area_flag import ChartAreaFlag
from libecalc.domain.process.value_objects.fluid_stream import FluidStream
from libecalc.presentation.yaml.mappers.charts.user_defined_chart_data import UserDefinedChartData

# Temporarily adding dummy/temp stage process unit here until we have one ready
class MyStageProcessUnit(CompressorStageProcessUnit):
    def __init__(self, compressor_stage: CompressorTrainStage):
        self._id = create_process_unit_id()
        self._compressor_stage = compressor_stage

    def get_id(self) -> ProcessUnitId:
        return self._id

    def get_speed_boundary(self) -> Boundary:
        chart = self._compressor_stage.compressor.compressor_chart
        return Boundary(min=chart.minimum_speed, max=chart.maximum_speed)

    def get_maximum_standard_rate(self, inlet_stream: FluidStream) -> float:
        compressor_inlet_stream = self._compressor_stage.get_compressor_inlet_stream(inlet_stream_stage=inlet_stream)
        density = compressor_inlet_stream.density
        max_actual_rate = self._compressor_stage.compressor.compressor_chart.maximum_rate_as_function_of_speed(
            self._compressor_stage.compressor.speed
        )
        max_mass_rate = max_actual_rate * density
        return self._compressor_stage.fluid_service.mass_rate_to_standard_rate(
            fluid_model=compressor_inlet_stream.fluid_model, mass_rate_kg_per_h=max_mass_rate
        )

    def get_minimum_standard_rate(self, inlet_stream: FluidStream) -> float:
        compressor_inlet_stream = self._compressor_stage.get_compressor_inlet_stream(inlet_stream_stage=inlet_stream)
        density = compressor_inlet_stream.density
        min_actual_rate = self._compressor_stage.compressor.compressor_chart.minimum_rate_as_function_of_speed(
            self._compressor_stage.compressor.speed
        )
        min_mass_rate = min_actual_rate * density
        return self._compressor_stage.fluid_service.mass_rate_to_standard_rate(
            fluid_model=compressor_inlet_stream.fluid_model, mass_rate_kg_per_h=min_mass_rate
        )

    def propagate_stream(self, inlet_stream: FluidStream) -> FluidStream:
        result = self._compressor_stage.evaluate(inlet_stream_stage=inlet_stream)
        if result.chart_area_flag == ChartAreaFlag.ABOVE_MAXIMUM_FLOW_RATE:
            raise RateTooHighError()
        if result.chart_area_flag == ChartAreaFlag.BELOW_MINIMUM_FLOW_RATE:
            raise RateTooLowError()

        if not result.within_capacity:
            raise OutsideCapacityError()
        return result.outlet_stream


def process_system_dummy() -> ProcessSystem:
    def chart_data() -> ChartData:
        return  UserDefinedChartData(
            curves=[
                ChartCurve(
                    rate_actual_m3_hour=[3000.0, 3500.0, 4000.0, 4500.0],
                    polytropic_head_joule_per_kg=[8500.0,8000.0,7500.0,6500.0],
                    efficiency_fraction=[0.72, 0.75, 0.74, 0.70],
                    speed_rpm=7500.0,
                ),
                ChartCurve(
                    rate_actual_m3_hour=[4100.0, 4600.0, 5000.0, 5500.0, 6000.0, 6500.0],
                    polytropic_head_joule_per_kg=[16500.0,16500.0,15500.0,14500.0,13500.0,12000.0],
                    efficiency_fraction=[0.72, 0.73, 0.74, 0.74, 0.72, 0.70],
                    speed_rpm=10500.0,
                ),
            ],
            control_margin=0.0,
        )

    def shaft() -> Shaft:
        return VariableSpeedShaft(speed_rpm=10500.0)  # TODO: Should not set speed here, but we may want to set min and max here ...(from data or explicit)

    ## e.g. loaded from db, after solving has taken place
    def train() -> ProcessSystem:
        common_shaft = shaft()
        return SerialProcessSystem(
            propagators=[
                MyStageProcessUnit(
                    compressor_stage=CompressorTrainStage(
                        compressor=Compressor(
                            compressor_chart=chart_data(),
                            fluid_service=NeqSimFluidService.instance(),
                            shaft=common_shaft
                        ),
                        temperature_setter=TemperatureSetter(
                            process_unit_id=create_process_unit_id(),
                            fluid_service=NeqSimFluidService.instance(),
                            required_temperature_kelvin=30+273.15
                        ),
                        liquid_remover=None,
                        rate_modifier=RateModifier(
                            compressor_chart=chart_data(),
                            shaft=common_shaft
                        ),
                        fluid_service=NeqSimFluidService.instance(),
                        splitter=None,
                        mixer=None,
                        choke=None,
                        interstage_pressure_control=None,
                    )
                ),
                MyStageProcessUnit(
                    compressor_stage=CompressorTrainStage(
                        compressor=Compressor(
                            compressor_chart=chart_data(),
                            fluid_service=NeqSimFluidService.instance(),
                            shaft=common_shaft
                        ),
                        temperature_setter=TemperatureSetter(
                            process_unit_id=create_process_unit_id(),
                            fluid_service=NeqSimFluidService.instance(),
                            required_temperature_kelvin=30+273.15
                        ),
                        liquid_remover=None,
                        rate_modifier=RateModifier(
                            compressor_chart=chart_data(),
                            shaft=common_shaft
                        ),
                        fluid_service=NeqSimFluidService.instance(),
                        splitter=None,
                        mixer=None,
                        choke=None,
                        interstage_pressure_control=None,
                    )
                ),
                Choke(  # DownStreamChoke - default PressureControlMechanism when not specified
                    process_unit_id=create_process_unit_id(),
                    fluid_service=NeqSimFluidService.instance(),
                    pressure_change=0.0,  # No need to choke...we meet outlet target pressure perfectly...
                )
            ]
        )

    return train()
