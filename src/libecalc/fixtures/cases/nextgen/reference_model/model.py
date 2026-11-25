from pathlib import Path

from libecalc.common.utils.rates import RateType
from libecalc.ecalc_model.timeline_event import TimelineEventType
from libecalc.expression import Expression
from libecalc.presentation.yaml.yaml_types.components.yaml_asset import YamlNextgenAsset
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import YamlExpressionType
from libecalc.presentation.yaml.yaml_types.energy.yaml_energy_network import (
    YamlCombustionEngineModelChange,
    YamlDispatchStrategy,
    YamlEnergySource,
    YamlEnergyUnitChangeType,
    YamlGeneratorModelChange,
    YamlJunctionInput,
    YamlTurbineDefinition,
)
from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_chart import (
    YamlEfficiencyUnits,
    YamlHeadUnits,
    YamlRateUnits,
    YamlUnits,
)
from libecalc.presentation.yaml.yaml_types.process.yaml_process_pipeline import (
    PipelineEventAction,
    PipelineEventChangeType,
    YamlPipelineChange,
    YamlProcessPipeline,
)
from libecalc.presentation.yaml.yaml_types.process.yaml_process_simulation import YamlProcessConstraint
from libecalc.presentation.yaml.yaml_types.process.yaml_stream_distribution import YamlCommonStreamSetting
from libecalc.presentation.yaml.yaml_types.pump.yaml_liquid_stream import YamlLiquidStreamRateUnit
from libecalc.presentation.yaml.yaml_types.pump.yaml_pump_pipeline import YamlPumpPipeline
from libecalc.presentation.yaml.yaml_types.pump.yaml_pump_simulation import YamlPumpPressureControl
from libecalc.presentation.yaml.yaml_types.streams.yaml_inlet_stream import YamlStreamRateUnit
from libecalc.presentation.yaml.yaml_types.time_series.yaml_time_series import YamlTimeSeriesCollection
from libecalc.presentation.yaml.yaml_types.yaml_compressor import YamlCompressor
from libecalc.presentation.yaml.yaml_types.yaml_pump import YamlPump
from libecalc.presentation.yaml.yaml_types.yaml_shaft import YamlShaft
from libecalc.presentation.yaml.yaml_types.yaml_variable import YamlSingleVariable, YamlVariables
from libecalc.process.process_solver.anti_surge.anti_surge_strategy import AntiSurgeType
from libecalc.testing.energy_builders import (
    YamlCombustionEngineModelChangeBuilder,
    YamlCompressorSampledBuilder,
    YamlDieselConsumerBuilder,
    YamlDieselEngineBuilder,
    YamlDieselSourceBuilder,
    YamlDriveTrainBuilder,
    YamlElectricalBusBuilder,
    YamlElectricalCableBuilder,
    YamlElectricalConsumerBuilder,
    YamlElectricalMotorBuilder,
    YamlElectricalSourceBuilder,
    YamlEnergyGeneratorSetBuilder,
    YamlEnergyNetworkBuilder,
    YamlFileBuilder,
    YamlFuelGasConsumerBuilder,
    YamlFuelGasSourceBuilder,
    YamlGasTurbineBuilder,
    YamlGeneratorCurveBuilder,
    YamlGeneratorDefinitionBuilder,
    YamlGeneratorModelChangeBuilder,
    YamlGeneratorSetEngineDefinitionBuilder,
    YamlMechanicalConsumerBuilder,
    YamlTurbineCurveBuilder,
    YamlTurbineDefinitionBuilder,
)
from libecalc.testing.process_builders import (
    YamlCommonStreamDistributionBuilder,
    YamlCompressorChartBuilder,
    YamlCompressorModelChartBuilder,
    YamlDefinitionsBuilder,
    YamlInletStreamBuilder,
    YamlInletStreamRateBuilder,
    YamlLiquidRemoverBuilder,
    YamlPredefinedFluidDefinitionBuilder,
    YamlPressureDropperBuilder,
    YamlProcessPipelineBuilder,
    YamlProcessSimulationBuilder,
    YamlTemperatureSetterBuilder,
    YamlTimelineBuilder,
    YamlTimelineEventBuilder,
)
from libecalc.testing.pump_builders import (
    YamlLiquidInletStreamBuilder,
    YamlLiquidStreamRateBuilder,
    YamlPumpBuilder,
    YamlPumpChartBuilder,
    YamlPumpCommonStreamDistributionBuilder,
    YamlPumpConstraintBuilder,
    YamlPumpModelBuilder,
    YamlPumpPipelineBuilder,
    YamlPumpSimulationBuilder,
)
from libecalc.testing.yaml_builder import YamlAssetBuilder, YamlTimeSeriesBuilder

