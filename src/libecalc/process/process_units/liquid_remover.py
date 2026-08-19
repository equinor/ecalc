import logging
from typing import Final

from libecalc.process.fluid_stream.constants import ThermodynamicConstants
from libecalc.process.fluid_stream.fluid_service import FluidService
from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_pipeline.process_error import NoGasPhaseError
from libecalc.process.process_pipeline.process_unit import ProcessUnit, ProcessUnitId

logger = logging.getLogger(__name__)

_PURE_VAPOR_THRESHOLD = ThermodynamicConstants.PURE_VAPOR_THRESHOLD  # 0.9999
_PURE_LIQUID_THRESHOLD = 1.0 - _PURE_VAPOR_THRESHOLD  # 0.0001


class LiquidRemover(ProcessUnit):
    def __init__(self, fluid_service: FluidService, process_unit_id: ProcessUnitId | None = None):
        self._id: Final[ProcessUnitId] = process_unit_id or ProcessUnit._create_id()
        self._fluid_service = fluid_service

    def get_id(self) -> ProcessUnitId:
        return self._id

    def _is_supercritical(self, inlet_stream: FluidStream) -> bool:
        """Check if the fluid is above its EoS-computed critical point.

        Uses the fluid service's cached critical point calculation, which is
        exact for both pure components and mixtures.
        """
        tc, pc = self._fluid_service.get_critical_point(inlet_stream.fluid_model)
        return inlet_stream.temperature_kelvin > tc and inlet_stream.pressure_bara > pc

    def propagate_stream(self, inlet_stream: FluidStream) -> FluidStream:
        """Remove liquid from a two-phase fluid stream.

        Liquid removal only makes sense when both phases coexist:

        - vapor_fraction >= 0.9999: all gas, nothing to remove.
        - vapor_fraction <= 0.0001 AND supercritical: mislabelled by flash,
          pass through unchanged.
        - vapor_fraction <= 0.0001 AND NOT supercritical: genuinely liquid,
          raise NoGasPhaseError — liquid removal cannot produce gas.
        - Otherwise: genuine two-phase, remove liquid and keep gas.
        """
        vf = inlet_stream.vapor_fraction_molar

        if vf >= _PURE_VAPOR_THRESHOLD:
            return inlet_stream

        if vf <= _PURE_LIQUID_THRESHOLD:
            if self._is_supercritical(inlet_stream):
                logger.debug(
                    "LiquidRemover: skipping — supercritical fluid (T=%.1f K, P=%.1f bara, vf=%.6f)",
                    inlet_stream.temperature_kelvin,
                    inlet_stream.pressure_bara,
                    vf,
                )
                return inlet_stream

            raise NoGasPhaseError(
                process_unit_id=self._id,
                vapor_fraction=vf,
            )

        new_fluid = self._fluid_service.remove_liquid(inlet_stream.fluid)
        inlet_molar_mass = inlet_stream.fluid.molar_mass
        assert inlet_molar_mass > 0.0, (
            f"Degenerate stream with non-positive molar mass ({inlet_molar_mass}) reached LiquidRemover — "
            "this should have been caught at stream construction."
        )
        gas_mass_fraction = vf * new_fluid.molar_mass / inlet_molar_mass
        new_mass_rate = inlet_stream.mass_rate_kg_per_h * gas_mass_fraction
        return inlet_stream.with_new_fluid(new_fluid).with_mass_rate(new_mass_rate)
