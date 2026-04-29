"""
DDD Tactical Building Blocks

To make sure that we are consistent and make sure that we get
the things right, we reuse the building blocks here in code,
instead of redoing everything all the time, in slightly
different ways, and possibly introducing bugs.
"""

from libecalc.common.ddd.entity import Entity
from libecalc.common.ddd.value_object import value_object

__all__ = ["Entity", "value_object"]