RESOURCE_DIRECTORY = Path(__file__).parent / "data"

START = "2020-01-01"
END = "2052-01-01"

NUMBER_OF_EXPORT_TRAINS = 4
COMPRESSORS_PER_EXPORT_TRAIN = 2

FLUID_NAME = "medium_fluid2"
COMPRESSOR_MODEL_A = "compressor_model_A"
COMPRESSOR_MODEL_B = "compressor_model_B"
COMPRESSOR_CHART_FILE = "compressor_chart.csv"
NEW_WELLS_TIE_IN_EVENT = "new_wells_tie_in"
GENSET_A_UPGRADE_EVENT = "genset_a_upgrade"
EXPORT_TURBINE_UPGRADE_EVENT = "export_turbine_upgrade"

TURBINE_PERFORMANCE_CURVE = "turbine_performance_curve"
UPGRADED_TURBINE_PERFORMANCE_CURVE = "upgraded_turbine_performance_curve"
GENERATOR_PERFORMANCE_CURVE = "generator_performance_curve"
MAIN_BUS = "main_bus"

PUMP_MODEL = "injection_pump_model"
PUMP_NAMES = ["injection_pump_1", "injection_pump_2"]
PUMP_ALIASES = ["Injection pump 1", None]
PUMP_PIPELINE_NAMES = ["injection_line_1", "injection_line_2"]

EXPORT_TRAIN_ALIASES = [
    ["aliasA", "aliasB"],
    ["aliasC", "aliasD"],
    ["alias3", "aliasF"],
    ["aliasG", "aliasH"],
]

SAMPLED_COMPRESSOR_RATE = "sampled_compressor_rate"


def _train_name(train_number: int) -> str:
    return f"export_train_{train_number}"


def _shaft_name(train_number: int) -> str:
    return f"export_shaft_{train_number}"


def _compressor_name(train_number: int, compressor_number: int) -> str:
    return f"{_train_name(train_number)}_compressor{compressor_number}"


def _train_numbers() -> range:
    return range(1, NUMBER_OF_EXPORT_TRAINS + 1)


def _compressor_numbers() -> range:
    return range(1, COMPRESSORS_PER_EXPORT_TRAIN + 1)


def _time_series() -> list[YamlTimeSeriesCollection]:
    return [
        YamlTimeSeriesBuilder().with_name("SIM").with_type("DEFAULT").with_file("base_profile.csv").validate(),
    ]


def _variables() -> YamlVariables:
    expressions = {
        "hydrocarbon_export_sm3_per_day": "SIM;OIL_PROD {+} SIM;GAS_PROD {/} 1000",
        "gas_export_rate_sm3_per_day": "SIM;GAS_PROD",
        "water_injection_rate": "SIM;WATER_INJ",
        "gas_export_condition": "SIM;GAS_PROD > 0",
        "peb": "0.95",
        "gasrateb_cd": "$var.gas_export_rate_sm3_per_day {*} $var.peb",
        SAMPLED_COMPRESSOR_RATE: "1200000",
        "hcexpb_cd": "$var.hydrocarbon_export_sm3_per_day {*} $var.peb",
    }
    return {
        name: YamlSingleVariable(value=Expression.validator(expression)) for name, expression in expressions.items()
    }


