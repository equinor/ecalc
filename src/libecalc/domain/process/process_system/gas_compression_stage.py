from ecalc_neqsim_wrapper.thermo import STANDARD_TEMPERATURE_KELVIN
from libecalc.domain.process.entities.process_units.choke import Choke
from libecalc.domain.process.entities.process_units.gas_compressor import GasCompressor
from libecalc.domain.process.entities.process_units.liquid_remover import LiquidRemover
from libecalc.domain.process.entities.process_units.temperature_setter import TemperatureSetter
from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_system.compressor_stage_process_unit import CompressorStageProcessUnit
from libecalc.domain.process.process_system.process_unit import ProcessUnit, ProcessUnitId, create_process_unit_id
from libecalc.domain.process.value_objects.fluid_stream import FluidService, FluidStream


class GasCompressionStage(CompressorStageProcessUnit):
    """
    A process unit which job in to compress gas. It consists of a series of process units, but there are restrictions:
    1. There can be a choke (pressure drop ahead of the stage), but this will later be moved into
       the something like a InterstageManifold process unit, which will be placed between two GasCompressionStages.
    2. There must be exactly one TemperatureSetter (maybe changed to a Cooler some time in the future).
    3. There will usually be a LiquidRemover, but it is not strictly required (e.g. if the inlet gas is guaranteed to be dry).
    4. There must be exactly one GasCompressor process unit.

    This means that this ProcessUnit can not include Chokes, Splitters or Mixers. They will be made part of
    the InterstageManifold process unit, which will be placed between two GasCompressionStages.

    """

    def __init__(
        self,
        compressor: GasCompressor,
        process_unit_id: ProcessUnitId,
        fluid_service: FluidService,
        inlet_temperature_kelvin: float = STANDARD_TEMPERATURE_KELVIN,
        remove_liquid: bool = False,
        pressure_drop_ahead_of_stage: float = 0.0,   #  TODO: Move this to InterstageManifold process unit, which will be placed between two GasCompressionStages
    ):
        self._process_units: list[ProcessUnit] = []
        self._id = process_unit_id
        self._compressor = compressor
        self._remove_liquid = remove_liquid
        self._pressure_drop_ahead_of_stage = pressure_drop_ahead_of_stage
        self._inlet_temperature_kelvin = inlet_temperature_kelvin
        self.fluid_service = fluid_service
        self._make_list_of_process_units()

    def get_id(self) -> ProcessUnitId:
        return self._id

    def get_speed_boundary(self) -> Boundary:
        chart = self._compressor.compressor_chart
        return Boundary(min=chart.minimum_speed, max=chart.maximum_speed)

    def get_maximum_standard_rate(self, inlet_stream: FluidStream) -> float:
        """Maximum standard rate at current speed"""
        compressor_inlet_stream = self.get_compressor_inlet_stream(inlet_stream=inlet_stream)
        density = compressor_inlet_stream.density
        max_actual_rate = self._compressor.compressor_chart.maximum_rate_as_function_of_speed(self._compressor.speed)
        max_mass_rate = max_actual_rate * density
        return self.fluid_service.mass_rate_to_standard_rate(
            fluid_model=compressor_inlet_stream.fluid_model, mass_rate_kg_per_h=max_mass_rate
        )

    def get_minimum_standard_rate(self, inlet_stream: FluidStream) -> float:
        compressor_inlet_stream = self.get_compressor_inlet_stream(inlet_stream=inlet_stream)
        density = compressor_inlet_stream.density
        min_actual_rate = self._compressor.compressor_chart.minimum_rate_as_function_of_speed(self._compressor.speed)
        min_mass_rate = min_actual_rate * density
        return self.fluid_service.mass_rate_to_standard_rate(
            fluid_model=compressor_inlet_stream.fluid_model, mass_rate_kg_per_h=min_mass_rate
        )

    def get_process_units(self) -> list[ProcessUnit]:
        """Get the list of process units in this stage."""
        return self._process_units

    def propagate_stream(self, inlet_stream: FluidStream) -> FluidStream:
        current_stream = inlet_stream
        for unit in self._process_units:
            current_stream = unit.propagate_stream(inlet_stream=current_stream)
        return current_stream

    def get_compressor_inlet_stream(self, inlet_stream: FluidStream) -> FluidStream:
        """Get the inlet stream to the GasCompressor process unit.
        The compressor is always last in the list of process units,
        so we can just propagate through all units until we reach the compressor.
        """
        current_stream = inlet_stream
        for unit in self._process_units[:-1]:
            current_stream = unit.propagate_stream(current_stream)
        return current_stream

    def _make_list_of_process_units(self) -> None:
        """
        Make the list of process units in the correct order. The order is as follows:
            1. Choke (if pressure_drop_ahead_of_stage > 0)
            2. TemperatureSetter
            3. LiquidRemover (if remove_liquid is True)
            4. GasCompressor
        """
        if self._pressure_drop_ahead_of_stage > 0:
            self._process_units.append(
                Choke(
                    process_unit_id=create_process_unit_id(),
                    fluid_service=self.fluid_service,
                    pressure_change=self._pressure_drop_ahead_of_stage,
                )
            )
        self._process_units.append(
            TemperatureSetter(
                process_unit_id=create_process_unit_id(),
                required_temperature_kelvin=self._inlet_temperature_kelvin,
                fluid_service=self.fluid_service,
            )
        )
        if self._remove_liquid:
            self._process_units.append(
                LiquidRemover(process_unit_id=create_process_unit_id(), fluid_service=self.fluid_service)
            )
        self._process_units.append(self._compressor)
