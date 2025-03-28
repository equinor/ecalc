from copy import deepcopy
from decimal import Decimal
from typing import TypeVar

import numpy as np
from pydantic import BaseModel

TResult = TypeVar("TResult")


class Numbers:
    """Class to handle eCalc specific logic to numbers."""

    @staticmethod
    def format_to_precision(number: float, precision: int) -> str:
        """This method is currently only to format numbers for consistent
        reporting, and hence a string is returned, and not the number
        primitive.

        See tests for examples on how it works, but in general:

        * Numbers with decimals are restricted to <#precision> decimals/digits after the decimal sign,
        but only when they are significant (matter, ie. 0.10 is formatted to 0.1)
        * Numbers without decimals, are reported without decimals (ie, where it is not significant)
        * Floats that equal integers are NOT rounded (ie 1000.0 is reported as 1000)
        * If a number has more decimals than precision, it is rounded (3.1415288454854 to 3.14 if precision is 2)
        * If a number is smaller than the 10^-precision (EPSILON), then it is rounded off to "0" (0.001 ~= 0 if precision is 2)

        Uses Dragon4 algorithm implemented by Numpy, with some modifications/overrides as stated above.
        Ref.
            Article: https://www.cs.tufts.edu/~nr/cs257/archive/florian-loitsch/printf.pdf
            Numpy: https://numpy.org/devdocs/reference/generated/numpy.format_float_positional.html

        :param number:
        :param precision:
        :return:
        """
        if precision < -1:
            raise ValueError(f"Precision must be >= 0. {precision} was given.")

        if abs(number) <= pow(
            10, (-precision) - 1
        ):  # -1, because user indicates number of significant decimals behind decimal sign
            return "0"

        my_decimal = Decimal(number)
        significant_digits = my_decimal.adjusted()

        if significant_digits < 0:
            new_precision = precision
        elif significant_digits < precision:
            new_precision = precision - significant_digits  # we dont want unnecessary decimals on high numbers
        else:
            new_precision = 0

        return str(
            np.format_float_positional(
                number,
                new_precision,
                unique=True,
                fractional=True,
                trim="-",
            )
        )

    @staticmethod
    def format_results_to_precision(result: TResult, precision: int) -> TResult:
        """Traverse the graph_results, locate all numbers and round to the specified precision

        Args:
            result: The results
            precision: The precision

        Returns:
            Copy of results, rounded to the given precision
        """

        def recursive_rounding(value):
            if isinstance(value, BaseModel) or hasattr(value, "round_values"):
                for k, v in value.__dict__.items():
                    value.__setattr__(k, recursive_rounding(v))
                return value
            elif isinstance(value, dict):
                return {k: recursive_rounding(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [recursive_rounding(val) for val in value]
            elif isinstance(value, float):
                return float(Numbers.format_to_precision(value, precision=precision))
            else:
                return value

        return recursive_rounding(deepcopy(result))