def _timeline():
    return (
        YamlTimelineBuilder()
        .with_event(
            NEW_WELLS_TIE_IN_EVENT,
            YamlTimelineEventBuilder()
            .with_title("Tie-in of new wells")
            .with_type(TimelineEventType.TIE_IN)
            .with_from_when("2025-01-01")
            .with_description("New production wells are tied in to the platform.")
            .validate(),
        )
        .with_event(
            EXPORT_TURBINE_UPGRADE_EVENT,
            YamlTimelineEventBuilder()
            .with_title("Turbine upgrade")
            .with_type(TimelineEventType.ENERGY_EFFICIENCY_MEASURE)
            .with_from_when("2028-01-01")
            .with_description("Gas turbine export_turbine gets a new turbine model.")
            .validate(),
        )
        .with_event(
            GENSET_A_UPGRADE_EVENT,
            YamlTimelineEventBuilder()
            .with_title("Generator upgrade")
            .with_type(TimelineEventType.ENERGY_EFFICIENCY_MEASURE)
            .with_from_when("2030-01-01")
            .with_description("Generator set genset_a gets a new generator model.")
            .validate(),
        )
        .validate()
    )


def _shafts() -> list[YamlShaft]:
    return [
        YamlShaft(
            name=_shaft_name(train_number),
            compressors=[_compressor_name(train_number, number) for number in _compressor_numbers()],
        )
        for train_number in _train_numbers()
    ]


def _compressors() -> list[YamlCompressor]:
    export_compressors = [
        YamlCompressor(
            name=_compressor_name(train_number, number), alias=EXPORT_TRAIN_ALIASES[train_number - 1][number - 1]
        )
        for train_number in _train_numbers()
        for number in _compressor_numbers()
    ]
    sampled_compressors = [YamlCompressor(name=name) for name in ("sampled_el_compressor", "sampled_mech_compressor")]
    return export_compressors + sampled_compressors


def _compressor_model():
    chart = (
        YamlCompressorChartBuilder()
        .with_curves(YamlFileBuilder().with_file(COMPRESSOR_CHART_FILE).validate())
        .with_units(
            YamlUnits(
                rate=YamlRateUnits.AM3_PER_HOUR,
                head=YamlHeadUnits.M,
                efficiency=YamlEfficiencyUnits.FRACTION,
            )
        )
        .validate()
    )
    return YamlCompressorModelChartBuilder().with_chart(chart).with_control_margin(0.0).validate()


def _pump_model():
    chart = YamlPumpChartBuilder().with_test_data().validate()
    return YamlPumpModelBuilder().with_chart(chart).with_minimum_flow_rate(300).validate()


def _pumps() -> list[YamlPump]:
    return [
        YamlPumpBuilder().with_name(name).with_alias(alias).validate() for name, alias in zip(PUMP_NAMES, PUMP_ALIASES)
    ]


def _pump_pipelines() -> list[YamlPumpPipeline]:
    first_line = YamlPumpPipelineBuilder().with_name(PUMP_PIPELINE_NAMES[0]).with_pump_item(PUMP_NAMES[0], PUMP_MODEL)
    second_line = (
        YamlPumpPipelineBuilder()
        .with_name(PUMP_PIPELINE_NAMES[1])
        .with_pressure_dropper_item(4)
        .with_pump_item(PUMP_NAMES[1], PUMP_MODEL)
    )
    return [first_line.validate(), second_line.validate()]


def _pump_simulation():
    inlet_stream = (
        YamlLiquidInletStreamBuilder()
        .with_name("injection_header")
        .with_pressure(10.0)
        .with_density(1022.0)
        .with_rate(
            YamlLiquidStreamRateBuilder()
            .with_value("$var.water_injection_rate")
            .with_unit(YamlLiquidStreamRateUnit.M3_PER_DAY)
            .with_type(RateType.STREAM_DAY)
            .validate()
        )
        .validate()
    )
    stream_distribution = (
        YamlPumpCommonStreamDistributionBuilder()
        .with_inlet_stream(inlet_stream)
        .with_rate_fractions([[1.0, 0.0], [0.5, 0.5]])
        .validate()
    )
    return (
        YamlPumpSimulationBuilder()
        .with_name("water_injection_simulation")
        .with_target(PUMP_PIPELINE_NAMES[0])
        .with_target(PUMP_PIPELINE_NAMES[1])
        .with_stream_distribution(stream_distribution)
        .with_constraint(
            PUMP_PIPELINE_NAMES[0],
            [YamlPumpConstraintBuilder().with_outlet_pressure(240).validate()],
        )
        .with_constraint(
            PUMP_PIPELINE_NAMES[1],
            [
                YamlPumpConstraintBuilder()
                .with_outlet_pressure(190)
                .with_pressure_control(YamlPumpPressureControl.DOWNSTREAM_CHOKE)
                .validate()
            ],
        )
        .validate()
    )


