from libecalc.domain.component_validation_error import DomainValidationException


class SimplifiedTrainEnvelopeException(DomainValidationException):
    """Base exception for simplified compressor train envelope validation errors.

    These are user-facing validation errors that occur when extracting operational
    envelopes for simplified train models.
    """

    pass


class EmptyEnvelopeException(SimplifiedTrainEnvelopeException):
    """No valid operational data found for simplified train model.

    Raised when envelope extraction finds no valid operating points across
    all operational settings for trains sharing the same compressor model.
    """

    def __init__(self, model_reference: str, compressor_indices: list[int]):
        self.model_reference = model_reference
        self.compressor_indices = compressor_indices
        message = (
            f"No valid operational data found for simplified train model '{model_reference}'. "
            f"Compressor train indices {compressor_indices} have no valid rate and pressure data "
            f"across all operational settings. This may be caused by:\n"
            f"  - All rates are zero or NaN\n"
            f"  - All pressures are zero, negative, or NaN\n"
            f"  - Mismatched array lengths in operational settings\n"
            f"Please verify the rate and pressure expressions for these trains."
        )
        super().__init__(message)


class InvalidEnvelopeDataException(SimplifiedTrainEnvelopeException):
    """Envelope data arrays have inconsistent lengths.

    Raised when the operational envelope has mismatched array lengths between
    rates, suction pressures, and discharge pressures.
    """

    def __init__(
        self,
        rates_length: int,
        suction_length: int,
        discharge_length: int,
        model_reference: str | None = None,
        compressor_indices: list[int] | None = None,
    ):
        self.rates_length = rates_length
        self.suction_length = suction_length
        self.discharge_length = discharge_length
        self.model_reference = model_reference
        self.compressor_indices = compressor_indices

        context = ""
        if model_reference:
            context = f" for model '{model_reference}'"
        if compressor_indices:
            context += f" (train indices {compressor_indices})"

        message = (
            f"Operational envelope data has mismatched array lengths{context}:\n"
            f"  - Rates: {rates_length} values\n"
            f"  - Suction pressures: {suction_length} values\n"
            f"  - Discharge pressures: {discharge_length} values\n"
            f"All arrays must have the same length. This indicates inconsistent data "
            f"in the operational settings."
        )
        super().__init__(message)
