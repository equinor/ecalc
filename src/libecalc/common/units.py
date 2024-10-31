from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from enum import Enum
from functools import singledispatch
from typing import TypeVar, Union

import numpy as np
from numpy.typing import NDArray

from libecalc.common.logger import logger

TInput = TypeVar("TInput", bound=Union[int, float, NDArray[np.float64], list])


def _type_handler(unit_func: Callable[[TInput], TInput]) -> Callable[[TInput], TInput]:
    """
    Receives a unit conversion function and registers a list specific override so that the resulting unit
    function can handle conversion of both lists and single items.

    Args:
        unit_func: the unit conversion function

    Returns: a unit conversion function that can handle both lists and single items

    """

    @singledispatch
    def func(i: TInput) -> Callable[[TInput], TInput]:
        """
        Apply unit_func to a single item
        Args:
            i: the single item that should be converted

        Returns:

        """
        return unit_func(i)

    @func.register  # type: ignore
    def _(i: list) -> TInput:
        """
        list specific override. The type of the first parameter is used to decide which function to use.
         Args:
             i: list of items that should be converted

         Returns:

        """
        return unit_func(np.asarray(i, dtype=(type(i)))).tolist()  # type: ignore

    return func


class UnitConstants:
    TO_KILO = 1e-3
    STANDARD_PRESSURE_BARA = 1.01325
    STANDARD_TEMPERATURE_KELVIN = 288.15
    STANDARD_TEMPERATURE_CELSIUS = 15.0
    CELSIUS_TO_KELVIN = 273.15
    HOURS_PER_DAY = 24.0
    EARTH_GRAVITY = 9.81
    GAS_CONSTANT = 8.314472  # m3 * Pa / (K * mol) - SI units
    WATT_TO_MEGAWATT = 1e-6
    SECONDS_PER_HOUR = 3600.0
    SECONDS_IN_A_DAY = 86400.0
    WATT_PER_MEGAWATT = 1e6