def _definitions():
    return (
        YamlDefinitionsBuilder()
        .with_fluid(FLUID_NAME, YamlPredefinedFluidDefinitionBuilder().with_test_data().validate())
        .with_compressor_model(COMPRESSOR_MODEL_A, _compressor_model())
        .with_compressor_model(COMPRESSOR_MODEL_B, _compressor_model())
        .with_pump_model(PUMP_MODEL, _pump_model())
        .with_performance_curve(TURBINE_PERFORMANCE_CURVE, YamlTurbineDefinitionBuilder().with_test_data().validate())
        .with_performance_curve(
            UPGRADED_TURBINE_PERFORMANCE_CURVE,
            YamlTurbineDefinitionBuilder()
            .with_curve(
                YamlTurbineCurveBuilder()
                .with_load([2.352, 4.589, 6.853])
                .with_efficiency([0.142, 0.216, 0.263])
                .validate()
            )
            .validate(),
        )
        .with_performance_curve(
            GENERATOR_PERFORMANCE_CURVE, YamlGeneratorDefinitionBuilder().with_test_data().validate()
        )
        .validate()
    )


def _export_train_changes(train_number: int) -> list[YamlPipelineChange]:
    return [
        YamlPipelineChange(
            type=PipelineEventAction.CHANGE,
            change_type=PipelineEventChangeType.REBUNDLE,
            change_target=_compressor_name(train_number, number),
            change_to=COMPRESSOR_MODEL_B,
            ref=NEW_WELLS_TIE_IN_EVENT,
        )
        for number in _compressor_numbers()
    ]


def _export_train(train_number: int, changes: list[YamlPipelineChange] | None = None) -> YamlProcessPipeline:
    builder = YamlProcessPipelineBuilder().with_name(_train_name(train_number))
    for number in _compressor_numbers():
        builder = (
            builder.with_item(YamlPressureDropperBuilder().with_pressure_drop(0).validate())
            .with_item(YamlTemperatureSetterBuilder().with_temperature(30).validate())
            .with_item(YamlLiquidRemoverBuilder().validate())
            .with_compressor_item(compressor=_compressor_name(train_number, number), model=COMPRESSOR_MODEL_A)
        )
    if changes:
        builder = builder.with_changes(changes)
    return builder.validate()


def _process_pipelines() -> list[YamlProcessPipeline]:
    return [
        _export_train(train_number, changes=_export_train_changes(train_number) if train_number == 1 else None)
        for train_number in _train_numbers()
    ]


def _process_simulation():
    inlet_stream = (
        YamlInletStreamBuilder()
        .with_name("main_inlet")
        .with_fluid(FLUID_NAME)
        .with_temperature(288.15)
        .with_pressure(20.0)
        .with_rate(
            YamlInletStreamRateBuilder()
            .with_value("$var.gasrateb_cd")
            .with_unit(YamlStreamRateUnit.SM3_PER_DAY)
            .with_type(RateType.STREAM_DAY)
            .with_condition(1)
            .validate()
        )
        .validate()
    )
    rate_fractions: list[list[YamlExpressionType]] = [
        [1.0, 0.0, 0.0, 0.0],
        [0.5, 0.5, 0.0, 0.0],
        [0.33, 0.33, 0.34, 0.0],
        [0.25, 0.25, 0.25, 0.25],
    ]
    stream_distribution = (
        YamlCommonStreamDistributionBuilder()
        .with_inlet_stream(inlet_stream)
        .with_settings([YamlCommonStreamSetting(rate_fractions=fractions) for fractions in rate_fractions])
        .validate()
    )

    builder = YamlProcessSimulationBuilder().with_name("main_export_simulation")
    for train_number in _train_numbers():
        builder = builder.with_target(_train_name(train_number)).with_constraint(
            _train_name(train_number),
            [
                YamlProcessConstraint(
                    outlet_pressure=200.0,
                    pressure_control="DOWNSTREAM_CHOKE",
                    anti_surge=AntiSurgeType.INDIVIDUAL_ASV,
                )
            ],
        )
    return builder.with_stream_distribution(stream_distribution).validate()


