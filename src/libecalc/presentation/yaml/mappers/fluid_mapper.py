from typing import Any

from libecalc.common.fluid import EoSModel, FluidComposition, FluidModel
from libecalc.domain.resource import Resources
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords
from libecalc.presentation.yaml.yaml_types.models import YamlFluidModel
from libecalc.presentation.yaml.yaml_types.models.yaml_fluid import YamlCompositionFluidModel, YamlPredefinedFluidModel

"""
Some "standard" predefined compositions to choose from
notation ..._MW_XXPXX means molecular weight xx.x g/mol
The lower molecular weight, the dryer the gas is, thus the naming Ultra dry, dry, medium, rich, ultra rich
used for increasing molecular weight.
"""

ULTRA_DRY_MW_17P1 = FluidComposition(
    nitrogen=1.140841432,
    CO2=0.607605069,
    methane=94.90924895,
    ethane=2.480677384,
    propane=0.319357855,
    i_butane=0.154760057,
    n_butane=0.081099138,
    i_pentane=0.074745555,
    n_pentane=0.033999676,
    n_hexane=0.197664882,
)
DRY_MW_18P3 = FluidComposition(
    nitrogen=1.6545,
    CO2=0.8396,
    methane=89.3891,
    ethane=5.101,
    propane=1.7083,
    i_butane=0.4718,
    n_butane=0.385,
    i_pentane=0.1155,
    n_pentane=0.0793,
    n_hexane=0.2559,
)
MEDIUM_MW_19P4 = FluidComposition(
    nitrogen=0.74373,
    CO2=2.415619,
    methane=85.60145,
    ethane=6.707826,
    propane=2.611471,
    i_butane=0.45077,
    n_butane=0.691702,
    i_pentane=0.210714,
    n_pentane=0.197937,
    n_hexane=0.368786,
)
RICH_MW_21P4 = FluidComposition(
    nitrogen=0.682785869,
    CO2=2.466921329,
    methane=79.57192993,
    ethane=5.153816223,
    propane=9.679747581,
    i_butane=0.691399336,
    n_butane=1.174334645,
    i_pentane=0.208390206,
    n_pentane=0.201853022,
    n_hexane=0.16881974,
)
ULTRA_RICH_MW_24P6 = FluidComposition(
    nitrogen=3.433045573,
    CO2=0.341296928,
    methane=62.50752861,
    ethane=15.64946798,
    propane=13.2202369,
    i_butane=1.606103192,
    n_butane=2.479421803,
    i_pentane=0.351335073,
    n_pentane=0.291106204,
    n_hexane=0.120457739,
)

_predefined_fluid_composition_mapper = {
    EcalcYamlKeywords.models_type_fluid_predefined_gas_type_dry: DRY_MW_18P3,
    EcalcYamlKeywords.models_type_fluid_predefined_gas_ultra_dry: ULTRA_DRY_MW_17P1,
    EcalcYamlKeywords.models_type_fluid_predefined_gas_type_medium: MEDIUM_MW_19P4,
    EcalcYamlKeywords.models_type_fluid_predefined_gas_type_rich: RICH_MW_21P4,
    EcalcYamlKeywords.models_type_fluid_predefined_gas_ultra_rich: ULTRA_RICH_MW_24P6,
}

_eos_model_mapper = {
    EcalcYamlKeywords.models_type_fluid_eos_model_pr: EoSModel.PR,
    EcalcYamlKeywords.models_type_fluid_eos_model_srk: EoSModel.SRK,
    EcalcYamlKeywords.models_type_fluid_eos_model_gerg_pr: EoSModel.GERG_PR,
    EcalcYamlKeywords.models_type_fluid_eos_model_gerg_srk: EoSModel.GERG_SRK,
}


def fluid_model_mapper(model_config: YamlFluidModel, input_models: dict[str, Any], resources: Resources):
    fluid_model_type = model_config.fluid_model_type
    mapper = _fluid_model_map.get(fluid_model_type)
    if mapper is None:
        raise ValueError(f"Fluid model type {fluid_model_type} not supported")
    return mapper(model_config=model_config)


def _predefined_fluid_model_mapper(model_config: YamlPredefinedFluidModel) -> FluidModel:
    predefined_composition_type = model_config.gas_type
    eos_model_type = model_config.eos_model
    return FluidModel(
        eos_model=_eos_model_mapper.get(eos_model_type),
        composition=_predefined_fluid_composition_mapper.get(predefined_composition_type),
    )


def _composition_fluid_model_mapper(
    model_config: YamlCompositionFluidModel,
) -> FluidModel:
    user_defined_composition = model_config.composition
    if user_defined_composition is None:
        raise ValueError("User defined composition not found in Yaml keywords")
    eos_model_type = model_config.eos_model
    return FluidModel(
        eos_model=_eos_model_mapper.get(eos_model_type),
        composition=FluidComposition(
            water=user_defined_composition.water,
            nitrogen=user_defined_composition.nitrogen,
            CO2=user_defined_composition.CO2,
            methane=user_defined_composition.methane,
            ethane=user_defined_composition.ethane,
            propane=user_defined_composition.propane,
            i_butane=user_defined_composition.i_butane,
            n_butane=user_defined_composition.n_butane,
            i_pentane=user_defined_composition.i_pentane,
            n_pentane=user_defined_composition.n_pentane,
            n_hexane=user_defined_composition.n_hexane,
        ),
    )


_fluid_model_map = {
    EcalcYamlKeywords.models_type_compressor_train_chart_predefined: _predefined_fluid_model_mapper,
    EcalcYamlKeywords.composition: _composition_fluid_model_mapper,
}
