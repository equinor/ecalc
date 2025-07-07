from abc import ABC, abstractmethod

import numpy as np
from numpy.typing import NDArray


class PowerLossFactorInterface(ABC):
    """Interface for power loss factor."""

    @abstractmethod
    def as_vector(self) -> NDArray[np.float64] | None: ...

    @abstractmethod
    def apply_to_array(
        self,
        energy_usage: NDArray[np.float64],
    ) -> NDArray[np.float64]: ...
