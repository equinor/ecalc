from collections.abc import Hashable, Iterable
from typing import TypeVar

TItem = TypeVar("TItem", bound=Hashable)


def get_duplicates(names: Iterable[TItem]) -> set[TItem]:
    seen = set()
    duplicates = set()
    for name in names:
        if name in seen:
            duplicates.add(name)
        else:
            seen.add(name)
    return duplicates


def generate_id(*args: str) -> str:
    """
    Deprecated: When names were not unique, this was necessary in order to make names unique based on context/hierarchy. Now names should
    be unique for any part of the eCalc model that supports names, and it should therefore not be needed any more.

    TODO: First step is to make the function return the string as normal, next step is to remove it altogether.

    Generate an id from one or more strings. The string is encoded to avoid it being used to get other info than
    the id, i.e. it should not be used to get the name of a consumer, even if the name might be used to create the id.

    If there are many strings they are joined together.
    """
    return "-".join(args)


def to_camel_case(string: str) -> str:
    """Convert string from snake_case to camelCase

    Args:
        string: String in snake_case format

    Returns:
        String in camelCase format

    """
    string_split = string.replace("__", "_").split("_")
    string_split = [word for word in string_split if len(word) > 0]  # Allow names such as 'from_'
    return string_split[0] + "".join(word[0].upper() + word[1:] for word in string_split[1:])
