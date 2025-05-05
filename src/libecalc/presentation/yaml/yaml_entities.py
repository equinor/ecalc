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
)
from libecalc.domain.process.compressor.dto.model_types import CompressorModelTypes
from libecalc.domain.process.dto.base import EnergyModel
from libecalc.domain.process.dto.tabulated import TabulatedData
from libecalc.domain.process.generator_set import GeneratorSetProcessUnit
from libecalc.domain.process.pump.pump import PumpModelDTO
from libecalc.domain.resource import Resource
from libecalc.dto import FuelType
from libecalc.presentation.yaml.domain.reference_service import InvalidReferenceException, ReferenceService


@dataclass
class MemoryResource(Resource):
    """
    Resource object where the data is already read and parsed.
    """

    # TODO: Hmmm, so the validation needs to be done, not only in the `from methods`? But also in the init
    headers: list[str]
    data: list[list[float | int | str]]

    def get_headers(self) -> list[str]:
        return self.headers

    def get_column(self, header: str) -> list[float | int | str]:
        try:
            header_index = self.headers.index(header)
            return self.data[header_index]
        except ValueError as e:
            raise HeaderNotFoundException(header=header) from e
        except IndexError as e:
            # Should validate that header and columns are of equal length, but that is currently done elsewhere.
            raise ColumnNotFoundException(header=header) from e

    # def from_stringlike(self, csv_data: str, StringIO | TextIO) -> Self:
    # def from_string(csv_data: str) -> Self:
    def validate(self) -> Self:
        self._validate_headers(self.headers)
        self._validate_not_nan(self.data)

        return self

    @classmethod
    def from_string(cls, csv_data: str, fill_nan: bool = True) -> Self:
        """

        Args:
            csv_data:
            fill_nan:

        Returns:

        """
        df_resource = pd.read_csv(
            StringIO(csv_data), comment="#", float_precision="round_trip", skipinitialspace=True, thousands=" "
        )

        cls._validate_headers_fast(df_resource.columns)
        headers = df_resource.columns.str.strip().tolist()

        cls._validate_headers(headers)
        # TODO: Pick one of "fast and slow"
        if fill_nan:
            df_resource = df_resource.fillna("")
        else:
            cls._validate_not_nan_fast(df_resource)
            cls._validate_not_nan(df_resource.T.values.tolist())

        data = df_resource.T.values.tolist()
        return MemoryResource(headers=headers, data=data)

    # TODO:
    @classmethod
    def from_path(cls, path: Path | str, fill_nan: bool = True) -> Self:
        with open(path) as f:
            return MemoryResource.from_string(f.read(), fill_nan=fill_nan)

    @staticmethod
    def _validate_headers(headers: list[str]) -> None:
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
    def _validate_headers_fast(headers: pd.Series) -> None:
        if not headers.str.fullmatch(r"^[A-Za-z][A-Za-z0-9_.,\-\s#+:/]*$").all():
            # if not all([re.match(r"^[A-Za-z][A-Za-z0-9_.,\-\s#+:/]*$", header) for header in headers]):
            raise InvalidHeaderException(
                "Each header value must start with a letter in the english alphabet (a-zA-Z). "
                "Header may only contain letters, spaces, numbers, or any of the following characters "
                "[ _ - # + : . , /]."
            )
        if headers.str.fullmatch(r"^Unnamed: \d+$").any():
            # if re.match(r"^Unnamed: \d+$", headers.str):
            raise InvalidHeaderException(message="One or more headers are missing in resource")

    @staticmethod
    def _validate_not_nan(columns: list[list]) -> None:
        for column in columns:
            for index, item in enumerate(column):
                if isinstance(item, float) and math.isnan(item):
                    raise InvalidColumnException(
                        # TODO: Fix this to actually get column if we are to use this version
                        header="",  # column,
                        message=(
                            f"CSV file contains invalid data at row {index + 1}, "
                            "all headers must be associated with a valid column value."
                        ),
                        row=index,
                    )

    @staticmethod
    def _validate_not_nan_fast(df: pd.DataFrame) -> None:
        mask = df.isna()
        headers = ", ".join(df.columns[mask.any()])
        rows = ", ".join(df.index[mask.any(axis=1)].astype(str))
        if mask.any().any():
            raise InvalidColumnException(
                header=headers,
                message=(
                    f"CSV file contains invalid data for headers '{headers}' at rows '{rows}'."
                    "All headers must be associated with a valid column value."
                ),
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

    def get_generator_set_model(self, reference: str) -> GeneratorSetProcessUnit:
        model = self._get_model_reference(reference, "generator set model")
        if not isinstance(model, GeneratorSetProcessUnit):
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
