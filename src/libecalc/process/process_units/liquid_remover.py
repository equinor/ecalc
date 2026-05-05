from typing import Final

from libecalc.process.fluid_stream.constants import ThermodynamicConstants
from libecalc.process.fluid_stream.fluid_service import FluidService
from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_pipeline.process_unit import ProcessUnit, ProcessUnitId


class LiquidRemover(ProcessUnit):
    def __init__(self, fluid_service: FluidService, process_unit_id: ProcessUnitId | None = None):
        self._id: Final[ProcessUnitId] = process_unit_id or ProcessUnit._create_id()
        self._fluid_service = fluid_service

    def get_id(self) -> ProcessUnitId:
        return self._id

    def propagate_stream(self, inlet_stream: FluidStream) -> FluidStream:
        """
        Removes liquid from the fluid stream. The new stream's mass rate is scaled
        down by the gas mass fraction so the dropped-out liquid isn't re-injected
        into the gas phase.

        Args:
            inlet_stream: The fluid stream to be scrubbed.

        Returns:
            FluidStream: A new FluidStream with liquid removed.
        """
        if inlet_stream.vapor_fraction_molar < ThermodynamicConstants.PURE_VAPOR_THRESHOLD:
            new_fluid = self._fluid_service.remove_liquid(inlet_stream.fluid)
            inlet_molar_mass = inlet_stream.fluid.molar_mass
            if inlet_molar_mass > 0.0:
                gas_mass_fraction = inlet_stream.vapor_fraction_molar * new_fluid.molar_mass / inlet_molar_mass
            else:
                gas_mass_fraction = 1.0
            new_mass_rate = inlet_stream.mass_rate_kg_per_h * gas_mass_fraction
            return inlet_stream.with_new_fluid(new_fluid).with_mass_rate(new_mass_rate)
        else:
            return inlet_stream
