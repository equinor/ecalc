import abc
import logging

from libecalc.common.errors.exceptions import InvalidColumnException

logger = logging.getLogger(__name__)


class Resource(abc.ABC):
    """
    A resource containing tabular data
    """

    @abc.abstractmethod
    def get_headers(self) -> list[str]: ...

    @abc.abstractmethod
    def get_column(self, header: str) -> list[float | int | str]: ...

    def get_float_column(self, header: str) -> list[float]:
        try:
            column = self.get_column(header)
            column = [float(value) for value in column]
        except ValueError as e:
            msg = f"Resource contains non-numeric value: {e}"
            logger.error(msg)
            raise InvalidColumnException(header=header, message=msg) from e
        return column


Resources = dict[str, Resource]
