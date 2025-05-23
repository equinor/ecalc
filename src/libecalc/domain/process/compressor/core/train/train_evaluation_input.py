from dataclasses import dataclass


@dataclass(frozen=True)
class CompressorTrainEvaluationInput:
    """
    Class to hold the input data for the compressor train evaluation.

    Attributes:
        rate: The flow rate of at the inlet of the compressor train [Sm3/day].
        suction_pressure: The suction pressure of the compressor train [bara].
        discharge_pressure: The discharge pressure of the compressor train [bara].
        interstage_pressure: An optional interstage pressure for multi-stage compressors [bara].
        speed: The speed of the compressor train [rpm]. This is optional and can be None.

    """

    rate: float | None = None
    suction_pressure: float | None = None
    discharge_pressure: float | None = None
    interstage_pressure: float | None = None
    speed: float | None = None
