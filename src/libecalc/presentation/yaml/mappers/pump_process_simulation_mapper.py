from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.common.errors.exceptions import InvalidResourceException
from libecalc.common.time_utils import Period
from libecalc.common.variables import ExpressionEvaluator
from libecalc.domain.process.value_objects.chart.chart import ChartData
from libecalc.domain.regularity import Regularity
from libecalc.domain.resource import Resources
from libecalc.presentation.yaml.domain.expression_time_series_flow_rate import ExpressionTimeSeriesFlowRate
from libecalc.presentation.yaml.domain.expression_time_series_fluid_density import ExpressionTimeSeriesFluidDensity
from libecalc.presentation.yaml.domain.expression_time_series_pressure import ExpressionTimeSeriesPressure
from libecalc.presentation.yaml.domain.reference_service import ReferenceService
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression
from libecalc.presentation.yaml.mappers.charts.user_defined_chart_data import UserDefinedChartData
from libecalc.presentation.yaml.yaml_types.facility_model.yaml_facility_model import (
    YamlPumpChartSingleSpeed,
)
from libecalc.presentation.yaml.yaml_types.process.yaml_process_simulation import YamlPumpProcessSimulation
from libecalc.process.pump.liquid_stream import LiquidStream
from libecalc.process.pump.pump import Pump
from libecalc.process.pump.pump_process_simulation import (
    PumpOperatingInput,
    PumpProcessSimulation,
)


class PumpProcessSimulationMapper:
    def __init__(
        self,
        expression_evaluator: ExpressionEvaluator,
        reference_service: ReferenceService,
        resources: Resources,
        process_simulation_period: Period,
    ):
        self._expression_evaluator = expression_evaluator.get_subset_for_period(process_simulation_period)
        self._reference_service = reference_service
        self._resources = resources

    def map(
        self,
        yaml_process_simulation: YamlPumpProcessSimulation,
    ) -> tuple[PumpProcessSimulation, list[PumpOperatingInput], list[Period]]:
        chart_data = self._get_chart_data(yaml_process_simulation.pump_model.chart)
        pump = Pump(
            pump_chart=chart_data,
            minimum_flow_rate_m3_per_hour=yaml_process_simulation.pump_model.minimum_flow_rate,
        )
        simulation = PumpProcessSimulation(
            pump=pump,
            name=yaml_process_simulation.name,
        )

        regularity = Regularity(
            expression_evaluator=self._expression_evaluator,
            target_period=self._expression_evaluator.get_period(),
        )
        rate = ExpressionTimeSeriesFlowRate(
            time_series_expression=TimeSeriesExpression(
                expression_evaluator=self._expression_evaluator,
                expression=yaml_process_simulation.inlet.rate,
            ),
            regularity=regularity,
        )
        rate_values = rate.get_stream_day_values()
        suction_pressure = ExpressionTimeSeriesPressure(
            time_series_expression=TimeSeriesExpression(
                expression_evaluator=self._expression_evaluator,
                expression=yaml_process_simulation.inlet.pressure,
            ),
        )
        discharge_pressure = ExpressionTimeSeriesPressure(
            time_series_expression=TimeSeriesExpression(
                expression_evaluator=self._expression_evaluator,
                expression=yaml_process_simulation.required_discharge_pressure,
            ),
        )
        density = ExpressionTimeSeriesFluidDensity(
            time_series_expression=TimeSeriesExpression(
                expression_evaluator=self._expression_evaluator,
                expression=yaml_process_simulation.inlet.density,
            )
        )

        suction_values = suction_pressure.get_values()
        discharge_values = discharge_pressure.get_values()
        density_values = density.get_values()

        # The domain is time-agnostic: build one physical input per period and keep the period
        # vector here in the presentation layer, paired with the inputs (and the results) by index.
        periods = list(rate.get_periods())
        operating_inputs = [
            self._to_operating_input(
                rate_value=rate_value,
                suction_pressure_bara=suction,
                required_discharge_pressure_bara=discharge,
                density_kg_per_m3=density_value,
            )
            for rate_value, suction, discharge, density_value in zip(
                rate_values,
                suction_values,
                discharge_values,
                density_values,
                strict=True,
            )
        ]
        if len(periods) != len(operating_inputs):
            raise ValueError("Pump period vector and input vector length mismatch.")
        return simulation, operating_inputs, periods

    def _to_operating_input(
        self,
        rate_value: float,
        suction_pressure_bara: float,
        required_discharge_pressure_bara: float,
        density_kg_per_m3: float,
    ) -> PumpOperatingInput:
        # Suction pressure and density describe the physical inlet fluid; they must be positive
        # whether or not the pump runs.
        self._require_positive(suction_pressure_bara, "suction pressure [bara]")
        self._require_positive(density_kg_per_m3, "inlet density [kg/m3]")
        inlet_stream = LiquidStream.from_volumetric_rate(
            volumetric_rate_m3_per_day=rate_value,
            pressure_bara=suction_pressure_bara,
            density_kg_per_m3=density_kg_per_m3,
        )

        if rate_value > 0:
            self._require_positive(required_discharge_pressure_bara, "required discharge pressure [bara]")
            discharge = required_discharge_pressure_bara
        else:
            # Pump off (zero rate): the required discharge is a meaningless duty target. Keep the
            # user's value when it is a valid absolute pressure, otherwise fall back to the inlet
            # pressure (the pump delivers no head, so the outlet equals the inlet).
            discharge = (
                required_discharge_pressure_bara if required_discharge_pressure_bara > 0 else suction_pressure_bara
            )

        return PumpOperatingInput(
            inlet_stream=inlet_stream,
            required_discharge_pressure_bara=discharge,
        )

    @staticmethod
    def _require_positive(value: float, subject: str) -> None:
        if value <= 0:
            raise EcalcValidationException(f"Pump {subject} must be greater than 0; got {value}.")

    def _get_chart_data(self, reference: str) -> ChartData:
        model = self._reference_service.get_pump_model(reference)
        if model.head_margin != 0.0:
            raise EcalcValidationException(
                "HEAD_MARGIN is not supported by the new pump process domain "
                "(points above the maximum head are flagged infeasible instead of snapped to it)."
            )
        resource = self._resources.get(model.file)
        if resource is None:
            raise EcalcValidationException(f"Pump chart resource '{model.file}' was not found.")
        try:
            return UserDefinedChartData.from_resource(
                resource,
                units=model.units,
                is_single_speed=isinstance(model, YamlPumpChartSingleSpeed),
            )
        except InvalidResourceException as error:
            raise EcalcValidationException(str(error)) from error