def _energy_sources() -> list[YamlEnergySource]:
    lower_heating_value_by_source = {"fuel_gas": 38.0, "fuel_gas3": 38.0, "fuel_gas6": 38.0}

    def _fuel_gas_source(name: str):
        builder = YamlFuelGasSourceBuilder().with_name(name)
        lower_heating_value = lower_heating_value_by_source.get(name)
        if lower_heating_value is not None:
            builder = builder.with_lower_heating_value(lower_heating_value)
        return builder.validate()

    fuel_gas_sources: list[YamlEnergySource] = [
        _fuel_gas_source(name) for name in ("fuel_gas", "fuel_gas2", "fuel_gas3", "fuel_gas6")
    ]
    electrical_sources: list[YamlEnergySource] = [
        YamlElectricalSourceBuilder().with_name("pfs").with_capacity(12).validate()
    ]
    diesel_sources: list[YamlEnergySource] = [
        YamlDieselSourceBuilder().with_name("diesel").with_lower_heating_value(35.7).validate()
    ]
    return fuel_gas_sources + electrical_sources + diesel_sources


def _sampled_compressor(
    input: str,
    compressor: str,
    file: str,
    suction_pressure: float | None = None,
    discharge_pressure: float | None = None,
):
    builder = (
        YamlCompressorSampledBuilder()
        .with_input(input)
        .with_compressor(compressor)
        .with_file(file)
        .with_rate(f"$var.{SAMPLED_COMPRESSOR_RATE}")
    )
    if suction_pressure is not None:
        builder = builder.with_suction_pressure(suction_pressure)
    if discharge_pressure is not None:
        builder = builder.with_discharge_pressure(discharge_pressure)
    return builder.validate()


def _gas_turbine(name: str, input: str, changes: list[YamlCombustionEngineModelChange] | None = None):
    return (
        YamlGasTurbineBuilder()
        .with_name(name)
        .with_input(input)
        .with_model(TURBINE_PERFORMANCE_CURVE)
        .with_changes(changes or [])
        .validate()
    )


def _electrical_motor(name: str, input: str):
    return (
        YamlElectricalMotorBuilder().with_name(name).with_input(input).with_efficiency(0.95).with_capacity(5).validate()
    )


def _diesel_engine(name: str, input: str, model: str | YamlTurbineDefinition):
    return YamlDieselEngineBuilder().with_name(name).with_input(input).with_model(model).validate()


def _drive_train(input: str, shaft: str, mechanical_efficiencies: dict[str, float] | None = None):
    builder = YamlDriveTrainBuilder().with_input(input).with_shaft(shaft)
    for compressor, efficiency in (mechanical_efficiencies or {}).items():
        builder = builder.with_mechanical_efficiency(compressor, efficiency)
    return builder.validate()


def _genset_a_changes() -> list[YamlGeneratorModelChange]:
    return [YamlGeneratorModelChangeBuilder().with_test_data().with_ref(GENSET_A_UPGRADE_EVENT).validate()]


def _export_turbine_changes() -> list[YamlCombustionEngineModelChange]:
    return [
        YamlCombustionEngineModelChangeBuilder()
        .with_change_to(UPGRADED_TURBINE_PERFORMANCE_CURVE)
        .with_change_type(YamlEnergyUnitChangeType.REBUNDLE)
        .with_ref(EXPORT_TURBINE_UPGRADE_EVENT)
        .validate()
    ]


