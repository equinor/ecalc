from dataclasses import dataclass


@dataclass
class Boundary:
    min: float
    max: float

    def with_margin(self, epsilon: float) -> "Boundary":
        """Shrink boundary inward by a relative margin."""
        return Boundary(
            min=self.min * (1 + epsilon) if self.min > 0 else self.min,
            max=self.max * (1 - epsilon) if self.max > 0 else self.max,
        )
