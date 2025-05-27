import math
import re
from dataclasses import dataclass
from enum import Enum
from io import StringIO
from pathlib import Path
from typing import Self, TextIO, get_args

import pandas as pd

from libecalc.common.errors.exceptions import (
    ColumnNotFoundException,
    HeaderNotFoundException,
    InvalidColumnException,
    InvalidHeaderException,
    InvalidResourceException,
)
from libecalc.domain.infrastructure.energy_components.generator_set import GeneratorSetModel
from libecalc.domain.process.compressor.dto.model_types import CompressorModelTypes
from libecalc.domain.process.dto.base import EnergyModel
from libecalc.domain.process.dto.tabulated import TabulatedData
from libecalc.domain.process.pump.pump import PumpModelDTO
from libecalc.domain.resource import Resource
from libecalc.dto import FuelType
from libecalc.presentation.yaml.domain.reference_service import InvalidReferenceException, ReferenceService


@dataclass
class MemoryResource(Resource):
    """Resource object where the data is already read and parsed.

    Attributes:
        headers: Header names.
        data: Column contents.
    """

    headers: list[str]
    data: list[list[float | int | str]]

    def get_headers(self) -> list[str]:
        return self.headers

    def get_column(self, header: str) -> list[float | int | str]:
        """Get data in the specified column.

        Args:
            header: Header name to get column data for.

        Returns:
            Column data.
        """
        try:
            header_index = self.headers.index(header)
            return self.data[header_index]
        except ValueError as e:
            raise HeaderNotFoundException(header=header) from e
        except IndexError as e:
            # Should validate that header and columns are of equal length, but that is currently done elsewhere.
            raise ColumnNotFoundException(header=header) from e

    def validate(self, allow_nans: bool) -> Self:
        self._validate_headers(self.headers)
        if not allow_nans:
            self._validate_not_nan(self.data, self.headers)
        return self

    @classmethod
    def from_string(cls, csv_data: str, allow_nans: bool) -> Self:
        """Read csv strings with settings:
            comment=#, float_precision="round_trip", skipinitialspace=True, and thousands=" ".

        Args:
            csv_data: Comma separated data.
            allow_nans: Whether to fail validation on nan values.

        Returns:
            MemoryResource.
        """
        try:
            df_resource = pd.read_csv(
                StringIO(csv_data), comment="#", float_precision="round_trip", skipinitialspace=True, thousands=" "
            )
        except pd.errors.ParserError as e:
            msg = str(e)
            if "Expected" in msg:
                msg = "Expected" + msg.split("Expected", 1)[1]
            raise InvalidResourceException(title="Invalid CSV data", message=msg) from e
        except ValueError as e:
            raise InvalidResourceException(title="Invalid resource", message=str(e)) from e

        headers = df_resource.columns.str.strip().tolist()
        cls._validate_headers(headers)

        if not allow_nans:
            tmp_data: list[list[float | int | str]] = df_resource.T.values.tolist()
            cls._validate_not_nan(tmp_data, headers)

        data: list[list[float | int | str]]
        if df_resource.empty:
            # Empty column data is fine, but it must retain the shape of the headers.
            data = [[] * len(headers)]
        else:
            data = df_resource.T.values.tolist()

        return MemoryResource(headers=headers, data=data)

    @classmethod
    def from_path(cls, path: Path | str, allow_nans: bool) -> Self:
        """Read csv strings with settings equals to `from_string`.

        Args:
            path: Path to csv file.
            allow_nans: Whether to fail validation on nan values.

        Returns:
            MemoryResource.
        """
        with open(path) as f:
            return MemoryResource.from_string(f.read(), allow_nans=allow_nans)

    @staticmethod
    def _validate_headers(headers: list[str]) -> None:
        """Ensure headers only contains allowed characters, and no unnamed columns exist.

        Args:
            headers: The headers to validate.

        Raises:
            InvalidHeaderException: If headers do not follow naming conventions, or are unnamed.
        """
        for header in headers:
            if not re.match(r"^[A-Za-z][A-Za-z0-9_.,\-\s#+:/]*$", header):
                raise InvalidHeaderException(
                    "Each header value must start with a letter in the english alphabet (a-zA-Z). "
                    "Header may only contain letters, spaces, numbers, or any of the following characters "
                    "[ _ - # + : . , /]."
                )
            if re.match(r"^Unnamed: \d+$", header):
                raise InvalidHeaderException(message="One or more headers are missing in resource")

    @staticmethod
    def _validate_not_nan(rows: list[list[float | int | str]], headers: list[str] | None = None) -> None:
        """Find the first value containing NaN and raise an error message with row index and optional column name.

        Args:
            rows: The contents of the columns.
            headers: Optional, if set it is used to give better error messages. Defaults to None.

        Raises:
            InvalidColumnException: If there are NaNs in the data.
        """
        err_header = ""
        for i, row in enumerate(rows):
            for index_col, item in enumerate(row):
                if isinstance(item, float) and math.isnan(item):
                    if headers is not None:
                        err_header = headers[index_col]
                    raise InvalidColumnException(
                        header=err_header,
                        message=(
                            "CSV file contains invalid data all headers must be associated with a valid column value."
                        ),
                        row=i,
                    )


@dataclass
class References(ReferenceService):
    models: dict[str, EnergyModel] = None
    fuel_types: dict[str, FuelType] = None

    def get_fuel_reference(self, reference: str) -> FuelType:
        try:
            return self.fuel_types[reference]
        except (KeyError, TypeError) as e:
            # KeyError: key does not exist
            # TypeError: fuel_types is None
            raise InvalidReferenceException("fuel", reference, self.fuel_types.keys()) from e

    def _get_model_reference(self, reference: str, reference_type_name: str) -> EnergyModel:
        try:
            return self.models[reference]
        except (KeyError, TypeError) as e:
            # KeyError: key does not exist
            # TypeError: fuel_types is None
            raise InvalidReferenceException(reference_type_name, reference, self.models.keys()) from e

    def get_generator_set_model(self, reference: str) -> GeneratorSetModel:
        model = self._get_model_reference(reference, "generator set model")
        if not isinstance(model, GeneratorSetModel):
            raise InvalidReferenceException("generator set model", reference)
        return model

    def get_compressor_model(self, reference: str) -> CompressorModelTypes:
        model = self._get_model_reference(reference, "compressor model")
        if not isinstance(model, get_args(CompressorModelTypes)):
            raise InvalidReferenceException("compressor model", reference)
        return model  # noqa

    def get_pump_model(self, reference: str) -> PumpModelDTO:
        model = self._get_model_reference(reference, "compressor model")
        if not isinstance(model, PumpModelDTO):
            raise InvalidReferenceException("pump model", reference)
        return model

    def get_tabulated_model(self, reference: str) -> TabulatedData:
        model = self._get_model_reference(reference, "tabulated")
        if not isinstance(model, TabulatedData):
            raise InvalidReferenceException("tabulated", reference)
        return model


class YamlTimeseriesType(str, Enum):
    MISCELLANEOUS = "MISCELLANEOUS"
    DEFAULT = "DEFAULT"


@dataclass
class YamlTimeseriesResource:
    name: str
    typ: YamlTimeseriesType


@dataclass
class ResourceStream:
    name: str
    stream: TextIO

    # Implement read to make resource behave as a stream.
    def read(self, *args, **kwargs):
        return self.stream.read(*args, **kwargs)
