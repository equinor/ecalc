import hashlib
from typing import Iterable, Set


def get_duplicates(names: Iterable[str]) -> Set[str]:
    seen = set()
    duplicates = set()
    for name in names:
        if name in seen:
            duplicates.add(name)
        else:
            seen.add(name)
    return duplicates


def generate_id(*args: str) -> str:
    """Generate an id from one or more strings. The string is encoded to avoid it being used to get other info than
    the id, i.e. it should not be used to get the name of a consumer, even if the name might be used to create the id.

    If there are many strings they are joined together.
    """
    full_string = "-".join(args)
    return hashlib.md5(full_string.encode()).hexdigest()  # noqa: S324 - insecure hash for ids


def to_camel_case(string: str) -> str:
    """Convert string from snake_case to camelCase

    Args:
        string: String in snake_case format

    Returns:
        String in camelCase format

    """
    string_split = string.replace("__", "_").split("_")
    return string_split[0] + "".join(word[0].upper() + word[1:] for word in string_split[1:])
