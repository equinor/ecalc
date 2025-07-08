from abc import ABC, abstractmethod

import numpy as np


class TimeSeriesInterface(ABC):
    @abstractmethod
    def get_values_list(self) -> list[float]: ...

    @abstractmethod
    def get_values_array(self) -> np.ndarray: ...
