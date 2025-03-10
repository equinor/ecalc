import os
import typing
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Any

from libecalc.common.logger import logger

unique_id: int = 1
"""
global static id to increase by one for each file being dumped
"""


class Jsonable(typing.Protocol):
    """
    Protocol to make sure that functions that are decorated for capture
    can be serialized to json through the json() method
    """

    def json(self) -> str:
        """
        Serialize object as JSON

        :return: a string according to json spec
        """
        ...


def save(output_directory: Path, content: Jsonable):
    """
    A function to save serializable content. Each time this function is
    called the name of the file that data is dumped to (which is an integer) will be incremented with 1.
    E.g. file number one will be given the name 1.json, number two; 2.json and so on.

    :param output_directory:   Where to save it. Missing parent directories will be created.
    :param content:    What to save. Must be serializable to JSON through .json() method
    """
    Path.mkdir(output_directory, parents=True, exist_ok=True)
    global unique_id
    file_name = output_directory / f"{str(unique_id)}.json"
    unique_id += 1

    with open(file_name, "w") as file:
        file.write(content.json())


class Capturer:
    """Decorator to capture values from a decorated function and optionally save to file"""

    @staticmethod
    def capture_return_values(
        do_save_captured_content: bool = False, output_directory: Path = Path(os.getcwd()) / "captured_data"
    ) -> Any | None:
        """If enabled, save the return values from decorated function to the given output directory. If disabled,
        the function works as if the decorator is not there.

        Note! This currently only supports functions that returns a value/object that support serialization to json() through implementing a .json() method

        Args:
            do_save_captured_content: whether the captured content should be saved or not. Default False.
            output_directory: Directory to where the captured content should be stored. Missing parent directories will be created.

        Returns:
            The same signature as the function it is decorating
        """

        def decorate(capturable: Callable[..., Jsonable]):
            @wraps(capturable)
            def with_capture(self, *args, **kwargs):
                return_values = capturable(self, *args, **kwargs)
                try:
                    save(output_directory, return_values) if do_save_captured_content is True else ...
                except Exception as e:
                    logger.debug(f"Failed to dump data for debug {str(e)}. Not critical.")
                return return_values

            return with_capture

        return decorate
