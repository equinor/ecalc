from enum import StrEnum
from typing import Annotated, Literal, TypeGuard, Union

from pydantic import (
    AfterValidator,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.common.string.string_utils import get_duplicates
from libecalc.energy.models.curve_interpolator import validate_curve_interpolator
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import YamlExpressionType
from libecalc.presentation.yaml.yaml_types.energy.yaml_generator_set_definition import (
    YamlGeneratorSetEngineDefinition,
    YamlGeneratorSetModel,
)
from libecalc.presentation.yaml.yaml_types.energy.yaml_turbine_definition import YamlTurbineDefinition
from libecalc.presentation.yaml.yaml_types.process.yaml_process_references import (
    DefinitionReference,
    validate_definition_reference_or_inline_model,
)
from libecalc.presentation.yaml.yaml_types.yaml_compressor import CompressorReference
from libecalc.presentation.yaml.yaml_types.yaml_data_or_file import DataOrFile
from libecalc.presentation.yaml.yaml_types.yaml_shaft import ShaftReference
from libecalc.presentation.yaml.yaml_types.yaml_timeline import TimelineEventReference
from libecalc.presentation.yaml.yaml_validators.file_validators import file_exists_validator


def _check_non_negative[T](v: T, field_name: str) -> T:
    if isinstance(v, (int, float)) and v < 0:
        raise ValueError(f"{field_name} must be non-negative, got {v}")
    return v


def _check_efficiency[T: YamlExpressionType | None](v: T) -> T:
    if isinstance(v, (int, float)) and not (0 < v <= 1):
        raise ValueError(f"EFFICIENCY must be in (0, 1], got {v}")
    return v


YamlCapacity = Annotated[
    YamlExpressionType | None,
    Field(title="CAPACITY", description="Maximum output capacity. Omit for unlimited."),
    AfterValidator(lambda v: _check_non_negative(v, "CAPACITY")),
]


class YamlEnergySourceType(StrEnum):
    FUEL_GAS_SOURCE = "FUEL_GAS_SOURCE"
    ELECTRICAL_SOURCE = "ELECTRICAL_SOURCE"
    DIESEL_SOURCE = "DIESEL_SOURCE"


YamlLowerHeatingValue = Annotated[
    float | None,
    Field(
        title="LOWER_HEATING_VALUE",
        description="Lower heating value [MJ/Sm3 for FUEL_GAS_SOURCE, MJ/L for DIESEL_SOURCE] of the fuel, "
        "required for any GAS_TURBINE or DIESEL_ENGINE drawing from this source.",
        gt=0,
        lt=100,
    ),
]


class YamlEnergySourceBase(YamlBase):
    name: Annotated[
        str,
        Field(
            title="NAME",
            description="Unique name for this energy source.",
        ),
    ]


class YamlFuelSourceBase(YamlEnergySourceBase):
    lower_heating_value: YamlLowerHeatingValue = None


class YamlFuelGasSource(YamlFuelSourceBase):
    model_config = ConfigDict(title="FuelGasSource")

    type: Literal[YamlEnergySourceType.FUEL_GAS_SOURCE]


class YamlDieselSource(YamlFuelSourceBase):
    model_config = ConfigDict(title="DieselSource")

    type: Literal[YamlEnergySourceType.DIESEL_SOURCE]


class YamlElectricalSource(YamlEnergySourceBase):
    model_config = ConfigDict(title="ElectricalSource")

    type: Literal[YamlEnergySourceType.ELECTRICAL_SOURCE]
    capacity: YamlCapacity = None


YamlEnergySource = Annotated[
    Union[YamlFuelGasSource, YamlDieselSource, YamlElectricalSource],
    Field(discriminator="type"),
]


class YamlConverterBase(YamlBase):
    name: Annotated[
        str,
        Field(
            title="NAME",
            description="Unique name for this component.",
        ),
    ]
    input: Annotated[
        str,
        Field(
            title="INPUT",
            description="Source or component this receives energy from.",
        ),
    ]


class YamlEnergyUnitChangeType(StrEnum):
    """How the energy unit's model changes at the event. REBUNDLE: same physical unit, new model."""

    REBUNDLE = "REBUNDLE"


YamlModelChangeType = Annotated[
    YamlEnergyUnitChangeType,
    Field(
        title="CHANGE_TYPE",
        description="Nature of the change. REBUNDLE: the unit stays the same unit in the energy network, with a new "
        "model.",
    ),
]

YamlModelChangeReference = Annotated[
    TimelineEventReference,
    Field(
        title="REF",
        description="Reference to an event in TIMELINE.EVENTS. The change takes effect from the event date "
        "(inclusive).",
    ),
]


class YamlGeneratorModelChange(YamlBase):
    """A dated change of the generator set's model. The generator set stays the same unit in the energy network;
    only the model used to convert power to fuel changes."""

    model_config = ConfigDict(
        title="GeneratorModelChange",
        json_schema_extra={
            "examples": [
                {
                    "CHANGE_TO": {
                        "TYPE": "POWER_TO_FUEL",
                        "CURVE": {"POWER": [0, 5, 10, 15], "FUEL": [0, 23000, 44000, 64000]},
                    },
                    "CHANGE_TYPE": "REBUNDLE",
                    "REF": "generator_upgrade",
                },
                {"CHANGE_TO": "upgraded_generator", "CHANGE_TYPE": "REBUNDLE", "REF": "generator_upgrade"},
            ],
        },
    )

    change_to: Annotated[
        YamlGeneratorSetModel,
        Field(
            title="CHANGE_TO",
            description="The generator set model to use from the event date on.",
        ),
    ]
    change_type: YamlModelChangeType = YamlEnergyUnitChangeType.REBUNDLE
    ref: YamlModelChangeReference


class YamlCombustionEngineModelChange(YamlBase):
    """A dated change of a gas turbine's or diesel engine's model. The unit stays the same unit in the energy network;
    only the model used to convert power to fuel changes."""

    model_config = ConfigDict(
        title="CombustionEngineModelChange",
        json_schema_extra={
            "examples": [
                {
                    "CHANGE_TO": {
                        "TYPE": "LOAD_TO_EFFICIENCY",
                        "CURVE": {"LOAD": [2.352, 4.589, 6.853], "EFFICIENCY": [0.142, 0.216, 0.263]},
                    },
                    "CHANGE_TYPE": "REBUNDLE",
                    "REF": "turbine_upgrade",
                },
                {"CHANGE_TO": "upgraded_turbine", "CHANGE_TYPE": "REBUNDLE", "REF": "turbine_upgrade"},
            ],
        },
    )

    change_to: Annotated[
        DefinitionReference | YamlTurbineDefinition,
        validate_definition_reference_or_inline_model(YamlTurbineDefinition),
        Field(
            title="CHANGE_TO",
            description="The model to use from the event date on.",
        ),
    ]
    change_type: YamlModelChangeType = YamlEnergyUnitChangeType.REBUNDLE
    ref: YamlModelChangeReference


class YamlGeneratorSet(YamlConverterBase):
    model_config = ConfigDict(title="GeneratorSet")

    type: Literal["GENERATOR_SET"]
    model: Annotated[
        YamlGeneratorSetModel,
        Field(
            title="MODEL",
            description="Generator set model, given directly as a power-to-fuel curve or a gas turbine/diesel "
            "engine driven model.",
        ),
    ]
    changes: Annotated[
        list[YamlGeneratorModelChange],
        Field(
            title="CHANGES",
            description="Changes to the generator set model over time, such as a rebundle. Each change takes "
            "effect from the date of its referenced TIMELINE.EVENTS entry.",
        ),
    ] = []


class YamlGasTurbine(YamlConverterBase):
    model_config = ConfigDict(title="GasTurbine")

    type: Literal["GAS_TURBINE"]
    model: Annotated[
        DefinitionReference | YamlTurbineDefinition,
        validate_definition_reference_or_inline_model(YamlTurbineDefinition),
        Field(
            title="MODEL",
            description="Turbine model, given directly in place or as a reference to DEFINITIONS.PERFORMANCE_CURVES.",
        ),
    ]
    changes: Annotated[
        list[YamlCombustionEngineModelChange],
        Field(
            title="CHANGES",
            description="Changes to the turbine model over time, such as a rebundle. Each change takes "
            "effect from the date of its referenced TIMELINE.EVENTS entry.",
        ),
    ] = []


class YamlDieselEngine(YamlConverterBase):
    model_config = ConfigDict(title="DieselEngine")

    type: Literal["DIESEL_ENGINE"]
    model: Annotated[
        DefinitionReference | YamlTurbineDefinition,
        validate_definition_reference_or_inline_model(YamlTurbineDefinition),
        Field(
            title="MODEL",
            description="Diesel engine model, given directly in place or as a reference to "
            "DEFINITIONS.PERFORMANCE_CURVES.",
        ),
    ]
    changes: Annotated[
        list[YamlCombustionEngineModelChange],
        Field(
            title="CHANGES",
            description="Changes to the diesel engine model over time, such as a rebundle. Each change takes "
            "effect from the date of its referenced TIMELINE.EVENTS entry.",
        ),
    ] = []


class YamlElectricalMotor(YamlConverterBase):
    model_config = ConfigDict(title="ElectricalMotor")

    capacity: YamlCapacity = None
    type: Literal["ELECTRICAL_MOTOR"]
    efficiency: Annotated[
        YamlExpressionType | None,
        Field(
            title="EFFICIENCY",
            description="Conversion efficiency (0–1]. Defaults to 0.95 if omitted.",
        ),
    ] = None

    @field_validator("efficiency", mode="after")
    @classmethod
    def _efficiency_in_range(cls, v: YamlExpressionType | None) -> YamlExpressionType | None:
        return _check_efficiency(v)


class YamlElectricalCable(YamlConverterBase):
    model_config = ConfigDict(title="ElectricalCable")

    capacity: YamlCapacity = None
    type: Literal["ELECTRICAL_CABLE"]
    efficiency: Annotated[
        YamlExpressionType | None,
        Field(
            title="EFFICIENCY",
            description="Transmission efficiency (0–1]. 1.0 means no loss. Defaults to 1.0 if omitted.",
        ),
    ] = None

    @field_validator("efficiency", mode="after")
    @classmethod
    def _efficiency_in_range(cls, v: YamlExpressionType | None) -> YamlExpressionType | None:
        return _check_efficiency(v)


class YamlDispatchStrategy(StrEnum):
    PRIORITY = "PRIORITY"
    EQUAL_SPLIT = "EQUAL_SPLIT"


class YamlJunctionInput(YamlBase):
    model_config = ConfigDict(title="JunctionInput")

    name: Annotated[
        str,
        Field(
            title="NAME",
            description="Source or unit feeding into this junction.",
        ),
    ]
    capacity: Annotated[
        YamlExpressionType | None,
        Field(
            title="CAPACITY",
            description=(
                "Dispatch limit for this input, measured at the junction after any upstream loss. It guides how "
                "demand is split and does not cap it: demand beyond every limit is placed on the last input, and "
                "exceeding a limit is not itself a capacity failure. Omit for unlimited, until a deliverability "
                "rule exists."
            ),
        ),
    ] = None

    @field_validator("capacity", mode="after")
    @classmethod
    def _capacity_non_negative(cls, v: YamlExpressionType | None) -> YamlExpressionType | None:
        return _check_non_negative(v, "CAPACITY")


class YamlJunctionBase(YamlBase):
    name: Annotated[
        str,
        Field(
            title="NAME",
            description="Unique name for this component.",
        ),
    ]
    input: Annotated[
        list[str | YamlJunctionInput],
        Field(
            title="INPUT",
            description=(
                "At least two sources or units feeding into this junction, in dispatch priority order. An entry is "
                "either a name, or a NAME with an optional CAPACITY dispatch limit. A single supplier connects "
                "directly to its consumers instead."
            ),
            min_length=2,
        ),
    ]
    dispatch_strategy: Annotated[
        YamlDispatchStrategy,
        Field(
            title="DISPATCH_STRATEGY",
            description="How to allocate demand across the inputs.",
        ),
    ]

    def get_inputs(self) -> list[YamlJunctionInput]:
        """Normalize inputs to objects, preserving declared priority order."""
        return [YamlJunctionInput(name=entry) if isinstance(entry, str) else entry for entry in self.input]

    @model_validator(mode="after")
    def check_dispatch_strategy_supported(self):
        # EQUAL_SPLIT is reserved in the schema but has no domain implementation yet.
        if self.dispatch_strategy == YamlDispatchStrategy.EQUAL_SPLIT:
            raise ValueError(f"'{self.name}': DISPATCH_STRATEGY {self.dispatch_strategy} is not supported yet.")
        return self

    @model_validator(mode="after")
    def check_no_duplicate_inputs(self):
        names = [junction_input.name for junction_input in self.get_inputs()]
        if len(names) != len(set(names)):
            duplicates = [ref for ref in names if names.count(ref) > 1]
            raise ValueError(f"'{self.name}': duplicate INPUT references: {set(duplicates)}")
        return self


class YamlElectricalBus(YamlJunctionBase):
    model_config = ConfigDict(title="ElectricalBus")

    type: Literal["ELECTRICAL_BUS"]


class YamlConsumerBase(YamlBase):
    name: Annotated[
        str,
        Field(
            title="NAME",
            description="Unique name for this component.",
        ),
    ]
    input: Annotated[
        str,
        Field(
            title="INPUT",
            description="Source or component this receives energy from.",
        ),
    ]


class YamlPowerCurve(YamlBase):
    model_config = ConfigDict(title="PowerCurve")

    variable: Annotated[
        list[float],
        Field(
            title="VARIABLE",
            description="Values of the variable the curve is keyed on, strictly increasing. In a FILE, "
            "this is whichever column isn't POWER.",
        ),
    ]
    power: Annotated[
        list[float],
        Field(
            title="POWER",
            description="Power [MW] for each VARIABLE value. In a FILE, this is the POWER column.",
        ),
    ]


class YamlLoadCurve(YamlBase):
    """Alternative to a direct LOAD expression: looks POWER up in a curve keyed on VARIABLE."""

    model_config = ConfigDict(
        title="LoadCurve",
        json_schema_extra={
            "examples": [
                {"CURVE": {"VARIABLE": [0, 1000, 5000], "POWER": [0, 0.8, 3.4]}, "VARIABLE": "SIM;RATE"},
                {"CURVE": {"FILE": "pump_sampled.csv"}, "VARIABLE": "SIM;RATE"},
            ],
        },
    )

    curve: Annotated[
        DataOrFile[YamlPowerCurve],
        Field(
            title="CURVE",
            description="Variable and power values, given directly or in a FILE with a POWER column and "
            "one other column for the variable.",
        ),
    ]
    variable: Annotated[
        YamlExpressionType,
        Field(
            title="VARIABLE",
            description="Value looked up in CURVE.",
        ),
    ]

    @model_validator(mode="after")
    def validate_inline_curve(self):
        if isinstance(self.curve, YamlPowerCurve):
            try:
                validate_curve_interpolator(self.curve.variable, self.curve.power)
            except EcalcValidationException as e:
                raise ValueError(str(e)) from e
        return self


class YamlFuelTable(YamlBase):
    model_config = ConfigDict(title="FuelTable")

    variable: Annotated[
        list[float],
        Field(
            title="VARIABLE",
            description="Values of the variable the curve is keyed on, strictly increasing. In a FILE, "
            "this is whichever column isn't FUEL.",
        ),
    ]
    fuel: Annotated[
        list[float],
        Field(
            title="FUEL",
            description="Consumption rate for each VARIABLE value. In a FILE, this is the FUEL column "
            "(matching the legacy TABULAR/TABULATED convention, so existing files can be reused as-is).",
        ),
    ]


class YamlRateCurve(YamlBase):
    """Alternative to a direct RATE expression: looks FUEL up in a curve keyed on VARIABLE."""

    model_config = ConfigDict(
        title="RateCurve",
        json_schema_extra={
            "examples": [
                {"CURVE": {"VARIABLE": [0, 1000, 5000], "FUEL": [0, 8000, 35000]}, "VARIABLE": "SIM;RATE"},
                {"CURVE": {"FILE": "flare_sampled.csv"}, "VARIABLE": "SIM;RATE"},
            ],
        },
    )

    curve: Annotated[
        DataOrFile[YamlFuelTable],
        Field(
            title="CURVE",
            description="Variable and fuel values, given directly or in a FILE with a FUEL column and "
            "one other column for the variable.",
        ),
    ]
    variable: Annotated[
        YamlExpressionType,
        Field(
            title="VARIABLE",
            description="Value looked up in CURVE.",
        ),
    ]

    @model_validator(mode="after")
    def validate_inline_curve(self):
        if isinstance(self.curve, YamlFuelTable):
            try:
                validate_curve_interpolator(self.curve.variable, self.curve.fuel)
            except EcalcValidationException as e:
                raise ValueError(str(e)) from e
        return self


class YamlElectricalConsumer(YamlConsumerBase):
    model_config = ConfigDict(title="ElectricalConsumer")

    type: Literal["ELECTRICAL_CONSUMER"]
    load: Annotated[
        YamlExpressionType | YamlLoadCurve,
        Field(
            title="LOAD",
            description="Electrical power demand (MW), as an expression or a curve lookup.",
        ),
    ]

    @field_validator("load", mode="after")
    @classmethod
    def _load_non_negative(cls, v: YamlExpressionType | YamlLoadCurve) -> YamlExpressionType | YamlLoadCurve:
        if isinstance(v, YamlLoadCurve):
            return v
        return _check_non_negative(v, "LOAD")


class YamlMechanicalConsumer(YamlConsumerBase):
    model_config = ConfigDict(title="MechanicalConsumer")

    type: Literal["MECHANICAL_CONSUMER"]
    load: Annotated[
        YamlExpressionType | YamlLoadCurve,
        Field(
            title="LOAD",
            description="Shaft power demand (MW), as an expression or a curve lookup.",
        ),
    ]

    @field_validator("load", mode="after")
    @classmethod
    def _load_non_negative(cls, v: YamlExpressionType | YamlLoadCurve) -> YamlExpressionType | YamlLoadCurve:
        if isinstance(v, YamlLoadCurve):
            return v
        return _check_non_negative(v, "LOAD")


class YamlCompressorMechanicalEfficiency(YamlBase):
    model_config = ConfigDict(title="CompressorMechanicalEfficiency")

    compressor: Annotated[
        CompressorReference,
        Field(
            title="COMPRESSOR",
            description="Reference to a compressor on the drive train's shaft.",
        ),
    ]
    efficiency: Annotated[
        YamlExpressionType,
        Field(
            title="EFFICIENCY",
            description=(
                "Mechanical efficiency (0–1] of the compressor: gas power divided by the shaft power it demands "
                "from the driver. Covers losses in the compressor's bearings and seals and its share of the gearbox "
                "and couplings, not the driver's own losses."
            ),
        ),
    ]

    @field_validator("efficiency", mode="after")
    @classmethod
    def _efficiency_in_range(cls, v: YamlExpressionType) -> YamlExpressionType:
        return _check_efficiency(v)


class YamlDriveTrain(YamlBase):
    type: Literal["DRIVE_TRAIN"]
    input: Annotated[
        str,
        Field(
            title="INPUT",
            description="Source or component this receives energy from.",
        ),
    ]
    shaft: Annotated[
        ShaftReference,
        Field(
            title="SHAFT",
            description="Reference to a shaft in SHAFTS. The compressors on the shaft determine shaft power demand.",
        ),
    ]
    mechanical_efficiencies: Annotated[
        list[YamlCompressorMechanicalEfficiency],
        Field(
            default_factory=list,
            title="MECHANICAL_EFFICIENCIES",
            description=(
                "Mechanical efficiency per compressor on the shaft. Each compressor demands its gas power "
                "divided by its efficiency as shaft power. A compressor not listed has efficiency 1.0."
            ),
        ),
    ]

    @field_validator("mechanical_efficiencies", mode="after")
    @classmethod
    def _unique_compressors(
        cls, mechanical_efficiencies: list[YamlCompressorMechanicalEfficiency]
    ) -> list[YamlCompressorMechanicalEfficiency]:
        duplicates = get_duplicates(entry.compressor for entry in mechanical_efficiencies)
        if duplicates:
            raise ValueError(
                f"MECHANICAL_EFFICIENCIES lists compressors more than once: {', '.join(sorted(duplicates))}. "
                f"Give one efficiency per compressor."
            )
        return mechanical_efficiencies


class YamlFuelGasConsumer(YamlConsumerBase):
    model_config = ConfigDict(title="FuelGasConsumer")

    type: Literal["FUEL_GAS_CONSUMER"]
    rate: Annotated[
        YamlExpressionType | YamlRateCurve,
        Field(
            title="RATE",
            description="Fuel gas consumption rate (Sm³/d), as an expression or a curve lookup.",
        ),
    ]

    @field_validator("rate", mode="after")
    @classmethod
    def _rate_non_negative(cls, v: YamlExpressionType | YamlRateCurve) -> YamlExpressionType | YamlRateCurve:
        if isinstance(v, YamlRateCurve):
            return v
        return _check_non_negative(v, "RATE")


class YamlDieselConsumer(YamlConsumerBase):
    model_config = ConfigDict(title="DieselConsumer")

    type: Literal["DIESEL_CONSUMER"]
    rate: Annotated[
        YamlExpressionType | YamlRateCurve,
        Field(
            title="RATE",
            description="Diesel consumption rate (l/d), as an expression or a curve lookup.",
        ),
    ]

    @field_validator("rate", mode="after")
    @classmethod
    def _rate_non_negative(cls, v: YamlExpressionType | YamlRateCurve) -> YamlExpressionType | YamlRateCurve:
        if isinstance(v, YamlRateCurve):
            return v
        return _check_non_negative(v, "RATE")


class YamlCompressorSampled(YamlBase):
    """
    A compressor whose mechanical power is looked up in `FILE` from `RATE`, `SUCTION_PRESSURE` and/or
    `DISCHARGE_PRESSURE`. `FILE` must have a `MECHANICAL_POWER` column [MW], and `INPUT` must provide mechanical
    power, e.g. a `GAS_TURBINE` or an `ELECTRICAL_MOTOR`.

    `FILE` must have a column for exactly those of `RATE`, `SUCTION_PRESSURE` and `DISCHARGE_PRESSURE` that are
    given.
    """

    model_config = ConfigDict(
        title="CompressorSampled",
    )

    type: Literal["COMPRESSOR_SAMPLED"]
    input: Annotated[
        str,
        Field(
            title="INPUT",
            description="Source or component this receives energy from.",
        ),
    ]
    compressor: Annotated[
        CompressorReference,
        Field(
            title="COMPRESSOR",
            description="Reference to a compressor defined in COMPRESSORS.",
        ),
    ]
    file: Annotated[
        str,
        Field(
            title="FILE",
            description="Resource with a MECHANICAL_POWER [MW] column, and a column for each of RATE, SUCTION_PRESSURE "
            "and DISCHARGE_PRESSURE that is given.",
        ),
    ]
    rate: Annotated[
        YamlExpressionType | None,
        Field(
            title="RATE",
            description="Rate through the compressor (Sm³/d), looked up in FILE.",
        ),
    ] = None
    suction_pressure: Annotated[
        YamlExpressionType | None,
        Field(
            title="SUCTION_PRESSURE",
            description="Compressor inlet pressure (bara), looked up in FILE.",
        ),
    ] = None
    discharge_pressure: Annotated[
        YamlExpressionType | None,
        Field(
            title="DISCHARGE_PRESSURE",
            description="Compressor outlet pressure (bara), looked up in FILE.",
        ),
    ] = None

    validate_file_exists = field_validator("file", mode="after")(file_exists_validator)

    @field_validator("rate", mode="after")
    @classmethod
    def _rate_non_negative(cls, v: YamlExpressionType | None) -> YamlExpressionType | None:
        return _check_non_negative(v, "RATE")

    @field_validator("suction_pressure", mode="after")
    @classmethod
    def _suction_pressure_non_negative(cls, v: YamlExpressionType | None) -> YamlExpressionType | None:
        return _check_non_negative(v, "SUCTION_PRESSURE")

    @field_validator("discharge_pressure", mode="after")
    @classmethod
    def _discharge_pressure_non_negative(cls, v: YamlExpressionType | None) -> YamlExpressionType | None:
        return _check_non_negative(v, "DISCHARGE_PRESSURE")

    @model_validator(mode="after")
    def check_at_least_one_variable(self):
        if self.rate is None and self.suction_pressure is None and self.discharge_pressure is None:
            raise ValueError(
                f"'{self.compressor}': at least one of RATE, SUCTION_PRESSURE or DISCHARGE_PRESSURE is required."
            )
        return self


YamlComponent = Annotated[
    Union[
        YamlGeneratorSet,
        YamlGasTurbine,
        YamlDieselEngine,
        YamlElectricalMotor,
        YamlElectricalCable,
        YamlElectricalBus,
        YamlElectricalConsumer,
        YamlMechanicalConsumer,
        YamlDriveTrain,
        YamlFuelGasConsumer,
        YamlDieselConsumer,
        YamlCompressorSampled,
    ],
    Field(discriminator="type"),
]


YamlNamedComponent = (
    YamlGeneratorSet
    | YamlGasTurbine
    | YamlDieselEngine
    | YamlElectricalMotor
    | YamlElectricalCable
    | YamlElectricalBus
    | YamlElectricalConsumer
    | YamlMechanicalConsumer
    | YamlFuelGasConsumer
    | YamlDieselConsumer
)


def get_named_units(units: list[YamlComponent]) -> list[YamlNamedComponent]:
    """The units with a NAME, i.e. all but COMPRESSOR_SAMPLED and DRIVE_TRAIN."""
    return [unit for unit in units if isinstance(unit, YamlNamedComponent)]


class EnergyType(StrEnum):
    FUEL_GAS = "FUEL_GAS"
    ELECTRICAL = "ELECTRICAL"
    MECHANICAL = "MECHANICAL"
    DIESEL = "DIESEL"


INPUT_ENERGY: dict[str, EnergyType] = {
    "GAS_TURBINE": EnergyType.FUEL_GAS,
    "DIESEL_ENGINE": EnergyType.DIESEL,
    "ELECTRICAL_MOTOR": EnergyType.ELECTRICAL,
    "ELECTRICAL_CABLE": EnergyType.ELECTRICAL,
    "ELECTRICAL_BUS": EnergyType.ELECTRICAL,
    "ELECTRICAL_CONSUMER": EnergyType.ELECTRICAL,
    "MECHANICAL_CONSUMER": EnergyType.MECHANICAL,
    "DRIVE_TRAIN": EnergyType.MECHANICAL,
    "COMPRESSOR_SAMPLED": EnergyType.MECHANICAL,
    "FUEL_GAS_CONSUMER": EnergyType.FUEL_GAS,
    "DIESEL_CONSUMER": EnergyType.DIESEL,
}

# Allowed input types for a curve-based GENERATOR_SET; the actual type is inferred from its connected source.
GENERATOR_SET_INPUT_ENERGY = {EnergyType.FUEL_GAS, EnergyType.DIESEL}


def _generator_set_model_energy_type(model: YamlGeneratorSetModel) -> EnergyType | None:
    """The fuel energy type required by a generator set's engine model, or None for a curve/reference model that
    is not tied to a specific engine and instead follows its connected source."""
    if isinstance(model, YamlGeneratorSetEngineDefinition):
        return EnergyType.FUEL_GAS if model.type == "GAS_TURBINE_DRIVEN" else EnergyType.DIESEL
    return None


def _generator_set_allowed_inputs(unit: YamlGeneratorSet) -> set[EnergyType]:
    """The energy types a GENERATOR(_SET) may draw from, constrained by its MODEL and any CHANGES.CHANGE_TO engine
    model: a GAS_TURBINE_DRIVEN model requires FUEL_GAS, a DIESEL_ENGINE_DRIVEN model requires DIESEL, and a
    curve-based model is unconstrained (inferred from the connected source). The legacy GENERATOR has no CHANGES
    and is always curve-based."""
    changes = unit.changes if isinstance(unit, YamlGeneratorSet) else []
    required_types = {
        energy_type
        for energy_type in (
            _generator_set_model_energy_type(model) for model in (unit.model, *(c.change_to for c in changes))
        )
        if energy_type is not None
    }
    if len(required_types) > 1:
        raise ValueError(
            f"{get_unit_label(unit)}: its MODEL and CHANGES require incompatible engine fuel types "
            f"{sorted(t.value for t in required_types)}. A GENERATOR_SET's INPUT must match the fuel type of "
            "every GAS_TURBINE_DRIVEN/DIESEL_ENGINE_DRIVEN model used over its lifetime."
        )
    return required_types or GENERATOR_SET_INPUT_ENERGY


OUTPUT_ENERGY: dict[str, EnergyType] = {
    "GENERATOR_SET": EnergyType.ELECTRICAL,
    "GAS_TURBINE": EnergyType.MECHANICAL,
    "DIESEL_ENGINE": EnergyType.MECHANICAL,
    "ELECTRICAL_MOTOR": EnergyType.MECHANICAL,
    "ELECTRICAL_CABLE": EnergyType.ELECTRICAL,
    "ELECTRICAL_BUS": EnergyType.ELECTRICAL,
}

SOURCE_OUTPUT_ENERGY: dict[YamlEnergySourceType, EnergyType] = {
    YamlEnergySourceType.FUEL_GAS_SOURCE: EnergyType.FUEL_GAS,
    YamlEnergySourceType.DIESEL_SOURCE: EnergyType.DIESEL,
    YamlEnergySourceType.ELECTRICAL_SOURCE: EnergyType.ELECTRICAL,
}

CONSUMER_TYPES = set(INPUT_ENERGY) - set(OUTPUT_ENERGY)


def get_unit_label(component: YamlComponent) -> str:
    """Human-readable identification of a unit, for units without a NAME too."""
    match component:
        case YamlCompressorSampled():
            return f"COMPRESSOR_SAMPLED '{component.compressor}'"
        case YamlDriveTrain():
            return f"DRIVE_TRAIN for shaft '{component.shaft}'"
        case _:
            return f"'{component.name}'"


def get_input_names(component: YamlComponent) -> list[str]:
    """Return input names in declared order."""
    if isinstance(component, YamlJunctionBase):
        return [junction_input.name for junction_input in component.get_inputs()]
    return [component.input]


class LowerHeatingValueLookup:
    """Looks up a fuel/diesel source's lower heating value by name, resolved once from the network's sources."""

    def __init__(self, sources: list[YamlEnergySource]) -> None:
        self._by_source_name: dict[str, float] = {
            source.name: source.lower_heating_value
            for source in sources
            if isinstance(source, YamlFuelSourceBase) and source.lower_heating_value is not None
        }

    def for_source(self, source_name: str) -> float | None:
        """The source's lower heating value, or None if it has none set."""
        return self._by_source_name.get(source_name)


def _requires_lower_heating_value(
    unit: YamlComponent,
) -> TypeGuard[YamlGasTurbine | YamlDieselEngine | YamlGeneratorSet]:
    """A GAS_TURBINE/DIESEL_ENGINE always needs a LOWER_HEATING_VALUE; a GENERATOR_SET only when its MODEL or
    CHANGES.CHANGE_TO is an engine-driven model, since a curve-based model is not tied to a specific fuel."""
    if isinstance(unit, (YamlGasTurbine, YamlDieselEngine)):
        return True
    if isinstance(unit, YamlGeneratorSet):
        return any(
            _generator_set_model_energy_type(model) is not None
            for model in (unit.model, *(ch.change_to for ch in unit.changes))
        )
    return False


class YamlEnergyNetwork(YamlBase):
    model_config = ConfigDict(title="EnergyNetwork")

    sources: Annotated[
        list[YamlEnergySource],
        Field(
            min_length=1,
            title="SOURCES",
            description="External energy entering the system (fuel gas, electrical, diesel).",
        ),
    ]
    units: Annotated[
        list[YamlComponent],
        Field(
            title="UNITS",
            description="Converters, junctions, and consumers forming the energy network.",
        ),
    ] = []

    def _named_units(self) -> list[YamlNamedComponent]:
        return get_named_units(self.units)

    def _all_names(self) -> list[str]:
        return (
            [s.name for s in self.sources]
            + [c.name for c in self._named_units()]
            + [c.compressor for c in self.units if isinstance(c, YamlCompressorSampled)]
        )

    def _valid_input_names(self) -> set[str]:
        names = {s.name for s in self.sources}
        names.update(c.name for c in self._named_units() if c.type not in CONSUMER_TYPES)
        return names

    @model_validator(mode="after")
    def check_unique_names(self):
        duplicates = get_duplicates(self._all_names())
        if duplicates:
            raise ValueError(
                f"Duplicate names: {set(duplicates)}. A COMPRESSOR_SAMPLED unit is named by its COMPRESSOR, which "
                f"must differ from the names of sources and units."
            )
        return self

    @model_validator(mode="after")
    def check_input_references(self):
        valid = self._valid_input_names()
        for c in self.units:
            for ref in get_input_names(c):
                if ref not in valid:
                    raise ValueError(f"{get_unit_label(c)} has INPUT '{ref}' which is not a known source or provider.")
        return self

    @model_validator(mode="after")
    def check_no_cycles(self):
        from graphlib import CycleError, TopologicalSorter

        graph: dict[str, set[str]] = {c.name: set(get_input_names(c)) for c in self._named_units()}
        try:
            tuple(TopologicalSorter(graph).static_order())
        except CycleError as e:
            raise ValueError(f"Cycle detected in energy network: {e}") from None
        return self

    @model_validator(mode="after")
    def check_combustion_engine_lower_heating_value(self):
        lhv_lookup = LowerHeatingValueLookup(self.sources)
        for c in self.units:
            if not _requires_lower_heating_value(c):
                continue
            if lhv_lookup.for_source(c.input) is None:
                raise ValueError(
                    f"'{c.name}': could not resolve a LOWER_HEATING_VALUE from '{c.input}'. Set it on the "
                    "fuel/diesel source this unit draws from."
                )
        return self

    @model_validator(mode="after")
    def check_energy_type_compatibility(self):
        output_types: dict[str, EnergyType] = {}
        for s in self.sources:
            output_types[s.name] = SOURCE_OUTPUT_ENERGY[s.type]
        for c in self._named_units():
            if c.type in OUTPUT_ENERGY:
                output_types[c.name] = OUTPUT_ENERGY[c.type]

        for c in self.units:
            if isinstance(c, YamlGeneratorSet):
                allowed_inputs = _generator_set_allowed_inputs(c)
            else:
                if c.type not in INPUT_ENERGY:
                    raise ValueError(
                        f"{get_unit_label(c)}: unknown component type '{c.type}' — not in energy type map."
                    )
                allowed_inputs = {INPUT_ENERGY[c.type]}
            for ref in get_input_names(c):
                provided = output_types.get(ref)
                if provided is not None and provided not in allowed_inputs:
                    expected = (
                        next(iter(allowed_inputs)).value
                        if len(allowed_inputs) == 1
                        else f"one of {sorted(t.value for t in allowed_inputs)}"
                    )
                    raise ValueError(
                        f"{get_unit_label(c)} ({c.type}) expects {expected} input, but '{ref}' provides {provided}."
                    )
        return self
