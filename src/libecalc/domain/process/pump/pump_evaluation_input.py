from dataclasses import dataclass


@dataclass(frozen=True)
class PumpEvaluationInputSingleTimeStep:
    rate: float
    suction_pressure: float
    discharge_pressure: float
    fluid_density: float
