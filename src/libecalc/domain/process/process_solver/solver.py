import abc
from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

from libecalc.domain.process.value_objects.fluid_stream import FluidStream

TConfiguration = TypeVar("TConfiguration")


@dataclass
class Solution(Generic[TConfiguration]):
    success: bool
    configuration: TConfiguration


class Solver(abc.ABC, Generic[TConfiguration]):
    @abc.abstractmethod
    def solve(self, func: Callable[[TConfiguration], FluidStream]) -> Solution[TConfiguration]: ...
