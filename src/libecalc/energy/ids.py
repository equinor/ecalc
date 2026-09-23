"""Shared identifiers, isolated to avoid cyclic imports between energy units and topology."""

from typing import NewType
from uuid import UUID

EnergyUnitId = NewType("EnergyUnitId", UUID)
EnergyConnectionId = NewType("EnergyConnectionId", UUID)
EnergyNetworkId = NewType("EnergyNetworkId", UUID)
