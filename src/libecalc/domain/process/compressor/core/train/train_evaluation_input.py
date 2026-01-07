from dataclasses import dataclass, field
from numbers import Number


@dataclass(frozen=True)
class CompressorTrainEvaluationInput:
    """
    Class to hold the input data for the compressor train evaluation.

    Attributes:
        suction_pressure: The suction pressure of the compressor train [bara].
        discharge_pressure: The discharge pressure of the compressor train [bara].
        interstage_pressure: An optional interstage pressure for multi-stage compressors [bara].
        rates: List of all the flow rates of the different streams in the model.
        rate: Optional shortcut for a single inlet rate.
    """

    suction_pressure: float | None = None
    discharge_pressure: float | None = None
    interstage_pressure: float | None = None
    rates: list[float] | None = None
    rate: float | None = field(default=None)

    def __post_init__(self):
        if self.rate is not None and self.rates is not None:
            raise ValueError("Cannot specify both rate and rates.")
        if self.rate is not None:
            normalized = [self.rate]
        else:
            rates = self.rates
            if rates is None:
                normalized = None
            elif isinstance(rates, Number):
                normalized = [rates]
            elif isinstance(rates, list):
                normalized = rates
            else:
                raise TypeError("rates must be a number, list of numbers, or None.")
        object.__setattr__(self, "rates", normalized)

    def create_conditions_with_new_input(
        self,
        new_rate: float | None = None,
        new_suction_pressure: float | None = None,
        new_discharge_pressure: float | None = None,
        new_interstage_pressure: float | None = None,
        new_rates: list[float] | None = None,
    ) -> "CompressorTrainEvaluationInput":
        """
        Create a new instance of CompressorTrainEvaluationInput with new attributes where given.

        Args:
            new_rate: The flow rate of the compressor train [Sm3/day].
            new_suction_pressure: The suction pressure of the compressor train [bara].
            new_discharge_pressure: The discharge pressure of the compressor train [bara].
            new_interstage_pressure: The interstage pressure for multi-stage compressors [bara].
            new_rates: List of all the flow rates of the different streams in the model.

        Returns:
            A new instance of CompressorTrainEvaluationInput with the updated speed.
        """
        if new_rate is not None:
            new_rates = self.rates.copy()
            new_rates[0] = new_rate
        if new_suction_pressure is None:
            new_suction_pressure = self.suction_pressure
        if new_discharge_pressure is None:
            new_discharge_pressure = self.discharge_pressure
        if new_interstage_pressure is None:
            new_interstage_pressure = self.interstage_pressure
        if new_rates is None:
            new_rates = self.rates

        return CompressorTrainEvaluationInput(
            suction_pressure=new_suction_pressure,
            discharge_pressure=new_discharge_pressure,
            interstage_pressure=new_interstage_pressure,
            rates=new_rates,
        )

    @property
    def inlet_rate(self) -> float | None:
        """Shortcut to get the inlet rate (first rate in the rates list)."""
        if self.rates is None:
            return None
        return self.rates[0]
