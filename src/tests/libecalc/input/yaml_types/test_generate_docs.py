import typing
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Type, Union

from libecalc.presentation.yaml.yaml_types.components.yaml_asset import YamlAsset
from pydantic import BaseModel
from pydantic.fields import FieldInfo


@dataclass
class KeywordInfo:
    field: FieldInfo


def handle_type(annotation: Union[Type[Any], None], keywords: Dict[str, List[KeywordInfo]]):
    if hasattr(annotation, "__args__"):
        for sub_type in annotation.__args__:
            handle_type(sub_type, keywords)

    if hasattr(annotation, "__mro__"):
        if BaseModel in annotation.__mro__:
            handle_base_model(annotation, keywords)


def handle_base_model(cls: Type[BaseModel], keywords: Dict[str, List[KeywordInfo]]):
    for field_name, field in cls.model_fields.items():
        title = field.title or field.alias or field_name
        keywords[title].append(
            KeywordInfo(
                field=field,
            )
        )
        handle_type(field.annotation, keywords)


def test_generate_docs():
    """
    Successfully collects keywords and stores the FieldInfo
    TODO:
        - generate format (see docs) with json schema
        - add examples to the classes/fields and generate markdown examples (see docs for examples)
        -
    Returns:

    """
    keywords = defaultdict(list)
    handle_base_model(YamlAsset, keywords=keywords)
    sorted(keywords)
    typing.get_origin(keywords["TIME_SERIES"][0].field.annotation.__args__[0])
    typing.get_args(keywords["TIME_SERIES"][0].field.annotation.__args__[0])
    print(keywords)
