from typing import TypeVar

from libecalc.common.errors.exceptions import (
    DifferentLengthsError,
    IncompatibleDataError,
    MissingKeyError,
)

T = TypeVar("T")


class MathUtil:
    @staticmethod
    def elementwise_subtraction_by_key(this: dict[T, float], that: dict[T, float]) -> dict[T, float]:
        """For compatible dicts, with the same keys, subtract corresponding numbers in lists for each key
        :param this:
        :param that:
        :return:    a dict containing the delta/subtraction of each value for corresponding key.

        :throws: IncompatibleDataError if dicts cannot be subtracted
        """
        if this is None or that is None:
            raise IncompatibleDataError(f"A or B is None.dict A has value {this}, and B has {that}")

        if len(this.items()) != len(that.items()):
            raise DifferentLengthsError(
                f"Subtracting values A-B failed due to different vector lengths.dict A has value {len(this.items())}, but B has {len(that.items())}"
            )

        delta_dict: dict[T, float] = {}

        for item_key, this_value in this.items():
            that_value = that.get(item_key)

            if that_value is None:
                raise MissingKeyError(
                    f"Subtracting values A-B failed due to missing time step in B. Key {item_key} had value {this_value} in A but is missing in B"
                )

            if that_value is not None:
                delta_dict[item_key] = this_value - that_value

        return delta_dict
