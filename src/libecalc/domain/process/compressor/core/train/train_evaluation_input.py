from dataclasses import dataclass


@dataclass(frozen=True)
class CompressorTrainEvaluationInput:
    """
    Class to hold the input data for the compressor train evaluation.

    Attributes:
        discharge_pressure: The discharge pressure of the compressor train [bara].
        interstage_pressure: An optional interstage pressure for multi-stage compressors [bara].
        speed: The speed of the compressor train [rpm]. This is optional and can be None.
        stream_rates: List of all the flow rates of the different streams in the model
        stream_to_maximize: The index of the stream to maximize in the evaluation. Default is 0.
    """

    discharge_pressure: float | None = None
    interstage_pressure: float | None = None
    speed: float | None = None
    stream_rates: list[float] | None = None
    stream_to_maximize: int = 0

    def create_conditions_with_new_input(
        self,
        new_discharge_pressure: float | None = None,
        new_interstage_pressure: float | None = None,
        new_speed: float | None = None,
        new_stream_rates: list[float] | None = None,
        new_stream_to_maximize: int | None = None,
    ) -> "CompressorTrainEvaluationInput":
        """
        Create a new instance of CompressorTrainEvaluationInput with new attributes where given.

        Args:
            new_discharge_pressure: The discharge pressure of the compressor train [bara].
            new_interstage_pressure: The interstage pressure for multi-stage compressors [bara].
            new_speed: The speed of the compressor train [rpm].
            new_stream_rates: List of all the flow rates of the different streams in the model.
            new_stream_to_maximize: The index of the stream to maximize in the evaluation.

        Returns:
            A new instance of CompressorTrainEvaluationInput with the updated speed.
        """
        if new_discharge_pressure is None:
            new_discharge_pressure = self.discharge_pressure
        if new_interstage_pressure is None:
            new_interstage_pressure = self.interstage_pressure
        if new_speed is None:
            new_speed = self.speed
        if new_stream_rates is None:
            new_stream_rates = self.stream_rates
        if new_stream_to_maximize is None:
            new_stream_to_maximize = self.stream_to_maximize

        return CompressorTrainEvaluationInput(
            discharge_pressure=new_discharge_pressure,
            interstage_pressure=new_interstage_pressure,
            speed=new_speed,
            stream_rates=new_stream_rates,
            stream_to_maximize=new_stream_to_maximize,
        )
