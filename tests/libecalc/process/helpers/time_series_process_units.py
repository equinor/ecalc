from collections.abc import Sequence

from libecalc.ecalc_model.process.process_units import (
    TimeSeriesChokeProcessUnit,
    TimeSeriesCompressorProcessUnit,
    TimeSeriesDirectMixerProcessUnit,
    TimeSeriesDirectSplitterProcessUnit,
    TimeSeriesInletProcessUnit,
    TimeSeriesLiquidRemoverProcessUnit,
    TimeSeriesMixerProcessUnit,
    TimeSeriesOutletProcessUnit,
    TimeSeriesPressureDropperProcessUnit,
    TimeSeriesProcessUnit,
    TimeSeriesSplitterProcessUnit,
    TimeSeriesTemperatureSetterProcessUnit,
)
from libecalc.process.fluid_stream.fluid_service import FluidService
from libecalc.process.process_pipeline.process_unit import ProcessUnit
from libecalc.process.process_units.choke import Choke
from libecalc.process.process_units.compressor import Compressor
from libecalc.process.process_units.direct_mixer import DirectMixer
from libecalc.process.process_units.direct_splitter import DirectSplitter
from libecalc.process.process_units.inlet import Inlet
from libecalc.process.process_units.liquid_remover import LiquidRemover
from libecalc.process.process_units.mixer import Mixer
from libecalc.process.process_units.outlet import Outlet
from libecalc.process.process_units.pressure_dropper import PressureDropper
from libecalc.process.process_units.splitter import Splitter
from libecalc.process.process_units.temperature_setter import TemperatureSetter


def create_process_unit(unit: TimeSeriesProcessUnit, fluid_service: FluidService) -> ProcessUnit:
    process_unit_id = unit.get_id()
    match unit:
        case TimeSeriesCompressorProcessUnit():
            return Compressor(
                compressor_chart=unit.compressor_chart.chart_data,
                fluid_service=fluid_service,
                process_unit_id=process_unit_id,
            )
        case TimeSeriesChokeProcessUnit():
            return Choke(fluid_service=fluid_service, process_unit_id=process_unit_id)
        case TimeSeriesDirectMixerProcessUnit():
            return DirectMixer(process_unit_id=process_unit_id)
        case TimeSeriesDirectSplitterProcessUnit():
            return DirectSplitter(process_unit_id=process_unit_id)
        case TimeSeriesInletProcessUnit():
            return Inlet(process_unit_id=process_unit_id)
        case TimeSeriesOutletProcessUnit():
            return Outlet(process_unit_id=process_unit_id)
        case TimeSeriesLiquidRemoverProcessUnit():
            return LiquidRemover(fluid_service=fluid_service, process_unit_id=process_unit_id)
        case TimeSeriesMixerProcessUnit():
            return Mixer(fluid_service=fluid_service, process_unit_id=process_unit_id)
        case TimeSeriesPressureDropperProcessUnit():
            return PressureDropper(fluid_service=fluid_service, process_unit_id=process_unit_id)
        case TimeSeriesSplitterProcessUnit():
            return Splitter(fluid_service=fluid_service, process_unit_id=process_unit_id)
        case TimeSeriesTemperatureSetterProcessUnit():
            return TemperatureSetter(fluid_service=fluid_service, process_unit_id=process_unit_id)
        case _:
            raise ValueError(f"Unknown process unit type '{type(unit).__name__}'.")


def create_process_units(units: Sequence[TimeSeriesProcessUnit], fluid_service: FluidService) -> list[ProcessUnit]:
    return [create_process_unit(unit, fluid_service) for unit in units]
