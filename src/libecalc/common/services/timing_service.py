"""
A singleton service to register timing information for decorated methods.
It has functionality to store and retrieve timing data.
Storing is achieved through dump to file (csv or json).
"""

import json
from dataclasses import dataclass
from pathlib import Path
from random import randint
from typing import Self

from libecalc.common.errors.exceptions import ProgrammingError


@dataclass
class TimingRecord:
    method_name: str
    elapsed_time_ns: int


class TimingService:
    __instance: Self = None
    """
    A singleton service to register timing information for decorated methods.
    It has functionality to store and retrieve timing data.
    Storing is achieved through dump to file (csv or json).
    """

    def __new__(cls) -> "TimingService":
        instance = super().__new__(cls)
        instance.__timings = []
        return instance

    @classmethod
    def instance(cls) -> Self:
        if cls.__instance is None:
            cls.__instance = cls.__new__(cls)
        return cls.__instance

    def __init__(self) -> None:
        raise ProgrammingError("Use instance() to get a singleton instance of TimingService.")

    def record_timing(self, timing_record: TimingRecord) -> None:
        """
        Record the timing for a method.

        Args:
            timing_record: TimingRecord: The timing record to be added.
        """
        self.__timings.append(timing_record)

    def get_timings(self) -> list[TimingRecord]:
        """
        Get all recorded timings.

        Returns:
            TimingRecordsInterface: A dictionary with method names as keys and lists of TimingRecordInterface as values.
        """
        return self.__timings

    def print_timings(self):
        """
        Print the recorded timings.

        Just a convenience method for quick debugging.

        Returns:
            TimingSummaries: A dictionary with method names as keys and TimingSummaryInterface as values.
        """
        for timing_record in self.__timings:
            print(f"Method: {timing_record.method_name}, Elapsed Time (ns): {timing_record.elapsed_time_ns}")

        # Calculate total time and average time per method
        total_time_ns = sum(timing_record.elapsed_time_ns for timing_record in self.__timings)
        average_time_ns = total_time_ns / len(self.__timings) if self.__timings else 0
        print(f"Total Time (s): {total_time_ns / 10e9}")
        print(f"Average Time per Method (ns): {average_time_ns}")  # median instead?
        print(f"Number of method calls: {len(self.__timings)}")
        # Note: currently we only debug one method at a time, so we do not check for different method names
        # to be extended

    def dump_to_file(self, output_directory: Path, file_format: str = "csv") -> None:
        """
        Dump the recorded timings to a file in the specified format.

        Args:
            file_path (PathLike): The path to the file where timings should be dumped.
            file_format (str): The format of the file ('csv' or 'json'). Default is 'csv'.

        Raises:
            ProgrammingError: If the specified file format is not supported.
        """
        Path.mkdir(output_directory, parents=True, exist_ok=True)

        data = ""
        if file_format == "csv":
            data += "method_name,elapsed_time_ns\n"
            for timing_record in self.__timings:
                data += f"{timing_record.method_name},{timing_record.elapsed_time_ns}\n"

        elif file_format == "json":
            json_data: list[dict] = []
            for timing_record in self.__timings:
                json_data.append(
                    {"method_name": timing_record.method_name, "elapsed_time_ns": timing_record.elapsed_time_ns}
                )
            data = json.dumps(json_data)
        else:
            raise ProgrammingError(f"Unsupported file format: {file_format}")

        file_name = output_directory / f"timings_{str(randint(0, 10000))}.{file_format}"  # noqa: S311
        with open(file_name, "w") as file:
            file.write(data)