def _energy_units():
    return [
        _gas_turbine("export_turbine", "fuel_gas", changes=_export_turbine_changes()),
        _gas_turbine("export_turbine_2", "fuel_gas"),
        YamlEnergyGeneratorSetBuilder()
        .with_name("genset_a")
        .with_input("fuel_gas2")
        .with_model(GENERATOR_PERFORMANCE_CURVE)
        .with_changes(_genset_a_changes())
        .validate(),
        YamlEnergyGeneratorSetBuilder()
        .with_name("essential_generator")
        .with_input("diesel")
        .with_model(
            YamlGeneratorDefinitionBuilder()
            .with_curve(
                YamlGeneratorCurveBuilder()
                .with_power([0.0, 1.0, 3.0, 5.0])
                .with_fuel([0.0, 7000.0, 21000.0, 35000.0])
                .validate()
            )
            .validate()
        )
        .validate(),
        YamlElectricalBusBuilder()
        .with_name(MAIN_BUS)
        .with_input(
            [
                YamlJunctionInput(name="genset_a", capacity=15),
                YamlJunctionInput(name="pfs_cable", capacity=10),
                "essential_generator",
            ]
        )
        .with_dispatch_strategy(YamlDispatchStrategy.PRIORITY)
        .validate(),
        YamlElectricalCableBuilder()
        .with_name("pfs_cable")
        .with_input("pfs")
        .with_capacity(10)
        .with_efficiency(0.98)
        .validate(),
        _electrical_motor("export_motor", MAIN_BUS),
        YamlEnergyGeneratorSetBuilder()
        .with_name("genset_b")
        .with_input("fuel_gas6")
        .with_model(YamlGeneratorSetEngineDefinitionBuilder().with_test_data().validate())
        .validate(),
        YamlElectricalConsumerBuilder().with_name("genset_b_load").with_input("genset_b").with_load(2).validate(),
        _drive_train(
            "export_turbine",
            _shaft_name(1),
            mechanical_efficiencies={_compressor_name(1, 1): 0.97, _compressor_name(1, 2): 0.95},
        ),
        _drive_train(
            "export_turbine_2",
            _shaft_name(2),
            mechanical_efficiencies={_compressor_name(2, 1): 0.96},
        ),
        _drive_train("export_motor", _shaft_name(3)),
        _electrical_motor("export_motor_2", MAIN_BUS),
        _drive_train(
            "export_motor_2",
            _shaft_name(4),
            mechanical_efficiencies={_compressor_name(4, 1): 0.95, _compressor_name(4, 2): 0.93},
        ),
        YamlElectricalConsumerBuilder().with_name("base_load").with_input(MAIN_BUS).with_load(5).validate(),
        YamlElectricalConsumerBuilder()
        .with_name("water_injection_pump")
        .with_input(MAIN_BUS)
        .with_load_curve(
            curve={"variable": [0, 15000, 30000], "power": [0.0, 2.2, 4.5]},
            variable="$var.water_injection_rate",
        )
        .validate(),
        _electrical_motor("sampled_el_motor", MAIN_BUS),
        _sampled_compressor(
            "sampled_el_motor",
            "sampled_el_compressor",
            "sampled_el_compressor.csv",
            suction_pressure=20,
            discharge_pressure=120,
        ),
        _gas_turbine("sampled_turbine", "fuel_gas3"),
        _sampled_compressor("sampled_turbine", "sampled_mech_compressor", "sampled_mech_compressor.csv"),
        YamlFuelGasConsumerBuilder()
        .with_name("flare")
        .with_input("fuel_gas2")
        .with_rate_curve(curve={"file": "flare_rate.csv"}, variable="$var.gasrateb_cd")
        .validate(),
        _diesel_engine(
            "rig_diesel_engine",
            "diesel",
            YamlTurbineDefinitionBuilder()
            .with_curve(
                YamlTurbineCurveBuilder().with_load([0.5, 1.5, 3.0]).with_efficiency([0.28, 0.34, 0.37]).validate()
            )
            .validate(),
        ),
        YamlMechanicalConsumerBuilder()
        .with_name("drilling_equipment")
        .with_input("rig_diesel_engine")
        .with_load(1.5)
        .validate(),
        YamlDieselConsumerBuilder()
        .with_name("firewater_pump")
        .with_input("diesel")
        .with_rate("$var.gas_export_condition {*} 600")
        .validate(),
    ]


def _energy_network():
    return YamlEnergyNetworkBuilder().with_sources(_energy_sources()).with_units(_energy_units()).validate()


def build_reference_model() -> YamlNextgenAsset:
    return (
        YamlAssetBuilder()
        .with_start(START)
        .with_end(END)
        .with_time_series(_time_series())
        .with_variables(_variables())
        .with_timeline(_timeline())
        .with_shafts(_shafts())
        .with_compressors(_compressors())
        .with_definitions(_definitions())
        .with_process_pipelines(_process_pipelines())
        .with_process_simulations([_process_simulation()])
        .with_pumps(_pumps())
        .with_pump_pipelines(_pump_pipelines())
        .with_pump_simulations([_pump_simulation()])
        .with_energy_network(_energy_network())
        .validate()
    )