class Unit(str, Enum):
    """A very simple unit registry to convert between common eCalc units."""

    NONE = "N/A"
    KG_BOE = "kg/BOE"
    KG_SM3 = "kg/Sm3"
    KG_M3 = "kg/m3"
    STANDARD_CUBIC_METER = "Sm3"
    BOE = "BOE"

    TONS_PER_DAY = "t/d"
    TONS = "t"

    KILO_PER_DAY = "kg/d"
    KILO_PER_HOUR = "kg/h"
    KILO = "kg"

    LITRES_PER_DAY = "L/d"
    LITRES = "L"

    MEGA_WATT_DAYS = "MWd"
    GIGA_WATT_HOURS = "GWh"
    MEGA_WATT = "MW"

    YEAR = "Y"
    BARA = "bara"
    KILO_PASCAL = "kPa"
    PASCAL = "Pa"

    CELSIUS = "C"
    KELVIN = "K"

    FRACTION = "frac"
    PERCENTAGE = "%"

    POLYTROPIC_HEAD_KILO_JOULE_PER_KG = "kJ/kg"
    POLYTROPIC_HEAD_JOULE_PER_KG = "J/kg"
    POLYTROPIC_HEAD_METER_LIQUID_COLUMN = "N.m/kg"

    ACTUAL_VOLUMETRIC_M3_PER_HOUR = "Am3/h"
    STANDARD_CUBIC_METER_PER_DAY = "Sm3/d"

    SPEED_RPM = "RPM"

    def __str__(self) -> str:
        return self.value

    @staticmethod
    def _unit_registry() -> dict[Unit, dict[Unit, Callable]]:
        unit_registry: dict[Unit, dict[Unit, Callable]] = defaultdict(dict)

        unit_registry[Unit.TONS_PER_DAY][Unit.KILO_PER_DAY] = lambda a: a * 1000
        unit_registry[Unit.KILO_PER_DAY][Unit.TONS_PER_DAY] = lambda a: a / 1000

        unit_registry[Unit.KILO][Unit.TONS] = lambda a: a / 1000
        unit_registry[Unit.TONS][Unit.KILO] = lambda a: a * 1000

        unit_registry[Unit.STANDARD_CUBIC_METER][Unit.LITRES] = lambda a: a * 1000
        unit_registry[Unit.LITRES][Unit.STANDARD_CUBIC_METER] = lambda a: a / 1000

        # Temperature
        unit_registry[Unit.CELSIUS][Unit.KELVIN] = lambda a: a + 273.15
        unit_registry[Unit.KELVIN][Unit.CELSIUS] = lambda a: a - 273.15

        # Pressure
        unit_registry[Unit.BARA][Unit.KILO_PASCAL] = lambda a: a * 100
        unit_registry[Unit.KILO_PASCAL][Unit.BARA] = lambda a: a / 100
        unit_registry[Unit.BARA][Unit.PASCAL] = lambda a: a * 1e5
        unit_registry[Unit.PASCAL][Unit.BARA] = lambda a: a / 1e5

        # User for compressor charts.
        unit_registry[Unit.PERCENTAGE][Unit.FRACTION] = lambda a: a / 100
        unit_registry[Unit.FRACTION][Unit.PERCENTAGE] = lambda a: a * 100

        # Compressor chart polytropic head
        unit_registry[Unit.POLYTROPIC_HEAD_JOULE_PER_KG][Unit.POLYTROPIC_HEAD_KILO_JOULE_PER_KG] = lambda a: a / 1000
        unit_registry[Unit.POLYTROPIC_HEAD_KILO_JOULE_PER_KG][Unit.POLYTROPIC_HEAD_JOULE_PER_KG] = lambda a: a * 1000
        unit_registry[Unit.POLYTROPIC_HEAD_METER_LIQUID_COLUMN][Unit.POLYTROPIC_HEAD_JOULE_PER_KG] = (
            lambda a: a * UnitConstants.EARTH_GRAVITY
        )
        unit_registry[Unit.POLYTROPIC_HEAD_METER_LIQUID_COLUMN][Unit.POLYTROPIC_HEAD_KILO_JOULE_PER_KG] = (
            lambda a: (a * UnitConstants.EARTH_GRAVITY) / 1000
        )
        unit_registry[Unit.POLYTROPIC_HEAD_JOULE_PER_KG][Unit.POLYTROPIC_HEAD_METER_LIQUID_COLUMN] = (
            lambda a: a / UnitConstants.EARTH_GRAVITY
        )
        unit_registry[Unit.POLYTROPIC_HEAD_KILO_JOULE_PER_KG][Unit.POLYTROPIC_HEAD_METER_LIQUID_COLUMN] = (
            lambda a: (a * 1000) / UnitConstants.EARTH_GRAVITY
        )

        # Other
        unit_registry[Unit.KG_BOE][Unit.KG_SM3] = lambda a: a * 6.29
        unit_registry[Unit.KG_SM3][Unit.KG_BOE] = lambda a: a / 6.29
        unit_registry[Unit.STANDARD_CUBIC_METER][Unit.BOE] = lambda a: a * 6.29
        unit_registry[Unit.BOE][Unit.STANDARD_CUBIC_METER] = lambda a: a / 6.29
        unit_registry[Unit.MEGA_WATT_DAYS][Unit.GIGA_WATT_HOURS] = lambda a: a * 24 / 1000

        return unit_registry

    def to(self, unit: Unit) -> Callable:
        if self is unit:
            return lambda a: a

        try:
            unit_registry = Unit._unit_registry()
            try:
                converter = _type_handler(unit_registry[self][unit])
                if converter is not None:
                    return converter
            except KeyError as ke:
                msg = (
                    f"The conversion between {self.value} to {unit.value}"
                    f" has not been added to unit conversion registry."
                )
                logger.exception(msg)
                raise NotImplementedError(msg) from ke
                # NOTE: Not sure about this one, add conversion manually both ways for now
                # Maybe add all conversions as of base of 10?
                # return lambda inv: inv / unit_registry[unit][self](1)
        except Exception as e:
            msg = (
                f"The conversion between {self.value} to {unit.value}"
                f" has not been added to unit conversion registry.: {e}"
            )
            logger.exception(msg)
            raise NotImplementedError(msg) from e

    def volume_to_rate(self) -> Unit:
        """
        For a unit describing volume in a period, the corresponding rate unit is returned.
        """
        if self == Unit.STANDARD_CUBIC_METER:
            return Unit.STANDARD_CUBIC_METER_PER_DAY
        elif self == Unit.MEGA_WATT_DAYS:
            return Unit.MEGA_WATT
        elif self == Unit.TONS:
            return Unit.TONS_PER_DAY
        elif self == Unit.KILO:
            return Unit.KILO_PER_DAY
        elif self == Unit.LITRES:
            return Unit.LITRES_PER_DAY
        else:
            raise NotImplementedError(f"Unknown unit for cumulative calculation '{self}'")

    def rate_to_volume(self) -> Unit:
        """
        For a unit describing rates, the corresponding unit for volume in a period is returned.
        """
        if self == Unit.STANDARD_CUBIC_METER_PER_DAY:
            return Unit.STANDARD_CUBIC_METER
        elif self == Unit.MEGA_WATT:
            return Unit.MEGA_WATT_DAYS
        elif self == Unit.TONS_PER_DAY:
            return Unit.TONS
        elif self == Unit.KILO_PER_DAY:
            return Unit.KILO
        elif self == Unit.LITRES_PER_DAY:
            return Unit.LITRES
        else:
            raise NotImplementedError(f"Unknown unit for rate calculation '{self}'")
