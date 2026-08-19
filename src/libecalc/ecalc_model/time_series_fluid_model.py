from libecalc.common.ddd import value_object
from libecalc.common.errors.exceptions import ProgrammingError
from libecalc.common.time_utils import Period
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression
from libecalc.process.fluid_stream.fluid_model import EoSModel, FluidComposition, FluidModel


@value_object
class TimeSeriesFluidComposition:
    water: TimeSeriesExpression
    nitrogen: TimeSeriesExpression
    CO2: TimeSeriesExpression
    methane: TimeSeriesExpression
    ethane: TimeSeriesExpression
    propane: TimeSeriesExpression
    i_butane: TimeSeriesExpression
    n_butane: TimeSeriesExpression
    i_pentane: TimeSeriesExpression
    n_pentane: TimeSeriesExpression
    n_hexane: TimeSeriesExpression

    def get_value(self, period: Period) -> FluidComposition:
        """Evaluate all component expressions and materialize the fluid composition for the given period."""
        try:
            index = self.methane.get_periods().index(period)
        except ValueError as error:
            raise ProgrammingError(f"Period {period} is not available for the fluid composition.") from error

        return FluidComposition(
            water=self.water.get_masked_values()[index],
            nitrogen=self.nitrogen.get_masked_values()[index],
            CO2=self.CO2.get_masked_values()[index],
            methane=self.methane.get_masked_values()[index],
            ethane=self.ethane.get_masked_values()[index],
            propane=self.propane.get_masked_values()[index],
            i_butane=self.i_butane.get_masked_values()[index],
            n_butane=self.n_butane.get_masked_values()[index],
            i_pentane=self.i_pentane.get_masked_values()[index],
            n_pentane=self.n_pentane.get_masked_values()[index],
            n_hexane=self.n_hexane.get_masked_values()[index],
        )

    def get_periods(self) -> list[Period]:
        return self.methane.get_periods()


@value_object
class TimeSeriesFluidModel:
    eos_model: EoSModel
    composition: TimeSeriesFluidComposition

    def get_value(self, period: Period) -> FluidModel:
        """Materialize a fluid model with the composition evaluated for the given period."""
        return FluidModel(
            eos_model=self.eos_model,
            composition=self.composition.get_value(period),
        )

    def get_periods(self) -> list[Period]:
        return self.composition.get_periods()
