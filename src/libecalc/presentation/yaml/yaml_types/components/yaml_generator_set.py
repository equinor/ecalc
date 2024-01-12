from typing import List, Union

try:
    from pydantic.v1 import Field
except ImportError:
    from pydantic import Field

from libecalc.dto.base import ConsumerUserDefinedCategoryType
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.legacy.yaml_electricity_consumer import (
    YamlElectricityConsumer,
)
from libecalc.presentation.yaml.yaml_types.components.system.yaml_consumer_system import (
    YamlConsumerSystem,
)
from libecalc.presentation.yaml.yaml_types.components.train.yaml_train import YamlTrain
from libecalc.presentation.yaml.yaml_types.components.yaml_category_field import (
    CategoryField,
)
from libecalc.presentation.yaml.yaml_types.components.yaml_compressor import (
    YamlCompressor,
)
from libecalc.presentation.yaml.yaml_types.components.yaml_pump import YamlPump
from libecalc.presentation.yaml.yaml_types.yaml_temporal_model import YamlTemporalModel


class YamlGeneratorSet(YamlBase):
    class Config:
        title = "GeneratorSet"

    name: str = Field(
        ...,
        title="NAME",
        description="Name of the generator set.\n\n$ECALC_DOCS_KEYWORDS_URL/NAME",
    )
    category: YamlTemporalModel[ConsumerUserDefinedCategoryType] = CategoryField(...)
    fuel: YamlTemporalModel[str] = Field(
        None,
        title="FUEL",
        description="The fuel used by the generator set." "\n\n$ECALC_DOCS_KEYWORDS_URL/FUEL",
    )
    electricity2fuel: YamlTemporalModel[str] = Field(
        ...,
        title="ELECTRICITY2FUEL",
        description="Specifies the correlation between the electric power delivered and the fuel burned by a "
        "generator set.\n\n$ECALC_DOCS_KEYWORDS_URL/ELECTRICITY2FUEL",
    )
    consumers: List[
        Union[
            YamlElectricityConsumer,
            YamlConsumerSystem[YamlCompressor],
            YamlConsumerSystem[YamlPump],
            YamlConsumerSystem[YamlTrain[YamlCompressor]],
        ]
    ] = Field(
        ...,
        title="CONSUMERS",
        description="Consumers getting electrical power from the generator set.\n\n$ECALC_DOCS_KEYWORDS_URL/CONSUMERS",
    )
