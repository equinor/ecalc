from typing import Dict, List, Protocol, Union


class Resource(Protocol):
    """
    A resource containing tabular data
    """

    def get_headers(self) -> List[str]: ...

    def get_column(self, header: str) -> List[Union[float, int, str]]: ...


Resources = Dict[str, Resource]
