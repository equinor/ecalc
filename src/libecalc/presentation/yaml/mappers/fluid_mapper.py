from typing import Any, Dict

from libecalc import dto
from libecalc.common.logger import logger
from libecalc.presentation.yaml.yaml_entities import Resources
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords

"""
Some "standard" predefined compositions to choose from
notation ..._MW_XXPXX means molecular weight xx.x g/mol
The lower molecular weight, the dryer the gas is, thus the naming Ultra dry, dry, medium, rich, ultra rich
used for increasing molecular weight.
"""


ULTRA_DRY_MW_17P1 = dto.FluidComposition(
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
DRY_MW_18P3 = dto.FluidComposition(
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
MEDIUM_MW_19P4 = dto.FluidComposition(
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
RICH_MW_21P4 = dto.FluidComposition(
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
ULTRA_RICH_MW_24P6 = dto.FluidComposition(
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
    EcalcYamlKeywords.models_type_fluid_eos_model_pr: dto.types.EoSModel.PR,
    EcalcYamlKeywords.models_type_fluid_eos_model_srk: dto.types.EoSModel.SRK,
    EcalcYamlKeywords.models_type_fluid_eos_model_gerg_pr: dto.types.EoSModel.GERG_PR,
    EcalcYamlKeywords.models_type_fluid_eos_model_gerg_srk: dto.types.EoSModel.GERG_SRK,
}


def fluid_model_mapper(model_config: Dict, input_models: Dict[str, Any], resources: Resources):
    fluid_model_type = model_config.get(EcalcYamlKeywords.models_type_fluid_model_type)
    mapper = _fluid_model_map.get(fluid_model_type)
    if mapper is None:
        raise ValueError(f"Fluid model type {fluid_model_type} not supported")
    return mapper(model_config=model_config)


def _predefined_fluid_model_mapper(model_config: Dict) -> dto.FluidModel:
    predefined_composition_type = model_config.get(EcalcYamlKeywords.models_type_fluid_predefined_gas_type)
    eos_model_type = model_config.get(EcalcYamlKeywords.models_type_fluid_eos_model)
    return dto.FluidModel(
        eos_model=_eos_model_mapper.get(eos_model_type),
        composition=_predefined_fluid_composition_mapper.get(predefined_composition_type),
    )


def _composition_fluid_model_mapper(
    model_config: Dict,
) -> dto.FluidModel:
    user_defined_composition = model_config.get(EcalcYamlKeywords.composition)
    if user_defined_composition is None:
        raise ValueError("User defined composition not found in Yaml keywords")
    if EcalcYamlKeywords.composition_H2O in user_defined_composition:
        """
        This is a work to allow both H2O and water to be specified as fluid definition
        """

        # Fixme: Remove in version 9
        logger.warning(
            "DeprecationWarning: H2O is deprecated as fluid composition. Use 'water' instead. "
            "Will be removed in the next version."
        )
        if EcalcYamlKeywords.composition_water in user_defined_composition:
            user_defined_composition[EcalcYamlKeywords.composition_water] += user_defined_composition[
                EcalcYamlKeywords.composition_H2O
            ]
        else:
            user_defined_composition[EcalcYamlKeywords.composition_water] = user_defined_composition[
                EcalcYamlKeywords.composition_H2O
            ]
        del user_defined_composition[
            EcalcYamlKeywords.composition_H2O
        ]  # Need to remove this in order to put it into the DTO
    eos_model_type = model_config.get(EcalcYamlKeywords.models_type_fluid_eos_model)
    return dto.FluidModel(
        eos_model=_eos_model_mapper.get(eos_model_type),
        composition=user_defined_composition,
    )


_fluid_model_map = {
    EcalcYamlKeywords.models_type_compressor_train_chart_predefined: _predefined_fluid_model_mapper,
    EcalcYamlKeywords.composition: _composition_fluid_model_mapper,
}
