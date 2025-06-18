"""Canonical port-name constants for process units."""

from __future__ import annotations

from enum import Enum


class PortName(str, Enum):
    """Base class for all port name enums."""

    pass


class SingleIO(PortName):
    """Default names for 1-in / 1-out units (valve, pump, compressor etc.)."""

    INLET = "inlet"
    OUTLET = "outlet"


class MixerIO(PortName):
    """Port names for multiple in, one out units."""

    OUTLET = "outlet"
    INLET_1 = "inlet_1"
    INLET_2 = "inlet_2"
    # Add more as needed


class SplitterIO(PortName):
    """Port names for one in, multiple out units."""

    INLET = "inlet"
    OUTLET_1 = "outlet_1"
    OUTLET_2 = "outlet_2"
    # Add more as needed


class SeparatorIO(PortName):
    """Port names for one in, multiple phase outlets."""

    INLET = "inlet"
    GAS_OUTLET = "gas_outlet"
    LIQUID_OUTLET = "liquid_outlet"
