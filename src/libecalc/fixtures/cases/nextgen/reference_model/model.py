from pathlib import Path

from libecalc.common.utils.rates import RateType
from libecalc.ecalc_model.timeline_event import TimelineEventType
from libecalc.expression import Expression
from libecalc.presentation.yaml.yaml_types.components.yaml_asset import YamlAsset
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import YamlExpressionType
from libecalc.presentation.yaml.yaml_types.energy.yaml_energy_network import (
    YamlEnergySourceType,
    YamlGeneratorEventChangeType,
    YamlGeneratorModelEvent,
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
    YamlPipelineEvent,
    YamlProcessPipeline,
)
from libecalc.presentation.yaml.yaml_types.process.yaml_process_simulation import YamlProcessConstraint
from libecalc.presentation.yaml.yaml_types.process.yaml_stream_distribution import YamlCommonStreamSetting
from libecalc.presentation.yaml.yaml_types.streams.yaml_inlet_stream import YamlStreamRateUnit
from libecalc.presentation.yaml.yaml_types.time_series.yaml_time_series import YamlTimeSeriesCollection
from libecalc.presentation.yaml.yaml_types.yaml_compressor import YamlCompressor
from libecalc.presentation.yaml.yaml_types.yaml_shaft import YamlShaft
from libecalc.presentation.yaml.yaml_types.yaml_variable import YamlSingleVariable, YamlVariables
from libecalc.process.process_solver.anti_surge.anti_surge_strategy import AntiSurgeType
from libecalc.testing.energy_builders import (
    YamlCompressorSampledBuilder,
    YamlDriveTrainBuilder,
    YamlElectricalCableBuilder,
    YamlElectricalConsumerBuilder,
    YamlElectricalMotorBuilder,
    YamlEnergyGeneratorBuilder,
    YamlEnergyNetworkBuilder,
    YamlEnergySourceBuilder,
    YamlFileBuilder,
    YamlGasTurbineBuilder,
    YamlGeneratorCurveBuilder,
    YamlGeneratorDefinitionBuilder,
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
TIE_IN_EVENT = "increased_gas_rate_2027"
GENERATOR_UPGRADE_EVENT = "generator_upgrade_2030"

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
            TIE_IN_EVENT,
            YamlTimelineEventBuilder()
            .with_title("Tie-in of new wells")
            .with_type(TimelineEventType.TIE_IN)
            .with_from_when("2025-01-01")
            .with_description("New production wells are tied in to the platform.")
            .validate(),
        )
        .with_event(
            GENERATOR_UPGRADE_EVENT,
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
    sampled_compressors = [
        YamlCompressor(name=name)
        for name in ("sampled_el_compressor", "sampled_fuel_compressor", "sampled_mech_compressor", "sampled_turbine")
    ]
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


def _definitions():
    return (
        YamlDefinitionsBuilder()
        .with_fluid(FLUID_NAME, YamlPredefinedFluidDefinitionBuilder().with_test_data().validate())
        .with_compressor_model(COMPRESSOR_MODEL_A, _compressor_model())
        .with_compressor_model(COMPRESSOR_MODEL_B, _compressor_model())
        .validate()
    )


def _rebundle_events(train_number: int) -> list[YamlPipelineEvent]:
    return [
        YamlPipelineEvent(
            type=PipelineEventAction.CHANGE,
            change_type=PipelineEventChangeType.REBUNDLE,
            change_target=_compressor_name(train_number, number),
            change_to=COMPRESSOR_MODEL_B,
            ref=TIE_IN_EVENT,
        )
        for number in _compressor_numbers()
    ]


def _export_train(train_number: int, events: list[YamlPipelineEvent] | None = None) -> YamlProcessPipeline:
    builder = YamlProcessPipelineBuilder().with_name(_train_name(train_number))
    for number in _compressor_numbers():
        builder = (
            builder.with_item(YamlPressureDropperBuilder().with_pressure_drop(0).validate())
            .with_item(YamlTemperatureSetterBuilder().with_temperature(30).validate())
            .with_item(YamlLiquidRemoverBuilder().validate())
            .with_compressor_item(compressor=_compressor_name(train_number, number), model=COMPRESSOR_MODEL_A)
        )
    if events:
        builder = builder.with_events(events)
    return builder.validate()


def _process_pipelines() -> dict[str, YamlProcessPipeline]:
    pipelines = [
        _export_train(train_number, events=_rebundle_events(train_number) if train_number == 1 else None)
        for train_number in _train_numbers()
    ]
    return {pipeline.name: pipeline for pipeline in pipelines}


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


def _energy_sources():
    fuel_gas_sources = [
        YamlEnergySourceBuilder().with_name(name).with_type(YamlEnergySourceType.FUEL_GAS_SOURCE).validate()
        for name in ("fuel_gas", "fuel_gas2", "fuel_gas3", "fuel_gas4", "fuel_gas5")
    ]
    electrical_sources = [
        YamlEnergySourceBuilder().with_name(name).with_type(YamlEnergySourceType.ELECTRICAL_SOURCE).validate()
        for name in ("el_source", "pfs")
    ]
    return fuel_gas_sources + electrical_sources


def _sampled_compressor(name: str, input: str, compressor: str, file: str):
    return (
        YamlCompressorSampledBuilder()
        .with_name(name)
        .with_input(input)
        .with_compressor(compressor)
        .with_file(file)
        .with_rate(f"$var.{SAMPLED_COMPRESSOR_RATE}")
        .with_suction_pressure(20)
        .with_discharge_pressure(120)
        .validate()
    )


def _gas_turbine(name: str, input: str):
    return (
        YamlGasTurbineBuilder()
        .with_name(name)
        .with_input(input)
        .with_model(YamlTurbineDefinitionBuilder().with_test_data().validate())
        .validate()
    )


def _electrical_motor(name: str, input: str):
    return (
        YamlElectricalMotorBuilder().with_name(name).with_input(input).with_efficiency(0.95).with_capacity(5).validate()
    )


def _drive_train(name: str, input: str, shaft: str):
    return YamlDriveTrainBuilder().with_name(name).with_input(input).with_shaft(shaft).validate()


def _generator_upgrade_events() -> list[YamlGeneratorModelEvent]:
    upgraded_curve = (
        YamlGeneratorCurveBuilder().with_power([0.0, 5.0, 10.0, 15.0]).with_fuel([0.0, 23000.0, 44000.0, 64000.0])
    )
    return [
        YamlGeneratorModelEvent(
            change_type=YamlGeneratorEventChangeType.REBUNDLE,
            change_to=YamlGeneratorDefinitionBuilder().with_curve(upgraded_curve.validate()).validate(),
            ref=GENERATOR_UPGRADE_EVENT,
        )
    ]


def _energy_units():
    return [
        _gas_turbine("export_turbine", "fuel_gas"),
        YamlEnergyGeneratorBuilder()
        .with_name("genset_a")
        .with_input("fuel_gas2")
        .with_model(YamlGeneratorDefinitionBuilder().with_test_data().validate())
        .with_events(_generator_upgrade_events())
        .validate(),
        YamlElectricalCableBuilder()
        .with_name("long_cable")
        .with_input("genset_a")
        .with_capacity(20)
        .with_efficiency(0.98)
        .validate(),
        _electrical_motor("export_motor", "long_cable"),
        _drive_train("export_train_1_drive", "export_turbine", _shaft_name(1)),
        _drive_train("export_train_2_el", "export_motor", _shaft_name(2)),
        _electrical_motor("pfs_motor", "pfs"),
        _drive_train("pfs_train", "pfs_motor", _shaft_name(3)),
        YamlElectricalConsumerBuilder().with_name("base_load").with_input("el_source").with_load(5).validate(),
        _sampled_compressor("el_compressor_sampled", "genset_a", "sampled_el_compressor", "sampled_el_compressor.csv"),
        _sampled_compressor(
            "fuel_compressor_sampled", "fuel_gas3", "sampled_fuel_compressor", "sampled_fuel_compressor.csv"
        ),
        _gas_turbine("sampled_turbine", "fuel_gas4"),
        _sampled_compressor(
            "mech_compressor_sampled", "sampled_turbine", "sampled_mech_compressor", "sampled_mech_compressor.csv"
        ),
        _sampled_compressor("turbine_compressor_sampled", "fuel_gas5", "sampled_turbine", "sampled_fuel_turbine.csv"),
    ]


def _energy_network():
    return YamlEnergyNetworkBuilder().with_sources(_energy_sources()).with_units(_energy_units()).validate()


def build_reference_model() -> YamlAsset:
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
        .with_energy_network(_energy_network())
        .validate()
    )
