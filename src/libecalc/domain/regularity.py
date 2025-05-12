from datetime import datetime

from libecalc.common.time_utils import Period
from libecalc.common.units import Unit
from libecalc.common.utils.rates import TimeSeriesFloat
from libecalc.common.variables import ExpressionEvaluator, VariablesMap
from libecalc.domain.base_temporal_logic import BaseTemporalLogic
from libecalc.domain.component_validation_error import ComponentValidationException, ModelValidationError
from libecalc.domain.infrastructure.energy_components.utils import _convert_keys_in_dictionary_from_str_to_periods
from libecalc.expression import Expression
from libecalc.expression.expression import ExpressionType
from libecalc.presentation.yaml.validation_errors import Location


class Regularity(BaseTemporalLogic):
    """
    Represents the regularity for an installation.

    This class models the regularity values over a specified time period,
    including validation to ensure they are valid fractions between 0 and 1.
    """

    def __init__(
        self,
        name: str,
        target_period: Period,
        expression_evaluator: ExpressionEvaluator,
        expression: ExpressionType | dict[datetime, ExpressionType] | None = None,
    ):
        super().__init__(name, expression_evaluator, target_period, expression)
        self.data: dict[Period, Expression]  # Eksplicit typeannotasjon for MyPy
        self.check_regularity()
        self.validate()

    @property
    def time_series(self) -> TimeSeriesFloat:
        """
        Returns the evaluated regularity values as a time series.
        """
        return TimeSeriesFloat(
            periods=self.expression_evaluator.get_periods(),
            values=self.values,
            unit=Unit.NONE,
        )

    def default_expression_value(self) -> float:
        """
        Returns the default expression value for Regularity.
        """
        return 1

    def check_regularity(self) -> dict[Period, Expression]:
        """
        Validates and converts the keys in the regularity dictionary from strings to Period objects if necessary.
        """
        if isinstance(self.data, dict) and len(self.data.values()) > 0:
            self.data = _convert_keys_in_dictionary_from_str_to_periods(self.data)
        return self.data

    def validate(self):
        """
        Validates the evaluated regularity values for the installation.

        Ensures that all values in the `evaluated_regularity` time series are fractions
        between 0 and 1. If any value falls outside this range, a `ComponentValidationException`
        is raised with details about the invalid value and its location.

        Raises:
            ComponentValidationException: If any regularity value is not between 0 and 1.
        """
        invalid_values = [value for value in self.values if not (0 <= value <= 1)]
        if invalid_values:
            msg = (
                f"REGULARITY for component '{self.name}' must evaluate to fractions between 0 and 1. "
                f"Invalid values: {invalid_values}"
            )
            raise ComponentValidationException(
                errors=[
                    ModelValidationError(
                        name=self.name,
                        location=Location([self.name]),
                        message=msg,
                    )
                ],
            )

    @classmethod
    def create(
        cls,
        period: Period = None,
        expression_evaluator: ExpressionEvaluator = None,
        expression_value: ExpressionType = 1,
    ):
        """
        Creates a default Regularity instance with a given expression value.
        Mostly used for testing purposes.
        """
        if period and not expression_evaluator:
            expression_evaluator = VariablesMap(time_vector=[period.start, period.end])

        if not period and not expression_evaluator:
            expression_evaluator = VariablesMap(
                time_vector=[Period(datetime(1900, 1, 1)).start, Period(datetime(1900, 1, 1)).end]
            )

        return cls(
            name="default",
            expression=expression_value,
            target_period=expression_evaluator.get_period(),
            expression_evaluator=expression_evaluator,
        )
