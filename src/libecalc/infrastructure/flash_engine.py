"""Factory for selecting the FluidService implementation.

Controls which flash engine (NeqSim or Thermopack) is used at runtime.

Configuration (in priority order):
    1. Call set_flash_engine(FlashEngine.THERMOPACK) programmatically
    2. Set env var ECALC_FLASH_ENGINE=thermopack
    3. Default: neqsim
"""

from __future__ import annotations

import logging
import os
from enum import Enum

from libecalc.domain.process.value_objects.fluid_stream.fluid_service import FluidService

_logger = logging.getLogger(__name__)


class FlashEngine(str, Enum):
    NEQSIM = "neqsim"
    THERMOPACK = "thermopack"


def _default_engine() -> FlashEngine:
    env = os.environ.get("ECALC_FLASH_ENGINE", "").lower().strip()
    if env in FlashEngine.__members__.values():
        return FlashEngine(env)
    return FlashEngine.NEQSIM


_active_engine: FlashEngine = _default_engine()


def set_flash_engine(engine: FlashEngine) -> None:
    """Set the active flash engine. Must be called before any FluidService usage."""
    global _active_engine
    _active_engine = engine
    _logger.info(f"Flash engine set to: {engine.value}")


def get_flash_engine() -> FlashEngine:
    """Get the currently active flash engine."""
    return _active_engine


def get_fluid_service() -> FluidService:
    """Get the active FluidService singleton based on configured engine.

    Returns:
        The FluidService instance for the active engine.
    """
    if _active_engine == FlashEngine.THERMOPACK:
        from libecalc.infrastructure.thermopack_fluid_service.fluid_service import ThermopackFluidService

        return ThermopackFluidService.instance()
    else:
        from ecalc_neqsim_wrapper.fluid_service import NeqSimFluidService

        return NeqSimFluidService.instance()
