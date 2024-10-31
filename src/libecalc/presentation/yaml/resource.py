from typing import Protocol, Union


class Resource(Protocol):
    """
    A resource containing tabular data
    """

    def get_headers(self) -> list[str]: ...

    def get_column(self, header: str) -> list[Union[float, int, str]]: ...


Resources = dict[str, Resource]
